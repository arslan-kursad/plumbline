# scripts/ci

Invariant gates and the Terraform plan guard. Everything here runs locally with
no arguments and no cloud access, and CI runs exactly the same scripts — a check
that only exists inside a workflow file cannot be reproduced by the person whose
commit it rejects.

| Script | Purpose |
| --- | --- |
| `invariant-gates.sh` | Gates A–E (F0 spec §W6.2). Exits non-zero printing offending `path:line`. |
| `prove-gates.sh` | Proves each gate fails on a deliberate violation, in a throwaway git worktree. |
| `terraform-plan-guard.sh` | Plan assertions from architecture §7.1; `--self-test` runs them against fixtures. |
| `plan_guard.py` | The plan assertions themselves, kept readable apart from the wrapper. |
| `testdata/` | Trimmed plan fixtures, one per assertion, plus a clean plan. |

Three conventions hold across all of them.

**Scan set.** Gates scan every file git considers part of the repository: tracked
files plus untracked ones that are not ignored. No gate needs an exclusion list.

Two consequences of that choice are easy to trip over:

- A local run is **stricter** than CI, because CI only ever sees committed files.
  An untracked scratch file that violates a gate fails locally and does not exist
  in CI. That direction is deliberate — the reverse, which is what this script
  did first, passes a violation locally until someone runs `git add` and then
  fails it in CI.
- `.gitignore` therefore defines gate scope. A broad ignore pattern silently does
  what an exclusion list would do, in a file nobody reads as a security control.
  Widening `.gitignore` is a change to what these gates cover, and belongs in
  review as one.

**Pattern notation.** Forbidden-string patterns are written so they cannot match
their own text — `private[_]key`, `agent[-_. ]?lens` (ADR-0004 §4). Consequence:
these scripts can name the strings they forbid, no gate needs an exclusion list,
and none can be weakened by adding a path to one.

**Which repository a guard binds to.** Its own — the one it ships in, derived
from `${BASH_SOURCE[0]}` — never the one the caller happens to be standing in.
A guard reads `docs/architecture.md`, `plan_guard.py` and the fixtures next to
it, and those have to be the copies that were reviewed together with it. This
matters because the project has more than one root at a time: the primary
checkout plus `.claude/worktrees/*`, routinely at different commits.

These scripts used to open with `cd "$(git rev-parse --show-toplevel)"`, which
answers the other question and fails badly in two ways (issue #198). Outside a
repository the substitution is empty and `cd ""` succeeds as a no-op — a failed
command substitution in an argument does not trip `set -e` — so the script
carried on in the caller's directory and died later at the first path it
assumed. Inside a *different* repository it succeeded and read that repository's
files. Deriving the root from the script's own path removes both, and needs no
git at all, so a guard now runs from anywhere.

Nothing here changes what CI does: a workflow checks out one repository and runs
from its root, where the two answers coincide. The path that broke was always
the human one.

Neither the gates nor the guard are trusted because they pass. `prove-gates.sh`
and `--self-test` run in CI on every build, so a gate that stops being able to
fail is itself a build failure.
