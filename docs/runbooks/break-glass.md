# Runbook — break-glass: regaining project access

**Status:** written 2026-09-01 for F2C-22, **not yet dry-run**. Until the dry-run record at
§5 carries a date, this document is a plan and not a control — which is the distinction
F2C-22's own ordering constraint exists to enforce.

Scope: what to do when a human principal can no longer administer `plumbline-19458`, and
what the recovery depends on. It is written before any role is removed, because removing
access against an untested recovery path is the error class F2C-08 named.

## 1. The shape of this project, measured

Four facts decide everything below. All read from the API on 2026-09-01.

| Fact | Value | Consequence |
| --- | --- | --- |
| Project parent | **none** — standalone, no organization | There is no higher-level admin to grant anything back. A folder or org would normally be the recovery path; here there is not one. |
| Human bindings | exactly one: `roles/owner` on a single user | There are no granular "apply roles" to remove separately. Owner is the only thing a human holds. |
| Other principal able to grant | `ci-deploy@…iam.gserviceaccount.com`, `roles/resourcemanager.projectIamAdmin` | Confirmed to carry `resourcemanager.projects.setIamPolicy`. This is the **entire** recovery capability. |
| How that principal is reached | GitHub Actions → Workload Identity Federation | It has no key. It cannot be assumed from a laptop. |

**So the break-glass chain is:** GitHub → WIF → `ci-deploy@` → `setIamPolicy`. Four links,
each a single point of failure, with nothing behind them.

## 2. What this can recover from

- A human owner binding removed **deliberately** (F2C-22) or by accident.
- A human account that loses access to the project while the repository and its WIF
  configuration stay intact.

## 3. What this cannot recover from

Named, because a runbook that lists only its successes is the unproven control this project
keeps refusing.

- **The GitHub repository or organization being unavailable.** The recovery path is a
  workflow dispatch; no repository, no dispatch.
- **The WIF pool, provider, or `ci-deploy@` being deleted or misconfigured.** Terraform owns
  them, but Terraform is applied *through* them, so a break here is self-sealing.
- **`ci-deploy@` losing `projectIamAdmin`.** Nothing else on the project can grant.
- **Both the human binding and `ci-deploy@` failing together.** At that point the only route
  is Google Cloud support, on a project with no organization — days, not minutes.

The human's `roles/owner` binding is **not Terraform-managed**; it predates the
configuration. A `terraform apply` will not restore it, and no plan will show it missing.

## 4. The procedure

**Do not start here.** Confirm first that the human binding is actually gone rather than a
console session being stale:

```bash
gcloud projects get-iam-policy plumbline-19458 --format=json | grep -A5 'roles/owner'
```

If it is gone, dispatch the recovery through the path that still has permission. The grant
is a single `setIamPolicy` call made *as* `ci-deploy@` from a workflow run — the same
identity and the same authentication path a deploy uses, so if a deploy can run, this can.

The exact workflow does not exist yet. **Writing it is part of the dry run**, not of the
emergency: a recovery step first performed under pressure is not a recovery step.

## 5. Dry-run record

*(No dry run has been performed. This section is deliberately empty rather than absent, so
that its emptiness is visible to anyone who reaches for this document.)*

**The workflow exists:** [`.github/workflows/break-glass-drill.yml`](../../.github/workflows/break-glass-drill.yml).
`workflow_dispatch` only, and it refuses without `confirm: dry-run` typed in — it writes IAM
on purpose, so it does not run by accident.

What it does, in the order it does it:

1. Authenticates **as `ci-deploy@` through WIF**, the same identity and path a real recovery
   would use. Running it as the human proves nothing: the human's access is the thing the
   emergency assumes absent, so a laptop with owner credentials answers a different question.
2. Records the owner-binding count and refuses if `roles/browser` is already bound to the
   test member — a drill that cannot tell its own write from a pre-existing one is not
   measuring anything.
3. Grants `roles/browser` to `ci-readonly@`, reads it back, and asserts it landed.
4. Revokes it, under `if: always()`. A drill that leaves its own binding behind has changed
   the thing it was measuring.
5. Asserts the test role is gone **and the owner-binding count is unchanged**, then prints a
   summary block for §5 below.

**The role is deliberately inert.** `ci-readonly@` already holds `roles/viewer`, which
subsumes `roles/browser`, so the grant moves no effective permission while still being a real
`setIamPolicy` write. The test is the write, not the role.

**It cannot grant owner.** Both the member and the role are literals in the workflow rather
than inputs — a drill that can be pointed at an arbitrary principal is not a drill, it is a
grant tool. Rehearsing the owner grant would mean performing it.

*Pre-flight, run against the live policy 2026-09-01:* one owner binding present,
`roles/browser` bound to nobody, test member present in the policy. Both guards would pass.

## 6. Removal is withdrawn; this runbook is not

**F2C-22 was re-scoped on 2026-09-01 (Decision 18).** No standing role is removed from a
human principal, and none is scheduled to be — the removal is deferred out of F2 to a phase
in which the project has an organization parent or more than one maintainer, which are the
conditions under which its reasoning applies (#129).

**The dry run at §5 is still owed.** That is the part worth insisting on. This document is
the control for the recovery path whether or not a role is ever removed, and a control that
has never been exercised is not one — which is the same argument F2C-22's own ordering
constraint made, surviving the task that made it.

**§1's arithmetic is unchanged: one human binding, one recovery path.** Decision 18
recommends a second owner rather than requiring one, and none has been added. If one ever is,
it changes §1's first two rows and not this section — an untested second path is still an
untested path.
