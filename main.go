package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"
)

const (
	DefaultUpstream   = "https://www.kimi.ai"
	DefaultPort       = "18770"
	DefaultModel      = "k2d6-chat"
	AccessTokenMaxAge = 15 * time.Minute
)

// ---- config ----

type Config struct {
	Port         string
	Upstream     string
	APIKey       string // bridge-side key (client -> bridge); empty = no auth
	TokensPath   string
	DeviceID     string
	SessionID    string
	DefaultModel string
}

func loadConfig() Config {
	return Config{
		Port:         envOr("KIMI_WEB_PORT", DefaultPort),
		Upstream:     envOr("KIMI_WEB_UPSTREAM", DefaultUpstream),
		APIKey:       os.Getenv("KIMI_WEB_API_KEY"),
		TokensPath:   envOr("KIMI_WEB_TOKENS", "tokens.json"),
		DeviceID:     envOr("KIMI_WEB_DEVICE_ID", "7691245069365436681"),
		SessionID:    envOr("KIMI_WEB_SESSION_ID", "1731763799132339910"),
		DefaultModel: envOr("KIMI_WEB_MODEL", DefaultModel),
	}
}

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

// ---- token store ----

type TokenStore struct {
	mu      sync.RWMutex
	path    string
	Access  string
	Refresh string
	expAt   time.Time
}

func NewTokenStore(path string) (*TokenStore, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read tokens: %w", err)
	}
	var raw struct {
		At        string  `json:"at"`
		Rt        string  `json:"rt"`
		FetchedAt float64 `json:"fetched_at"`
	}
	if err := json.Unmarshal(b, &raw); err != nil {
		return nil, fmt.Errorf("parse tokens: %w", err)
	}
	s := &TokenStore{path: path, Access: raw.At, Refresh: raw.Rt}
	s.expAt = jwtExp(raw.At)
	if s.expAt.IsZero() {
		s.expAt = time.Now().Add(AccessTokenMaxAge)
	}
	return s, nil
}

func (s *TokenStore) Get() (string, bool) {
	s.mu.RLock()
	if s.Access != "" && time.Now().Before(s.expAt.Add(-90*time.Second)) {
		s.mu.RUnlock()
		return s.Access, true
	}
	s.mu.RUnlock()
	// expired — try auto-refresh
	s.RefreshNow()
	s.mu.RLock()
	defer s.mu.RUnlock()
	if s.Access != "" && time.Now().Before(s.expAt.Add(-5*time.Second)) {
		return s.Access, true
	}
	return "", false
}

// RefreshNow calls auth.kimi.ai RefreshToken with the stored refresh_token.
func (s *TokenStore) RefreshNow() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.Refresh == "" {
		return fmt.Errorf("no refresh token")
	}
	body, _ := json.Marshal(map[string]string{"refresh_token": s.Refresh})
	req, err := http.NewRequest(http.MethodPost, "https://auth.kimi.ai/api/account.gateway.v1.AuthService/RefreshToken",
		bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("content-type", "application/json")
	req.Header.Set("origin", "https://www.kimi.ai")
	req.Header.Set("referer", "https://www.kimi.ai/")
	req.Header.Set("user-agent", UAChrome)
	client := &http.Client{Timeout: 20 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("refresh: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(io.LimitReader(resp.Body, 2048))
		return fmt.Errorf("refresh HTTP %d: %s", resp.StatusCode, string(b))
	}
	var out struct {
		AccessToken  string `json:"accessToken"`
		RefreshToken string `json:"refreshToken"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return fmt.Errorf("refresh decode: %w", err)
	}
	if out.AccessToken == "" {
		return fmt.Errorf("refresh: empty accessToken")
	}
	s.Access = out.AccessToken
	if e := jwtExp(out.AccessToken); !e.IsZero() {
		s.expAt = e
	}
	if out.RefreshToken != "" {
		s.Refresh = out.RefreshToken
	}
	out2, _ := json.Marshal(map[string]any{"at": s.Access, "rt": s.Refresh, "fetched_at": time.Now().Unix()})
	_ = os.WriteFile(s.path, out2, 0o600)
	logInfo("token auto-refreshed (exp %s)", s.expAt.Format(time.RFC3339))
	return nil
}

func (s *TokenStore) Update(access string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.Access = access
	if e := jwtExp(access); !e.IsZero() {
		s.expAt = e
	}
	out, _ := json.Marshal(map[string]any{"at": s.Access, "rt": s.Refresh, "fetched_at": time.Now().Unix()})
	_ = os.WriteFile(s.path, out, 0o600)
}

func jwtExp(tok string) time.Time {
	parts := strings.Split(tok, ".")
	if len(parts) < 3 {
		return time.Time{}
	}
	pl := parts[1]
	if n := len(pl) % 4; n != 0 {
		pl += strings.Repeat("=", 4-n)
	}
	b, err := base64.URLEncoding.DecodeString(pl)
	if err != nil {
		return time.Time{}
	}
	var p struct {
		Exp int64 `json:"exp"`
	}
	if json.Unmarshal(b, &p) != nil || p.Exp == 0 {
		return time.Time{}
	}
	return time.Unix(p.Exp, 0)
}

// ---- sentinel protocol (English, anti-hallucination over-fire) ----

const SentinelOpen = "<|tool_calls_begin|>"
const SentinelClose = "<|tool_calls_end|>"

// ---- main server ----

func main() {
	cfg := loadConfig()
	tok, err := NewTokenStore(cfg.TokensPath)
	if err != nil {
		logFatal("token store: %v", err)
	}

	srv := &Server{cfg: cfg, tok: tok}

	mux := http.NewServeMux()
	mux.HandleFunc("/v1/models", srv.authWrap(srv.handleModels))
	mux.HandleFunc("/v1/chat/completions", srv.authWrap(srv.handleChat))
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
		io.WriteString(w, "ok")
	})

	addr := "0.0.0.0:" + cfg.Port
	logInfo("kimi-web-bridge listening on %s (upstream %s, model %s)", addr, cfg.Upstream, cfg.DefaultModel)
	if err := http.ListenAndServe(addr, mux); err != nil {
		logFatal("listen: %v", err)
	}
}

func logFatal(f string, a ...any) {
	fmt.Fprintf(os.Stderr, "FATAL: "+f+"\n", a...)
	os.Exit(1)
}

func logInfo(f string, a ...any) {
	fmt.Fprintf(os.Stderr, "INFO: "+f+"\n", a...)
}

var _ = bytes.MinRead
