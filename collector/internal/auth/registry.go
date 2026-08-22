// Package auth resolves an API key presented by an agent to the identity the rest of
// the collector works with.
//
// The collector never sees a stored plaintext key: the registry holds SHA-256 hashes
// (architecture §6.3, "generated once, shown once, stored hashed"), and authentication
// hashes what was presented and compares. In the cloud the registry is Firestore
// (§4.2); locally it is a file, behind the same interface (F1 directive D5).
package auth

import (
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"regexp"
	"strings"
)

// ErrUnknownKey is returned for a key that is absent, revoked, or malformed. It is
// deliberately one error for all three: telling a caller which of those applies tells an
// attacker which guesses were close.
var ErrUnknownKey = errors.New("auth: unknown API key")

// Key is what a successful authentication yields.
type Key struct {
	// ID is the `api_key_id` carried on every published message (§3.2). It is
	// provenance, not a secret, and it appears in logs and in BigQuery rows.
	ID string

	// SourceDialect is the dialect registered against this key. It travels as a
	// *hint* only: the worker's detection is authoritative and overrides it (§5).
	SourceDialect string

	// RatePerSecond and Burst configure this key's token bucket.
	RatePerSecond float64
	Burst         int
}

// Registry answers "who presented this key".
//
// One method, because that is the whole contract the data plane needs; key issuance,
// revocation and rotation are control-plane operations that do not belong on the hot
// path.
type Registry interface {
	Lookup(presented string) (Key, error)
}

// Collection is the Firestore collection holding one document per issued key, keyed by
// api_key_id. Shared by the data plane (FirestoreRegistry) and the issuing tool
// (cmd/keyctl) for the same reason the key format is (W1.7): two places agreeing about
// a name by inspection is how a tool writes keys the collector never reads.
const Collection = "api_keys"

// KeyPrefix is the fixed prefix every issued plumbline key carries.
//
// GitHub's non-provider secret-scanning patterns require a paid plan, which the
// zero-cost invariant forbids, and provider patterns would never match a plumbline key
// because it carries no vendor signature (issue #19). A prefix chosen by this project
// makes a leaked key matchable by this project's own gate framework instead, at no cost.
// It is fixed here, before any key is issued, because retrofitting one afterwards is a
// migration.
//
// Format: `plb_<environment>_<32 lowercase hex>` — sixteen random bytes, hex encoded.
//
// Two environment markers are issued: `local` and `live`. **`test` is reserved and is
// never issued**, which is what lets test data and documentation carry realistic
// key-shaped strings while the gate in `scripts/ci/invariant-gates.sh` matches only the
// markers a real key can have. The alternative — a gate with an exclusion list for the
// test files — is the shape this repository refuses on principle, because an exclusion
// list is how a control quietly stops covering the file that matters.
const KeyPrefix = "plb_"

// IssuedEnvironments are the markers a real key may carry. Keep this in step with the
// gate pattern: they are two statements of one rule, and the gate is the one that has
// to be right.
var IssuedEnvironments = []string{"local", "live"}

var keyShape = regexp.MustCompile(`^plb_[a-z]{3,8}_[0-9a-f]{32}$`)

// HasIssuableShape reports whether a string is shaped like a key this project issues.
//
// Exported for the issuing tool (cmd/keyctl), which asserts that what it just generated
// is something the data plane would accept. Two places agreeing about a format by
// inspection is how a tool ships keys that fail at an agent, in production, on someone
// else's clock; one function, called by both, cannot drift from itself.
//
// Shape only. It says nothing about whether the key is registered, active, or real —
// Lookup answers that, and a caller that treats this as authentication has misread it.
func HasIssuableShape(presented string) bool {
	if !keyShape.MatchString(presented) {
		return false
	}

	for _, environment := range IssuedEnvironments {
		if strings.HasPrefix(presented, KeyPrefix+environment+"_") {
			return true
		}
	}

	// `test` matches keyShape and is never issued (see IssuedEnvironments).
	return false
}

// FileRegistry is the local stand-in for the Firestore key registry: a JSON file of
// hashed keys, mounted into the container.
type FileRegistry struct {
	keyset
}

// storedKey is one registry entry as both backends store it. The JSON tags are the
// file format; the firestore tags are the document fields cmd/keyctl writes. They are
// the same names on purpose — one entry shape, two encodings of it.
type storedKey struct {
	APIKeyID      string  `json:"api_key_id" firestore:"api_key_id"`
	KeySHA256     string  `json:"key_sha256" firestore:"key_sha256"`
	SourceDialect string  `json:"source_dialect" firestore:"source_dialect"`
	RatePerSecond float64 `json:"rate_limit_per_second" firestore:"rate_limit_per_second"`
	Burst         int     `json:"burst" firestore:"burst"`
	Status        string  `json:"status" firestore:"status"`

	hash []byte
}

// keyset is the in-memory registry both backends resolve to: validated active keys and
// the constant-time lookup over them. Loading and looking up are separate concerns —
// the backends differ only in where the entries come from.
type keyset struct {
	keys []storedKey
}

// buildKeyset validates entries into a keyset. Inactive keys are skipped; a malformed
// entry is an error rather than a skip, because a registry that quietly drops the entry
// with the typo is a collector that refuses one agent's traffic with no error anywhere
// near the person who caused it. `source` names the registry in errors.
func buildKeyset(entries []storedKey, source string) (keyset, error) {
	var set keyset
	for i, key := range entries {
		if key.APIKeyID == "" {
			return keyset{}, fmt.Errorf("auth: %s entry %d has no api_key_id", source, i)
		}

		hash, err := hex.DecodeString(strings.TrimSpace(key.KeySHA256))
		if err != nil || len(hash) != sha256.Size {
			return keyset{}, fmt.Errorf("auth: key %q has no valid sha256 hash (want %d hex-encoded bytes)",
				key.APIKeyID, sha256.Size)
		}

		if key.Status != "active" {
			continue
		}

		key.hash = hash
		set.keys = append(set.keys, key)
	}

	if len(set.keys) == 0 {
		return keyset{}, fmt.Errorf("auth: %s holds no active keys", source)
	}

	return set, nil
}

// LoadFileRegistry reads the registry file once, at startup.
//
// Once, not per request: a data-plane component that re-reads a file on the hot path
// buys hot-reload nobody asked for and pays for it in latency and in an unbounded
// failure mode when the file is briefly unreadable. Rotating a key is a redeploy, which
// with min-instances=0 costs no money and no downtime.
func LoadFileRegistry(path string) (*FileRegistry, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("auth: reading key registry: %w", err)
	}

	var file struct {
		Keys []storedKey `json:"keys"`
	}
	if err := json.Unmarshal(raw, &file); err != nil {
		return nil, fmt.Errorf("auth: parsing key registry %s: %w", path, err)
	}

	set, err := buildKeyset(file.Keys, fmt.Sprintf("key registry %s", path))
	if err != nil {
		return nil, err
	}

	return &FileRegistry{keyset: set}, nil
}

// Lookup hashes the presented key and compares it against every active entry in
// constant time.
//
// Every entry is compared even after a match, so the work done does not depend on which
// key was presented or on how far down the list it sits. With a registry of this size
// the cost is irrelevant; the property is not.
func (r *keyset) Lookup(presented string) (Key, error) {
	if !keyShape.MatchString(presented) {
		return Key{}, ErrUnknownKey
	}

	sum := sha256.Sum256([]byte(presented))

	var found *storedKey
	for i := range r.keys {
		if subtle.ConstantTimeCompare(sum[:], r.keys[i].hash) == 1 {
			found = &r.keys[i]
		}
	}

	if found == nil {
		return Key{}, ErrUnknownKey
	}

	return Key{
		ID:            found.APIKeyID,
		SourceDialect: found.SourceDialect,
		RatePerSecond: found.RatePerSecond,
		Burst:         found.Burst,
	}, nil
}

// HashKey returns the registry representation of a plaintext key. It exists so that key
// seeding has one implementation rather than a shell one-liner that has to agree with
// this file.
func HashKey(presented string) string {
	sum := sha256.Sum256([]byte(presented))
	return hex.EncodeToString(sum[:])
}
