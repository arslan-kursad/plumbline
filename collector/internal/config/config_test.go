package config

import (
	"testing"
	"time"
)

func setRequired(t *testing.T) {
	t.Helper()
	t.Setenv("PLUMBLINE_KEY_REGISTRY", "/etc/plumbline/keys.json")
	t.Setenv("PLUMBLINE_PUBSUB_PROJECT", "plumbline-local")
	t.Setenv("PLUMBLINE_PUBSUB_TOPIC", "traces")
}

func TestDefaultsAreTheOTLPPorts(t *testing.T) {
	setRequired(t)

	cfg, err := FromEnv()
	if err != nil {
		t.Fatal(err)
	}
	if cfg.HTTPAddr != ":4318" || cfg.GRPCAddr != ":4317" {
		t.Fatalf("want the OTLP default ports, got %s and %s", cfg.HTTPAddr, cfg.GRPCAddr)
	}
	if cfg.MaxCompressedBytes != 4<<20 {
		t.Fatalf("want the 4 MiB working target from architecture §3.2, got %d", cfg.MaxCompressedBytes)
	}
}

func TestEachRequiredSettingFailsAtStartupWhenAbsent(t *testing.T) {
	for _, missing := range []string{
		"PLUMBLINE_KEY_REGISTRY",
		"PLUMBLINE_PUBSUB_PROJECT",
		"PLUMBLINE_PUBSUB_TOPIC",
	} {
		t.Run(missing, func(t *testing.T) {
			setRequired(t)
			t.Setenv(missing, "")

			if _, err := FromEnv(); err == nil {
				t.Fatalf("%s was absent and the collector started anyway: it would boot healthy "+
					"and reject every export, with the health check saying it is fine", missing)
			}
		})
	}
}

func TestExactlyOneKeyRegistryBackendIsConfigured(t *testing.T) {
	t.Run("firestore alone is enough", func(t *testing.T) {
		setRequired(t)
		t.Setenv("PLUMBLINE_KEY_REGISTRY", "")
		t.Setenv("PLUMBLINE_KEY_FIRESTORE_PROJECT", "plumbline-prod")

		cfg, err := FromEnv()
		if err != nil {
			t.Fatal(err)
		}
		if cfg.KeyFirestoreDatabase != "(default)" {
			t.Fatalf("want the default Firestore database, got %q", cfg.KeyFirestoreDatabase)
		}
	})

	t.Run("both backends is a startup failure", func(t *testing.T) {
		// Ambiguity refused rather than resolved: whichever backend a guess picked,
		// the collector would look configured while authenticating against the other
		// one's keys.
		setRequired(t)
		t.Setenv("PLUMBLINE_KEY_FIRESTORE_PROJECT", "plumbline-prod")

		if _, err := FromEnv(); err == nil {
			t.Fatal("a file registry and a Firestore project were both set and the collector started anyway")
		}
	})
}

func TestAnUnparsableOverrideIsRefusedRatherThanIgnored(t *testing.T) {
	for name, value := range map[string]string{
		"PLUMBLINE_MAX_COMPRESSED_BYTES":          "4MiB",
		"PLUMBLINE_MAX_COMPRESSED_BYTES/negative": "-1",
		"PLUMBLINE_SHUTDOWN_TIMEOUT":              "fifteen seconds",
	} {
		t.Run(name, func(t *testing.T) {
			setRequired(t)
			key := name
			if i := len(name) - len("/negative"); i > 0 && name[i:] == "/negative" {
				key = name[:i]
			}
			t.Setenv(key, value)

			if _, err := FromEnv(); err == nil {
				t.Fatalf("%s=%q was accepted; a silently ignored size budget is how a "+
					"message limit stops being enforced", key, value)
			}
		})
	}
}

func TestOverridesAreApplied(t *testing.T) {
	setRequired(t)
	t.Setenv("PLUMBLINE_HTTP_ADDR", ":8080")
	t.Setenv("PLUMBLINE_MAX_COMPRESSED_BYTES", "1048576")
	t.Setenv("PLUMBLINE_SHUTDOWN_TIMEOUT", "5s")

	cfg, err := FromEnv()
	if err != nil {
		t.Fatal(err)
	}
	if cfg.HTTPAddr != ":8080" || cfg.MaxCompressedBytes != 1<<20 || cfg.ShutdownTimeout != 5*time.Second {
		t.Fatalf("overrides not applied: %+v", cfg)
	}
}
