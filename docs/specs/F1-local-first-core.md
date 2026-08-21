# F1 — Local-First Core: Work Package Spec

**Version:** 0.1 · **Status:** Approved on handoff (2026-08-21) · **Date:** 2026-08-21
**Phase budget:** ~25 h · **Executor:** Claude Code (autonomous mode, §1)
**Predecessor:** F0 complete ([`F0-completion-note.md`](F0-completion-note.md)); the
kill-switch live-fire is deferred to the F2 entry gate (issue #33), which F1 does not
touch because F1 does not touch the cloud.

---

## 1. Purpose

Build the whole pipeline locally: Go collector, .NET ingestion worker, v1.41
normalization for three dialects, and a docker-compose end-to-end path that takes raw
`ExportTraceServiceRequest` fixtures to queryable normalized rows. GCP is not touched.

The phase exits when three dialects **plus the unknown-dialect fallback** are normalized
and queryable locally, with golden-file tests as the enforcement mechanism of ADR-0001
§3.1 rather than as a testing habit.

## 2. Governance mode: autonomous (phase-scoped)

F1 runs under a relaxed governance model, authorized by the maintainer on handoff of the
directive this document renders. The delta from the standard propose → confirm model:

1. **The handoff directive is the single approval.** Every decision inside its scope is
   pre-authorized; Claude Code decides, implements, and proceeds.
2. **A decision log replaces propose → confirm.** Every autonomous decision of
   consequence is recorded in [`F1-decision-log.md`](F1-decision-log.md) when it is made,
   with alternatives, rationale, and reversibility class.
3. **Self-merge is authorized** once CI is green and Gates A–E pass. One work item = one
   branch = one PR still holds (`CLAUDE.md`); what is relaxed is the review wait, not the
   branch discipline.
4. **Two batched human checkpoints only** (§8).
5. **The hard limits are unchanged** (§7, "Never"). Autonomy does not reach them.

Why this is safe here, stated so that F2 does not inherit it by habit: F1 creates and
mutates no GCP resource, so the bill cannot move; every artefact is a revertible commit
behind branch protection. The blast radius of a wrong autonomous decision is rework, not
an invariant violation. F2 has a cloud footprint and does not inherit this mode.

## 3. Decisions resolved on handoff

These are settled, not open. Each is restated in [`F1-decision-log.md`](F1-decision-log.md)
with its reversibility class.

### D1 — Freeze A moves to the F3 entry gate

The Brief and the F0 spec place the eval-plan freeze before "F1 code". F1 code —
collector, worker, normalization — has no dependency on evaluation criteria. Freeze A
protects the integrity of the seeded-regression experiment, which begins in F3. Holding
F1 behind the unresolved Adjudicator ground-truth question buys nothing and blocks
everything.

**Decision:** Freeze A (criteria, formulas, rubric, dataset spec) is the **F3 entry
gate**. Freeze B (numeric constants via `tools/calibrate.py`) stays where it is, at F3
before the first run.

Consequences carried out in W1: [`F0-foundations.md`](F0-foundations.md) §2 and W3, and
the Brief's phase text, carry dated amendment notes. `docs/eval-plan.md` §2 still reads
"F1 entry gate" and **is not edited in F1** (§4) — the contradiction is real, is recorded
here and in ratification issue #35, and is resolved at Freeze A by the human who performs
it. Ratification is a C2 item and blocks nothing before then.

### D2 — External-dialect fixtures are constructed, and say so

The Anomaly Adjudicator and the Apartment Triage agent are independent projects outside
this handoff. Real captures from them cannot be produced autonomously.

**Decision:** `langgraph-python` and `dotnet-agent` fixtures are **constructed** from
documented emitter behaviour and tagged `provenance: constructed` in the fixture
manifest, with the construction basis named per fixture.

**Accepted risk:** the resource and scope markers that dialect detection keys on may not
match what those emitters really send. What the golden tests then prove is the
*normalization contract*; what they do not prove is *detection fidelity against a real
emitter*. That limit is stated in the manifest, not buried here. Mitigation is an F4
re-validation issue (opened in W8) where real captures confirm or replace the
constructed ones during dogfooding.

### D3 — The claude-code fixture reuses P11 evidence if it can

**Decision:** inspect [`docs/evidence/claude-code-otel-capture.md`](../evidence/claude-code-otel-capture.md)
first. If it yields usable `ExportTraceServiceRequest`-level data including tool and hook
spans, promote it to a fixture with `provenance: captured`. If it does not, trigger
checkpoint C1: write the capture runbook, hand it to the maintainer, consume the dropped
file. Other work items do not wait on C1.

Outcome, recorded in the decision log: the evidence is a redacted marker inventory, the
raw capture was deliberately never committed, and no tool or hook span was ever observed.
Both halves of the condition fail, so C1 fires and the F1 fixture is built from the
measured inventory under its own provenance class.

### D4 — Local BigQuery stand-in

**Decision:** prefer `goccy/bigquery-emulator`, which speaks the Storage Write API over
gRPC, and verify that empirically before the worker's write path depends on it.
**Authorized fallback:** an `ISpanSink` abstraction with the real Storage Write API
client behind it and a local sink for the end-to-end run. Either branch must keep the
`insertAll` prohibition structurally true — the worker has no code path to the legacy
streaming-insert surface in either case, which is Gate A's subject and not a matter of
discipline.

### D5 — Local key registry stand-in

The collector validates API keys against a hashed registry, which is Firestore in the
cloud. **Decision:** define a `KeyRegistry` interface; the local implementation is
file-backed — hashed keys in a mounted file — rather than the Firestore emulator, to keep
docker-compose from growing an emulator per cloud dependency. The Firestore adapter is
F2 work. Reversal is cheap.

### D6 — ADR-0006 is authored and implemented as `Proposed`

Claude Code emits `user.email`, `user.id` and (documented, unobserved) `workspace.host_paths`.
Architecture §2.1 forbids semantic parsing in the collector, so redaction must live in the
worker — which means PII transits Pub/Sub in the wire payload. Locally that is a
non-issue; the ADR exists to argue the cloud consequence, including the DLQ, where a
poison message would sit until a human drains it.

**Decision:** Claude Code authors ADR-0006 with status `Proposed` — never self-accepted
(§7) — and implements redaction as an **isolated normalization stage**: post-deserialize,
pre-write, driven by a rule file versioned alongside the mappings at
`normalization/redaction/v1/claude-code.yaml`. Isolation is the point: if C2 rejects the
boundary, moving the stage is a small change rather than a rewrite. Redacted values are
replaced by a deterministic marker so that joins and counts survive redaction, and each
rule states which field it covers and why.

## 4. Out of scope (hard)

- Any GCP resource creation, mutation, or API call against the real project. F1's bill
  impact is exactly zero because F1 never reaches the cloud.
- Kill-switch work (#33) — F2 entry gate, human-gated.
- Eval engine, judges, datasets, `tools/calibrate.py` (F3).
- **Editing `docs/eval-plan.md` in any way.** Standing prohibition for the phase.
- The Adjudicator and Apartment Triage codebases (independent projects).
- Terraform: zero changes. F0 state is untouched and F2 owns application infrastructure.
- Flipping any ADR to `Accepted`.
- Dashboards, SPA, load generator (F4).

## 5. Work items

Dependency-ordered. W3 and W4 are independent of each other and both depend on W2.

### W1 — Phase bootstrap
- This spec and [`F1-decision-log.md`](F1-decision-log.md).
- D1 amendments to the F0 spec and the Brief, plus a ratification issue for C2.
- Vendor the semconv v1.41 registry at `normalization/semconv/v1.41/` with checksums, a
  refresh procedure, the upstream license, and the closed external-attribute allowlist
  (issue #8). First because every mapping YAML and golden expectation references it.

### W2 — Fixture corpus and golden harness
- Layout `testdata/fixtures/<dialect>/`: the raw `ExportTraceServiceRequest` as binary
  `.pb`, a human-readable twin, the expected normalized rows as JSON, and a
  `manifest.yaml` carrying provenance, capture date or construction basis, and validation
  status.
- Constructed fixtures per D2; the claude-code fixture per D3.
- Each dialect corpus carries three cases: a happy-path multi-span trace with GenAI
  attributes, an unmapped-attribute case that proves losslessness, and a malformed
  payload for the W5 NACK path.
- One golden harness per language, diffing normalizer output against expected rows.
  **Failure output shows a field-level diff, not a blob mismatch** — these tests are
  ADR-0001's enforcement mechanism, so the quality of their diagnostics is a deliverable
  and not a nicety.

### W3 — Go collector
- OTLP receivers on HTTP `4318` and gRPC `4317`, health endpoint, graceful shutdown,
  configuration from the environment only (no config file in the image).
- API-key authentication through `KeyRegistry` (D5), constant-time comparison,
  `api_key_id` resolution.
- Per-key in-memory token bucket; architecture §6.2's approximation limit is accepted and
  named in a code comment that cites the section rather than restating it.
- Batching and split: compressed payload target ≤ 4 MiB; oversized export requests are
  **split, never truncated**; gzip.
- Publish to the official Pub/Sub emulator with exactly the message attributes in
  architecture §3.2.
- **Boundary enforcement:** the collector imports no OTLP semantic helper. It handles the
  request as opaque bytes plus the minimal envelope structure that splitting requires,
  and a test asserts payload bytes in == payload bytes out.
- Unit tests per component, a contract test on the published envelope, race detector in
  CI.

### W4 — Mapping tables and the normalization core (.NET)
- Mapping YAML schema, documented beside the mappings: source attribute → target column,
  type coercion, multi-source precedence.
- Build-time embedding (mechanism chosen and logged).
- Dialect detection per architecture §5: deterministic, resource/scope-marker based, with
  the collector hint as tiebreaker only and mismatches logged. Unknown dialect takes the
  generic OTLP path, `source_dialect='unknown'`, counter incremented, nothing dropped.
- Normalizer producing typed `gen_ai_*` columns, the lossless `attributes` JSON
  remainder, and `events`/`links` as unflattened JSON.
- Redaction stage per D6, plus ADR-0006 authored as `Proposed`.
- Golden-file tests for three dialects and the unknown path, on the W2 harness.

### W5 — Ingestion worker service (.NET)
- Push endpoint accepting the Pub/Sub push envelope. OIDC validation is **stubbed behind
  an interface** locally and the stub is visible in the code, so it cannot reach the cloud
  unnoticed; real validation is F2.
- Gunzip → deserialize → detect → normalize → redact → write through the D4 sink.
- Poison handling: a malformed fixture NACKs, is redelivered by the emulator, and lands
  in `traces-dlq` after the maximum attempts, while happy-path messages are unaffected.
  The tested property is *no silent degradation*.
- Dedup is **not** implemented in the worker (architecture §3.3 — downstream views own
  it). The `spans_deduped` and `spans_real` view DDL lives in `analytics/sql/`, is applied
  in compose, and tests read views rather than the base table.

### W6 — docker-compose end-to-end
- Services: collector, worker, Pub/Sub emulator, BigQuery emulator (or the D4 fallback),
  and a sender utility that posts fixture files with a test API key.
- One command brings the stack up, seeds keys, sends every dialect fixture, polls, queries
  the views, diffs against the golden expectations, asserts the DLQ state, and exits with
  a meaningful code. Deterministic and CI-runnable.
- `docs/runbooks/local-dev.md`: prerequisites, commands, teardown, troubleshooting.

### W7 — CI extension
- Path-filtered jobs run real tests: Go build/vet/test with `-race`, .NET build/test,
  golden tests.
- Whether the compose end-to-end runs on every pull request or on `main` only is decided
  from its measured runtime. Either answer is acceptable; not stating which was chosen,
  and why, is not.
- Gates A–E stay whole-repo and unchanged in scope. A new file class that trips a gate
  falsely is fixed **in the pattern**, per the notation discipline in
  `scripts/ci/invariant-gates.sh`, never by adding an exclusion list.

### W8 — Phase close
- F1 completion note: DoD checklist with evidence links, decision-log summary, deferred
  items.
- Issues: close #8 on its three repository-side items (#36 carries the fourth to Freeze
  A), resolve #10's procedure half and record the capture status, update #11 with the
  ADR-0006 state, open the F4 fixture re-validation issue (D2).
- Assemble the C2 review packet (§8).

## 6. Definition of Done

1. Three dialects and the unknown fallback normalized; golden-file tests green and
   running in CI on `main`.
2. A single command runs the end-to-end path green: fixtures in, normalized rows
   queryable through `spans_deduped` / `spans_real`, poison message provably in the DLQ.
3. The collector byte-identity test is green — ADR-0001's wire-only scope mechanically
   enforced rather than asserted.
4. Mapping YAML versioned under `normalization/mappings/v1.41/` and embedded at build;
   redaction rules under `normalization/redaction/v1/`; semconv vendored and #8 closed.
5. ADR-0006 exists as `Proposed`, with the redaction stage implemented and isolated.
6. [`F1-decision-log.md`](F1-decision-log.md) complete: every D-level and W-level
   autonomous decision recorded with rationale and reversibility class.
7. CI green on `main`, Gates A–E passing, zero GCP mutations — Terraform state untouched
   and no cloud API call in the end-to-end path, asserted by the absence of credentials
   in it rather than by intent.
8. Fixture manifests state provenance honestly, and the F4 re-validation issue is open.

## 7. Decision authority

| Class | Examples | Authority |
| --- | --- | --- |
| Decide alone, log it | Library and package choices, project layout, test frameworks, embedding mechanism, end-to-end cadence in CI, port conventions, coverage thresholds | Claude Code |
| Decide alone, log prominently and surface at C2 | D4 fallback activation, fixture construction basis, any spec-gap fix, any deviation from architecture wording | Claude Code |
| Batched human checkpoint | claude-code real capture (C1), ADR-0006 acceptance, D1 ratification, constructed-fixture risk sign-off (C2) | Human |
| **Never** | Flipping an ADR to `Accepted`; editing `eval-plan.md`; any GCP mutation; kill-switch scope; weakening branch protection or a gate; secrets in the repository; touching the Adjudicator or Triage codebases | — |

## 8. Human checkpoints

**C1 — conditional, mid-phase.** Fires when P11 evidence is insufficient (D3; it is).
Claude Code delivers a ready-to-run capture runbook — commands, expected output shape,
where to drop the file — the maintainer executes it on their own terminal, because a
nested `claude -p` cannot authenticate and therefore never reaches a tool call, and
Claude Code then validates and promotes the capture. Every other work item proceeds in
parallel: C1 never blocks the phase.

**C2 — phase exit.** One review batch: ADR-0006 accept or reject, D1 ratification,
constructed-fixture risk acknowledgement, completion-note sign-off. A rejection at C2
produces scoped rework items; it does not reopen the phase.

## 9. Test expectations

- Golden-file tests are the primary contract tests. Diff quality is part of the
  deliverable.
- Collector: unit, envelope contract, and byte identity; `-race` in CI.
- Worker: unit per stage (detect, normalize, redact), golden per dialect, and
  poison/DLQ behaviour asserted in the end-to-end run rather than mocked away.
- End-to-end: deterministic, single command, CI-capable. Flakiness is a defect, not an
  environment excuse.
- No coverage theatre. A threshold, if set, is chosen for signal and logged with its
  reason; it does not decorate the README.

## 10. Changelog

**v0.1 — 2026-08-21** — handoff directive rendered into the repository as the phase's
source of truth (W1). Content follows the directive; three things are stated here that
the directive left implicit:

1. §3 D1 records that `docs/eval-plan.md` §2 still names the F1 entry gate and is not
   edited in this phase, so the contradiction is visible in the repository rather than
   only in the ratification issue.
2. §3 D3 records the outcome of the P11 inspection (C1 fires) rather than leaving the
   condition open, because the inspection is complete.
3. §8 C1 names why the maintainer must run the capture — the nested-authentication
   finding already recorded in `docs/evidence/claude-code-otel-capture.md` §3 — so the
   checkpoint does not read as a preference.
