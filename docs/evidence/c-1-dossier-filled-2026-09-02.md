# C-1 dossier — filled copy, 2026-09-02

**Form:** [`c-1-adjudicator-dossier.md`](../specs/c-1-adjudicator-dossier.md) v0.1
**Filled by:** Lane A, from repository reads only · **Status:** partial — see §7
**Revised 2026-09-02** — second pass closed A3 and gave E3 numbers; third pass closed A4 and A5.
**Every field is now answered or carries a decision-shaped `UNKNOWN`.** See §7.
**Source for every sourced field:** `github.com/arslan-kursad/aiqs-agent` @
`0779c04ff98a744285b8b1c93ce35f4efd4a89b2`, committed 2026-07-18T18:20:33Z, read
2026-09-02. Detail in [`c1-adjudicator-readout.md`](c1-adjudicator-readout.md).

**This is not a completed dossier.** Six fields are `UNKNOWN` and §7 lists them with which
of the form's four reasons applies. Two of the six are work; four are not.

---

## Section A — Output contract

**A1 — Output serialization.** **Structured JSON over HTTP.** Schema:
`src/aiqs/api/schemas.py` → `AdjudicateResponse` (Pydantic v2). Enforced at runtime by
Pydantic as the FastAPI response model. The graph's internal state
(`src/aiqs/graph/state.py` → `AdjudicationState`) is wider; the API response is the public
contract and is what P1 should fix.

**A2 — Field inventory.** `AdjudicateResponse`, `schemas.py`:

| Field name | Type | Required | Finite value set? |
|---|---|---|---|
| `item_id` | `str` | yes | no |
| `decision` | `str \| None` | nullable | **yes** — three values |
| `resolved_by` | `str \| None` | nullable | **yes** — three values |
| `pending_human` | `bool` | yes | yes — boolean |
| `calibrated_p` | `float \| None` | nullable | no |
| `tier1_decision` | `str \| None` | nullable | **yes** — three values |
| `applied_target_prevalence` | `float \| None` | nullable | no |
| `pi_source` | `float \| None` | nullable | no |
| `expected_costs` | `dict[str, float] \| None` | nullable | no |
| `indifference_points` | `dict[str, float] \| None` | nullable | no |
| `vlm` | `VLMInfo \| None` | nullable | no (nested) |
| `run_guard_warnings` | `list[str]` | yes, default `[]` | no |

`VLMInfo`: `fired: bool` (required), `verdict`, `confidence`, `reasoning`, `tokens_in`,
`tokens_out` (all nullable). `VLMInfo.verdict` is finite — three values.

**A3 — Enumerations, as emitted.** **Answered.** The values are a typed enum, and the
documentation's casing is not the wire's.

`src/aiqs/eval/decision.py:47-50`:

```python
class Decision(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ESCALATE = "escalate"  # route to a human
```

**A `str, Enum`, so it serialises as its value — lowercase.** `schemas.py` describes
`tier1_decision` as `PASS/FAIL/ESCALATE`, which are the **Python attribute names, not the
emitted strings**. A3 asks for the second, and the answer is `pass` / `fail` / `escalate`.

| Field | Emitted set, exact | Source |
|---|---|---|
| `decision` | `pass` \| `fail` \| `pending_human` | `Decision` values; `pending_human` set literally at `api/main.py:102` |
| `resolved_by` | `policy` \| `vlm` \| `human` | `graph/nodes.py`, `finalize` |
| `tier1_decision` | `pass` \| `fail` \| `escalate` | `Decision` values — **not** the documented upper case |
| `VLMInfo.verdict` | `defect` \| `clean` \| `unsure` | `vlm/backend.py:26`, `Verdict = Literal[...]` |

**Correction to the readout, and it is a real one.** `c1-adjudicator-readout.md` recorded
the sets as *documented in descriptions rather than enforced by types*. That is true of the
**API response model** — `AdjudicateResponse.decision` is `str | None` — and false of the
values themselves:

- `Decision` is a typed enum.
- `vlm/backend.py:26` declares `Verdict = Literal["defect", "clean", "unsure"]`, and the
  parser **raises `VLMParseError`** on an unknown verdict, an out-of-range confidence or a
  missing field (`backend.py:47-66`).

So the sets **are** enforced where they are produced. What is untyped is the response
model's re-declaration of them as bare strings (`api/main.py:103-111` passes the enum
values straight through). **Milder than "contract by convention", and a different fix:**
narrowing the response model's annotations, not adding validation that already exists.

**A4 — Contract stability.** **Answered by measurement, not by argument.**

`results/runs/efficient_ad-small_mvtec-screw_20260622T055657Z/decision_scores.csv` holds
**160 per-item rows** with three decision columns. Every value observed across
**480 emissions**:

| Column | Observed |
|---|---|
| `decision_native` | `escalate` × 41, `fail` × 119 |
| `decision_target` | `pass` × 160 |
| `decision_target_realistic` | `escalate` × 152, `pass` × 8 |

**Nothing outside `{pass, fail, escalate}`.** This is the first field in the dossier
answered by looking at what was emitted rather than at what the code permits, which is what
A4 asks for.

Consistent with the three structural enforcement points — `Decision` is an enum, `Verdict`
is a `Literal` whose parser raises, `AdjudicationState` forbids extra fields — and with the
test coverage in `tests/`.

**One observation worth carrying, though it is not A4's question.** At the plan's default
`target_prevalence = 0.02`, `decision_target` is `pass` for **all 160 items**. Under the
realistic cost matrix it is 152 `escalate` and 8 `pass`. So the policy's verdict
distribution moves sharply with the prevalence prior, and a baseline run whose verdicts are
constant offers a seeded-regression experiment no variance in that column to work with.
**This does not affect E1**, which scores the `R1∧R2∧R3∧R4` contract rather than the
agent's verdict — recorded so it is not mistaken for one.

**A5 — Failure and refusal shape.** **Answered. Three shapes, and only one of them is the
agent declining.**

**Abstain — a first-class outcome, not an error.** `graph/build.py` routes
`cost_policy → vlm_second_look → vlm_abstain_rule → human_interrupt → finalize`. `decision`
is `pending_human` and `resolved_by` is null while the item waits.

**Consequence for E1, and it is why A5 is in the form:** R3 must score a `pending_human`
response as **well-formed**. Treating it as a contract failure would drop
contract-pass-rate every time the cost policy correctly escalated — the endpoint would
penalise the agent for working.

**Rejected input — HTTP, no response body.** `api/main.py`: `400` for invalid base64, an
`image_path` escaping `--image-root`, or a missing file; `401` for a bad key; `404` for an
unknown `item_id`; `409` for an item already finalised. **No `AdjudicateResponse` is
produced**, so these are not contract failures — they are absent outputs, and R3 must not
count them in the denominator.

**Model failure — raised, not coerced.** `vlm/backend.py:47-66` raises `VLMParseError` on
an empty response, invalid JSON, schema-validation failure, out-of-range confidence or an
unknown verdict. **It does not fall back to `unsure`** — the mock backend's
`"no label -> abstain"` at `backend.py:90` is a test path, not production behaviour.

**Answered: a parse failure surfaces as HTTP 400.** `VLMParseError(ValueError)`
(`vlm/backend.py:39`) is caught by the `except ValueError` around `graph.invoke`
(`api/main.py:176-179`) and re-raised as a 400. The Anthropic client is built with
`max_retries=8` (`backend.py:109,128`), so transport failures are retried inside the SDK
before a parse error can surface.

**And that creates a conflation the eval has to undo.** A malformed image and an
unparseable model response produce **the same status code**, so from outside the API they
are indistinguishable. `eval-plan.md` §5.1 needs them apart: *"`error` (harness or quota
failure) is never silently coerced to `fail`; it is reported separately and excluded from
the denominator."* A bad input is a harness error and belongs outside the denominator; a
model that cannot produce parseable output is the agent failing, and belongs inside it.

**Recorded as a finding rather than an `UNKNOWN`:** the distinction is not available at the
API boundary today. Recovering it needs either a distinguishable status or an error body
that names the cause — a small change in the Adjudicator, and one more item for B4's list.

---

## Section B — Trace observability

**B1 — Does the output reach a span attribute?** **No.** There is no instrumentation at
all. Verified four ways: no `opentelemetry-*` among 21 dependencies in `pyproject.toml`; no
OTel import in `api/main.py`, `graph/nodes.py` or `vlm_decide.py`; no file named for
telemetry across 209 blobs; `langfuse` declared as a dependency and **imported nowhere**
(the one `trace` hit in `nodes.py` is the phrase *"audit-trace granularity"* in a
docstring).

**B2 — Is it complete?** **Not applicable while B1 is no.** Recorded as not-applicable
rather than `UNKNOWN`, per the form's rule 4: there is no attribute value to be truncated.

**B3 — Is the input case on the trace?** **No**, same reason as B1.

**B4 — What change makes B1 and B3 yes?** Add OpenTelemetry instrumentation to the
Adjudicator: the dependency, a tracer, and span attributes carrying the request and the
response.

**Lane: outside plumbline entirely.** By the form's rule — strongest permission its
execution requires — this is a change to a different repository, so no plumbline lane
covers it. By the Project Brief's phase list it is **F4** work (*"instrument both real
agents + Claude Code source"*).

**Size: `UNKNOWN — not decided`.** It depends on how much of the state is exported, which
is a design choice nobody has made. **This is work, and it is the largest item in this
dossier.**

---

## Section C — Reference labels

**C1 — Per enumerated field: does a reference label exist or can one be produced?**

| Field (from A3) | Label |
|---|---|
| `decision` (`pass`/`fail`) | **exists** — the dataset's own per-image good/defective annotation |
| `tier1_decision` | **neither** — it is an intermediate policy call, not a ground-truth-bearing claim |
| `resolved_by` | **neither** — it records which path resolved the item, not whether the answer was right |
| `VLMInfo.verdict` | **exists, indirectly** — `defect`/`clean` maps onto the same annotation; `unsure` has no ground truth by construction |

**C2 — Label source and independence.** **MVTec AD**, and it is independent. **Confirmed
per item, not inferred:** `decision_scores.csv` carries a `label` column alongside every
decision — `0` = good, `1` = defective, 41 and 119 in the screw run. `vlm/state.py:28`
records the same field as *"ground truth (eval only; 0=good, 1=defective)"* and notes that
in production it is `None` and never consulted.
`src/aiqs/data.py:31` pins *"anomalib 1.2: original MVTec AD only (task=SEGMENTATION keeps
GT masks for AUPRO/AUPIMO)"*, and `api/artifact.py` carries `n`, `n_good`, `n_defective`
and `pi_source` (native sample defect prevalence) per run — the counts only exist because
the items are labelled.

**The independence is strong and worth stating:** MVTec AD's annotations are published with
the benchmark and predate this agent entirely. They are not the Adjudicator's own prior
output, which is what C2 exists to rule out. `configs/patchcore_visa.yaml` suggests VisA as
a second labelled source.

**One consequence the form should carry forward.** These labels belong to a **benchmark
dataset**, not to production traffic. `eval-plan.md` SC-2 counts *"real-traffic"* days and
C-4 asks for *"available real case volume"* — if `adjudicator-v1` is built from MVTec, then
E3 is answerable from the dataset and the word "real" in C-4 means something different from
what it means in SC-2. **Raised, not resolved: it is a Freeze A decision about what the
`gate` split is drawn from.**

**C3 — Production cost per item, and who can produce it.** **Zero, for labels that already
exist** — MVTec ships them. For any item outside the benchmark, `UNKNOWN — not decided`,
because whether the corpus extends beyond it has not been decided.

**C4 — Available or producible label volume.** `UNKNOWN — not looked up`, with a sourcing
procedure: it is `n_good + n_defective` per category from a run artifact
(`api/artifact.py`), readable per category without new work. Per the form's rule in
[`c-1-adjudicator-dossier.md`](../specs/c-1-adjudicator-dossier.md) §0, the procedure is
recorded rather than a constant — MVTec's per-category counts are fixed and
public, but which categories the dataset draws from is a Freeze A decision.

**C5 — Label agreement.** **Not applicable in the usual sense, and better than n = 1.**
The labels are the benchmark's published annotations, not a local annotator's, so the
single-annotator ceiling C5 warns about does not apply. **What does apply and is
`UNKNOWN — not looked up`:** MVTec AD's own inter-annotator reliability, if it was ever
published. Any accuracy figure the gate reports is bounded by it either way.

### Scenario derivation

| Field | Scenario | Reason |
|---|---|---|
| `decision` | **A** | finite (A2/A3) **and** an independent reference label exists (C1, C2) |
| `VLMInfo.verdict` | **A** for `defect`/`clean`; **B** for `unsure` | `unsure` has no ground truth by construction |
| `tier1_decision` | **B** | finite, but no reference label |
| `resolved_by` | **B** | finite, but not a claim ground truth can settle |
| `VLMInfo.reasoning` | E2 territory | free text |

**Overall reading: Scenario A**, carried by `decision` — the field E1's `task_pass_rate`
would actually be scored on. **E1 is viable as the primary deterministic endpoint**, so per
[`freeze-a-prep.md`](../specs/freeze-a-prep.md) §4.1 P4 carries the load and P5 is
secondary.

**Under-determined because:** nothing. The A/B/C question is determined. **What is not
determined is whether E1 can be *computed*** — that is B1, and it is no.

> **The two are separable and the distinction matters.** Scenario A says a correct answer
> exists to compare against. B1 says the agent's answer never reaches the trace the
> comparison would read. **A viable endpoint with no observable input is still not a
> measurement**, and reporting "Scenario A" without B1 beside it would be the more
> comfortable half of the finding.

---

## Section D — Degradation vector

**D1 — Is there a separable constraint section?** **Yes.** `src/aiqs/vlm/prompt.py` holds
two module-level constants: `SYSTEM_PROMPT` — role, task, and the calibration constraints
(*"Do not assume the detector is right. Be calibrated: reserve high confidence for clear
cases and say 'unsure' when the evidence is ambiguous."*) — and `QUESTION`, which carries
the JSON output contract and the verdict definitions.

Versioned with the repository; no separate prompt versioning.

**D2 — Can it be degraded controllably?** **Yes**, and the split is what makes it so.
Removing the constraint sentences from `SYSTEM_PROMPT` leaves `QUESTION` untouched, so the
output stays well-formed and only judgement quality degrades — which is precisely what
`eval-plan.md` §7.2 calls *"the hardest realistic regression"*. Reversible, expressible as a
diff, and pinned by commit.

**D3 — Alternative vector.** Not applicable; D1 is yes.

**Also read, for the catalog's other entries:** **D5 is applicable** — there is a VLM
backend call to make fail. **D4 is probably not** — one item carries one image plus an
optional crop, so *"context truncated to 1 item"* may have no second item to remove.

---

## Section E — Input shape, stratification, volume

**E1 — Input case schema.** `schemas.py` → `AdjudicateRequest`: `item_id` (optional, uuid4
if absent), `anomaly_score` (required float, raw detector score), `image_path` **or**
`image_b64`, `target_prevalence` (float, `"native"`, or omitted), `cost_matrix` override,
`lam` (VLM shrinkage, 0–1). One case = one adjudication of one image.

**E2 — Stratification keys.** Candidates from the input and the run artifact: **category**
(the MVTec class), `anomaly_score` band, `target_prevalence`, and the cost-matrix
configuration. Category is the natural key — it is what the benchmark varies and what
`artifact.py` already carries per run.

**None of them is on the trace**, because B3 is no. Per the form's own note, *a
stratification key that exists in the source but not on the trace is not usable by a
trace-computed gate.* **Every candidate here is blocked behind B4.**

**E3 — Real case volume over the window.** **Partly answered from stored runs**, and the
numbers land at the plan's threshold.

`results/decisions.csv` carries eight run records with per-category counts:

| Category | n | normal | defective | image AUROC |
|---|---:|---:|---:|---:|
| `mvtec-screw` | 160 | 41 | 119 | 0.9758 |
| `mvtec-capsule` | 132 | 23 | 109 | 0.9765 |
| a `patchcore-wide` run | 160 | 60 | 100 | 0.7387 |

**One category yields 132–160 items**, against `eval-plan.md` §7.5's `N_gate ≥ 160`. Read
against the sizing table in [`freeze-a-prep.md`](../specs/freeze-a-prep.md) §4.4: a single
category at 132 gives a conservative MDE of about **11.7 pp** where the plan wants 0.10; at
160 it is **9.9 pp** and the target is met.

**So the volume question is a category-count question.** One category is borderline, two or
three pooled clear it — and pooling is one of the three named responses in
[`freeze-a-prep.md`](../specs/freeze-a-prep.md) §4.4, at the cost of
the per-category stratification E2 would use.

**Still `UNKNOWN — not decided`: which categories `adjudicator-v1` draws from.** A Freeze A
choice, and the number follows from it rather than the other way round. **And
see C2's consequence** — if the corpus is the benchmark, this number is a property of the
dataset rather than of a 32-day window, and C-4's phrasing does not survive that reading
unchanged.

---

## 7. Completion test

**Blocking `UNKNOWN`s:**

| Field | Reason | Is it work? |
|---|---|---|
| ~~A3 (exact emitted strings)~~ | **answered on the second pass** — `Decision(str, Enum)`, all lowercase | **closed** |
| ~~A4 (historical out-of-set values)~~ | **measured** — 480 emissions, none outside the set | **closed** |
| ~~A5 (`VLMParseError` path)~~ | **answered** — HTTP 400, and it conflates with bad input | **closed, and it added an item to B4** |
| B4 (size of the instrumentation change) | not decided — depends on how much state is exported | **yes, and it is the largest item here** |
| C4 (label volume) | not looked up — procedure recorded instead | no, until the dataset's categories are decided |
| C5 (MVTec inter-annotator reliability) | not looked up — may not have been published | no |
| E3 (which categories the dataset draws from) | not decided — a Freeze A choice | no; the counts follow from it |

**Rules 1–3 satisfied:** every field carries an answer or an `UNKNOWN` with one of the four
reasons, and every answer names its source. **Rule 4 observed:** B2 is recorded as
not-applicable rather than inferred, and C1 is answered per field rather than for the output
as a whole.

**This dossier locates its gap.** The scenario question is determined — **A** — and the
blocker is somewhere the form did not originally point: not at whether a correct answer
exists, but at whether the agent's answer is observable at all.


---

## Revision note — 2026-09-02, second pass

A3, A4 and A5 were re-read after the first pass left them `UNKNOWN`. Three changes, and one
corrects the readout this copy was built from.

**A3 is closed.** `eval/decision.py:47-50` defines `Decision(str, Enum)` with values `pass`,
`fail`, `escalate` — **all lowercase**. `schemas.py`'s `PASS/FAIL/ESCALATE` are the Python
attribute names. A field that asked for *"exact strings, exact casing"* found a casing
difference between the documentation and the wire, which is what it was for.

**The "contract by convention" finding is corrected and narrowed.** `Decision` is a typed
enum, `Verdict` is a `Literal` whose parser raises on anything outside it, and
`AdjudicationState` forbids extra fields. The values **are** enforced where they are
produced; only the API response model widens them to `str | None`. The fix is narrowing
those annotations, not adding validation that already exists — smaller and different from
what the first pass implied.

**A5 turned out to be three shapes, not one**, and the distinction decides a denominator:
an abstain is a well-formed response, a rejected input produces no response at all, and a
model failure raises rather than coercing to `unsure`. R3 has to separate those or it will
score absent outputs as failures.

**E3 gained numbers** and they sit at the threshold — 132 to 160 per category against
`N_gate ≥ 160`. So the volume question is a category-count question, which is a Freeze A
choice rather than an operational measurement.


---

## Third pass — 2026-09-02. C-1 is complete in the form's sense.

**A4 is closed by measurement.** 160 per-item rows, three decision columns, 480 emissions,
nothing outside `{pass, fail, escalate}`. The dossier's first field answered by looking at
what was emitted rather than at what the code permits.

**A5 is closed, and closing it produced a finding.** `VLMParseError` subclasses
`ValueError`, so it is caught by the guard around `graph.invoke` and returned as **HTTP
400** — the same code a malformed image gets. From outside the API the two are
indistinguishable, and `eval-plan.md` §5.1 requires them apart: a bad input is a harness
error and leaves the denominator, a model that cannot produce parseable output is the agent
failing and stays in it. **One more item for B4.**

**C2 is now confirmed per item.** `decision_scores.csv` carries `label` beside every
decision — the reference label is not inferred from run-level counts, it is in the same row
as the output it would score.

### What remains, and why none of it is a read

| Field | Why it is open |
|---|---|
| **B4** — the size of the instrumentation change | **not decided.** Depends on how much state is exported, which nobody has chosen. Now carries a second item: making a parse failure distinguishable from a bad input |
| **C3, C4** — label cost and volume | follow from which categories `adjudicator-v1` draws |
| **C5** — MVTec inter-annotator reliability | upstream of this project; may never have been published |
| **E3** — case volume | 132–160 per category is measured; **which categories** is a Freeze A choice |

**Three of the four are one decision.** Choose the categories and C3, C4 and E3 resolve
together. That decision belongs to Freeze A, not to C-1 — the dossier's job was to make it
a decision rather than an unknown, and it has.

**B4 is the one that is neither a read nor a Freeze A choice.** It is work in another
repository, it is F4 by the Brief's phase list, and both SC-1 and SC-2 depend on it.

### The completion test, applied

1. Every field carries an answer or an `UNKNOWN` with a stated reason. **Yes.**
2. Every answer names its source. **Yes** — file and line, or a stored run artefact.
3. The derivation table is filled per field and the overall reading is a scenario.
   **Yes — Scenario A**, carried by `decision`.
4. Blocking `UNKNOWN`s are listed in one place. **Yes**, §7 and the table above.

**C-1 is complete.** What it hands to Freeze A is a determined scenario, a viable primary
endpoint, a working primary degradation vector — and one blocker the form was not built to
find: the endpoint's input is not observable, because the agent emits nothing.
