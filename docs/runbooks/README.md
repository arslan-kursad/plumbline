# Runbooks

Operational procedures, and the archived evidence that each one has actually been
run. A procedure with an empty evidence section is a procedure nobody has tested.

| Runbook | Covers |
| --- | --- |
| [`kill-switch.md`](kill-switch.md) | Billing kill-switch: what triggers it, the mandatory live-fire, the manual re-attach, and the BigQuery query quota. |
| [`repository-settings.md`](repository-settings.md) | Every manually managed GitHub setting, with dates, reasons and read-back evidence. |
| [`branch-protection.md`](branch-protection.md) | `main` protection: what it does and does not enforce, and the deadlock escape. |
| [`api-keys.md`](api-keys.md) | Issuing, losing and revoking agent API keys: the `api_keys` collection, `keyctl`, and why revocation is not instant. |
| [`dead-letter.md`](dead-letter.md) | The dead-letter path: what a dead-lettered message contains, how to triage it without exposing it, replay, and why retention is seven days. |
| [`wave4-first-delivery.md`](wave4-first-delivery.md) | Wave 4's first push delivery: what to read before sending, the four failure signatures and how to tell them apart, the success signature, and the base-table verification including the dedup premise check. |
| [`collector-endpoints.md`](collector-endpoints.md) | Which collector paths reach the container from outside, the unexplained `/healthz` interception, and what it costs F4's uptime check. |
| [`apply-identity-ledger.md`](apply-identity-ledger.md) | Every grant `ci-deploy@` holds: the wave that asked for it, what that wave needed, and what the grant actually covers. |
