package publisher

import (
	"bytes"
	"compress/gzip"
	"context"
	"io"
	"sync"
)

// Recorder is an in-memory Publisher used by tests.
//
// It lives beside the real implementation rather than in a test file because three
// packages need it, and because the property most worth testing — that what was
// received is what was published, byte for byte — is only checkable by something that
// keeps the published bytes.
type Recorder struct {
	mu       sync.Mutex
	messages []Recorded

	// Err, when set, is returned by every Publish call.
	Err error
}

// Recorded is one published message, kept compressed as it went out plus decompressed
// for comparison against what the receiver was handed.
type Recorded struct {
	Compressed []byte
	Payload    []byte
	Metadata   Metadata
}

func (r *Recorder) Publish(_ context.Context, gzipped []byte, meta Metadata) error {
	if r.Err != nil {
		return r.Err
	}

	reader, err := gzip.NewReader(bytes.NewReader(gzipped))
	if err != nil {
		return err
	}
	payload, err := io.ReadAll(reader)
	if err != nil {
		return err
	}
	if err := reader.Close(); err != nil {
		return err
	}

	r.mu.Lock()
	defer r.mu.Unlock()
	r.messages = append(r.messages, Recorded{
		Compressed: append([]byte(nil), gzipped...),
		Payload:    payload,
		Metadata:   meta,
	})
	return nil
}

func (r *Recorder) Close() error { return nil }

func (r *Recorder) Messages() []Recorded {
	r.mu.Lock()
	defer r.mu.Unlock()
	return append([]Recorded(nil), r.messages...)
}
