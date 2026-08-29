// Package state manages the build state JSON file.
package state

import (
	"encoding/json"
	"fmt"
	"os"
	"sync"
	"time"
)

// Entry represents a package's build state.
type Entry struct {
	Ver    string  `json:"ver,omitempty"`
	Ts     float64 `json:"ts,omitempty"` // Can be float from Python
	Locked bool    `json:"locked,omitempty"`
}

// State is a thread-safe wrapper around the state JSON file.
type State struct {
	mu   sync.Mutex
	path string
	data map[string]Entry
}

// New loads or creates a state file.
func New(path string) (*State, error) {
	s := &State{
		path: path,
		data: make(map[string]Entry),
	}

	body, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return s, nil
		}
		return nil, fmt.Errorf("read state: %w", err)
	}

	if len(body) > 0 {
		if err := json.Unmarshal(body, &s.data); err != nil {
			return nil, fmt.Errorf("parse state: %w", err)
		}
	}

	return s, nil
}

// Get returns the entry for a package.
func (s *State) Get(name string) (Entry, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	e, ok := s.data[name]
	return e, ok
}

// Set updates a package entry and saves to disk.
func (s *State) Set(name string, ver string, locked bool) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.data[name] = Entry{
		Ver:    ver,
		Ts:     float64(time.Now().Unix()),
		Locked: locked,
	}

	return s.save()
}

// Delete removes a package entry.
func (s *State) Delete(name string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	delete(s.data, name)
	return s.save()
}

// IsLocked returns true if the package is marked as locked.
func (s *State) IsLocked(name string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.data[name].Locked
}

// Ver returns the version for a package.
func (s *State) Ver(name string) string {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.data[name].Ver
}

// Timestamp returns the last update timestamp for a package.
func (s *State) Timestamp(name string) float64 {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.data[name].Ts
}

func (s *State) save() error {
	body, err := json.MarshalIndent(s.data, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal state: %w", err)
	}

	tmp := s.path + ".tmp"
	if err := os.WriteFile(tmp, body, 0600); err != nil {
		return fmt.Errorf("write state: %w", err)
	}

	return os.Rename(tmp, s.path)
}
