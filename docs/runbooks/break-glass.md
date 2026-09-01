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

The dry run must exercise the real chain without touching the owner binding:

1. Grant a harmless role — `roles/browser` — to a throwaway principal, **as `ci-deploy@`,
   through a workflow dispatch**, not from a laptop with owner credentials. Running it as
   the human proves nothing: the human's access is the thing assumed absent.
2. Read the binding back from the API.
3. Remove it the same way.
4. Record the run number, the timestamps and the raw output here.

Step 1 is the whole test. A dry run performed with the credentials the emergency assumes
missing is the F2C-08 error class wearing a different hat.

## 6. Removal is withdrawn; this runbook is not

**F2C-22 was re-scoped on 2026-09-01 (Decision 18).** No standing role is removed from a
human principal, and none is scheduled to be — the removal is deferred out of F2 to a phase
in which the project has an organization parent or more than one maintainer, which are the
conditions under which its reasoning applies (#129).

**The dry run at §5 is still owed.** That is the part worth insisting on. This document is
the control for the recovery path whether or not a role is ever removed, and a control that
has never been exercised is not one — which is the same argument F2C-22's own ordering
constraint made, surviving the task that made it.

The second owner added under Decision 18 changes the arithmetic of §1 but not this section:
two recovery paths that have both never been tested are two untested paths.
