package main

import (
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"time"

	"github.com/launchdarkly/go-ntlm-proxy-auth/ntlm"
)

// Config holds the proxy configuration
type Config struct {
	ListenAddr    string
	ProxyUser     string
	ProxyPass     string
	UpstreamProxy string
}

// NtlmBridge is our proxy server
type NtlmBridge struct {
	config        *Config
	ntlmClient    *http.Client
	ntlmTransport *ntlm.NTLMProxyTransport
}

// NewNtlmBridge creates a new bridge server
func NewNtlmBridge(cfg *Config) (*NtlmBridge, error) {
	proxyURL, err := url.Parse(cfg.UpstreamProxy)
	if err != nil {
		return nil, fmt.Errorf("invalid upstream proxy URL: %v", err)
	}

	// 1. Create the special NTLM Transport
	// This transport will handle all auth logic
	transport := &ntlm.NTLMProxyTransport{
		ProxyURL: *proxyURL,
		Username: cfg.ProxyUser,
		Password: cfg.ProxyPass,
		// Domain: "YOUR-DOMAIN", // Uncomment if NTLM requires it
	}

	// 2. Create an HTTP Client that uses this transport
	// This client is for handling plain HTTP requests
	client := &http.Client{
		Transport: transport,
	}

	return &NtlmBridge{
		config:        cfg,
		ntlmClient:    client,
		ntlmTransport: transport,
	}, nil
}

// ServeHTTP is the main request handler
func (b *NtlmBridge) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	log.Printf("INFO: Handling request: %s %s %s", r.Method, r.Host, r.URL.String())

	if r.Method == http.MethodConnect {
		// This is an HTTPS request
		b.handleHTTPS(w, r)
	} else {
		// This is an HTTP request
		b.handleHTTP(w, r)
	}
}

// handleHTTP handles plain HTTP requests (GET, POST, etc.)
func (b *NtlmBridge) handleHTTP(w http.ResponseWriter, r *http.Request) {
	// We are a proxy, so the request URI is the full URL.
	// We need to send this to our NTLM client.

	// Create a new request to forward
	// r.URL is already the full target URL
	req, err := http.NewRequest(r.Method, r.URL.String(), r.Body)
	if err != nil {
		log.Printf("ERROR: Failed to create new HTTP request: %v", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	// Copy headers from original request
	req.Header = r.Header

	// Use our NTLM-enabled client to make the request
	// This client's transport will add the NTLM auth
	resp, err := b.ntlmClient.Do(req)
	if err != nil {
		log.Printf("ERROR: Failed to make upstream HTTP request: %v", err)
		http.Error(w, err.Error(), http.StatusServiceUnavailable)
		return
	}
	defer resp.Body.Close()

	// Copy the response back to the original client
	copyHeaders(w.Header(), resp.Header)
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)
}

// handleHTTPS handles HTTPS requests (CONNECT)
func (b *NtlmBridge) handleHTTPS(w http.ResponseWriter, r *http.Request) {
	// The client (e.g., Python app) wants to connect to r.Host (e.g., "google.com:443")

	// 1. We must first establish the tunnel with our *upstream* NTLM proxy
	// We do this by sending a CONNECT request *to* the NTLM transport.
	connectReq, _ := http.NewRequest(http.MethodConnect, "https://"+r.Host, nil)

	// The RoundTrip will:
	// - Connect to "my-super-secure-proxy:9899"
	// - Send "CONNECT google.com:443"
	// - Perform the NTLM auth handshake
	// - Return a response with the hijacked TCP connection in resp.Body
	resp, err := b.ntlmTransport.RoundTrip(connectReq)
	if err != nil {
		log.Printf("ERROR: Upstream CONNECT failed: %v", err)
		http.Error(w, err.Error(), http.StatusServiceUnavailable)
		return
	}

	// If auth failed, we won't get a 200 OK
	if resp.StatusCode != http.StatusOK {
		log.Printf("ERROR: Upstream CONNECT returned status %d", resp.StatusCode)
		http.Error(w, "upstream connect failed", http.StatusBadGateway)
		return
	}

	// 2. Now we have the upstream connection (in resp.Body)
	// We need to tell our *client* (Python app) that its tunnel is ready.
	clientConn, _, err := w.(http.Hijacker).Hijack()
	if err != nil {
		log.Printf("ERROR: Failed to hijack client connection: %v", err)
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Send "200 OK" to the Python app
	clientConn.Write([]byte("HTTP/1.1 200 Connection Established\r\n\r\n"))

	// 3. Stream data in both directions
	// resp.Body is the connection to the upstream proxy
	upstreamConn := resp.Body

	defer upstreamConn.Close()
	defer clientConn.Close()

	// Bi-directional copy
	go io.Copy(upstreamConn, clientConn)
	io.Copy(clientConn, upstreamConn)
}

// copyHeaders copies all headers from src to dst
func copyHeaders(dst, src http.Header) {
	for k, vv := range src {
		for _, v := range vv {
			dst.Add(k, v)
		}
	}
}

// --- Main Function ---

func main() {
	// Load config from environment variables
	cfg := &Config{
		ListenAddr:    getenv("LISTEN_ADDR", ":8080"),
		ProxyUser:     getenv("PROXY_USER", "super_username"),
		ProxyPass:     getenv("PROXY_PASS", "super_password"),
		UpstreamProxy: getenv("UPSTREAM_PROXY", "http://my-super-secure-proxy:9899"),
	}

	// Create the bridge
	bridge, err := NewNtlmBridge(cfg)
	if err != nil {
		log.Fatalf("FATAL: Could not create NTLM bridge: %v", err)
	}

	// Create the HTTP server
	server := &http.Server{
		Addr:         cfg.ListenAddr,
		Handler:      bridge,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	log.Printf("INFO: Starting NTLM bridge on %s", cfg.ListenAddr)
	log.Printf("INFO: Forwarding to upstream proxy: %s", cfg.UpstreamProxy)

	if err := server.ListenAndServe(); err != nil {
		log.Fatalf("FATAL: Server failed: %v", err)
	}
}

// getenv is a helper to get env var with a default
func getenv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}

// # Initialize the Go module
// go mod init ntlm-bridge

// # Get the necessary NTLM library
// go get github.com/launchdarkly/go-ntlm-proxy-auth

