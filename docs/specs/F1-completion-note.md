# F1 — Completion note

**Phase:** F1, Local-First Core · **Status:** complete; C2 reviewed and closed (§8)
**Date:** 2026-08-21 · **Spec:** [`F1-local-first-core.md`](F1-local-first-core.md)
**Decisions:** [`F1-decision-log.md`](F1-decision-log.md) — D1–D6 and 26 W-level entries

The pipeline runs end to end on a laptop: OTLP into a Go collector, out of BigQuery views
as normalized rows, with three emitter dialects and the unknown fallback mapped to GenAI
semconv v1.41. No GCP resource was created and no credential was used — the end-to-end run
asserts the second of those rather than promising it.

---

## 1. Definition of Done

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Three dialects + unknown fallback normalized; golden tests green in CI on `main` | met | 7 golden files, 95 tests; `worker and analytics (.net)` on every run |
| 2 | One command runs the end-to-end path green: rows through the views, poison in the DLQ | met | `make e2e`; CI job `local end-to-end`, **1 m 54 s** |
| 3 | Collector byte-identity test green | met | `TestPayloadBytesInEqualPayloadBytesOut` — both transports, four dialects |
| 4 | Mappings embedded at build; redaction rules versioned; semconv vendored (#8) | met | `normalization/{mappings,redaction,semconv}/` |
| 5 | ADR-0006 exists as `Proposed`, redaction implemented and isolated | met — and **since accepted**, see §8 | [ADR-0006](../adr/ADR-0006-pii-redaction-boundary.md) |
| 6 | Decision log complete, every decision with rationale and reversibility class | met | [`F1-decision-log.md`](F1-decision-log.md) |
| 7 | CI green on `main`; gates passing; zero GCP mutations | met | Gates A–F + their failure proofs; the run refuses a stack that references a credential |
| 8 | Fixture manifests state provenance honestly; F4 re-validation issue open | met | four manifests; issue #42 |

**One-way decisions:** none, as the phase was designed to guarantee. Everything F1 produced
is a commit, and nothing it did reached outside the repository.

## 2. What the phase built

| Work item | Delivered | PR |
| --- | --- | --- |
| W1 | Phase spec and decision log; D1 amendments; semconv v1.41 vendored with checksums and the external-attribute allowlist | [#34](https://github.com/arslan-kursad/plumbline/pull/34) |
| W2 | Fixture corpus (3 dialects + unknown, 3 cases each), expected rows, row model, field-level diff engine, corpus integrity tests, C1 capture runbook | [#37](https://github.com/arslan-kursad/plumbline/pull/37) |
| W3 | Go collector: two OTLP transports, hashed key registry, per-key token bucket, envelope-only splitting, Pub/Sub publish; Gate F | [#38](https://github.com/arslan-kursad/plumbline/pull/38) |
| W4 | Three mapping tables, dialect detection, normalizer, redaction stage, ADR-0006, semconv conformance tests | [#39](https://github.com/arslan-kursad/plumbline/pull/39) |
| W5 | Push endpoint, `ISpanSink`, the `spans` table and both views as SQL | [#40](https://github.com/arslan-kursad/plumbline/pull/40) |
| W6 | docker-compose stack, seeding, sender, end-to-end runner and verifier, local-dev runbook, the CI job | [#41](https://github.com/arslan-kursad/plumbline/pull/41) |
| W7 | Folded into W2, W3 and W6 as each test suite appeared — see §3 | — |
| W8 | This note, the issue updates, the C2 packet | this PR |

**W7 was not a separate pull request, and that is a deviation worth naming.** The directive
scopes it as "path-filtered jobs now run real tests". A test suite that CI does not run is
not a control, so each suite joined CI in the work item that created it: `dotnet test` in
W2, `go test -race` in W3, the end-to-end job in W6. What remained for W7 — the cadence
decision and its reasoning — is decision-log entry W6.4 and the job table in
`.github/workflows/README.md`. Nothing is missing; it is in six commits instead of one.

## 3. Enforcement, and what each control actually catches

| Control | Class | Catches |
| --- | --- | --- |
| Golden-file tests | prevent (merge gate) | Any change to what a mapping produces, as a field-level diff |
| Byte identity | prevent | The collector re-encoding a payload |
| Import boundary | prevent | An OTLP semantic import in the collector — with a test proving the check can fail |
| Gate A | prevent | The forbidden BigQuery client package |
| Gate F | detect | An issued API key committed to the repository |
| Semconv conformance | prevent | A mapping targeting a name the pin does not define |
| Proto/SQL agreement | prevent | The row proto and the table schema drifting apart |
| Unknown-dialect note, hint-mismatch note | report only | A missing or wrong mapping, visibly rather than invisibly |
| Redaction | prevent | Personal data reaching a stored row — **for a dialect that has rules** (§4) |

## 4. What is not true, stated plainly

**SC-1 row 1.2 is not met, and cannot be met by this phase.** The eval plan requires
"≥1 fixture per dialect **captured from a real emitter**, not hand-authored". F1 ships
none: two dialects are `constructed` from documented emitter behaviour because those
agents are independent projects outside the handoff, and `claude-code` is
`derived-from-measured-evidence` — its markers are measured, its payload is not a promoted
capture. Every manifest says so. The golden tests are therefore evidence about the
**normalization contract** and not about **detection fidelity against a real emitter**.
Recorded on #36 for Freeze A; closed by C1 and by F4 dogfooding (#42).

**Detection may be wrong for the two external dialects.** Their scope markers come from
documentation. If a real Anomaly Adjudicator presents a different instrumentation scope,
its spans land as `unknown` — normalized generically, kept, and counted, which is the
designed failure mode rather than a loss.

**Redaction covers claude-code only, and nothing prevents a fourth dialect from arriving
without rules.** ADR-0006 names this as a report-class gap with no report. It is
procedural: a new dialect's pull request has to answer "what does this emitter send about
people".

**The end-to-end run is not evidence about the cloud.** Every service in it is a
stand-in — a file-backed key registry instead of Firestore, stubbed push authentication
instead of OIDC, an emulator instead of BigQuery. Two differences from the cloud path are
recorded rather than smoothed over: the local table is unpartitioned, because the stand-in
refuses `PARTITION BY` (W6.2), and the stand-in cannot resolve the implicit `_default`
write stream, so that one branch names a stream explicitly (W6.1).

**`docs/eval-plan.md` still says Freeze A is the F1 entry gate**, and row 1.1 still points
at a fixture path that does not exist. Both are deliberate: editing the pre-registration
document is prohibited for the whole phase. Recorded in #35 and #36 for the human who
performs Freeze A.

**OIDC push validation does not exist.** The worker refuses to start with the stub outside
a Development environment, and the OIDC implementation refuses every request until F2
writes it. An incomplete deployment is visibly broken rather than quietly open.

## 5. C2 — the review batch

Four decisions, all of them reversible today and expensive later.

1. **ADR-0006 — accept or reject** ([ADR](../adr/ADR-0006-pii-redaction-boundary.md), #11).
   The substance is not where the code lives; it is that the ADR accepts, in writing, that
   unredacted personal data transits Pub/Sub and **persists in `traces-dlq` until a human
   drains it**. Alternative C — not ingesting claude-code into the shared path — is the
   option to take if that is unacceptable, and it costs a success criterion rather than a
   rewrite. Two F2 obligations follow from acceptance and are named in the ADR.
2. **D1 ratification** (#35). Freeze A moved to the F3 entry gate. Rejecting it costs
   nothing already built.
3. **Constructed-fixture risk** (§4, #42). Acknowledge that SC-1's evidence is a
   normalization contract and not detection fidelity, until F4.
4. **Scope calls made autonomously**: Gate F and the key format (W3.4), the OTLP/JSON twin
   instead of textproto (W2.1), the `attributes` column shape (W2.3), `ROW_NUMBER` instead
   of `QUALIFY` (W5.4), and W7 folded into other work items (§2).

**C1 remains open and does not block.** `docs/runbooks/claude-code-capture.md` is ready to
run on an interactively authenticated session; a nested one cannot authenticate, which is
why this is a human step. When a capture lands, the fixture is promoted, the manifest
becomes `provenance: captured`, and the evidence file's §3 stops saying tool and hook spans
were never observed.

## 6. Deferred

| Item | To | Why |
| --- | --- | --- |
| Kill-switch live-fire (#33) | F2 entry gate | Deferred in F0; F1 deploys nothing, so nothing was at risk |
| OIDC push validation | F2 | Needs a real push subscription identity |
| Firestore key registry adapter | F2 | The interface is what F1 needed to get right (D5) |
| `require_partition_filter` in practice | F2 | Terraform owns the cloud table; the stand-in cannot express it |
| Real captures for all three dialects | C1 and F4 | #42 |
| `eval-plan.md` reconciliation | Freeze A | #35, #36 |

## 7. Numbers

| | |
| --- | --- |
| Tests | 95 .NET, 8 Go packages (`-race`), 7 golden files, 7 gate failure proofs |
| End-to-end | 13 rows, 3 dead-lettered poison messages, 1 m 54 s cold |
| Fixtures | 10 payloads across 4 dialect directories, every one synthetic in content |
| Mapped columns | 15 typed `gen_ai_*`, all validated against the vendored v1.41 registry |
| GCP resources created | 0 |

## 8. C2 outcome — 2026-08-21

The maintainer reviewed the batch in §5 and accepted all four items. What each acceptance
changed:

### 1. ADR-0006 — accepted

`Proposed` → `Accepted`, and architecture §10's index with it (v0.7). The status was not
a formality: an ADR written under autonomous governance could not flip its own status, and
the index carried `Proposed` for exactly as long as that was true.

What was accepted is the consequence, not the code's location: **unredacted personal data
transits Pub/Sub and persists in `traces-dlq` until a human drains it.** Two F2
obligations were advisory while the ADR was `Proposed` and are now binding — the DLQ
runbook must state that a dead-lettered message may carry personal data, and DLQ retention
must be set deliberately rather than left at the default. Tracked in
[#44](https://github.com/arslan-kursad/plumbline/issues/44), and F2 should not deploy a
subscription before they are met.

The stage stays isolated. That was the argument for isolation while the decision was open,
and it remains the argument for it now: a later boundary change should cost one class and
its call site.

Issue #11 is closed.

### 2. D1 — ratified

Freeze A is the F3 entry gate. The amendment notes in `F0-foundations.md` and
`project-brief.md` now record the ratification rather than describing it as pending.
Issue #35 is closed.

`docs/eval-plan.md` is still stale on this line, deliberately: it is a pre-registration
document, and the human performing Freeze A reconciles it in the same action
([#36](https://github.com/arslan-kursad/plumbline/issues/36)), which also carries the
row-1.1 path and the row-1.2 threshold this phase raised.

### 3. Constructed-fixture risk — acknowledged

The maintainer accepted that F1's golden tests are evidence about the **normalization
contract** and not about **detection fidelity against a real emitter**, and that SC-1 row
1.2 is therefore unmet until real captures exist. This changes no artefact — every
manifest already said so — and it does change what may be claimed from SC-1 before F4.
[#42](https://github.com/arslan-kursad/plumbline/issues/42) is the path to meeting it;
C1 remains available for claude-code at any time.

### 4. Autonomous scope calls — approved

Gate F and the API-key format (W3.4), the OTLP/JSON twin instead of textproto (W2.1), the
three-level `attributes` column shape (W2.3), `ROW_NUMBER` instead of `QUALIFY` (W5.4),
and W7 folded into the work items that created each test suite (§2). All five stand as
made.

### What C2 did not close

**C1.** `docs/runbooks/claude-code-capture.md` is still waiting on an interactively
authenticated session. It blocked nothing during the phase and blocks nothing now; what it
changes when it lands is the claude-code fixture's provenance, and the evidence file's §3
statement that tool and hook spans have never been observed.
