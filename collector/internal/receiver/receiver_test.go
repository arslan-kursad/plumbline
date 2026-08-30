package receiver

import (
	"bytes"
	"compress/gzip"
	"context"
	"io"
	"log/slog"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/arslan-kursad/plumbline/collector/internal/auth"
	"github.com/arslan-kursad/plumbline/collector/internal/ingest"
	"github.com/arslan-kursad/plumbline/collector/internal/publisher"
	"github.com/arslan-kursad/plumbline/collector/internal/ratelimit"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

const testKey = "plb_test_0123456789abcdef0123456789abcdef"

const exportMethod = "/opentelemetry.proto.collector.trace.v1.TraceService/Export"

func quietLogger() *slog.Logger {
	return slog.New(slog.NewTextHandler(io.Discard, nil))
}

func fixture(t *testing.T, dialect, kind string) []byte {
	t.Helper()
	payload, err := os.ReadFile(filepath.Join("..", "..", "..", "testdata", "fixtures", dialect, kind, "request.pb"))
	if err != nil {
		t.Fatal(err)
	}
	return payload
}

func newIngestor(t *testing.T) (*ingest.Ingestor, *publisher.Recorder) {
	t.Helper()

	path := filepath.Join(t.TempDir(), "keys.json")
	body := `{"keys":[{"api_key_id":"local-claude","key_sha256":"` + auth.HashKey(testKey) + `",
		"source_dialect":"claude-code","rate_limit_per_second":100,"burst":100,"status":"active"}]}`
	if err := os.WriteFile(path, []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}

	registry, err := auth.LoadFileRegistry(path)
	if err != nil {
		t.Fatal(err)
	}

	recorder := &publisher.Recorder{}
	return &ingest.Ingestor{
		Registry:           registry,
		Limiter:            ratelimit.New(time.Now),
		Publisher:          recorder,
		MaxCompressedBytes: 4 << 20,
	}, recorder
}

func post(t *testing.T, handler http.Handler, key string, body []byte, headers map[string]string) *http.Response {
	t.Helper()

	request := httptest.NewRequest(http.MethodPost, TracesPath, bytes.NewReader(body))
	request.Header.Set("Content-Type", protobufContentType)
	if key != "" {
		request.Header.Set(APIKeyHeader, key)
	}
	for name, value := range headers {
		request.Header.Set(name, value)
	}

	recorder := httptest.NewRecorder()
	handler.ServeHTTP(recorder, request)
	return recorder.Result()
}

// TestPayloadBytesInEqualPayloadBytesOut is the mechanical form of ADR-0001's wire-only
// scope (architecture §3.1, F1 DoD item 3).
//
// Every fixture goes in through both transports, and what the publisher was handed —
// after gunzip — has to be the same bytes. If the collector ever deserializes and
// re-serializes an export, a field ordering or a default value will differ here long
// before anyone notices a wrong row in BigQuery.
func TestPayloadBytesInEqualPayloadBytesOut(t *testing.T) {
	dialects := []string{"claude-code", "dotnet-agent", "langgraph-python", "unknown"}

	for _, dialect := range dialects {
		t.Run("http/"+dialect, func(t *testing.T) {
			in, recorder := newIngestor(t)
			payload := fixture(t, dialect, "happy-path")

			response := post(t, NewHTTP(in, quietLogger()), testKey, payload, nil)
			if response.StatusCode != http.StatusOK {
				t.Fatalf("status %d", response.StatusCode)
			}

			assertIdentical(t, payload, recorder)
		})

		t.Run("grpc/"+dialect, func(t *testing.T) {
			in, recorder := newIngestor(t)
			payload := fixture(t, dialect, "happy-path")

			conn := dialGRPC(t, in)
			if err := export(context.Background(), conn, testKey, payload); err != nil {
				t.Fatal(err)
			}

			assertIdentical(t, payload, recorder)
		})
	}
}

func assertIdentical(t *testing.T, payload []byte, recorder *publisher.Recorder) {
	t.Helper()

	messages := recorder.Messages()
	if len(messages) != 1 {
		t.Fatalf("want one published message, got %d", len(messages))
	}
	if !bytes.Equal(messages[0].Payload, payload) {
		t.Fatalf("the collector did not publish what it received: %d bytes in, %d bytes out",
			len(payload), len(messages[0].Payload))
	}
}

func TestAGzippedRequestBodyIsInflatedAndStillIdentical(t *testing.T) {
	in, recorder := newIngestor(t)
	payload := fixture(t, "dotnet-agent", "happy-path")

	var compressed bytes.Buffer
	writer := gzip.NewWriter(&compressed)
	if _, err := writer.Write(payload); err != nil {
		t.Fatal(err)
	}
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}

	response := post(t, NewHTTP(in, quietLogger()), testKey, compressed.Bytes(),
		map[string]string{"Content-Encoding": "gzip"})
	if response.StatusCode != http.StatusOK {
		t.Fatalf("status %d", response.StatusCode)
	}

	assertIdentical(t, payload, recorder)
}

func TestHTTPStatusCodesSayWhatWentWrong(t *testing.T) {
	payload := fixture(t, "claude-code", "happy-path")

	t.Run("no key", func(t *testing.T) {
		in, recorder := newIngestor(t)
		if got := post(t, NewHTTP(in, quietLogger()), "", payload, nil).StatusCode; got != http.StatusUnauthorized {
			t.Fatalf("want 401, got %d", got)
		}
		if len(recorder.Messages()) != 0 {
			t.Fatal("an unauthenticated export was published")
		}
	})

	t.Run("json is refused", func(t *testing.T) {
		in, _ := newIngestor(t)
		response := post(t, NewHTTP(in, quietLogger()), testKey, []byte("{}"),
			map[string]string{"Content-Type": "application/json"})
		if response.StatusCode != http.StatusUnsupportedMediaType {
			t.Fatalf("want 415, got %d", response.StatusCode)
		}
	})

	t.Run("content type with charset is accepted", func(t *testing.T) {
		in, _ := newIngestor(t)
		response := post(t, NewHTTP(in, quietLogger()), testKey, payload,
			map[string]string{"Content-Type": "application/x-protobuf; charset=utf-8"})
		if response.StatusCode != http.StatusOK {
			t.Fatalf("want 200, got %d", response.StatusCode)
		}
	})

	t.Run("empty body", func(t *testing.T) {
		in, _ := newIngestor(t)
		if got := post(t, NewHTTP(in, quietLogger()), testKey, nil, nil).StatusCode; got != http.StatusBadRequest {
			t.Fatalf("want 400, got %d", got)
		}
	})

	t.Run("wrong method", func(t *testing.T) {
		in, _ := newIngestor(t)
		request := httptest.NewRequest(http.MethodGet, TracesPath, nil)
		response := httptest.NewRecorder()
		NewHTTP(in, quietLogger()).ServeHTTP(response, request)
		if response.Code != http.StatusMethodNotAllowed {
			t.Fatalf("want 405, got %d", response.Code)
		}
	})

	// F4's uptime check binds `GET /v1/traces` and matches on this body
	// (docs/runbooks/collector-endpoints.md §3). The status code alone cannot carry
	// that check: 405 is also what Cloud Run's edge or any future middleware would
	// return, while this string is written by the handler above and by nothing else
	// in the path, so matching it is what distinguishes "something answered" from
	// "the collector answered".
	//
	// Reword the message and the uptime check reports a healthy collector until
	// somebody looks. That is why the string is pinned here rather than left to the
	// status assertion above.
	t.Run("wrong method body is the uptime check's probe string", func(t *testing.T) {
		in, _ := newIngestor(t)
		request := httptest.NewRequest(http.MethodGet, TracesPath, nil)
		response := httptest.NewRecorder()
		NewHTTP(in, quietLogger()).ServeHTTP(response, request)

		const probe = "only POST is accepted"
		if got := strings.TrimSpace(response.Body.String()); got != probe {
			t.Fatalf("want body %q, got %q\n\nF4's uptime check matches this string; "+
				"changing it silently breaks that check. If the change is intended, update "+
				"the uptime check binding and docs/runbooks/collector-endpoints.md in the "+
				"same commit.", probe, got)
		}
	})

	t.Run("a body claiming gzip that is not gzip", func(t *testing.T) {
		in, _ := newIngestor(t)
		response := post(t, NewHTTP(in, quietLogger()), testKey, payload,
			map[string]string{"Content-Encoding": "gzip"})
		if response.StatusCode != http.StatusBadRequest {
			t.Fatalf("want 400, got %d", response.StatusCode)
		}
	})
}

func TestHealthEndpointAnswersWithoutAKey(t *testing.T) {
	in, _ := newIngestor(t)

	request := httptest.NewRequest(http.MethodGet, HealthPath, nil)
	response := httptest.NewRecorder()
	NewHTTP(in, quietLogger()).ServeHTTP(response, request)

	if response.Code != http.StatusOK {
		t.Fatalf("want 200 from %s, got %d", HealthPath, response.Code)
	}
}

func TestGRPCStatusCodesSayWhatWentWrong(t *testing.T) {
	payload := fixture(t, "claude-code", "happy-path")

	t.Run("no key", func(t *testing.T) {
		in, recorder := newIngestor(t)
		err := export(context.Background(), dialGRPC(t, in), "", payload)
		if status.Code(err) != codes.Unauthenticated {
			t.Fatalf("want Unauthenticated, got %v", err)
		}
		if len(recorder.Messages()) != 0 {
			t.Fatal("an unauthenticated export was published")
		}
	})

	t.Run("unknown key", func(t *testing.T) {
		in, _ := newIngestor(t)
		err := export(context.Background(), dialGRPC(t, in), "plb_test_ffffffffffffffffffffffffffffffff", payload)
		if status.Code(err) != codes.Unauthenticated {
			t.Fatalf("want Unauthenticated, got %v", err)
		}
	})
}

// dialGRPC starts the real gRPC server over a pipe and returns a client connection that
// speaks the same raw codec, so the test exercises the registered service descriptor
// rather than calling the handler directly. A wrong service or method name shows up
// here as Unimplemented.
func dialGRPC(t *testing.T, in *ingest.Ingestor) *grpc.ClientConn {
	t.Helper()

	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}

	server := NewGRPC(in, quietLogger())
	go func() { _ = server.Serve(listener) }()
	t.Cleanup(server.Stop)

	conn, err := grpc.NewClient(listener.Addr().String(),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithDefaultCallOptions(grpc.ForceCodec(rawCodec{})))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = conn.Close() })

	return conn
}

func export(ctx context.Context, conn *grpc.ClientConn, key string, payload []byte) error {
	if key != "" {
		ctx = metadata.AppendToOutgoingContext(ctx, APIKeyHeader, key)
	}

	request := rawMessage(payload)
	response := new(rawMessage)
	return conn.Invoke(ctx, exportMethod, &request, response)
}
