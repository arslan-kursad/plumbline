// Package config reads the collector's configuration from the environment.
//
// Environment only, no config file in the image (12-factor, F1 spec W3). A collector
// that reads a file has a file to mount, a path to get wrong, and a second place for a
// setting to live; the one file it does read — the key registry — is data rather than
// configuration, and its path is itself an environment variable.
package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

// Config is the whole of it. Every field has a default that runs locally except the
// ones whose wrong value would be silent: the registry path, the project and the topic.
type Config struct {
	HTTPAddr string
	GRPCAddr string

	KeyRegistryPath string

	ProjectID string
	Topic     string

	// MaxCompressedBytes is the per-message budget the splitter works to. Architecture
	// §3.2 sets a working target of 4 MiB against a 10 MB Pub/Sub push limit; the
	// headroom absorbs the base64 expansion of the push envelope, which is applied to
	// the message after the collector has finished with it.
	MaxCompressedBytes int

	ShutdownTimeout time.Duration
}

const (
	DefaultHTTPAddr           = ":4318"
	DefaultGRPCAddr           = ":4317"
	DefaultMaxCompressedBytes = 4 << 20
	DefaultShutdownTimeout    = 15 * time.Second
)

func FromEnv() (Config, error) {
	cfg := Config{
		HTTPAddr:           env("PLUMBLINE_HTTP_ADDR", DefaultHTTPAddr),
		GRPCAddr:           env("PLUMBLINE_GRPC_ADDR", DefaultGRPCAddr),
		KeyRegistryPath:    os.Getenv("PLUMBLINE_KEY_REGISTRY"),
		ProjectID:          os.Getenv("PLUMBLINE_PUBSUB_PROJECT"),
		Topic:              os.Getenv("PLUMBLINE_PUBSUB_TOPIC"),
		MaxCompressedBytes: DefaultMaxCompressedBytes,
		ShutdownTimeout:    DefaultShutdownTimeout,
	}

	if raw := os.Getenv("PLUMBLINE_MAX_COMPRESSED_BYTES"); raw != "" {
		value, err := strconv.Atoi(raw)
		if err != nil || value <= 0 {
			return Config{}, fmt.Errorf("config: PLUMBLINE_MAX_COMPRESSED_BYTES must be a positive integer, got %q", raw)
		}
		cfg.MaxCompressedBytes = value
	}

	if raw := os.Getenv("PLUMBLINE_SHUTDOWN_TIMEOUT"); raw != "" {
		value, err := time.ParseDuration(raw)
		if err != nil || value <= 0 {
			return Config{}, fmt.Errorf("config: PLUMBLINE_SHUTDOWN_TIMEOUT must be a positive duration, got %q", raw)
		}
		cfg.ShutdownTimeout = value
	}

	// Missing required settings fail at startup rather than at the first request: a
	// collector that boots healthy and then rejects everything is the worse failure,
	// because the health check says it is fine.
	for name, value := range map[string]string{
		"PLUMBLINE_KEY_REGISTRY":   cfg.KeyRegistryPath,
		"PLUMBLINE_PUBSUB_PROJECT": cfg.ProjectID,
		"PLUMBLINE_PUBSUB_TOPIC":   cfg.Topic,
	} {
		if value == "" {
			return Config{}, fmt.Errorf("config: %s is required", name)
		}
	}

	return cfg, nil
}

func env(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}
