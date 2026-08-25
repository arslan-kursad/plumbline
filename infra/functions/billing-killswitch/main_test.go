package killswitch

import (
	"errors"
	"math"
	"net/http"
	"testing"

	"github.com/cloudevents/sdk-go/v2/event"
	"google.golang.org/api/googleapi"
)

// newBudgetEvent builds the CloudEvent shape Eventarc delivers for a Pub/Sub
// message: a JSON envelope whose data field carries the budget notification.
func newBudgetEvent(t *testing.T, notification string) event.Event {
	t.Helper()

	e := event.New()
	e.SetType("google.cloud.pubsub.topic.v1.messagePublished")
	e.SetSource("//pubsub.googleapis.com/projects/test/topics/billing-alerts")

	envelope := map[string]any{
		"message": map[string]any{
			"data": []byte(notification),
		},
	}
	if err := e.SetData("application/json", envelope); err != nil {
		t.Fatalf("SetData: %v", err)
	}

	return e
}

func TestParseNotification(t *testing.T) {
	payload := `{
		"budgetDisplayName": "plumbline zero-spend",
		"alertThresholdExceeded": 1.0,
		"costAmount": 0.04,
		"budgetAmount": 1.0,
		"currencyCode": "USD",
		"costIntervalStart": "2026-09-01T07:00:00Z"
	}`

	got, err := parseNotification(newBudgetEvent(t, payload))
	if err != nil {
		t.Fatalf("parseNotification: %v", err)
	}

	if got.CostAmount != 0.04 {
		t.Errorf("CostAmount = %v, want 0.04", got.CostAmount)
	}
	if got.BudgetDisplayName != "plumbline zero-spend" {
		t.Errorf("BudgetDisplayName = %q, want %q", got.BudgetDisplayName, "plumbline zero-spend")
	}
	if got.CurrencyCode != "USD" {
		t.Errorf("CurrencyCode = %q, want USD", got.CurrencyCode)
	}
}

// A notification carrying fields this function does not model must still parse:
// the schema is owned upstream and grows without this repository's involvement.
func TestParseNotificationIgnoresUnknownFields(t *testing.T) {
	got, err := parseNotification(newBudgetEvent(t, `{"costAmount": 1.5, "forecastThresholdExceeded": 0.9}`))
	if err != nil {
		t.Fatalf("parseNotification: %v", err)
	}
	if got.CostAmount != 1.5 {
		t.Errorf("CostAmount = %v, want 1.5", got.CostAmount)
	}
}

func TestParseNotificationRejectsGarbage(t *testing.T) {
	if _, err := parseNotification(newBudgetEvent(t, "not json")); err == nil {
		t.Fatal("parseNotification accepted a non-JSON notification")
	}
}

// The zero/non-zero boundary is the whole decision: at or below zero billing is
// left alone, above zero it is detached.
// The decision rule, at its boundary (ADR-0004 Amendment 4, D2).
//
// The old rule was `cost > 0` and it is what detached a live project on 0.04 TRY
// of the kill-switch's own CPU seconds. These cases pin the replacement: the
// threshold is inclusive, everything under it is inaction, and a figure that is
// not a number is never evidence of spend.
func TestShouldDetach(t *testing.T) {
	const threshold = 5.00

	cases := []struct {
		name string
		cost float64
		want bool
	}{
		{"no spend", 0, false},
		{"negative adjustment", -0.01, false},
		{"the observed false positive", 0.04, false},
		{"just below the threshold", 4.99, false},
		{"exactly the threshold detaches", 5.00, true},
		{"above the threshold", 5.01, true},
		{"far above", 1000, true},
		{"NaN is not spend", math.NaN(), false},
		{"positive infinity is not a cost figure", math.Inf(1), false},
		{"negative infinity is not a cost figure", math.Inf(-1), false},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := shouldDetach(tc.cost, threshold); got != tc.want {
				t.Errorf("shouldDetach(%v, %v) = %v, want %v", tc.cost, threshold, got, tc.want)
			}
		})
	}
}

// A threshold nobody chose is either zero — which restores the behaviour the
// amendment removes — or a number invented when the control is needed. Both are
// startup failures, and this is the test that says so.
func TestDetachThresholdRefusesAnythingButAPositiveNumber(t *testing.T) {
	t.Run("missing is a startup failure", func(t *testing.T) {
		t.Setenv("DETACH_THRESHOLD", "")
		if _, err := detachThreshold(); err == nil {
			t.Fatal("DETACH_THRESHOLD was absent and the function accepted it; " +
				"a control with an unchosen threshold looks identical to a working one")
		}
	})

	for _, raw := range []string{"five", "", "0", "-1", "NaN", "Inf", "5,00"} {
		t.Run("refuses "+raw, func(t *testing.T) {
			t.Setenv("DETACH_THRESHOLD", raw)
			if _, err := detachThreshold(); err == nil {
				t.Errorf("DETACH_THRESHOLD=%q was accepted", raw)
			}
		})
	}

	t.Run("accepts a positive number", func(t *testing.T) {
		t.Setenv("DETACH_THRESHOLD", "5.00")
		value, err := detachThreshold()
		if err != nil {
			t.Fatalf("detachThreshold: %v", err)
		}
		if value != 5.00 {
			t.Errorf("threshold = %v, want 5", value)
		}
	})
}

// Redelivery must stop for failures redelivery cannot fix, and must continue for
// everything else — the retry policy on the trigger depends on this split.
func TestPermanent(t *testing.T) {
	cases := []struct {
		name string
		err  error
		want bool
	}{
		{"forbidden", &googleapi.Error{Code: http.StatusForbidden}, true},
		{"unauthorized", &googleapi.Error{Code: http.StatusUnauthorized}, true},
		{"not found", &googleapi.Error{Code: http.StatusNotFound}, true},
		{"rate limited", &googleapi.Error{Code: http.StatusTooManyRequests}, false},
		{"backend error", &googleapi.Error{Code: http.StatusInternalServerError}, false},
		{"wrapped forbidden", errors.Join(errors.New("detach billing"), &googleapi.Error{Code: http.StatusForbidden}), true},
		{"transport failure", errors.New("connection reset"), false},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := permanent(tc.err); got != tc.want {
				t.Errorf("permanent(%v) = %v, want %v", tc.err, got, tc.want)
			}
		})
	}
}
