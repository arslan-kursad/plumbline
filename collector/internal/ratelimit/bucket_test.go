package ratelimit

import (
	"sync"
	"testing"
	"time"
)

type fakeClock struct {
	mu  sync.Mutex
	now time.Time
}

func (c *fakeClock) Now() time.Time {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.now
}

func (c *fakeClock) Advance(d time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.now = c.now.Add(d)
}

func TestBurstIsSpentThenRefused(t *testing.T) {
	clock := &fakeClock{now: time.Unix(0, 0)}
	limiter := New(clock.Now)

	for i := 0; i < 3; i++ {
		if !limiter.Allow("k", 1, 3) {
			t.Fatalf("request %d refused inside the burst", i+1)
		}
	}
	if limiter.Allow("k", 1, 3) {
		t.Fatal("the fourth request was allowed with an empty bucket")
	}
}

func TestTokensRefillOverTime(t *testing.T) {
	clock := &fakeClock{now: time.Unix(0, 0)}
	limiter := New(clock.Now)

	for i := 0; i < 2; i++ {
		limiter.Allow("k", 2, 2)
	}
	if limiter.Allow("k", 2, 2) {
		t.Fatal("bucket was not empty")
	}

	clock.Advance(500 * time.Millisecond) // one token at 2/s
	if !limiter.Allow("k", 2, 2) {
		t.Fatal("a refilled token was not granted")
	}
	if limiter.Allow("k", 2, 2) {
		t.Fatal("more than the refilled token was granted")
	}
}

func TestRefillIsCappedAtBurst(t *testing.T) {
	clock := &fakeClock{now: time.Unix(0, 0)}
	limiter := New(clock.Now)

	limiter.Allow("k", 1, 2)
	clock.Advance(time.Hour)

	if !limiter.Allow("k", 1, 2) || !limiter.Allow("k", 1, 2) {
		t.Fatal("the bucket did not refill to its burst")
	}
	if limiter.Allow("k", 1, 2) {
		t.Fatal("an hour of idling granted more than one burst — the cap is missing")
	}
}

func TestKeysAreLimitedIndependently(t *testing.T) {
	clock := &fakeClock{now: time.Unix(0, 0)}
	limiter := New(clock.Now)

	limiter.Allow("noisy", 1, 1)
	if limiter.Allow("noisy", 1, 1) {
		t.Fatal("the noisy key was not limited")
	}
	if !limiter.Allow("quiet", 1, 1) {
		t.Fatal("one key's exhausted bucket refused another key")
	}
}

func TestATierChangeAppliesToTheExistingBucket(t *testing.T) {
	clock := &fakeClock{now: time.Unix(0, 0)}
	limiter := New(clock.Now)

	limiter.Allow("k", 1, 1)
	if limiter.Allow("k", 1, 1) {
		t.Fatal("bucket was not empty")
	}

	// The same key comes back on a larger tier. Raising the burst does not hand out
	// tokens retroactively — an empty bucket stays empty until it refills — but the new
	// ceiling governs from here on, and the key keeps one bucket rather than gaining a
	// second.
	if limiter.Allow("k", 1, 5) {
		t.Fatal("raising the burst granted a token the bucket had not earned")
	}

	clock.Advance(10 * time.Second)

	granted := 0
	for i := 0; i < 10; i++ {
		if limiter.Allow("k", 1, 5) {
			granted++
		}
	}
	if granted != 5 {
		t.Fatalf("want the raised burst of 5 after refill, got %d", granted)
	}

	if limiter.Keys() != 1 {
		t.Fatalf("want one bucket for one key, got %d", limiter.Keys())
	}
}

func TestAnUnconfiguredKeyIsRefusedRatherThanUnlimited(t *testing.T) {
	limiter := New(nil)

	if limiter.Allow("k", 0, 0) {
		t.Fatal("a key with no rate configured was allowed through: the failure mode of a " +
			"missing tier must be refusal, not an unmetered channel")
	}
}

func TestConcurrentCallersDoNotExceedTheBurst(t *testing.T) {
	clock := &fakeClock{now: time.Unix(0, 0)}
	limiter := New(clock.Now)

	const burst = 50
	var granted int
	var mu sync.Mutex
	var wg sync.WaitGroup

	for i := 0; i < 200; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if limiter.Allow("k", 1, burst) {
				mu.Lock()
				granted++
				mu.Unlock()
			}
		}()
	}
	wg.Wait()

	if granted != burst {
		t.Fatalf("want exactly %d grants under contention, got %d", burst, granted)
	}
}
