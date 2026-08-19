// Package killswitch detaches the billing account from this GCP project as soon
// as any spend is reported against it.
//
// It is the last control in the cost chain (ADR-0004 §2): reaching it means
// Terraform configuration, CI gates, quotas and alerts have all already failed.
// Its job is to bound the loss, so it is deliberately one API call with one
// outcome, and it is live-fired before F0 is closed (F0 spec W4).
package killswitch

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
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

// HandleBudgetNotification detaches billing when reported cost is strictly
// greater than zero.
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

	notification, err := parseNotification(e)
	if err != nil {
		slog.Error("cannot decode budget notification", "error", err)
		return nil
	}

	slog.Info("budget notification received",
		"budget", notification.BudgetDisplayName,
		"cost", notification.CostAmount,
		"currency", notification.CurrencyCode,
		"threshold_exceeded", notification.AlertThresholdExceeded,
		"interval_start", notification.CostIntervalStart,
	)

	if notification.CostAmount <= 0 {
		slog.Info("no spend reported; billing left attached", "project", projectID)
		return nil
	}

	return detachBilling(ctx, projectID, notification)
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

func detachBilling(ctx context.Context, projectID string, notification budgetNotification) error {
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

	slog.Warn("spend reported; detaching billing account",
		"project", projectID,
		"billing_account", info.BillingAccountName,
		"cost", notification.CostAmount,
		"currency", notification.CurrencyCode,
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
