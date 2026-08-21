package otlpwire

import (
	"os"
	"path/filepath"
	"testing"
)

func TestSchemaURLPrefersTheScopeLevel(t *testing.T) {
	for _, tc := range []struct{ dialect, want string }{
		{"dotnet-agent", "https://opentelemetry.io/schemas/1.28.0"},
		{"unknown", "https://opentelemetry.io/schemas/1.41.0"},
		{"claude-code", ""},
		{"langgraph-python", ""},
	} {
		t.Run(tc.dialect, func(t *testing.T) {
			payload, err := os.ReadFile(filepath.Join("..", "..", "..", "testdata", "fixtures", tc.dialect, "happy-path", "request.pb"))
			if err != nil {
				t.Fatal(err)
			}
			if got := SchemaURL(payload); got != tc.want {
				t.Fatalf("want %q, got %q", tc.want, got)
			}
		})
	}
}
