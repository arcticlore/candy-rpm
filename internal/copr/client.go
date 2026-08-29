// Package copr provides a client for the COPR API.
package copr

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

const (
	baseURL        = "https://copr.fedorainfracloud.org/api_3"
	downloadBase   = "https://download.copr.fedorainfracloud.org/results"
	defaultTimeout = 30 * time.Second
)

// Client interacts with the COPR API.
type Client struct {
	owner   string
	project string
	http    *http.Client
}

// Build represents a COPR build.
type Build struct {
	ID            int    `json:"id"`
	State         string `json:"state"`
	SourcePackage struct {
		Name    string `json:"name"`
		Version string `json:"version"`
		URL     string `json:"url"`
	} `json:"source_package"`
	Chroots     []string `json:"chroots"`
	SubmittedOn int64    `json:"submitted_on"`
	StartedOn   *int64   `json:"started_on"`
	EndedOn     *int64   `json:"ended_on"`
}

// BuildListResponse is the API response for listing builds.
type BuildListResponse struct {
	Items []Build `json:"items"`
}

// NewClient creates a new COPR API client.
func NewClient(owner, project string) *Client {
	return &Client{
		owner:   owner,
		project: project,
		http: &http.Client{
			Timeout: defaultTimeout,
		},
	}
}

// ListBuilds fetches recent builds from COPR.
func (c *Client) ListBuilds(ctx context.Context, limit int) ([]Build, error) {
	url := fmt.Sprintf("%s/build/list?ownername=%s&projectname=%s&limit=%d",
		baseURL, c.owner, c.project, limit)

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil, fmt.Errorf("create request: %w", err)
	}

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, fmt.Errorf("fetch builds: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("unexpected status: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("read body: %w", err)
	}

	var result BuildListResponse
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("decode JSON: %w", err)
	}

	return result.Items, nil
}

// LatestByPackage returns the latest build for each package.
func LatestByPackage(builds []Build) map[string]Build {
	seen := make(map[string]bool)
	result := make(map[string]Build)

	// Builds are ordered by ID descending (newest first)
	for _, b := range builds {
		name := b.SourcePackage.Name
		if !seen[name] {
			seen[name] = true
			result[name] = b
		}
	}

	return result
}

// DownloadURL returns the URL for a build's chroot directory listing.
func (c *Client) DownloadURL(chroot string, buildID int, pkgName string) string {
	return fmt.Sprintf("%s/%s/%s/%d-%s/", downloadBase, c.project, chroot, buildID, pkgName)
}
