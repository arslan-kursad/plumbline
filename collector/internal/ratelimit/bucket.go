// Package ratelimit implements the per-key token bucket the collector applies before
// anything else touches a payload.
//
// Known limitation, accepted and documented rather than hidden: the bucket is in-memory
// per collector instance. With max-instances = 2 the effective limit is up to twice the
// nominal one. See docs/architecture.md §6.2 — a shared limiter (Redis/Memorystore) is
// the fix, and it violates the zero-cost invariant, so the approximation is the design
// and not a defect to file.
package ratelimit

import (
	"sync"
	"time"
)

// Clock is injected so the tests can advance time instead of sleeping through it.
type Clock func() time.Time

// Limiter holds one bucket per API key id.
type Limiter struct {
	now Clock

	mu      sync.Mutex
	buckets map[string]*bucket
}

type bucket struct {
	tokens   float64
	capacity float64
	rate     float64
	last     time.Time
}

func New(now Clock) *Limiter {
	if now == nil {
		now = time.Now
	}
	return &Limiter{now: now, buckets: make(map[string]*bucket)}
}

// Allow takes one token for keyID, refilling at ratePerSecond up to burst.
//
// The rate and burst travel with each call rather than being registered up front,
// because they are properties of the key that authentication has just resolved. A key
// whose tier changes takes effect on its next request without a restart.
func (l *Limiter) Allow(keyID string, ratePerSecond float64, burst int) bool {
	if ratePerSecond <= 0 || burst <= 0 {
		// An unconfigured key is not silently unlimited.
		return false
	}

	now := l.now()

	l.mu.Lock()
	defer l.mu.Unlock()

	b, ok := l.buckets[keyID]
	if !ok {
		b = &bucket{tokens: float64(burst), capacity: float64(burst), rate: ratePerSecond, last: now}
		l.buckets[keyID] = b
	}

	// A tier change applies to the existing bucket rather than creating a second one.
	// It is not retroactive: raising the burst raises the ceiling the bucket refills
	// towards, and an empty bucket stays empty until it earns tokens at the new rate.
	b.capacity = float64(burst)
	b.rate = ratePerSecond

	elapsed := now.Sub(b.last).Seconds()
	if elapsed > 0 {
		b.tokens += elapsed * b.rate
		if b.tokens > b.capacity {
			b.tokens = b.capacity
		}
		b.last = now
	}

	if b.tokens < 1 {
		return false
	}

	b.tokens--
	return true
}

// Keys reports how many buckets are held, for the memory-growth test: an unbounded map
// keyed by caller-supplied strings is a denial-of-service surface, and the registry is
// what bounds it — only authenticated key ids ever reach Allow.
func (l *Limiter) Keys() int {
	l.mu.Lock()
	defer l.mu.Unlock()
	return len(l.buckets)
}
