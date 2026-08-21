# Runbooks

Operational procedures, and the archived evidence that each one has actually been
run. A procedure with an empty evidence section is a procedure nobody has tested.

| Runbook | Covers |
| --- | --- |
| [`kill-switch.md`](kill-switch.md) | Billing kill-switch: what triggers it, the mandatory live-fire, the manual re-attach, and the BigQuery query quota. |
| [`repository-settings.md`](repository-settings.md) | Every manually managed GitHub setting, with dates, reasons and read-back evidence. |
| [`branch-protection.md`](branch-protection.md) | `main` protection: what it does and does not enforce, and the deadlock escape. |
| [`dead-letter.md`](dead-letter.md) | The dead-letter path: what a dead-lettered message contains, how to triage it without exposing it, replay, and why retention is seven days. |
