// Package ingest is the collector's pipeline: authenticate, rate limit, split, compress,
// publish. Both receivers hand a payload to the same Ingestor, so the HTTP and gRPC
// paths cannot drift into two different sets of rules.
package ingest

import (
	"context"
	"errors"
	"fmt"

	"github.com/arslan-kursad/plumbline/collector/internal/auth"
	"github.com/arslan-kursad/plumbline/collector/internal/otlpwire"
	"github.com/arslan-kursad/plumbline/collector/internal/publisher"
	"github.com/arslan-kursad/plumbline/collector/internal/ratelimit"
)

// Errors the receivers translate into their protocol's status codes. Anything else is
// an internal failure and is reported as one.
var (
	ErrUnauthenticated = errors.New("ingest: unknown or missing API key")
	ErrRateLimited     = errors.New("ingest: rate limit exceeded")
	ErrTooLarge        = errors.New("ingest: payload cannot be split small enough")
	ErrMalformed       = errors.New("ingest: payload is not a well-formed OTLP export request")
)

// Ingestor holds the pipeline's collaborators. It is safe for concurrent use.
type Ingestor struct {
	Registry           auth.Registry
	Limiter            *ratelimit.Limiter
	Publisher          publisher.Publisher
	MaxCompressedBytes int
}

// Result reports what an accepted export became, for logging and for the tests that
// assert splitting happened without reaching into the publisher.
type Result struct {
	APIKeyID string
	Messages int
}

// Accept runs one export request through the pipeline.
//
// The order is deliberate: authentication before rate limiting, because a bucket is a
// per-key resource and an unauthenticated caller must not be able to allocate one;
// rate limiting before splitting, because splitting is the expensive step and an
// over-quota caller should not be able to buy CPU with a large payload.
//
// The payload is never parsed for meaning here. It is measured, possibly regrouped at
// the envelope level, compressed, and published — see the otlpwire package for what
// "envelope level" is allowed to mean.
func (i *Ingestor) Accept(ctx context.Context, presentedKey string, payload []byte) (Result, error) {
	key, err := i.Registry.Lookup(presentedKey)
	if err != nil {
		return Result{}, ErrUnauthenticated
	}

	if !i.Limiter.Allow(key.ID, key.RatePerSecond, key.Burst) {
		return Result{APIKeyID: key.ID}, ErrRateLimited
	}

	if len(payload) == 0 {
		return Result{APIKeyID: key.ID}, fmt.Errorf("%w: empty body", ErrMalformed)
	}

	parts, err := otlpwire.Split(payload, i.MaxCompressedBytes, publisher.GzipSize)
	switch {
	case errors.Is(err, otlpwire.ErrIndivisible):
		return Result{APIKeyID: key.ID}, ErrTooLarge
	case err != nil:
		return Result{APIKeyID: key.ID}, fmt.Errorf("%w: %s", ErrMalformed, err)
	}

	meta := publisher.Metadata{
		APIKeyID:      key.ID,
		SourceDialect: key.SourceDialect,
		SchemaURL:     otlpwire.SchemaURL(payload),
	}

	for _, part := range parts {
		compressed, err := publisher.Gzip(part)
		if err != nil {
			return Result{APIKeyID: key.ID}, fmt.Errorf("ingest: compressing: %w", err)
		}

		if err := i.Publisher.Publish(ctx, compressed, meta); err != nil {
			// A partial publish is possible and is not concealed: the caller gets an
			// error, retries the whole export, and the duplicate spans are eliminated
			// downstream on (trace_id, span_id) — which is exactly what at-least-once
			// delivery and the dedup views are for (§3.3).
			return Result{APIKeyID: key.ID}, err
		}
	}

	return Result{APIKeyID: key.ID, Messages: len(parts)}, nil
}
