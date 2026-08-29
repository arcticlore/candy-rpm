// Command check verifies upstream versions and submits builds to COPR.
//
// It replaces update-check.sh + api_ver.sh with a single Go binary.
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/arcticlore/candy-rpm/internal/copr"
	metapkg "github.com/arcticlore/candy-rpm/internal/pkg"
	"github.com/arcticlore/candy-rpm/internal/state"
)

const (
	cooldownSec    = 1800 // 30 minutes
	httpTimeout    = 10 * time.Second
	coprAPITimeout = 30 * time.Second
)

func main() {
	var (
		force   = flag.Bool("force", false, "Force rebuild even if version unchanged")
		dryRun  = flag.Bool("dry-run", false, "Print what would be done without doing it")
		filters = flag.String("filter", "", "Comma-separated package names to process")
		owner   = flag.String("owner", "arcticlore", "COPR owner")
		project = flag.String("project", "candy", "COPR project")
		rootDir = flag.String("root", "", "Project root directory")
		skipEco = flag.String("skip-eco", "", "Comma-separated ecosystems to skip")
		workers = flag.Int("shard-count", 1, "Total number of shards")
		shardID = flag.Int("shard-id", 0, "This shard's ID (0-based)")
		_       = flag.Bool("v", false, "Verbose output") // Reserved for future use
	)
	flag.Parse()

	if *rootDir == "" {
		exe, err := os.Executable()
		if err == nil {
			*rootDir = filepath.Dir(filepath.Dir(exe))
		} else {
			*rootDir = "."
		}
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	logger := log.New(os.Stderr, "", log.LstdFlags)

	// Load package metadata
	pkgsPath := filepath.Join(*rootDir, "pkgs.json")
	pkgsFile, err := metapkg.Load(pkgsPath)
	if err != nil {
		logger.Fatalf("load pkgs.json: %v", err)
	}

	// Load state
	statePath := filepath.Join(*rootDir, "state", "state.json")
	st, err := state.New(statePath)
	if err != nil {
		logger.Fatalf("load state: %v", err)
	}

	// Load COPR build states
	coprClient := copr.NewClient(*owner, *project)
	builds, err := coprClient.ListBuilds(ctx, 200)
	if err != nil {
		logger.Printf("warning: failed to fetch COPR builds: %v", err)
		builds = nil
	}
	latest := copr.LatestByPackage(builds)

	// Load chroot plan if available
	chrootPlan := loadChrootPlan(filepath.Join(*rootDir, "logs", "chroot-plan.json"))

	// Parse filters
	filterSet := make(map[string]bool)
	if *filters != "" {
		for _, f := range strings.Split(*filters, ",") {
			filterSet[strings.TrimSpace(f)] = true
		}
	}

	skipEcoSet := make(map[string]bool)
	if *skipEco != "" {
		for _, e := range strings.Split(*skipEco, ",") {
			skipEcoSet[strings.TrimSpace(e)] = true
		}
	}

	// Process packages
	changed := 0
	failed := 0
	skipped := 0

	for _, name := range pkgsFile.Enabled(*skipEco, *shardID, *workers) {
		// Apply filters
		if len(filterSet) > 0 && !filterSet[name] {
			continue
		}

		meta := pkgsFile.ByName()[name]
		if meta == nil {
			continue
		}

		if skipEcoSet[meta.Eco] {
			continue
		}

		// Get current and new version
		oldEntry, _ := st.Get(name)
		oldVer := oldEntry.Ver

		newVer, err := getUpstreamVersion(ctx, meta)
		if err != nil {
			logger.Printf("[WARN] %s: version unavailable: %v", name, err)
			skipped++
			continue
		}

		if newVer == "" {
			logger.Printf("[WARN] %s: empty version", name)
			skipped++
			continue
		}

		// Check COPR build state
		lastState := ""
		if b, ok := latest[name]; ok {
			lastState = b.State
		}

		// Succeeded — skip
		if lastState == "succeeded" {
			logger.Printf("[SKIP] %s: already built (succeeded)", name)
			st.Set(name, newVer, true)
			continue
		}

		// Running/starting/pending/importing — wait
		if lastState == "running" || lastState == "starting" ||
			lastState == "pending" || lastState == "importing" {
			logger.Printf("[SKIP] %s: build in progress (%s)", name, lastState)
			continue
		}

		// Version unchanged and not force
		if newVer == oldVer && !*force {
			// Failed or no cache — retry with cooldown
			if lastState == "failed" || lastState == "" {
				if st.IsLocked(name) {
					continue
				}

				lastTs := st.Timestamp(name)
				now := float64(time.Now().Unix())

				if lastTs > 0 && now-lastTs < cooldownSec {
					remaining := int((cooldownSec - now + lastTs) / 60)
					logger.Printf("[SKIP] %s: failed/new, cooldown %d min", name, remaining)
					continue
				}

				if lastState == "" {
					logger.Printf("[SUBMIT] %s: no COPR cache — submitting", name)
				} else {
					logger.Printf("[RETRY] %s: failed, cooldown passed — rebuilding", name)
				}
			} else {
				continue
			}
		}

		if *dryRun {
			logger.Printf("[DRY] %s: %s -> %s", name, oldVer, newVer)
			changed++
			continue
		}

		// Build SRPM
		logger.Printf("[UPD] %s: %s -> %s — building SRPM...", name, oldVer, newVer)
		if err := buildSRPM(ctx, *rootDir, name, newVer); err != nil {
			logger.Printf("[FAIL] %s: SRPM build failed: %v", name, err)
			failed++
			continue
		}

		// Find SRPM file
		srpm, err := findSRPM(*rootDir, name, newVer)
		if err != nil {
			logger.Printf("[FAIL] %s: %v", name, err)
			failed++
			continue
		}

		// Submit to COPR
		if err := submitCOPR(ctx, *project, srpm, chrootPlan, name); err != nil {
			logger.Printf("[FAIL] %s: COPR submit failed: %v", name, err)
			failed++
			continue
		}

		st.Set(name, newVer, false)
		changed++
		time.Sleep(1 * time.Second) // Rate limit
	}

	logger.Printf("[ИТОГ] updated/built: %d, errors: %d, skipped: %d", changed, failed, skipped)
	os.Exit(failed)
}

func getUpstreamVersion(ctx context.Context, meta *metapkg.Package) (string, error) {
	var url string

	switch meta.Host {
	case "github":
		// Try releases first, then tags
		url = fmt.Sprintf("https://api.github.com/repos/%s/releases/latest", meta.Slug)
	case "codeberg":
		url = fmt.Sprintf("https://codeberg.org/api/v1/repos/%s/tags?limit=1", meta.Slug)
	case "gitlab":
		slug := strings.ReplaceAll(meta.Slug, "/", "%2F")
		url = fmt.Sprintf("https://gitlab.com/api/v4/projects/%s/releases", slug)
	case "npm":
		pkgName := meta.Pkg
		if pkgName == "" {
			pkgName = meta.Name
		}
		url = fmt.Sprintf("https://registry.npmjs.org/%s/latest", pkgName)
	case "pypi":
		pkgName := meta.Pkg
		if pkgName == "" {
			pkgName = meta.Name
		}
		url = fmt.Sprintf("https://pypi.org/pypi/%s/json", pkgName)
	case "web":
		return meta.URL, nil
	default:
		return "", fmt.Errorf("unknown host: %s", meta.Host)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return "", err
	}

	// Add GitHub token if available
	if meta.Host == "github" {
		if token := os.Getenv("GITHUB_TOKEN"); token != "" {
			req.Header.Set("Authorization", "Bearer "+token)
		}
	}

	httpClient := &http.Client{Timeout: httpTimeout}
	resp, err := httpClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	var tag string

	switch meta.Host {
	case "github":
		var release struct {
			TagName string `json:"tag_name"`
		}
		if err := json.Unmarshal(body, &release); err == nil && release.TagName != "" {
			tag = release.TagName
		} else {
			// Try tags
			var tags []struct {
				Name string `json:"name"`
			}
			if err := json.Unmarshal(body, &tags); err == nil && len(tags) > 0 {
				tag = tags[0].Name
			}
		}
	case "codeberg":
		var tags []struct {
			Name string `json:"name"`
		}
		if err := json.Unmarshal(body, &tags); err == nil && len(tags) > 0 {
			tag = tags[0].Name
		}
	case "gitlab":
		var releases []struct {
			TagName string `json:"tag_name"`
		}
		if err := json.Unmarshal(body, &releases); err == nil && len(releases) > 0 {
			tag = releases[0].TagName
		}
	case "npm":
		var pkgInfo struct {
			Version string `json:"version"`
		}
		if err := json.Unmarshal(body, &pkgInfo); err == nil {
			tag = pkgInfo.Version
		}
	case "pypi":
		var pkgInfo struct {
			Info struct {
				Version string `json:"version"`
			} `json:"info"`
		}
		if err := json.Unmarshal(body, &pkgInfo); err == nil {
			tag = pkgInfo.Info.Version
		}
	}

	// Strip tag prefix
	if meta.TagP != "" && strings.HasPrefix(tag, meta.TagP) {
		tag = strings.TrimPrefix(tag, meta.TagP)
	}
	tag = strings.TrimPrefix(tag, "v")

	// Sanitize for RPM version
	tag = sanitizeRPMVersion(tag)

	return tag, nil
}

func sanitizeRPMVersion(s string) string {
	// Replace - with ~ (valid in RPM)
	s = strings.ReplaceAll(s, "-", "~")
	// Keep only valid RPM version characters
	var b strings.Builder
	for _, c := range s {
		if (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') ||
			c == '.' || c == '~' || c == '+' {
			b.WriteRune(c)
		}
	}
	return b.String()
}

func buildSRPM(ctx context.Context, root, name, ver string) error {
	script := filepath.Join(root, "bin", "make-srpm.sh")
	cmd := exec.CommandContext(ctx, script, name, ver)
	cmd.Dir = root
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func findSRPM(root, name, ver string) (string, error) {
	srpmsDir := filepath.Join(root, "SRPMS")
	pattern := filepath.Join(srpmsDir, name+"-"+ver+"-*.src.rpm")

	matches, err := filepath.Glob(pattern)
	if err != nil {
		return "", fmt.Errorf("glob SRPM: %w", err)
	}

	if len(matches) == 0 {
		return "", fmt.Errorf("SRPM not found for %s-%s", name, ver)
	}

	// Return most recent
	var newest string
	var newestTime time.Time
	for _, m := range matches {
		info, err := os.Stat(m)
		if err != nil {
			continue
		}
		if newest == "" || info.ModTime().After(newestTime) {
			newest = m
			newestTime = info.ModTime()
		}
	}

	return newest, nil
}

func submitCOPR(ctx context.Context, project, srpm string, chrootPlan map[string][]string, name string) error {
	args := []string{"build", project, srpm, "--nowait"}

	// Add specific chroots if in plan
	if chroots, ok := chrootPlan[name]; ok && len(chroots) > 0 {
		for _, c := range chroots {
			args = append(args, "-r", c)
		}
	}

	cmd := exec.CommandContext(ctx, "copr-cli", args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func loadChrootPlan(path string) map[string][]string {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil
	}

	var plan struct {
		Plan map[string][]string `json:"plan"`
	}
	if err := json.Unmarshal(data, &plan); err != nil {
		return nil
	}

	return plan.Plan
}
