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

## Transcript

Produced by `./scripts/ci/prove-gates.sh` on 2026-08-19, macOS, git worktree from
the branch head. Exit code 0.

```
gate failure proofs (F0 spec §6)

--- case 0: clean tree
    invariant gates (F0 spec §W6.2)
    
    ok    Gate A — no legacy BigQuery client package
    ok    Gate B — no streaming-insert symbols in source
    ok    Gate B coverage — all source under the scanned roots
    ok    Gate C — no exported service account keys
    ok    Gate D — no pull_request_target in workflows
    ok    Gate E — retired project name absent
    
    all gates passed
    baseline: gates pass on a clean tree

--- case 1: Gate A: legacy BigQuery client package in a csproj
    invariant gates (F0 spec §W6.2)
    
          forbidden package: Google[.]Cloud[.]BigQuery[.]V2
            worker/Plumbline.Worker/Plumbline.Worker.csproj:3:    <PackageReference Include="Google.Cloud.BigQuery.V2" Version="3.5.0" />
    FAIL  Gate A — legacy BigQuery client package referenced
    ok    Gate B — no streaming-insert symbols in source
    ok    Gate B coverage — all source under the scanned roots
    ok    Gate C — no exported service account keys
    ok    Gate D — no pull_request_target in workflows
    ok    Gate E — retired project name absent
    
    1 gate(s) failed:
      - Gate A — legacy BigQuery client package referenced
    proven: Gate A failed on the violation

--- case 2: Gate B: streaming-insert symbol in worker source
    invariant gates (F0 spec §W6.2)
    
    ok    Gate A — no legacy BigQuery client package
          streaming-insert symbol: InsertRowsAsync[(]
            worker/Plumbline.Worker/BadWrite.cs:3:    public static void Write(BigQueryClient client) => client.InsertRowsAsync(null, null, null);
    FAIL  Gate B — streaming-insert symbol in source
    ok    Gate B coverage — all source under the scanned roots
    ok    Gate C — no exported service account keys
    ok    Gate D — no pull_request_target in workflows
    ok    Gate E — retired project name absent
    
    1 gate(s) failed:
      - Gate B — streaming-insert symbol in source
    proven: Gate B failed on the violation

--- case 3: Gate B coverage: source outside the declared roots
    invariant gates (F0 spec §W6.2)
    
    ok    Gate A — no legacy BigQuery client package
    ok    Gate B — no streaming-insert symbols in source
          source files outside the declared scan roots (collector worker analytics infra/functions):
            services/gateway/Program.cs
    FAIL  Gate B coverage — source outside the scanned roots
    ok    Gate C — no exported service account keys
    ok    Gate D — no pull_request_target in workflows
    ok    Gate E — retired project name absent
    
    1 gate(s) failed:
      - Gate B coverage — source outside the scanned roots
    proven: Gate B coverage failed on the violation

--- case 4: Gate C: exported service account key
    invariant gates (F0 spec §W6.2)
    
    ok    Gate A — no legacy BigQuery client package
    ok    Gate B — no streaming-insert symbols in source
    ok    Gate B coverage — all source under the scanned roots
          service account key field: "private[_]key"
            infra/terraform/leaked.json:3:  "private_key": "-----BEGIN PRIVATE KEY-----"
          service account key type: "type"[[:space:]]*:[[:space:]]*"service[_]account"
            infra/terraform/leaked.json:2:  "type": "service_account",
    FAIL  Gate C — exported service account key material
    ok    Gate D — no pull_request_target in workflows
    ok    Gate E — retired project name absent
    
    1 gate(s) failed:
      - Gate C — exported service account key material
    proven: Gate C failed on the violation

--- case 5: Gate D: pull_request_target in a workflow
    invariant gates (F0 spec §W6.2)
    
    ok    Gate A — no legacy BigQuery client package
    ok    Gate B — no streaming-insert symbols in source
    ok    Gate B coverage — all source under the scanned roots
    ok    Gate C — no exported service account keys
          fork-privileged trigger: pull_request[_]target
            3:  pull_request_target:
    FAIL  Gate D — pull_request_target in a workflow
    ok    Gate E — retired project name absent
    
    1 gate(s) failed:
      - Gate D — pull_request_target in a workflow
    proven: Gate D failed on the violation

--- case 6: Gate E: retired project name
    invariant gates (F0 spec §W6.2)
    
    ok    Gate A — no legacy BigQuery client package
    ok    Gate B — no streaming-insert symbols in source
    ok    Gate B coverage — all source under the scanned roots
    ok    Gate C — no exported service account keys
    ok    Gate D — no pull_request_target in workflows
          retired project name:
            docs/stale-snapshot.md:3:BigQuery dataset: agent_lens_dataset (pre-rename)
    FAIL  Gate E — retired project name present
    
    1 gate(s) failed:
      - Gate E — retired project name present
    proven: Gate E failed on the violation

all 6 gate failure proofs passed
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
