# Guard fixtures

Plans the guards under `scripts/ci/` are proven against, in both directions: for
every assertion there is a fixture that satisfies it and one that violates it. A
check verified only against a passing plan is unverified (F0 spec §6).

## The rule

**Fixtures are derived from real `terraform show -json` output. They are never
authored and never hand-edited.**

The only sanctioned path is [`scrub_plan.py`](../scrub_plan.py):

```bash
terraform -chdir=infra/terraform plan -lock=false -out=/tmp/capture.tfplan
terraform -chdir=infra/terraform show -json /tmp/capture.tfplan > /tmp/capture.json
python3 scripts/ci/scrub_plan.py /tmp/capture.json -o scripts/ci/testdata/plan-<name>.json
```

A plan can be captured *before* it is applied, so this works for a wave that has
not run yet — there is no state in which a real capture is unavailable and an
authored fixture is the only option.

### Why the rule exists

`plan-wave2.json` was written by hand and carried only the fields the checks of
its day happened to read. It was not wrong about anything it claimed; it was
**silent** about `name = "ingestion-worker"`, which every real plan carries. The
first check to read that field — the `allUsers` invoker guard — reported a
violation against the fixture rather than against the plan it stood for.

That failure runs in the expensive direction. A guard firing on a fixture looks
like a broken guard, and the cheap response is to loosen the guard until the
fixture goes quiet, which would have removed a real control to satisfy an
artifact of how a test file was typed. Decision log W3.6.

So: a fixture that omits a field is the failure mode. **It is never a size
optimisation** — see `plan-noop.json` below, which is large and stays large.

### What `scrub_plan.py` guarantees

- **No key is removed, added or retyped.** Values are substituted; structure,
  key sets and list lengths are asserted identical to the source.
- **No secret is named in the tool.** A captured plan is a secret-bearing
  artifact — `variables` alone carries `alert_email` and `billing_account_id` in
  plaintext, and `prior_state` repeats them. The rules for those are *shape*
  rules, so this repository holds no example of either.
- **Anything sensitive that survives is a failure**, reported by JSON path and
  rule name and never by value, because the message reaches a public log.
- **Idempotent**: re-running over its own output changes nothing.

Its own tests are in [`scrub_plan_test.py`](../scrub_plan_test.py) and run in the
`invariant gates` job.

## Provenance

[`fixtures.manifest.json`](fixtures.manifest.json) records where every fixture
came from. `provenance` is one of:

| Value | Meaning |
| --- | --- |
| `captured` | Derived from real plan output through `scrub_plan.py`, unmodified since. |
| `hand-authored-legacy` | Predates the rule. Grandfathered until touched — the moment a PR modifies one, it must be re-derived and become `captured`. |

The gate in `invariant-gates.sh` enforces both halves: a fixture added or changed
in a commit must be `captured`, and every fixture on disk must have a manifest
entry.

Legacy fixtures were **not** churned into captures. Re-deriving a fixture can
change what a guard concludes about it, and doing that across ten files at once
would mix "the guard's verdict moved" in with "the file was regenerated" — so the
rule binds going forward and the manifest is honest about the ones that predate
it.

## A note on `plan-noop.json`

It is roughly 330 KB, against 0.4–3.4 KB for every hand-authored fixture, and
that is deliberate.

It is a real capture of a converged plan — the artifact that reached the approval
gate twice on 2026-08-26 — and 87% of its bulk is `prior_state` and
`configuration`, which no guard currently reads. Deleting those blocks would
shrink it by an order of magnitude and would recreate, at the top level, exactly
the defect this directory's rule closes: a fixture silent about everything the
checks of today do not happen to read.

The smallest *honest* capture was chosen instead — `terraform plan -target=` on a
single resource, which refreshes fewer resources without omitting anything from
the ones it keeps.
