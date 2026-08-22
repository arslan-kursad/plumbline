// keyctl issues plumbline API keys.
//
// It generates a key, prints the plaintext **once**, and writes only the hash and its
// metadata to Firestore. The plaintext is never stored, never logged, and never
// recoverable: losing it means issuing another key, which is the intended shape of a
// show-once secret (F2 spec D5).
//
// It lives inside the collector module rather than at `tools/keyctl` as the directive
// sketched, and the reason is not filing convenience. A key this tool issues must be a
// key the collector accepts, and the only mechanical guarantee of that is sharing the
// code that defines the format and the hash — `internal/auth` is importable from here
// and from nowhere else. A tool in a separate module would restate the contract, and a
// restated contract drifts.
//
//	keyctl -project PROJECT -id adjudicator-prod -dialect langgraph
//	keyctl -project PROJECT -id local-dev -environment local -dry-run
package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"flag"
	"fmt"
	"os"
	"regexp"
	"slices"
	"time"

	"cloud.google.com/go/firestore"

	"github.com/arslan-kursad/plumbline/collector/internal/auth"
)

// One document per key, keyed by api_key_id. The collection name lives with the format
// contract in internal/auth, because the data plane reads what this tool writes.
const collection = auth.Collection

var idShape = regexp.MustCompile(`^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$`)

func main() {
	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "keyctl: %v\n", err)
		os.Exit(1)
	}
}

func run() error {
	var (
		project     = flag.String("project", "", "GCP project holding the Firestore database (required)")
		database    = flag.String("database", "(default)", "Firestore database name")
		id          = flag.String("id", "", "api_key_id: stable, human-readable, appears on every span (required)")
		environment = flag.String("environment", "live", "key environment marker: "+fmt.Sprint(auth.IssuedEnvironments))
		dialect     = flag.String("dialect", "", "registered source dialect hint (advisory; the worker's detection is authoritative)")
		rate        = flag.Float64("rate", 10, "per-key rate limit, requests per second")
		burst       = flag.Int("burst", 20, "per-key rate limit burst")
		dryRun      = flag.Bool("dry-run", false, "print what would be written; generate nothing, write nothing")
	)
	flag.Parse()

	if err := validate(*project, *id, *environment, *rate, *burst); err != nil {
		return err
	}

	if *dryRun {
		fmt.Printf("would create %s/%s in %s: dialect=%q rate=%.1f/s burst=%d status=active\n",
			collection, *id, *project, *dialect, *rate, *burst)
		fmt.Println("dry run: no key generated, nothing written")
		return nil
	}

	plaintext, err := generate(*environment)
	if err != nil {
		return err
	}

	ctx := context.Background()
	client, err := firestore.NewClientWithDatabase(ctx, *project, *database)
	if err != nil {
		return fmt.Errorf("connecting to Firestore: %w", err)
	}
	defer client.Close()

	document := map[string]any{
		"api_key_id":            *id,
		"key_sha256":            auth.HashKey(plaintext),
		"source_dialect":        *dialect,
		"rate_limit_per_second": *rate,
		"burst":                 *burst,
		"status":                "active",
		"issued_at":             time.Now().UTC(),
	}

	// Create, not Set. An api_key_id that already exists belongs to a key some agent may
	// still be presenting, and overwriting its hash would revoke that key silently — at
	// the next collector start, with no error anywhere near the person who caused it.
	if _, err := client.Collection(collection).Doc(*id).Create(ctx, document); err != nil {
		return fmt.Errorf("creating %s/%s (does it already exist?): %w", collection, *id, err)
	}

	// The plaintext goes to stdout alone, so `keyctl ... > key.txt` captures the key and
	// nothing else. Every word of explanation goes to stderr.
	fmt.Fprintf(os.Stderr, "issued %s/%s — printed once, stored nowhere:\n", collection, *id)
	fmt.Println(plaintext)
	fmt.Fprintln(os.Stderr, "Put it where the agent can read it. It cannot be recovered: "+
		"a lost key is reissued, not looked up.")

	return nil
}

func validate(project, id, environment string, rate float64, burst int) error {
	if project == "" || id == "" {
		flag.Usage()
		return errors.New("-project and -id are required")
	}
	if !idShape.MatchString(id) {
		return fmt.Errorf("api_key_id %q: lowercase letters, digits and hyphens, 3-64 characters", id)
	}
	if !slices.Contains(auth.IssuedEnvironments, environment) {
		// `test` is deliberately not issuable: it is the marker documentation and
		// fixtures carry, and Gate F matches only markers a real key can have.
		return fmt.Errorf("environment %q is not issued; choose one of %v", environment, auth.IssuedEnvironments)
	}
	if rate <= 0 || burst <= 0 {
		return errors.New("-rate and -burst must be positive")
	}
	return nil
}

// generate returns a key in the format internal/auth enforces, from crypto/rand.
func generate(environment string) (string, error) {
	raw := make([]byte, 16)
	if _, err := rand.Read(raw); err != nil {
		return "", fmt.Errorf("reading random bytes: %w", err)
	}

	key := auth.KeyPrefix + environment + "_" + hex.EncodeToString(raw)

	// The tool asserts the data plane would accept what it just issued, rather than
	// trusting that two places agree about a format.
	if !auth.HasIssuableShape(key) {
		return "", errors.New("generated a key the collector would reject; the format contract has drifted")
	}

	return key, nil
}
