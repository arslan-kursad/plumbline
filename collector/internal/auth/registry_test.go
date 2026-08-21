package auth

import (
	"errors"
	"os"
	"path/filepath"
	"testing"
)

const validKey = "plb_test_0123456789abcdef0123456789abcdef"

func writeRegistry(t *testing.T, body string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "keys.json")
	if err := os.WriteFile(path, []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestAKnownKeyResolvesToItsIdentity(t *testing.T) {
	path := writeRegistry(t, `{"keys":[
		{"api_key_id":"local-langgraph","key_sha256":"`+HashKey(validKey)+`",
		 "source_dialect":"langgraph-python","rate_limit_per_second":50,"burst":100,"status":"active"}]}`)

	registry, err := LoadFileRegistry(path)
	if err != nil {
		t.Fatal(err)
	}

	key, err := registry.Lookup(validKey)
	if err != nil {
		t.Fatal(err)
	}
	if key.ID != "local-langgraph" || key.SourceDialect != "langgraph-python" {
		t.Fatalf("unexpected identity: %+v", key)
	}
	if key.RatePerSecond != 50 || key.Burst != 100 {
		t.Fatalf("rate limit tier not carried: %+v", key)
	}
}

func TestAnUnknownKeyIsRejected(t *testing.T) {
	path := writeRegistry(t, `{"keys":[
		{"api_key_id":"a","key_sha256":"`+HashKey(validKey)+`","status":"active"}]}`)
	registry, err := LoadFileRegistry(path)
	if err != nil {
		t.Fatal(err)
	}

	if _, err := registry.Lookup("plb_test_ffffffffffffffffffffffffffffffff"); !errors.Is(err, ErrUnknownKey) {
		t.Fatalf("want ErrUnknownKey, got %v", err)
	}
}

func TestARevokedKeyStopsResolving(t *testing.T) {
	path := writeRegistry(t, `{"keys":[
		{"api_key_id":"revoked","key_sha256":"`+HashKey(validKey)+`","status":"revoked"},
		{"api_key_id":"live","key_sha256":"`+HashKey("plb_test_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")+`","status":"active"}]}`)

	registry, err := LoadFileRegistry(path)
	if err != nil {
		t.Fatal(err)
	}

	if _, err := registry.Lookup(validKey); !errors.Is(err, ErrUnknownKey) {
		t.Fatal("a revoked key still authenticates")
	}
}

func TestAKeyOfTheWrongShapeIsRejectedBeforeHashing(t *testing.T) {
	path := writeRegistry(t, `{"keys":[
		{"api_key_id":"a","key_sha256":"`+HashKey(validKey)+`","status":"active"}]}`)
	registry, err := LoadFileRegistry(path)
	if err != nil {
		t.Fatal(err)
	}

	for _, presented := range []string{
		"",
		"hunter2",
		"plb_test_short",
		"plb_LOCAL_0123456789abcdef0123456789abcdef",
		" plb_test_0123456789abcdef0123456789abcdef",
	} {
		if _, err := registry.Lookup(presented); !errors.Is(err, ErrUnknownKey) {
			t.Errorf("%q was not rejected", presented)
		}
	}
}

func TestARegistryWithNoActiveKeysIsAStartupFailure(t *testing.T) {
	path := writeRegistry(t, `{"keys":[
		{"api_key_id":"a","key_sha256":"`+HashKey(validKey)+`","status":"revoked"}]}`)

	if _, err := LoadFileRegistry(path); err == nil {
		t.Fatal("want a startup error; a collector with no usable key rejects everything " +
			"and should say so at boot rather than at the first request")
	}
}

func TestAMalformedHashIsAStartupFailure(t *testing.T) {
	path := writeRegistry(t, `{"keys":[{"api_key_id":"a","key_sha256":"not-hex","status":"active"}]}`)

	if _, err := LoadFileRegistry(path); err == nil {
		t.Fatal("want a startup error for an unusable hash")
	}
}

func TestHashKeyIsTheRegistryRepresentation(t *testing.T) {
	// Pinned, because a change to the hashing scheme is a migration: every issued key in
	// every environment stops resolving, and the failure looks like "all agents are
	// suddenly unauthorized" rather than like a code change.
	const want = "1387db43ca4123121612ebe2bbbbb1fee838d46aa4f3a4c0f49effb9faf6b39a"

	if got := HashKey(validKey); got != want {
		t.Fatalf("HashKey changed:\n  want %s\n  got  %s", want, got)
	}
}
