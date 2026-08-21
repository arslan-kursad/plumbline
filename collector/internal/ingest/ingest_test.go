package ingest

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/arslan-kursad/plumbline/collector/internal/auth"
	"github.com/arslan-kursad/plumbline/collector/internal/publisher"
	"github.com/arslan-kursad/plumbline/collector/internal/ratelimit"
)

const testKey = "plb_test_0123456789abcdef0123456789abcdef"

func fixture(t *testing.T, dialect, kind string) []byte {
	t.Helper()
	payload, err := os.ReadFile(filepath.Join("..", "..", "..", "testdata", "fixtures", dialect, kind, "request.pb"))
	if err != nil {
		t.Fatal(err)
	}
	return payload
}

func newIngestor(t *testing.T, maxBytes int) (*Ingestor, *publisher.Recorder) {
	t.Helper()
	return newIngestorWithTier(t, maxBytes, 100, 100)
}

func newIngestorWithTier(t *testing.T, maxBytes int, rate float64, burst int) (*Ingestor, *publisher.Recorder) {
	t.Helper()

	path := filepath.Join(t.TempDir(), "keys.json")
	body := fmt.Sprintf(`{"keys":[{"api_key_id":"local-claude","key_sha256":%q,
		"source_dialect":"claude-code","rate_limit_per_second":%v,"burst":%d,"status":"active"}]}`,
		auth.HashKey(testKey), rate, burst)
	if err := os.WriteFile(path, []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}

	registry, err := auth.LoadFileRegistry(path)
	if err != nil {
		t.Fatal(err)
	}

	recorder := &publisher.Recorder{}
	return &Ingestor{
		Registry:           registry,
		Limiter:            ratelimit.New(time.Now),
		Publisher:          recorder,
		MaxCompressedBytes: maxBytes,
	}, recorder
}

func TestAnAcceptedExportIsPublishedUnchanged(t *testing.T) {
	in, recorder := newIngestor(t, 4<<20)
	payload := fixture(t, "claude-code", "happy-path")

	result, err := in.Accept(context.Background(), testKey, payload)
	if err != nil {
		t.Fatal(err)
	}
	if result.Messages != 1 {
		t.Fatalf("want one message, got %d", result.Messages)
	}

	messages := recorder.Messages()
	if got := messages[0].Payload; string(got) != string(payload) {
		t.Fatalf("payload changed in transit: %d bytes in, %d bytes out", len(payload), len(got))
	}
}

func TestTheMessageCarriesTheContractedAttributes(t *testing.T) {
	in, recorder := newIngestor(t, 4<<20)

	if _, err := in.Accept(context.Background(), testKey, fixture(t, "dotnet-agent", "happy-path")); err != nil {
		t.Fatal(err)
	}

	attrs := recorder.Messages()[0].Metadata.Attributes()
	want := map[string]string{
		"api_key_id":       "local-claude",
		"source_dialect":   "claude-code", // the key's registration: a hint, not a verdict
		"content_encoding": "gzip",
		"schema_url":       "https://opentelemetry.io/schemas/1.28.0",
	}

	if len(attrs) != len(want) {
		t.Fatalf("attribute set differs: %v", attrs)
	}
	for key, value := range want {
		if attrs[key] != value {
			t.Errorf("%s: want %q, got %q", key, value, attrs[key])
		}
	}
}

func TestTheDialectHintComesFromTheKeyNotThePayload(t *testing.T) {
	// The key is registered as claude-code; the payload is a langgraph one. The
	// collector must not notice, because noticing would mean reading span semantics.
	// The worker's detection is what resolves this (§5), and the mismatch is its
	// business, not the collector's.
	in, recorder := newIngestor(t, 4<<20)

	if _, err := in.Accept(context.Background(), testKey, fixture(t, "langgraph-python", "happy-path")); err != nil {
		t.Fatal(err)
	}

	if got := recorder.Messages()[0].Metadata.SourceDialect; got != "claude-code" {
		t.Fatalf("want the registered hint claude-code, got %q", got)
	}
}

func TestAnOversizedExportIsSplitAndEverySpanSurvives(t *testing.T) {
	// The langgraph fixture is 850 bytes gzipped; at 600 the splitter has to divide it
	// and each span still fits with its context. Measured rather than guessed: at 500
	// the smallest possible message no longer fits and the correct answer becomes a
	// refusal, which is a different test.
	const budget = 600
	in, recorder := newIngestor(t, budget)
	payload := fixture(t, "langgraph-python", "happy-path")

	result, err := in.Accept(context.Background(), testKey, payload)
	if err != nil {
		t.Fatal(err)
	}
	if result.Messages < 2 {
		t.Fatalf("want the export split, got %d message(s)", result.Messages)
	}

	var total int
	for _, message := range recorder.Messages() {
		if len(message.Compressed) > budget {
			t.Errorf("a published message is %d compressed bytes, over the %d-byte budget",
				len(message.Compressed), budget)
		}
		total += len(message.Payload)
	}
	if total <= len(payload) {
		t.Fatalf("split parts total %d bytes, which cannot exceed the %d-byte input: "+
			"each part repeats the resource and scope context", total, len(payload))
	}
}

func TestAnUnknownKeyIsRejectedBeforeAnythingIsPublished(t *testing.T) {
	in, recorder := newIngestor(t, 4<<20)

	_, err := in.Accept(context.Background(), "plb_test_ffffffffffffffffffffffffffffffff", fixture(t, "claude-code", "happy-path"))
	if !errors.Is(err, ErrUnauthenticated) {
		t.Fatalf("want ErrUnauthenticated, got %v", err)
	}
	if len(recorder.Messages()) != 0 {
		t.Fatal("an unauthenticated export reached the topic")
	}
}

func TestAnUnauthenticatedCallerCannotAllocateARateLimitBucket(t *testing.T) {
	in, _ := newIngestor(t, 4<<20)

	for i := 0; i < 50; i++ {
		_, _ = in.Accept(context.Background(), "plb_test_ffffffffffffffffffffffffffffffff", []byte{0x01})
	}

	if got := in.Limiter.Keys(); got != 0 {
		t.Fatalf("want no buckets from unauthenticated traffic, got %d: authentication has to "+
			"come first or an anonymous caller can grow the limiter's map at will", got)
	}
}

func TestExhaustingTheBucketRefusesFurtherExports(t *testing.T) {
	// One token per second, burst five: the loop finishes long before a sixth token
	// exists, so the count published is the burst and not a race with the clock.
	in, recorder := newIngestorWithTier(t, 4<<20, 1, 5)
	payload := fixture(t, "claude-code", "unmapped-attributes")

	var lastErr error
	for i := 0; i < 20; i++ {
		if _, err := in.Accept(context.Background(), testKey, payload); err != nil {
			lastErr = err
			break
		}
	}

	if !errors.Is(lastErr, ErrRateLimited) {
		t.Fatalf("want ErrRateLimited within 20 requests at burst 5, got %v", lastErr)
	}
	if got := len(recorder.Messages()); got != 5 {
		t.Fatalf("want exactly the burst of 5 published, got %d", got)
	}
}

func TestAMalformedPayloadIsRejectedWhenItCannotBeSplit(t *testing.T) {
	// The poison payload is a truncated protobuf. At a budget it already fits, the
	// collector publishes it unread — deliberately: deciding a payload is malformed
	// would mean parsing it, and the worker's DLQ path is what handles poison (§3.4).
	in, recorder := newIngestor(t, 4<<20)
	poison := fixture(t, "claude-code", "poison")

	if _, err := in.Accept(context.Background(), testKey, poison); err != nil {
		t.Fatalf("a small malformed payload should pass through unread, got %v", err)
	}
	if len(recorder.Messages()) != 1 {
		t.Fatal("the poison payload was not forwarded to the topic")
	}

	// Below the budget it has to be split, which is the first moment the envelope is
	// walked and the first moment truncation is detectable at all.
	in, _ = newIngestor(t, 16)
	if _, err := in.Accept(context.Background(), testKey, poison); !errors.Is(err, ErrMalformed) {
		t.Fatalf("want ErrMalformed, got %v", err)
	}
}

func TestAnEmptyBodyIsRejected(t *testing.T) {
	in, _ := newIngestor(t, 4<<20)

	if _, err := in.Accept(context.Background(), testKey, nil); !errors.Is(err, ErrMalformed) {
		t.Fatalf("want ErrMalformed, got %v", err)
	}
}

func TestAPublishFailureIsReportedRatherThanSwallowed(t *testing.T) {
	in, recorder := newIngestor(t, 4<<20)
	recorder.Err = errors.New("topic unavailable")

	if _, err := in.Accept(context.Background(), testKey, fixture(t, "claude-code", "happy-path")); err == nil {
		t.Fatal("a failed publish returned success: the export would be lost with a 200 in the log")
	}
}
