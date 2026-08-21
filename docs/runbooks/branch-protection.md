# Runbook — `main` branch protection

Scope, deliberate limits, and the recovery procedure for the case where
protection deadlocks the branch (F0 spec §W6.5).

## Configuration

| Rule | State | Why |
| --- | --- | --- |
| Pull request required | yes | Every change to `main` arrives as a reviewable diff that CI has run against. |
| Required approving reviews | **0** | A single-author repository cannot self-approve; requiring one approval would deadlock every merge. |
| `enforce_admins` | true | The author is an admin. Without this the rules are decoration. |
| Force pushes | denied | History on a public repository is not erasable in practice; pretending otherwise is worse than not trying. |
| Branch deletion | denied | |
| Conversation resolution required | true | Pre-existing; kept. |
| Required status checks | `ci complete`, added once CI is green on `main` | See sequencing below. |

**The pull request requirement does not produce review.** With zero required
approvals, nothing mechanically forces a second pair of eyes, and a reader of a
public case study must not infer otherwise. What it produces is CI execution
before `main` and a recorded diff. Review here is a process commitment
(propose → confirm), not an enforced property.

## Why one aggregate check instead of several

`ci.yml` filters jobs by path, so `collector (go)` does not run on a
docs-only change. Branch protection cannot distinguish a job that was skipped
from one that never started, so requiring the individual jobs would leave
docs-only pull requests waiting forever on checks that will never report.

`ci complete` depends on every job and passes when each one either succeeded or
was skipped. One check is required; every job still gates the merge.

## Sequencing

Protection was enabled before the CI workflow existed, so required status checks
are added **after** the first green run on `main`, not before. Requiring a check
that has never run blocks the very pull request that would introduce it.

```bash
gh api -X PATCH repos/arslan-kursad/plumbline/branches/main/protection/required_status_checks \
  -F strict=true -f 'contexts[]=ci complete'
```

Read it back afterwards; a write that reports success is not evidence that
anything changed (see `repository-settings.md`).

## Deadlock recovery

`enforce_admins` blocks rule *bypass*, not rule *modification*. A broken workflow
file can therefore deadlock `main`: the fix cannot merge because the check it
repairs is failing. The escape is to disable protection, merge the fix, and
re-enable it.

```bash
# 1. Disable
gh api -X DELETE repos/arslan-kursad/plumbline/branches/main/protection
# 2. Merge the fix through a pull request, as usual.
# 3. Re-enable with the configuration above, then read it back.
```

**Every use of this escape is logged below** with date, pull request and reason.
An undocumented disable/re-enable cycle is exactly the silent degradation this
project rejects — and on a public repository the gap is visible in the audit log
anyway, so the only thing hiding it would cost is credibility.

## Log

| Date | Action | Pull request | Reason |
| --- | --- | --- | --- |
| 2026-08-19 | Documented existing protection; no change made | #15 | Protection predates this runbook. It was enabled outside any work package and was therefore undocumented drift until now — the F0 spec's own definition. |

State as read on 2026-08-19, before any change on this branch:

```json
{
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false,
    "required_approving_review_count": 0
  },
  "required_signatures": false,
  "enforce_admins": true,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": false
}
```

No `required_status_checks` key is present: none are configured yet.
