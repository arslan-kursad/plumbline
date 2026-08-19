# Evidence — F0 gate failure proofs

**Date:** 2026-08-19 · **Work package:** F0 W6 · **Acceptance criterion:** 9

F0 spec §6 requires each gate to be proven by a deliberate violation rather than
by passing on a clean tree. The proofs are produced by
[`scripts/ci/prove-gates.sh`](../../scripts/ci/prove-gates.sh), which introduces
one violation at a time in a throwaway git worktree and asserts that the expected
gate — and only that gate — reports it.

A repeatable prover was chosen over a one-time manual demonstration on purpose: a
transcript stops being evidence the moment the gate script changes, and the gate
script will change. The prover runs in CI on every build, so a gate that loses the
ability to fail becomes a build failure rather than a quiet regression.

Two of the strings the prover must write are strings a whole-repository gate
forbids; it assembles them at runtime from fragments, so the prover itself cannot
match them (ADR-0004 §4).

**The transcript below is redacted, mechanically, by the prover.** Gate C and
Gate E scan the whole repository, so a document quoting what they matched trips
the gate it documents — this file did exactly that, and CI caught it. Matched
literals are rewritten into the gates' own notation (`private[_]key`); paths,
line numbers, gate names and verdicts are untouched. The alternative fix would
have been to exempt `docs/evidence/` from Gate C, and a secret scan with a
directory it does not look at is not a secret scan.

## Transcript

Produced by `./scripts/ci/prove-gates.sh` on 2026-08-19, macOS, git worktree from
the branch head. Exit code 0.

```
PENDING REGENERATION
```

## What each case demonstrates

| Case | Violation | Gate | Why this violation and not another |
| --- | --- | --- | --- |
| 1 | `Google.Cloud.BigQuery.V2` in a `.csproj` | A | The package is the load-bearing control: absent it, the streaming-insert surface is unreachable whatever the symbols are called. |
| 2 | `InsertRowsAsync(` in worker source | B | The symbol the .NET client actually exposes. The retired `insertAll` grep could never have caught it — the defect that produced §W6.2. |
| 3 | A clean `.cs` file in an undeclared directory | B coverage | The gate stays green while covering less than it did; nothing else signals the narrowing (issue #5). |
| 4 | A service account key JSON | C | Both markers, in a path no denylist would have thought to include. |
| 5 | `pull_request_target` in a workflow | D | The trigger that hands repository write permissions to fork code. |
| 6 | The retired project name in a document | E | Reintroduced the realistic way: a document re-derived from a stale external snapshot. |

## A gate that fired on this branch

Gate D's first implementation scanned every file under `.github/workflows/` and
failed on `README.md` there — the document that explains why the workflow does
not use that trigger. The fix was to scan workflow files (`*.yml`, `*.yaml`), the
only extensions GitHub reads, rather than to start an exclusion list. The
invariant is a property of workflow files; a document naming the string is not a
defect.

Worth recording because it is the failure mode §W6.2 exists to prevent, arriving
from the direction nobody watches: not a gate too weak to catch a violation, but
a gate wide enough to catch its own documentation. Under time pressure the cheap
fix is an exclusion path, and the exclusion list is how gates stop meaning
anything.

## Not covered here

The Terraform plan guard is proven separately, against fixtures, by
`scripts/ci/terraform-plan-guard.sh --self-test`: one fixture per assertion
(forbidden resource type, scaling bounds, region, Pub/Sub topic retention) plus a
clean plan that must pass. It also runs on every CI build.

The kill-switch live-fire is the other proof this project treats as mandatory,
and it cannot be produced from the repository: see
[`docs/runbooks/kill-switch.md`](../runbooks/kill-switch.md) §4.
