# billing-killswitch

Cloud Function (Gen2, `us-central1`) that detaches the billing account from the
project when any spend is reported. Deployed by `infra/terraform/killswitch.tf`;
rationale in ADR-0004 §5.

- **Trigger:** Pub/Sub topic `billing-alerts`, fed by the budget's
  `all_updates_rule` — a notification on every cost update, not only on threshold
  crossings.
- **Decision:** detach when `costAmount > 0`. That comparison, not the budget
  threshold, is what implements "alert at any spend above $0".
- **Retry contract:** failures that redelivery could fix are returned as errors
  (Pub/Sub retries); permission and not-found failures are logged and acked, so a
  misconfigured deployment cannot become a redelivery loop.
- **Permissions:** `roles/billing.projectManager` on this project only. The
  identity can detach billing and cannot re-attach it; re-attaching is a human
  procedure (`docs/runbooks/kill-switch.md`).

`go.mod` pins the language version the Cloud Functions runtime must provide;
`infra/terraform/variables.tf` (`killswitch_runtime`) carries the matching
runtime ID. Changing one without the other breaks the build at deploy time.

Local checks:

```bash
go build ./... && go vet ./... && go test ./...
```
