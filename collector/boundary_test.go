package main

import (
	"go/parser"
	"go/token"
	"io/fs"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

// forbiddenImports are packages that would give the collector an understanding of what
// a span means.
//
// Architecture §2.1: the collector must not parse span semantics, normalize attributes,
// or apply dialect logic. ADR-0001 adds that the protobuf bytes are never re-modelled en
// route. Both are review-enforced everywhere else in the design; here they are a test,
// because the failure mode is an import someone adds for a good local reason — "just to
// read the resource", "only to count spans" — and which no reviewer would necessarily
// connect to an architectural decision made before the file existed.
var forbiddenImports = []struct {
	prefix string
	why    string
}{
	{"go.opentelemetry.io/proto", "the generated OTLP message types: importing them makes deserializing a span possible, and possible is where §2.1 stops being enforceable"},
	{"go.opentelemetry.io/otel/semconv", "semantic conventions belong to the worker's normalization layer (§2.3), not to the data plane"},
	{"go.opentelemetry.io/collector", "the upstream Collector's processing packages carry exactly the semantics this component is defined not to have"},
}

type violation struct {
	file     string
	imported string
	why      string
}

func scanImports(root string) ([]violation, error) {
	fset := token.NewFileSet()
	var found []violation

	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.IsDir() || !strings.HasSuffix(path, ".go") {
			return nil
		}

		file, err := parser.ParseFile(fset, path, nil, parser.ImportsOnly)
		if err != nil {
			return err
		}

		for _, spec := range file.Imports {
			imported, err := strconv.Unquote(spec.Path.Value)
			if err != nil {
				return err
			}
			for _, forbidden := range forbiddenImports {
				if imported == forbidden.prefix || strings.HasPrefix(imported, forbidden.prefix+"/") {
					found = append(found, violation{file: path, imported: imported, why: forbidden.why})
				}
			}
		}
		return nil
	})

	return found, err
}

func TestTheCollectorDoesNotImportOTLPSemantics(t *testing.T) {
	found, err := scanImports(".")
	if err != nil {
		t.Fatal(err)
	}

	for _, v := range found {
		t.Errorf("%s imports %s\n  %s", v.file, v.imported, v.why)
	}
}

// TestTheBoundaryCheckCanFail proves the check above is capable of failing.
//
// The repository's gate discipline is that a control verified only against a clean tree
// is unverified (F0 spec §6): a scanner with a broken walk or a typo'd prefix passes
// silently and forever. This runs the same scan over a file that violates the rule.
func TestTheBoundaryCheckCanFail(t *testing.T) {
	dir := t.TempDir()
	source := "package fake\n\nimport _ \"" + forbiddenImports[0].prefix + "/otlp/trace/v1\"\n"

	if err := os.WriteFile(filepath.Join(dir, "fake.go"), []byte(source), 0o600); err != nil {
		t.Fatal(err)
	}

	found, err := scanImports(dir)
	if err != nil {
		t.Fatal(err)
	}
	if len(found) != 1 {
		t.Fatalf("the boundary check did not flag a deliberate violation: %d finding(s)", len(found))
	}
}
