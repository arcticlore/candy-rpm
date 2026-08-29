// Command engine checks COPR build status per chroot.
//
// It queries the COPR API for build results and determines which chroots
// need rebuilding. Output is written to logs/chroot-plan.json.
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
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/arcticlore/candy-rpm/internal/copr"
	metapkg "github.com/arcticlore/candy-rpm/internal/pkg"
	"github.com/arcticlore/candy-rpm/internal/state"
)

const (
	maxWorkers     = 20
	httpTimeout    = 5 * time.Second
	coprAPITimeout = 30 * time.Second
)

// ChrootPlan is the output structure.
type ChrootPlan struct {
	Plan map[string][]string `json:"plan"`
	Done []string            `json:"done"`
}

// ChrootResult holds the result of checking one chroot for one package.
type ChrootResult struct {
	Pkg    string
	Chroot string
	Need   bool
}

func main() {
	var (
		owner    = flag.String("owner", "arcticlore", "COPR owner")
		project  = flag.String("project", "candy", "COPR project")
		rootDir  = flag.String("root", "", "Project root directory")
		stuckHrs = flag.Float64("stuck-hours", 6, "Hours before a pending build is considered stuck")
		workers  = flag.Int("workers", maxWorkers, "Number of concurrent workers")
		verbose  = flag.Bool("v", false, "Verbose output")
	)
	flag.Parse()

	if *rootDir == "" {
		// Auto-detect from script location
		exe, err := os.Executable()
		if err == nil {
			*rootDir = filepath.Dir(filepath.Dir(exe))
		} else {
			*rootDir = "."
		}
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	// Load package metadata
	pkgsPath := filepath.Join(*rootDir, "pkgs.json")
	pkgsFile, err := metapkg.Load(pkgsPath)
	if err != nil {
		log.Fatalf("load pkgs.json: %v", err)
	}

	// Load state
	statePath := filepath.Join(*rootDir, "state", "state.json")
	st, err := state.New(statePath)
	if err != nil {
		log.Fatalf("load state: %v", err)
	}

	// Load lock file
	lockPath := filepath.Join(*rootDir, "state", "chroot-lock.json")
	lock := loadLock(lockPath)

	// Fetch builds from COPR
	coprClient := copr.NewClient(*owner, *project)
	builds, err := coprClient.ListBuilds(ctx, 200)
	if err != nil {
		log.Fatalf("fetch COPR builds: %v", err)
	}

	latest := copr.LatestByPackage(builds)
	if *verbose {
		log.Printf("Found %d unique packages in COPR", len(latest))
	}

	// Check each package
	plan := make(map[string][]string)
	var done []string
	var mu sync.Mutex
	var wg sync.WaitGroup

	sem := make(chan struct{}, *workers)
	pkgCount := 0

	for _, meta := range pkgsFile.Packages {
		if !meta.IsEnabled() {
			continue
		}

		b, ok := latest[meta.Name]
		if !ok {
			continue
		}

		// Succeeded builds are done
		if b.State == "succeeded" {
			ver := st.Ver(meta.Name)
			if ver == "" {
				ver = "?"
			}
			lockKey := meta.Name + "|*"
			lock[lockKey] = map[string]interface{}{
				"ver": ver,
				"ok":  b.Chroots,
			}
			done = append(done, meta.Name)
			continue
		}

		pkgCount++
		if *verbose && pkgCount%10 == 0 {
			log.Printf("Checked %d packages...", pkgCount)
		}

		// Check chroots in parallel
		results := checkChroots(ctx, meta.Name, b, coprClient, sem, &wg)

		var need []string
		for _, r := range results {
			if r.Need {
				need = append(need, r.Chroot)
			}
		}

		if len(need) > 0 {
			mu.Lock()
			plan[meta.Name] = need
			mu.Unlock()
		}
	}

	// Apply stuck pending rules
	final := applyStuckRules(plan, lock, *stuckHrs)

	// Write output
	output := ChrootPlan{Plan: final, Done: done}
	outputPath := filepath.Join(*rootDir, "logs", "chroot-plan.json")
	if err := writeJSON(outputPath, output); err != nil {
		log.Fatalf("write plan: %v", err)
	}

	// Save lock
	if err := saveLock(lockPath, lock); err != nil {
		log.Fatalf("save lock: %v", err)
	}

	// Output to stdout
	outJSON, _ := json.Marshal(final)
	fmt.Println(string(outJSON))
}

func checkChroots(ctx context.Context, pkgName string, b copr.Build, client *copr.Client, sem chan struct{}, wg *sync.WaitGroup) []ChrootResult {
	var results []ChrootResult
	var mu sync.Mutex

	for _, chroot := range b.Chroots {
		wg.Add(1)
		sem <- struct{}{}

		go func(c string) {
			defer wg.Done()
			defer func() { <-sem }()

			need := checkOneChroot(ctx, pkgName, c, b.ID, client)
			mu.Lock()
			results = append(results, ChrootResult{
				Pkg:    pkgName,
				Chroot: c,
				Need:   need,
			})
			mu.Unlock()
		}(chroot)
	}

	wg.Wait()
	return results
}

func checkOneChroot(ctx context.Context, pkgName, chroot string, buildID int, client *copr.Client) bool {
	url := client.DownloadURL(chroot, buildID, pkgName)

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return false
	}

	httpClient := &http.Client{Timeout: httpTimeout}
	resp, err := httpClient.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return false
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return false
	}

	listing := string(body)

	// Check for RPM before builder-live.log.gz
	parts := strings.SplitN(listing, "builder-live.log.gz", 2)
	if len(parts) == 0 {
		return false
	}

	return strings.Contains(parts[0], ".rpm")
}

func applyStuckRules(plan map[string][]string, lock map[string]interface{}, stuckHours float64) map[string][]string {
	now := time.Now().Unix()
	stuckSec := int64(stuckHours * 3600)
	final := make(map[string][]string)

	for pkg, chroots := range plan {
		var keep []string
		for _, c := range chroots {
			key := pkg + "|" + c
			rec, ok := lock[key]
			if !ok {
				keep = append(keep, c)
				continue
			}

			recMap, ok := rec.(map[string]interface{})
			if !ok {
				keep = append(keep, c)
				continue
			}

			failVer, ok := recMap["fail_ver"]
			if !ok || failVer == nil || failVer == "" {
				keep = append(keep, c)
				continue
			}

			ts, ok := recMap["ts"].(float64)
			if !ok {
				keep = append(keep, c)
				continue
			}

			if now-int64(ts) < stuckSec {
				continue // recently failed, skip
			}
			keep = append(keep, c)
		}

		if len(keep) > 0 {
			final[pkg] = keep
		}
	}

	return final
}

func loadLock(path string) map[string]interface{} {
	data, err := os.ReadFile(path)
	if err != nil {
		return make(map[string]interface{})
	}

	var lock map[string]interface{}
	if err := json.Unmarshal(data, &lock); err != nil {
		return make(map[string]interface{})
	}

	return lock
}

func saveLock(path string, lock map[string]interface{}) error {
	body, err := json.MarshalIndent(lock, "", " ")
	if err != nil {
		return err
	}

	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, body, 0600); err != nil {
		return err
	}

	return os.Rename(tmp, path)
}

func writeJSON(path string, v interface{}) error {
	body, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return err
	}

	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}

	return os.WriteFile(path, body, 0644)
}
