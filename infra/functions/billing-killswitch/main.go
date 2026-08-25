// Package killswitch detaches the billing account from this GCP project when
// reported net cost reaches a small threshold.
//
// It is the last control in the cost chain (ADR-0004 §2): reaching it means
// Terraform configuration, CI gates, quotas and alerts have all already failed.
// Its job is to bound the loss, so it is deliberately one API call with one
// outcome, and it is live-fired before F0 is closed (F0 spec W4).
//
// The trigger is `>= DETACH_THRESHOLD` rather than `> 0` (ADR-0004 Amendment 4).
// Firing on any non-zero figure sounds stricter and was not: a reported cost can
// be non-zero while nothing has been billed, and this function detached a live
// project on 0.04 TRY of its own CPU seconds. The zero-cost claim is measured
// from the invoice; this threshold only decides when to pull the plug.
package killswitch

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"math"
	"net/http"
	"os"
	"strconv"

	"github.com/GoogleCloudPlatform/functions-framework-go/functions"
	"github.com/cloudevents/sdk-go/v2/event"
	"google.golang.org/api/cloudbilling/v1"
	"google.golang.org/api/googleapi"
)

func init() {
	functions.CloudEvent("HandleBudgetNotification", HandleBudgetNotification)
}

// pubSubMessage is the CloudEvent payload delivered for
// google.cloud.pubsub.topic.v1.messagePublished.
type pubSubMessage struct {
	Message struct {
		Data       []byte            `json:"data"`
		Attributes map[string]string `json:"attributes"`
	} `json:"message"`
}

// budgetNotification is the Cloud Billing budget notification, schema version
// 1.0. Only the fields this function acts on are modelled; unknown fields are
// ignored rather than rejected, because the notification schema is owned
// upstream and may grow.
type budgetNotification struct {
	BudgetDisplayName      string  `json:"budgetDisplayName"`
	AlertThresholdExceeded float64 `json:"alertThresholdExceeded"`
	CostAmount             float64 `json:"costAmount"`
	BudgetAmount           float64 `json:"budgetAmount"`
	CurrencyCode           string  `json:"currencyCode"`
	CostIntervalStart      string  `json:"costIntervalStart"`
}

// shouldDetach is the whole decision, isolated so it can be tested without a
// CloudEvent, a billing client or a network (ADR-0004 Amendment 4, D2).
//
// Detach at or above the threshold, not above zero. Amendment 1 used `> 0` on the
// premise that a reported figure is net of Always Free; live operation showed a
// reported figure can be non-zero while nothing has been billed, because a gross
// line can appear before — or instead of — the credit that cancels it.
//
// A cost that is not a number is not evidence of spend: NaN comparisons are false
// in every direction, so the guard is explicit rather than accidental, and a
// negative cost is a refund or a correction and never a reason to act.
func shouldDetach(cost, threshold float64) bool {
	if math.IsNaN(cost) || math.IsInf(cost, 0) || cost < 0 {
		return false
	}
	return cost >= threshold
}

// detachThreshold reads the epsilon from the environment.
//
// No default. A threshold nobody chose is either zero — which restores the
// behaviour this amendment exists to remove — or a number invented at the moment
// the control is needed. Failing at startup is loud, happens before any
// notification arrives, and cannot be mistaken for a working deployment.
func detachThreshold() (float64, error) {
	raw := os.Getenv("DETACH_THRESHOLD")
	if raw == "" {
		return 0, errors.New("DETACH_THRESHOLD is not set")
	}

	value, err := strconv.ParseFloat(raw, 64)
	if err != nil {
		return 0, fmt.Errorf("DETACH_THRESHOLD=%q is not a number: %w", raw, err)
	}
	if value <= 0 || math.IsNaN(value) || math.IsInf(value, 0) {
		return 0, fmt.Errorf("DETACH_THRESHOLD=%q must be a positive, finite number", raw)
	}

	return value, nil
}

// HandleBudgetNotification detaches billing when reported net cost reaches the
// configured threshold.
//
// Error convention: a returned error makes Pub/Sub redeliver. Errors that
// redelivery cannot fix — an unparseable payload, a missing permission — are
// logged at ERROR and acked, so a permanently broken deployment does not become
// a redelivery loop. Everything else is returned and retried.
func HandleBudgetNotification(ctx context.Context, e event.Event) error {
	projectID := os.Getenv("TARGET_PROJECT_ID")
	if projectID == "" {
		slog.Error("TARGET_PROJECT_ID is not set; refusing to guess the project")
		return nil
	}

	threshold, err := detachThreshold()
	if err != nil {
		// Fail closed and say so. Redelivery cannot fix a missing environment
		// variable, so this acks rather than looping — but it is FATAL-shaped:
		// the deployment is misconfigured and no notification will ever be acted
		// on until it is fixed.
		slog.Error("FATAL: refusing to evaluate a budget notification without a detach threshold",
			"error", err)
		return nil
	}

	notification, err := parseNotification(e)
	if err != nil {
		slog.Error("cannot decode budget notification", "error", err)
		return nil
	}

	slog.Info("budget notification received",
		"budget", notification.BudgetDisplayName,
		"cost", notification.CostAmount,
		"currency", notification.CurrencyCode,
		"threshold", threshold,
		"threshold_exceeded", notification.AlertThresholdExceeded,
		"interval_start", notification.CostIntervalStart,
	)

	if !shouldDetach(notification.CostAmount, threshold) {
		if notification.CostAmount <= 0 {
			slog.Info("no spend reported; billing left attached", "project", projectID)
			return nil
		}

		// The case this amendment was written for. Visible on purpose: a figure
		// below the threshold is the shape of a credit that has not landed yet,
		// and a run of these is the evidence for revisiting the threshold.
		slog.Warn("spend reported below detach threshold; no action",
			"project", projectID,
			"cost", notification.CostAmount,
			"currency", notification.CurrencyCode,
			"threshold", threshold,
			"interval_start", notification.CostIntervalStart,
		)
		return nil
	}

	return detachBilling(ctx, projectID, notification, threshold)
}

// parseNotification unwraps the Pub/Sub envelope and the budget notification it
// carries. Both layers are upstream-owned formats, so decoding failures are
// reported rather than guessed at.
func parseNotification(e event.Event) (budgetNotification, error) {
	var msg pubSubMessage
	if err := e.DataAs(&msg); err != nil {
		return budgetNotification{}, fmt.Errorf("decode CloudEvent payload: %w", err)
	}

	var notification budgetNotification
	if err := json.Unmarshal(msg.Message.Data, &notification); err != nil {
		return budgetNotification{}, fmt.Errorf("decode budget notification (%d bytes): %w", len(msg.Message.Data), err)
	}

	return notification, nil
}

func detachBilling(ctx context.Context, projectID string, notification budgetNotification, threshold float64) error {
	svc, err := cloudbilling.NewService(ctx)
	if err != nil {
		slog.Error("cannot create Cloud Billing client", "error", err)
		return fmt.Errorf("create cloudbilling client: %w", err)
	}

	resource := "projects/" + projectID

	info, err := svc.Projects.GetBillingInfo(resource).Context(ctx).Do()
	if err != nil {
		if permanent(err) {
			slog.Error("cannot read billing info and retrying will not help", "error", err, "project", projectID)
			return nil
		}
		return fmt.Errorf("get billing info for %s: %w", resource, err)
	}

	if info.BillingAccountName == "" {
		slog.Warn("billing already detached; nothing to do",
			"project", projectID,
			"cost", strconv.FormatFloat(notification.CostAmount, 'f', -1, 64),
		)
		return nil
	}

	slog.Warn("spend reported at or above the detach threshold; detaching billing account",
		"project", projectID,
		"billing_account", info.BillingAccountName,
		"cost", notification.CostAmount,
		"currency", notification.CurrencyCode,
		"threshold", threshold,
	)

	if _, err := svc.Projects.UpdateBillingInfo(resource, &cloudbilling.ProjectBillingInfo{
		BillingAccountName: "",
	}).Context(ctx).Do(); err != nil {
		if permanent(err) {
			slog.Error("cannot detach billing and retrying will not help", "error", err, "project", projectID)
			return nil
		}
		return fmt.Errorf("detach billing for %s: %w", resource, err)
	}

	slog.Warn("billing detached", "project", projectID, "previous_billing_account", info.BillingAccountName)
	return nil
}

// permanent reports whether redelivery is pointless: the caller lacks
// permission, or the resource does not exist.
func permanent(err error) bool {
	var apiErr *googleapi.Error
	if errors.As(err, &apiErr) {
		return apiErr.Code == http.StatusUnauthorized ||
			apiErr.Code == http.StatusForbidden ||
			apiErr.Code == http.StatusNotFound
	}
	return false
}
