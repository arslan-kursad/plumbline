package main

import (
	"strings"
	"testing"

	"github.com/arslan-kursad/plumbline/collector/internal/auth"
)

// The generated key has to be one the data plane accepts. This is the assertion the
// tool exists to keep true; everything else it does is a Firestore write.
func TestGeneratedKeysAreAcceptedByTheCollector(t *testing.T) {
	for _, environment := range auth.IssuedEnvironments {
		key, err := generate(environment)
		if err != nil {
			t.Fatalf("generate(%q): %v", environment, err)
		}
		if !auth.HasIssuableShape(key) {
			t.Fatalf("generate(%q) produced %q, which the collector would reject", environment, key)
		}
		if !strings.HasPrefix(key, auth.KeyPrefix+environment+"_") {
			t.Fatalf("generate(%q) produced %q, wrong environment marker", environment, key)
		}
	}
}

func TestTwoKeysAreNotTheSameKey(t *testing.T) {
	first, err := generate("live")
	if err != nil {
		t.Fatal(err)
	}
	second, err := generate("live")
	if err != nil {
		t.Fatal(err)
	}
	if first == second {
		t.Fatal("two generated keys are identical; the source of randomness is not")
	}
}

// `test` is reserved so documentation and fixtures can carry key-shaped strings without
// Gate F needing an exclusion list. A tool that could issue one would break that.
func TestTheReservedEnvironmentCannotBeIssued(t *testing.T) {
	if err := validate("p", "some-key", "test", 10, 20); err == nil {
		t.Fatal("validate accepted the reserved `test` environment")
	}
	if auth.HasIssuableShape("plb_test_0123456789abcdef0123456789abcdef") {
		t.Fatal("a test-marked key reports as issuable")
	}
}

func TestMalformedInputIsRefusedBeforeAnythingIsGenerated(t *testing.T) {
	cases := []struct {
		name                     string
		project, id, environment string
		rate                     float64
		burst                    int
	}{
		{"no project", "", "adjudicator", "live", 10, 20},
		{"no id", "p", "", "live", 10, 20},
		{"id with underscores", "p", "bad_id", "live", 10, 20},
		{"id too short", "p", "ab", "live", 10, 20},
		{"uppercase id", "p", "Adjudicator", "live", 10, 20},
		{"zero rate", "p", "adjudicator", "live", 0, 20},
		{"negative burst", "p", "adjudicator", "live", 10, -1},
	}

	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if err := validate(c.project, c.id, c.environment, c.rate, c.burst); err == nil {
				t.Fatal("accepted")
			}
		})
	}
}
