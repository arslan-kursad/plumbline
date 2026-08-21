// Package publisher puts payloads on the traces topic.
package publisher

import (
	"bytes"
	"compress/gzip"
	"context"
	"fmt"

	"cloud.google.com/go/pubsub/v2"
)

// Metadata is the Pub/Sub message attribute set fixed by architecture §3.2. It is a
// struct rather than a map so that a missing attribute is a compile error: the worker
// reads all four, and a message that silently lacks `api_key_id` loses its provenance.
type Metadata struct {
	// APIKeyID identifies the key that authenticated the export. Provenance; joins to
	// the key registry.
	APIKeyID string

	// SourceDialect is the dialect registered against the key — a hint only. The
	// worker's detection is authoritative and overrides it on mismatch (§5).
	SourceDialect string

	// SchemaURL is whatever the payload declared, or "" when it declared none. The
	// claude-code dialect declares none, and "" is a measurement rather than a gap.
	SchemaURL string
}

// Attributes renders the metadata as Pub/Sub message attributes.
//
// `content_encoding` is always gzip in v0.1 and is stated explicitly rather than
// assumed, so that a future uncompressed or differently-compressed payload is a value
// change rather than a silent incompatibility.
func (m Metadata) Attributes() map[string]string {
	return map[string]string{
		"api_key_id":       m.APIKeyID,
		"source_dialect":   m.SourceDialect,
		"content_encoding": "gzip",
		"schema_url":       m.SchemaURL,
	}
}

// Publisher accepts already-gzipped payloads.
type Publisher interface {
	Publish(ctx context.Context, gzipped []byte, meta Metadata) error
	Close() error
}

// PubSub publishes to a real topic, or to the emulator when PUBSUB_EMULATOR_HOST is set
// — the client library makes that choice, and the collector has no branch for it.
type PubSub struct {
	client    *pubsub.Client
	publisher *pubsub.Publisher
}

func NewPubSub(ctx context.Context, projectID, topic string) (*PubSub, error) {
	client, err := pubsub.NewClient(ctx, projectID)
	if err != nil {
		return nil, fmt.Errorf("publisher: creating client: %w", err)
	}

	return &PubSub{client: client, publisher: client.Publisher(topic)}, nil
}

func (p *PubSub) Publish(ctx context.Context, gzipped []byte, meta Metadata) error {
	result := p.publisher.Publish(ctx, &pubsub.Message{
		Data:       gzipped,
		Attributes: meta.Attributes(),
	})

	// Waiting for the server id is what makes an accepted export mean "durably queued".
	// Returning before it would turn a topic outage into a 200 and a silent data loss,
	// which is the failure mode the no-silent-degradation rule exists to prevent.
	if _, err := result.Get(ctx); err != nil {
		return fmt.Errorf("publisher: publishing to %s: %w", p.publisher.ID(), err)
	}
	return nil
}

func (p *PubSub) Close() error {
	p.publisher.Stop()
	return p.client.Close()
}

// Gzip compresses a payload with the settings the size budget was measured against.
func Gzip(payload []byte) ([]byte, error) {
	var buf bytes.Buffer
	writer := gzip.NewWriter(&buf)
	if _, err := writer.Write(payload); err != nil {
		return nil, err
	}
	if err := writer.Close(); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

// GzipSize reports the compressed size of a payload without keeping the result. The
// splitter budgets in compressed bytes, so it needs to ask this question far more often
// than it needs the bytes.
func GzipSize(payload []byte) (int, error) {
	compressed, err := Gzip(payload)
	if err != nil {
		return 0, err
	}
	return len(compressed), nil
}
