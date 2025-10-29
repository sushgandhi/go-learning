// main.go
// Go NTLM Bridge: in-cluster forward proxy that authenticates to an upstream NTLM proxy using libcurl.
// - Handles HTTP methods (GET/POST/PUT/PATCH/DELETE/HEAD/etc.)
// - Handles HTTPS via CONNECT tunnels (e.g., browsers/headless Chrome)
// - Delegates upstream work to libcurl (NTLM, TLS, HTTP/2, proxy-407 handshakes)
//
// Build prerequisites:
//   - libcurl with NTLM enabled present at build/runtime
//   - CGO_ENABLED=1
//
// Environment variables:
//   LISTEN_ADDR            (default ":3128")
//   UPSTREAM_PROXY_HOST    (required)
//   UPSTREAM_PROXY_PORT    (required, e.g. "9899")
//   UPSTREAM_PROXY_USER    (required, e.g. "DOMAIN\\user" or just "user")
//   UPSTREAM_PROXY_PASS    (required)
//   IDLE_TIMEOUT_SECONDS   (default 90)
//   CONNECT_TIMEOUT_MS     (default 10000)
//   TOTAL_TIMEOUT_MS       (default 120000)
//   ALLOW_PLAIN_HTTP       (default "true")
//
// Notes:
// - Downstream (client→this proxy) speaks HTTP/1.1 proxy semantics.
// - Upstream (this proxy→corporate proxy) is driven by libcurl with NTLM proxy auth.
// - For HTTPS, we establish an authenticated tunnel using HTTPProxyTunnel + ConnectOnly,
//   then splice bytes between client socket and the libcurl socket.
//
// DISCLAIMER: This is a production-grade *skeleton*. You should add robust logging,
// metrics (Prometheus), ACLs, graceful reloads, unit tests, and thorough error handling.

package main

import (
    "bufio"
    "context"
    "errors"
    "fmt"
    "io"
    "log"
    "net"
    "net/http"
    "net/textproto"
    "os"
    "strconv"
    "strings"
    "sync"
    "time"

    curl "github.com/andelf/go-curl"
)

// Global config
var (
    listenAddr         = getenv("LISTEN_ADDR", ":3128")
    upstreamHost       = mustGetenv("UPSTREAM_PROXY_HOST")
    upstreamPort       = mustGetenv("UPSTREAM_PROXY_PORT")
    upstreamUser       = mustGetenv("UPSTREAM_PROXY_USER")
    upstreamPass       = mustGetenv("UPSTREAM_PROXY_PASS")
    idleTimeoutSeconds = getenvInt("IDLE_TIMEOUT_SECONDS", 90)
    connectTimeoutMs   = getenvInt("CONNECT_TIMEOUT_MS", 10000)
    totalTimeoutMs     = getenvInt("TOTAL_TIMEOUT_MS", 120000)
    allowPlainHTTP     = getenv("ALLOW_PLAIN_HTTP", "true") == "true"
)

func main() {
    log.Printf("Starting Go NTLM Bridge on %s → upstream proxy %s:%s (NTLM via libcurl)", listenAddr, upstreamHost, upstreamPort)

    // Global curl init
    curl.GlobalInit(curl.GLOBAL_ALL)
    defer curl.GlobalCleanup()

    srv := &http.Server{
        Addr:              listenAddr,
        Handler:           http.HandlerFunc(proxyHandler),
        ReadTimeout:       time.Duration(idleTimeoutSeconds) * time.Second,
        ReadHeaderTimeout: 30 * time.Second,
        WriteTimeout:      time.Duration(idleTimeoutSeconds) * time.Second,
        IdleTimeout:       time.Duration(idleTimeoutSeconds) * time.Second,
        ErrorLog:          log.New(os.Stderr, "http: ", log.LstdFlags),
    }

    if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
        log.Fatalf("server error: %v", err)
    }
}

func proxyHandler(w http.ResponseWriter, r *http.Request) {
    if strings.EqualFold(r.Method, http.MethodConnect) {
        handleConnect(w, r)
        return
    }

    if !allowPlainHTTP && r.URL.Scheme != "https" {
        http.Error(w, "Plain HTTP disallowed by policy", http.StatusForbidden)
        return
    }

    if r.URL.Scheme == "" {
        // In proxy mode, r.URL should be absolute (http://host/path). If not, try to reconstruct.
        http.Error(w, "Bad request: expected absolute URL", http.StatusBadRequest)
        return
    }

    if err := handleHTTPViaCurl(w, r); err != nil {
        code := http.StatusBadGateway
        if errors.Is(err, context.DeadlineExceeded) {
            code = http.StatusGatewayTimeout
        }
        http.Error(w, fmt.Sprintf("Upstream error: %v", err), code)
    }
}

// handleHTTPViaCurl forwards non-CONNECT requests using libcurl and streams the response back.
func handleHTTPViaCurl(w http.ResponseWriter, r *http.Request) error {
    easy := curl.EasyInit()
    if easy == nil {
        return fmt.Errorf("curl init failed")
    }
    defer easy.Cleanup()

    // Timeouts
    _ = easy.Setopt(curl.OPT_CONNECTTIMEOUT_MS, connectTimeoutMs)
    _ = easy.Setopt(curl.OPT_TIMEOUT_MS, totalTimeoutMs)

    // Proxy with NTLM
    _ = easy.Setopt(curl.OPT_PROXY, fmt.Sprintf("%s:%s", upstreamHost, upstreamPort))
    _ = easy.Setopt(curl.OPT_PROXYAUTH, int(curl.AUTH_NTLM))
    _ = easy.Setopt(curl.OPT_PROXYUSERNAME, upstreamUser)
    _ = easy.Setopt(curl.OPT_PROXYPASSWORD, upstreamPass)

    // Target URL & method
    targetURL := r.URL.String() // absolute URL
    _ = easy.Setopt(curl.OPT_URL, targetURL)

    switch r.Method {
    case http.MethodGet:
        _ = easy.Setopt(curl.OPT_HTTPGET, 1)
    case http.MethodHead:
        _ = easy.Setopt(curl.OPT_NOBODY, 1)
    case http.MethodPost:
        _ = easy.Setopt(curl.OPT_POST, 1)
    default:
        _ = easy.Setopt(curl.OPT_CUSTOMREQUEST, r.Method)
    }

    // Headers: copy all except Hop-by-Hop per RFC 7230 (handled by Go server already), but we forward typical ones.
    headers := []string{}
    for k, vs := range r.Header {
        for _, v := range vs {
            // Skip Proxy-* from downstream
            if strings.HasPrefix(http.CanonicalHeaderKey(k), "Proxy-") {
                continue
            }
            headers = append(headers, fmt.Sprintf("%s: %s", k, v))
        }
    }
    if len(headers) > 0 {
        slist := (*curl.Slist)(nil)
        for _, h := range headers {
            slist = slist.Append(h)
        }
        defer slist.Free()
        _ = easy.Setopt(curl.OPT_HTTPHEADER, slist)
    }

    // Request body streaming (if any)
    if r.Body != nil && r.ContentLength != 0 {
        pr, pw := io.Pipe()
        // For libcurl to read request body from us
        _ = easy.Setopt(curl.OPT_READDATA, pr)
        _ = easy.Setopt(curl.OPT_UPLOAD, 1)
        if r.ContentLength > 0 {
            _ = easy.Setopt(curl.OPT_INFILESIZE_LARGE, r.ContentLength)
        }
        // Writer goroutine copies from client body into the pipe
        go func() {
            defer pw.Close()
            defer r.Body.Close()
            io.Copy(pw, r.Body)
        }()
    }

    // Capture status line + headers to write to client
    var (
        wroteHeader bool
        statusCode  = 200
        respHeader  = http.Header{}
        headerBuf   strings.Builder
    )

    _ = easy.Setopt(curl.OPT_HEADERFUNCTION, func(ptr []byte, _ interface{}) bool {
        line := string(ptr)
        headerBuf.WriteString(line)
        // Parse status line
        if strings.HasPrefix(line, "HTTP/") {
            // e.g., HTTP/1.1 200 OK
            parts := strings.SplitN(strings.TrimSpace(line), " ", 3)
            if len(parts) >= 2 {
                if v, err := strconv.Atoi(parts[1]); err == nil {
                    statusCode = v
                }
            }
            return true
        }
        // Header lines
        if i := strings.Index(line, ":"); i > 0 {
            key := textproto.CanonicalMIMEHeaderKey(strings.TrimSpace(line[:i]))
            val := strings.TrimSpace(line[i+1:])
            if key != "Connection" && key != "Transfer-Encoding" && key != "Proxy-Authenticate" && key != "Proxy-Authorization" {
                respHeader.Add(key, val)
            }
        }
        return true
    })

    // Stream body to client as it arrives
    bw := bufio.NewWriter(w)
    _ = easy.Setopt(curl.OPT_WRITEFUNCTION, func(ptr []byte, _ interface{}) bool {
        if !wroteHeader {
            // Write headers once we see first bytes of body or end of headers
            copyHeaders(w, statusCode, respHeader)
            wroteHeader = true
        }
        if len(ptr) > 0 {
            if _, err := bw.Write(ptr); err != nil {
                return false
            }
        }
        return true
    })

    // Perform the request
    if err := easy.Perform(); err != nil {
        return err
    }

    if !wroteHeader {
        // No body case (e.g., HEAD): still need to write headers
        copyHeaders(w, statusCode, respHeader)
    }
    if err := bw.Flush(); err != nil {
        return err
    }
    return nil
}

func copyHeaders(w http.ResponseWriter, status int, hdr http.Header) {
    // Map curl response headers to downstream client
    for k, vs := range hdr {
        for _, v := range vs {
            w.Header().Add(k, v)
        }
    }
    // Some proxies rely on Via header; optional:
    w.Header().Add("Via", "1.1 go-ntlm-bridge")
    w.WriteHeader(status)
}

// handleConnect establishes an NTLM-authenticated tunnel via upstream proxy, then splices bytes.
func handleConnect(w http.ResponseWriter, r *http.Request) {
    hj, ok := w.(http.Hijacker)
    if !ok {
        http.Error(w, "Hijacking not supported", http.StatusInternalServerError)
        return
    }
    clientConn, brw, err := hj.Hijack()
    if err != nil {
        http.Error(w, err.Error(), http.StatusServiceUnavailable)
        return
    }
    defer func() {
        // clientConn closed in splice tunnel
        if clientConn != nil {
            clientConn.Close()
        }
    }()

    // Target from CONNECT line
    target := r.Host // form host:port
    if target == "" {
        io.WriteString(brw, "HTTP/1.1 400 Bad Request\r\n\r\n")
        brw.Flush()
        clientConn.Close()
        return
    }

    // Prepare libcurl to create a proxy-authenticated tunnel
    easy := curl.EasyInit()
    if easy == nil {
        io.WriteString(brw, "HTTP/1.1 502 Bad Gateway\r\n\r\n")
        brw.Flush()
        clientConn.Close()
        return
    }
    defer easy.Cleanup()

    // Timeouts
    _ = easy.Setopt(curl.OPT_CONNECTTIMEOUT_MS, connectTimeoutMs)
    _ = easy.Setopt(curl.OPT_TIMEOUT_MS, totalTimeoutMs)

    // Proxy + NTLM
    _ = easy.Setopt(curl.OPT_PROXY, fmt.Sprintf("%s:%s", upstreamHost, upstreamPort))
    _ = easy.Setopt(curl.OPT_PROXYAUTH, int(curl.AUTH_NTLM))
    _ = easy.Setopt(curl.OPT_PROXYUSERNAME, upstreamUser)
    _ = easy.Setopt(curl.OPT_PROXYPASSWORD, upstreamPass)

    // Instruct curl to create an HTTP proxy tunnel to target
    _ = easy.Setopt(curl.OPT_HTTPPROXYTUNNEL, 1)

    // libcurl needs a URL to decide it must tunnel; https scheme is fine even if we won't do TLS here.
    _ = easy.Setopt(curl.OPT_URL, "https://"+target)

    // We'll take over the socket after CONNECT
    _ = easy.Setopt(curl.OPT_CONNECT_ONLY, 1)

    if err := easy.Perform(); err != nil {
        io.WriteString(brw, "HTTP/1.1 502 Bad Gateway\r\n\r\n")
        brw.Flush()
        clientConn.Close()
        return
    }

    // If we reached here, the CONNECT tunnel is established through the corp proxy.
    // Tell the client the tunnel is ready.
    io.WriteString(brw, "HTTP/1.1 200 Connection Established\r\n\r\n")
    if err := brw.Flush(); err != nil {
        clientConn.Close()
        return
    }

    // Retrieve curl's underlying socket
    var rawSock int
    _ = easy.Getinfo(curl.INFO_LASTSOCKET, &rawSock)
    if rawSock == 0 {
        clientConn.Close()
        return
    }

    // Splice bytes between clientConn and curl socket
    splice(clientConn, easy)
}

// splice bridges data between the client connection and the curl easy handle using easy.Send/easy.Recv.
func splice(client net.Conn, easy *curl.Easy) {
    defer client.Close()

    // Bidirectional copy with backpressure
    var wg sync.WaitGroup
    wg.Add(2)

    // client → upstream
    go func() {
        defer wg.Done()
        buf := make([]byte, 32*1024)
        for {
            client.SetReadDeadline(time.Now().Add(2 * time.Minute))
            n, err := client.Read(buf)
            if n > 0 {
                off := 0
                for off < n {
                    wrote, cerr := easy.Send(buf[off:n])
                    if wrote > 0 {
                        off += wrote
                    }
                    if cerr != nil {
                        return
                    }
                }
            }
            if err != nil {
                return
            }
        }
    }()

    // upstream → client
    go func() {
        defer wg.Done()
        buf := make([]byte, 32*1024)
        for {
            // curl.Recv blocks on upstream
            n, err := easy.Recv(buf)
            if n > 0 {
                client.SetWriteDeadline(time.Now().Add(2 * time.Minute))
                if _, werr := client.Write(buf[:n]); werr != nil {
                    return
                }
            }
            if err != nil {
                return
            }
        }
    }()

    wg.Wait()
}

// --- helpers ---
func getenv(key, def string) string {
    v := os.Getenv(key)
    if v == "" {
        return def
    }
    return v
}

func mustGetenv(key string) string {
    v := os.Getenv(key)
    if v == "" {
        log.Fatalf("missing required env: %s", key)
    }
    return v
}

func getenvInt(key string, def int) int {
    v := os.Getenv(key)
    if v == "" {
        return def
    }
    i, err := strconv.Atoi(v)
    if err != nil {
        return def
    }
    return i
}

// -----------------------------
// go.mod
// -----------------------------
// module example.com/go-ntlm-bridge
//
// go 1.22
//
// require github.com/andelf/go-curl v0.0.0-20230129072749-5a5b4c2a3b0b // or latest

// -----------------------------
// Dockerfile (UBI + libcurl)
// -----------------------------
// Use a UBI base commonly accepted in enterprise (adjust as needed)
//
// FROM registry.access.redhat.com/ubi9/ubi-minimal:latest AS build
// RUN microdnf install -y gcc gcc-c++ make git curl-devel pkgconfig ca-certificates && microdnf clean all
// ENV CGO_ENABLED=1 GO111MODULE=on
// RUN curl -L https://go.dev/dl/go1.22.5.linux-amd64.tar.gz -o /tmp/go.tgz \
//     && tar -C /usr/local -xzf /tmp/go.tgz
// ENV PATH="/usr/local/go/bin:${PATH}"
// WORKDIR /src
// COPY go.mod .
// RUN go mod download
// COPY . .
// RUN go build -trimpath -buildvcs=false -o /out/ntlm-bridge main.go
//
// FROM registry.access.redhat.com/ubi9/ubi-micro:latest
// # Ensure libcurl (with NTLM) and CA trust are present
// RUN microdnf install -y libcurl ca-certificates && microdnf clean all || true
// COPY --from=build /out/ntlm-bridge /usr/local/bin/ntlm-bridge
// USER 65534:65534
// EXPOSE 3128
// ENTRYPOINT ["/usr/local/bin/ntlm-bridge"]

// -----------------------------
// Kubernetes/OpenShift (snippets)
// -----------------------------
// apiVersion: v1
// kind: Secret
// metadata:
//   name: ntlm-bridge-secret
// type: Opaque
// stringData:
//   UPSTREAM_PROXY_USER: "super_username"      # or DOMAIN\\user if required
//   UPSTREAM_PROXY_PASS: "super_password"
// ---
// apiVersion: apps/v1
// kind: Deployment
// metadata:
//   name: ntlm-bridge
// spec:
//   replicas: 2
//   selector:
//     matchLabels: { app: ntlm-bridge }
//   template:
//     metadata:
//       labels: { app: ntlm-bridge }
//     spec:
//       containers:
//         - name: bridge
//           image: your-registry/ntlm-bridge:latest
//           ports: [{ containerPort: 3128 }]
//           env:
//             - name: LISTEN_ADDR
//               value: ":3128"
//             - name: UPSTREAM_PROXY_HOST
//               value: "my-super-secure-proxy"
//             - name: UPSTREAM_PROXY_PORT
//               value: "9899"
//             - name: UPSTREAM_PROXY_USER
//               valueFrom: { secretKeyRef: { name: ntlm-bridge-secret, key: UPSTREAM_PROXY_USER } }
//             - name: UPSTREAM_PROXY_PASS
//               valueFrom: { secretKeyRef: { name: ntlm-bridge-secret, key: UPSTREAM_PROXY_PASS } }
//           readinessProbe:
//             tcpSocket: { port: 3128 }
//             periodSeconds: 5
//           livenessProbe:
//             tcpSocket: { port: 3128 }
//             periodSeconds: 10
//           securityContext:
//             runAsNonRoot: true
//             runAsUser: 65534
// ---
// apiVersion: v1
// kind: Service
// metadata:
//   name: ntlm-bridge
// spec:
//   selector: { app: ntlm-bridge }
//   ports:
//     - port: 3128
//       targetPort: 3128
//       name: http
//   type: ClusterIP
