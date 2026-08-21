# Runbook — repository settings

The complete inventory of manually managed GitHub settings for
`arslan-kursad/plumbline`, with the date, reason and API evidence for each. GCP
resources are Terraform-owned and nothing there is hand-created (architecture
§8); that rule scopes to GCP, so these settings are managed by hand — adding a
GitHub Terraform provider for a handful of toggles is disproportionate.

A setting changed outside a work package is drift unless it is written down, and
drift is a bug. This file is the inventory, not a log of one work package.

## Current state

| Setting | State | Since | Owner |
| --- | --- | --- | --- |
| Repository visibility | public | 2026-08-18 | F0 spec §0.2 |
| Secret scanning | **enabled** | 2026-08-19 | W6.4 |
| Secret scanning push protection | **enabled** | 2026-08-19 | W6.4 |
| Secret scanning validity checks | unavailable on this plan | — | W6.4, see below |
| Secret scanning non-provider patterns | unavailable on this plan | — | W6.4, see below |
| Dependabot alerts | enabled | 2026-08-18 | issue #2, ahead of W6.6 |
| Dependabot security updates | disabled | — | W6.6, deferred to F1 in writing |
| Actions: fork PR approval | `all_external_contributors` | 2026-08-19 | W6.1 |
| Actions: default workflow permissions | `read` | pre-existing | W6.1 posture |
| `main` branch protection | enabled | pre-existing, documented 2026-08-19 | W6.5 → `branch-protection.md` |
| Environment `gcp-production` | **created**, 1 required reviewer, `main`-only deployments | 2026-08-21 | F2 W0a → `F2-minimal-gcp-footprint.md` §2 |
| Actions secret `ALERT_EMAIL` | **set** | 2026-08-21 | F2 Wave 1 — destination for the dead-letter depth alert |

## Evidence (2026-08-19, after the W6.4 changes)

```
$ gh api repos/arslan-kursad/plumbline --jq '.security_and_analysis'
{"dependabot_security_updates":{"status":"disabled"},"secret_scanning":{"status":"enabled"},"secret_scanning_non_provider_patterns":{"status":"disabled"},"secret_scanning_push_protection":{"status":"enabled"},"secret_scanning_validity_checks":{"status":"disabled"}}

$ gh api repos/arslan-kursad/plumbline/vulnerability-alerts -i | head -1
HTTP/2.0 204 No Content

$ gh api repos/arslan-kursad/plumbline/actions/permissions/fork-pr-contributor-approval
{"approval_policy":"all_external_contributors"}

$ gh api repos/arslan-kursad/plumbline/actions/permissions/workflow
{"default_workflow_permissions":"read","can_approve_pull_request_reviews":false}
```

## Evidence — the F2 deploy gate (2026-08-21)

```
$ ./scripts/ci/environment-guard.sh <(gh api repos/arslan-kursad/plumbline/environments/gcp-production)
environment guard: gcp-production protected by 1 required reviewer(s)

$ gh api repos/arslan-kursad/plumbline/environments/gcp-production/deployment-branch-policies \
    --jq '.branch_policies[] | "\(.name) (\(.type))"'
main (branch)
```

The read-back is run through `scripts/ci/environment-guard.sh` rather than eyeballed,
because that script is the same control the deploy workflow refuses on — checking the
setting with the thing that enforces it is worth more than checking it with a person.

**`prevent_self_review` is `false`, and that is not an accident to leave undocumented.**
The reviewer is the maintainer, who is also the only person who can dispatch a deploy, so
a self-review prohibition would make every wave unapprovable. What this gate provides is
therefore a deliberate pause with an auditable timestamp, not an independent second
opinion — the same honest distinction ADR-0004 draws when it refuses to count code review
as an enforcement point in a single-author repository.

**`ALERT_EMAIL` holds a personal email address.** It is a secret rather than a variable
for that reason alone: this repository is public, and Actions masks secret values in
workflow logs. It is not a credential.

The F0-start baseline, recorded in the spec on 2026-08-18, was `disabled` for
secret scanning, push protection and validity checks, and `404` (disabled) for
Dependabot alerts. Two of those are now enabled; the other two could not be.

## Two settings W6.4 requires cannot be enabled here

`secret_scanning_validity_checks` and `secret_scanning_non_provider_patterns`
were requested through the same API that enabled the other two. The requests
returned **HTTP 200 with no error**, and the settings stayed `disabled`. Repeated
individually, same result.

Cause: both are GitHub Secret Protection features, available on Team and
Enterprise Cloud plans. This repository is owned by a personal account on the
free plan. Enabling them means paying, and "no paid SaaS anywhere in the loop" is
a zero-cost invariant of this project — so the F0 spec asked for something the
project's own cost invariant forbids. The spec is corrected rather than the
invariant (F0 spec v0.7, §W6.4).

Two consequences worth stating rather than discovering at F1:

- **A silently ignored write is the dangerous part.** The API reports success and
  changes nothing. Any future "we enabled X" claim about repository settings is
  only worth what its *read-back* evidence is worth, which is why this file
  archives reads and not the commands that were run.
- **The F1 exposure W6.4 identified is still real and is now uncovered by
  GitHub.** Golden-file fixtures will carry OTLP payloads with key-like strings,
  and non-provider pattern detection was the control meant to catch a real leak
  among them. What remains is Gate C (detects, after the push) and the discipline
  of obviously-fake fixture values. F1 owns making that discipline explicit.

## Changing a setting

1. Change it, then **read it back** through the API — never trust the write.
2. Add or update the row above with date and reason.
3. Archive the read-back output in this file.
4. If the change was not part of a work package, say so in the row. That is the
   whole point of the inventory: `dependabot_security_updates` being disabled is
   a decision (W6.6, deferred to F1), not an oversight, and the difference is
   only visible because it is written down.
