# C-1 dossier — filled copy, 2026-09-02

**Form:** [`c-1-adjudicator-dossier.md`](../specs/c-1-adjudicator-dossier.md) v0.1
**Filled by:** Lane A, from repository reads only · **Status:** partial — see §7
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

**A3 — Enumerations.** **Partially answered, and the gap is the one A3 exists to catch.**

Documented sets, read from `description=` strings in `schemas.py`:

| Field | Documented set | Casing as written |
|---|---|---|
| `decision` | `pass` \| `fail` \| `pending_human` | lower |
| `resolved_by` | `policy` \| `vlm` \| `human` | lower |
| `tier1_decision` | `PASS` / `FAIL` / `ESCALATE` | **UPPER** |
| `VLMInfo.verdict` | `defect` \| `clean` \| `unsure` | lower (from `vlm/prompt.py`'s `QUESTION`) |

**`UNKNOWN — not looked up`: the exact strings as emitted.** These are descriptions, not
types. `graph/nodes.py` calls `Decision.ESCALATE.value`, so an enum exists and its `.value`
is what actually travels; that definition was not located, so **the casing above is what the
documentation says, not what the wire carries.** A3 asks for the second.

**Also recorded: the value sets are not enforced by types.** `decision`, `resolved_by`,
`tier1_decision` and `VLMInfo.verdict` are all `str | None`. The **request** side does it
properly — `HumanVerdictRequest.decision` is `Literal["pass", "fail"]`. So the same repo
types its inputs and leaves its outputs as bare strings, and R3's *"enum values in allowed
set"* would rest on convention rather than on the contract.

**And the vocabulary changes three times across one flow:** the VLM answers
`defect|clean|unsure`, `vlm_decision` becomes `pass|fail|escalate`, `final_decision` is
`pass|fail`. P4's R5 will have to say which layer it asserts about.

**A4 — Contract stability.** `UNKNOWN — not looked up.` Whether the agent has ever emitted
a field or value outside A2/A3 is a measurement over historical outputs, and no such
measurement exists in the repository. **This is work**, and it is small: it needs one pass
over stored run outputs.

**A5 — Failure and refusal shape.** **Declared, and it is not an error path.**
`pending_human` is a first-class outcome: `graph/build.py` routes
`cost_policy → vlm_second_look → vlm_abstain_rule → human_interrupt → finalize`, and
`finalize` (`graph/nodes.py`) resolves `human | vlm | policy`. `decision` is
`pending_human` and `resolved_by` is null while the item waits.

**Consequence for E1, and it is the reason A5 is in the form:** R3 must score a
`pending_human` response as **well-formed**. Treating it as a contract failure would
penalise the agent for performing its designed abstain, and contract-pass-rate would fall
whenever the cost policy correctly escalated.

`UNKNOWN — not looked up`: the shape on **timeout or backend error**, as distinct from
abstain. Not read.

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

**C2 — Label source and independence.** **MVTec AD**, and it is independent.
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

**E3 — Real case volume over the window.** `UNKNOWN — not looked up`, with the sourcing
procedure recorded per [`c-1-adjudicator-dossier.md`](../specs/c-1-adjudicator-dossier.md) §0:
`n_good + n_defective` per category from a run artifact. **And
see C2's consequence** — if the corpus is the benchmark, this number is a property of the
dataset rather than of a 32-day window, and C-4's phrasing does not survive that reading
unchanged.

---

## 7. Completion test

**Blocking `UNKNOWN`s:**

| Field | Reason | Is it work? |
|---|---|---|
| A3 (exact emitted strings) | not looked up — enum definition not located | **yes**, small: one file read |
| A4 (contract stability) | not looked up — no such measurement exists | **yes**, small: one pass over stored outputs |
| A5 (timeout/error shape) | not looked up | **yes**, small |
| B4 (size of the instrumentation change) | not decided — depends on how much state is exported | **yes, and it is the largest item here** |
| C4 (label volume) | not looked up — procedure recorded instead | no, until the dataset's categories are decided |
| C5 (MVTec inter-annotator reliability) | not looked up — may not have been published | no |
| E3 (case volume) | not looked up — procedure recorded instead | no, same dependency as C4 |

**Rules 1–3 satisfied:** every field carries an answer or an `UNKNOWN` with one of the four
reasons, and every answer names its source. **Rule 4 observed:** B2 is recorded as
not-applicable rather than inferred, and C1 is answered per field rather than for the output
as a whole.

**This dossier locates its gap.** The scenario question is determined — **A** — and the
blocker is somewhere the form did not originally point: not at whether a correct answer
exists, but at whether the agent's answer is observable at all.
