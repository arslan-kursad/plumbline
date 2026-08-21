package killswitch

import (
	"encoding/json"
	"errors"
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
func TestDetachDecisionBoundary(t *testing.T) {
	cases := []struct {
		name       string
		costAmount float64
		want       bool
	}{
		{"no spend", 0, false},
		{"negative adjustment", -0.01, false},
		{"one cent", 0.01, true},
		{"smallest reported amount", 0.000001, true},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			raw, err := json.Marshal(map[string]any{"costAmount": tc.costAmount})
			if err != nil {
				t.Fatalf("marshal: %v", err)
			}

			notification, err := parseNotification(newBudgetEvent(t, string(raw)))
			if err != nil {
				t.Fatalf("parseNotification: %v", err)
			}

			if got := notification.CostAmount > 0; got != tc.want {
				t.Errorf("detach decision for cost %v = %v, want %v", tc.costAmount, got, tc.want)
			}
		})
	}
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
