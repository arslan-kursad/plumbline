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

Two conventions hold across all of them.

**Scan set.** Gates scan git-tracked files. What is in the repository is exactly
the invariants' domain, so build output and local scratch files are irrelevant
without any gate needing an exclusion list.

**Pattern notation.** Forbidden-string patterns are written so they cannot match
their own text — `private[_]key`, `agent[-_. ]?lens` (ADR-0004 §4). Consequence:
these scripts can name the strings they forbid, no gate needs an exclusion list,
and none can be weakened by adding a path to one.

Neither the gates nor the guard are trusted because they pass. `prove-gates.sh`
and `--self-test` run in CI on every build, so a gate that stops being able to
fail is itself a build failure.
