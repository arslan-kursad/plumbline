// Package receiver exposes the two OTLP transports and hands whatever arrives to the
// ingest pipeline. Neither receiver interprets the payload.
package receiver

import (
	"compress/gzip"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"

	"github.com/arslan-kursad/plumbline/collector/internal/ingest"
)

// APIKeyHeader carries the agent's API key on both transports.
//
// A project-specific name rather than `authorization`: the value is not a bearer token
// in any standard scheme, and naming it `Bearer` would invite a proxy or a library to
// treat it as one.
const APIKeyHeader = "x-plumbline-api-key"

const (
	// TracesPath is the OTLP/HTTP path (opentelemetry-proto: /v1/traces).
	TracesPath = "/v1/traces"

	// HealthPath is a plain liveness endpoint. It is HTTP even for the gRPC listener's
	// sake: the gRPC server runs a raw-bytes codec (see grpc.go), which the standard
	// gRPC health service — a protobuf service — cannot share.
	HealthPath = "/healthz"

	// MaxRequestBytes caps what a single request may deliver *on the wire*. It exists
	// to bound memory, not to enforce the message budget: an oversized-but-legitimate
	// export is split, not refused, and that decision belongs to the splitter.
	MaxRequestBytes = 16 << 20

	// MaxDecompressedBytes caps the result of inflating a gzipped body. Without it a
	// compression bomb is an out-of-memory kill with a 200-shaped log line before it.
	MaxDecompressedBytes = 64 << 20

	protobufContentType = "application/x-protobuf"
)

// NewHTTP builds the OTLP/HTTP handler.
func NewHTTP(in *ingest.Ingestor, log *slog.Logger) http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc(HealthPath, func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		w.WriteHeader(http.StatusOK)
		_, _ = io.WriteString(w, "ok\n")
	})

	mux.HandleFunc(TracesPath, func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "only POST is accepted", http.StatusMethodNotAllowed)
			return
		}

		// Protobuf only. OTLP/HTTP also defines a JSON encoding, and accepting it here
		// would put a payload on the topic that the worker's protobuf deserializer
		// cannot read — a poison message manufactured by the collector. ADR-0001 makes
		// protobuf the interchange format; this is where that becomes enforcement
		// rather than intent.
		if ct := r.Header.Get("Content-Type"); ct != "" && !isProtobuf(ct) {
			http.Error(w,
				fmt.Sprintf("unsupported Content-Type %q: this collector accepts %s only, because the "+
					"protobuf encoding is the interchange format end to end (ADR-0001)", ct, protobufContentType),
				http.StatusUnsupportedMediaType)
			return
		}

		payload, err := readBody(r)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		result, err := in.Accept(r.Context(), r.Header.Get(APIKeyHeader), payload)
		if err != nil {
			status, message := httpStatusFor(err)
			log.Warn("export rejected",
				"transport", "http", "status", status, "api_key_id", result.APIKeyID, "error", err)
			http.Error(w, message, status)
			return
		}

		log.Info("export accepted",
			"transport", "http", "api_key_id", result.APIKeyID,
			"messages", result.Messages, "payload_bytes", len(payload))

		// An empty ExportTraceServiceResponse is zero bytes on the wire, which is what
		// a partial-success-free success looks like.
		w.Header().Set("Content-Type", protobufContentType)
		w.WriteHeader(http.StatusOK)
	})

	return mux
}

func isProtobuf(contentType string) bool {
	for i := 0; i < len(contentType); i++ {
		if contentType[i] == ';' {
			contentType = contentType[:i]
			break
		}
	}
	return trimSpace(contentType) == protobufContentType
}

func trimSpace(s string) string {
	start, end := 0, len(s)
	for start < end && (s[start] == ' ' || s[start] == '\t') {
		start++
	}
	for end > start && (s[end-1] == ' ' || s[end-1] == '\t') {
		end--
	}
	return s[start:end]
}

func readBody(r *http.Request) ([]byte, error) {
	body := http.MaxBytesReader(nil, r.Body, MaxRequestBytes)

	if r.Header.Get("Content-Encoding") == "gzip" {
		reader, err := gzip.NewReader(body)
		if err != nil {
			return nil, fmt.Errorf("body declared Content-Encoding: gzip but is not gzip: %w", err)
		}
		defer func() { _ = reader.Close() }()

		payload, err := io.ReadAll(io.LimitReader(reader, MaxDecompressedBytes))
		if err != nil {
			return nil, fmt.Errorf("reading gzipped body: %w", err)
		}
		return payload, nil
	}

	payload, err := io.ReadAll(body)
	if err != nil {
		return nil, fmt.Errorf("reading body: %w", err)
	}
	return payload, nil
}

// httpStatusFor maps pipeline errors to status codes, and returns a message that says
// what the client can do about it. An internal failure returns no detail: the caller
// cannot act on it and the log already has it.
func httpStatusFor(err error) (int, string) {
	switch {
	case errors.Is(err, ingest.ErrUnauthenticated):
		return http.StatusUnauthorized, "unknown or missing API key"
	case errors.Is(err, ingest.ErrRateLimited):
		return http.StatusTooManyRequests, "rate limit exceeded for this API key"
	case errors.Is(err, ingest.ErrTooLarge):
		return http.StatusRequestEntityTooLarge,
			"a single span exceeds the message budget; it is refused rather than truncated"
	case errors.Is(err, ingest.ErrMalformed):
		return http.StatusBadRequest, "payload is not a well-formed OTLP export request"
	default:
		return http.StatusInternalServerError, "export could not be published"
	}
}
