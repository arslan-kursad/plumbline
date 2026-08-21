package otlpwire

import (
	"bytes"
	"compress/gzip"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

// gzipSize is the sizer the collector uses in production: the size of the payload after
// compression, which is what the Pub/Sub message budget is measured in (§3.2).
func gzipSize(payload []byte) (int, error) {
	var buf bytes.Buffer
	w := gzip.NewWriter(&buf)
	if _, err := w.Write(payload); err != nil {
		return 0, err
	}
	if err := w.Close(); err != nil {
		return 0, err
	}
	return buf.Len(), nil
}

// rawSize measures the payload itself, which makes limits in tests readable: a limit of
// 500 means 500 bytes of protobuf rather than however much those bytes compress to.
func rawSize(payload []byte) (int, error) { return len(payload), nil }

func fixture(t *testing.T, dialect string) []byte {
	t.Helper()
	root, err := filepath.Abs(filepath.Join("..", "..", "..", "testdata", "fixtures"))
	if err != nil {
		t.Fatal(err)
	}
	payload, err := os.ReadFile(filepath.Join(root, dialect, "happy-path", "request.pb"))
	if err != nil {
		t.Fatalf("fixture %s: %v", dialect, err)
	}
	return payload
}

// spans walks the envelope generically and returns every span's bytes, in order. The
// test needs to know that no span was lost, changed, or duplicated, and it establishes
// that without any more knowledge of a span than the splitter has.
func spans(t *testing.T, payload []byte) [][]byte {
	t.Helper()
	var out [][]byte
	err := eachField(payload, func(field, wire int, value, _ []byte) error {
		if field != fieldResourceSpans || wire != wireBytes {
			return nil
		}
		return eachField(value, func(field, wire int, value, _ []byte) error {
			if field != fieldScopeSpans || wire != wireBytes {
				return nil
			}
			return eachField(value, func(field, wire int, value, _ []byte) error {
				if field == fieldSpans && wire == wireBytes {
					out = append(out, value)
				}
				return nil
			})
		})
	})
	if err != nil {
		t.Fatalf("walking payload: %v", err)
	}
	return out
}

func allSpans(t *testing.T, parts [][]byte) [][]byte {
	t.Helper()
	var out [][]byte
	for _, part := range parts {
		out = append(out, spans(t, part)...)
	}
	return out
}

func assertSameSpans(t *testing.T, want, got [][]byte) {
	t.Helper()
	if len(want) != len(got) {
		t.Fatalf("span count changed: want %d, got %d", len(want), len(got))
	}
	for i := range want {
		if !bytes.Equal(want[i], got[i]) {
			t.Fatalf("span %d differs after splitting: %d bytes in, %d bytes out", i, len(want[i]), len(got[i]))
		}
	}
}

func TestPayloadThatFitsIsReturnedUnchanged(t *testing.T) {
	payload := fixture(t, "claude-code")

	parts, err := Split(payload, 1<<22, gzipSize)
	if err != nil {
		t.Fatal(err)
	}

	if len(parts) != 1 {
		t.Fatalf("want 1 part, got %d", len(parts))
	}
	if &parts[0][0] != &payload[0] {
		t.Fatal("the fitting payload was re-encoded rather than passed through; " +
			"ADR-0001 byte identity depends on this path returning the input slice itself")
	}
}

func TestSplittingPreservesEverySpanExactly(t *testing.T) {
	for _, dialect := range []string{"claude-code", "dotnet-agent", "langgraph-python"} {
		t.Run(dialect, func(t *testing.T) {
			payload := fixture(t, dialect)
			want := spans(t, payload)

			// Small enough to force splitting inside the single ScopeSpans that every
			// fixture has — the deepest level the splitter reaches — and large enough
			// that the biggest single span still fits, which is where the difference
			// between splitting and refusing lies.
			const limit = 1200
			parts, err := Split(payload, limit, rawSize)
			if err != nil {
				t.Fatal(err)
			}
			if len(parts) < 2 {
				t.Fatalf("want the payload split, got %d part(s)", len(parts))
			}

			assertSameSpans(t, want, allSpans(t, parts))

			for i, part := range parts {
				if len(part) > limit {
					t.Errorf("part %d is %d bytes, over the %d-byte limit", i, len(part), limit)
				}
			}
		})
	}
}

func TestEveryPartCarriesTheResourceAndScopeContext(t *testing.T) {
	payload := fixture(t, "dotnet-agent")

	parts, err := Split(payload, 900, rawSize)
	if err != nil {
		t.Fatal(err)
	}

	for i, part := range parts {
		var sawResource, sawScope, sawSchemaURL bool
		err := eachField(part, func(field, wire int, value, _ []byte) error {
			if field != fieldResourceSpans {
				return nil
			}
			return eachField(value, func(field, wire int, value, _ []byte) error {
				switch field {
				case 1:
					sawResource = true
				case fieldScopeSpans:
					// The dotnet-agent fixture carries its schema_url on the scope,
					// which is the level that states which conventions the
					// instrumentation emitted — and the level the worker reads first.
					return eachField(value, func(field, wire int, _, _ []byte) error {
						switch field {
						case 1:
							sawScope = true
						case 3:
							sawSchemaURL = true
						}
						return nil
					})
				}
				return nil
			})
		})
		if err != nil {
			t.Fatal(err)
		}

		if !sawResource || !sawScope || !sawSchemaURL {
			t.Errorf("part %d lost context: resource=%v scope=%v schema_url=%v — a split that "+
				"drops the resource makes its spans unattributable", i, sawResource, sawScope, sawSchemaURL)
		}
	}
}

func TestASpanTooLargeToFitIsRefusedRatherThanTruncated(t *testing.T) {
	payload := fixture(t, "claude-code")

	_, err := Split(payload, 64, rawSize)
	if !errors.Is(err, ErrIndivisible) {
		t.Fatalf("want ErrIndivisible, got %v", err)
	}
}

func TestMalformedPayloadIsAnErrorNotAPanic(t *testing.T) {
	poison, err := os.ReadFile(filepath.Join("..", "..", "..", "testdata", "fixtures", "claude-code", "poison", "request.pb"))
	if err != nil {
		t.Fatal(err)
	}

	if _, err := Split(poison, 8, rawSize); err == nil {
		t.Fatal("want an error from a truncated payload, got none")
	}
}

func TestSplittingIsStableAcrossRuns(t *testing.T) {
	payload := fixture(t, "langgraph-python")

	first, err := Split(payload, 900, rawSize)
	if err != nil {
		t.Fatal(err)
	}
	second, err := Split(payload, 900, rawSize)
	if err != nil {
		t.Fatal(err)
	}

	if len(first) != len(second) {
		t.Fatalf("split is not deterministic: %d parts then %d", len(first), len(second))
	}
	for i := range first {
		if !bytes.Equal(first[i], second[i]) {
			t.Fatalf("part %d differs between runs", i)
		}
	}
}
