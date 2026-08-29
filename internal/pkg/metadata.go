// Package metadata parses pkgs.json package definitions.
package metadata

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
)

// Project holds project-wide configuration.
type Project struct {
	CoprName string   `json:"copr_name"`
	Chroots  []string `json:"chroots"`
}

// Package defines a single package's metadata.
type Package struct {
	Name      string   `json:"name"`
	Eco       string   `json:"eco"`
	Host      string   `json:"host"`
	Slug      string   `json:"slug"`
	Enabled   interface{} `json:"enabled,omitempty"` // Can be bool or string
	Prio      int      `json:"prio"`
	Ver       string   `json:"ver,omitempty"`
	Bins      []string `json:"bins,omitempty"`
	Files     []string `json:"files,omitempty"`
	ModDir    string   `json:"moddir,omitempty"`
	TagP      string   `json:"tagp,omitempty"`
	Fallback  string   `json:"fallback,omitempty"`
	BR        []string `json:"br,omitempty"`
	Req       []string `json:"req,omitempty"`
	Interp    string   `json:"interp,omitempty"`
	CDir      string   `json:"cdir,omitempty"`
	Pkg       string   `json:"pkg,omitempty"`
	URL       string   `json:"url,omitempty"`
	Summary   string   `json:"summary,omitempty"`
	License   string   `json:"license,omitempty"`
	Note      string   `json:"note,omitempty"`
	Mirror    string   `json:"mirror,omitempty"`
	Exp       bool     `json:"exp,omitempty"`
	Noman     bool     `json:"noman,omitempty"`
	Autoreconf bool   `json:"autoreconf,omitempty"`
	Cgo       bool     `json:"cgo,omitempty"`
	GitGit    bool     `json:"gem_git,omitempty"`
	GPkg      string   `json:"gpkg,omitempty"`
	NPMBin    string   `json:"npmbin,omitempty"`
	Entry     string   `json:"entry,omitempty"`
	Share     *Share   `json:"share,omitempty"`
	BuildCmd  string   `json:"build_cmd,omitempty"`
	BuildEnv  []string `json:"build_env,omitempty"`
	InstallCmd string  `json:"install_cmd,omitempty"`
	SrcMap    map[string]string `json:"script_src,omitempty"`
	PBRExclude []string `json:"pbr_exclude,omitempty"`
	ExtraFiles []string `json:"extra_files,omitempty"`
	TopDir    string   `json:"topdir,omitempty"`
}

// IsEnabled returns true if the package is enabled.
func (p *Package) IsEnabled() bool {
	if p.Enabled == nil {
		return true // default to enabled
	}
	switch v := p.Enabled.(type) {
	case bool:
		return v
	case string:
		return v != "false" && v != "0"
	default:
		return true
	}
}

// Share defines shared data installation.
type Share struct {
	Src string `json:"src"`
	Dst string `json:"dst"`
}

// PkgsFile is the root structure of pkgs.json.
type PkgsFile struct {
	Project  Project   `json:"project"`
	Packages []Package `json:"packages"`
}

// Load reads and parses pkgs.json.
func Load(path string) (*PkgsFile, error) {
	body, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read pkgs.json: %w", err)
	}

	var pf PkgsFile
	if err := json.Unmarshal(body, &pf); err != nil {
		return nil, fmt.Errorf("parse pkgs.json: %w", err)
	}

	return &pf, nil
}

// Enabled returns enabled package names sorted by priority.
func (pf *PkgsFile) Enabled(skipEco string, shardID, shardCount int) []string {
	type entry struct {
		name string
		prio int
		eco  string
	}

	var entries []entry
	for _, p := range pf.Packages {
		if !p.IsEnabled() {
			continue
		}
		if skipEco != "" && p.Eco == skipEco {
			continue
		}
		prio := p.Prio
		if prio == 0 {
			prio = 5
		}
		entries = append(entries, entry{name: p.Name, prio: prio, eco: p.Eco})
	}

	sort.Slice(entries, func(i, j int) bool {
		return entries[i].prio < entries[j].prio
	})

	var result []string
	for i, e := range entries {
		if shardCount > 0 && i%shardCount != shardID {
			continue
		}
		result = append(result, e.name)
	}

	return result
}

// ByName returns a map of package name to Package.
func (pf *PkgsFile) ByName() map[string]*Package {
	result := make(map[string]*Package, len(pf.Packages))
	for i := range pf.Packages {
		result[pf.Packages[i].Name] = &pf.Packages[i]
	}
	return result
}
