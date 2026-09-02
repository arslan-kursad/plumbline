# C-1 — the Adjudicator's output contract, read from the repo

**Read:** 2026-09-02 · **Lane:** A · **Source:** `github.com/arslan-kursad/aiqs-agent`
**Pinned at commit `0779c04ff98a744285b8b1c93ce35f4efd4a89b2`**, committed
`2026-07-18T18:20:33Z`. Public repo, read-only.

**Record the repo name and this SHA in `eval-plan.md` v0.2.** C-1 currently names its
source as *"Adjudicator repo"* — a description, not an identity. Nothing in plumbline names
this repository, and six months from now nobody reading P1 could tell which schema was
frozen.

---

## The headline: **there is no OTLP instrumentation in this agent**

Checked four ways, because it contradicts something written in `#153` today:

| Check | Result |
|---|---|
| `opentelemetry-*` in `pyproject.toml` dependencies | **absent** (21 deps, none) |
| OTel imports in `api/main.py`, `graph/nodes.py`, `vlm_decide.py` | **none** |
| Files named for telemetry across 209 blobs | **none** |
| `langfuse` — declared as a dependency | present, **imported nowhere**; the one "trace" hit in `nodes.py` is the phrase *"audit-trace granularity"* in a docstring |

**So the Adjudicator emits nothing today.** Consequences, in order of who they hurt:

- **C-1 question 2.1 is answered, and the answer is "nowhere".** `eval-plan.md` §5.1 says a
  metric that cannot be computed from persisted telemetry is not a metric. **R3 cannot be
  computed at all** until this agent is instrumented, and E1 loses a conjunct of
  `R1∧R2∧R3∧R4`.
- **It cannot be an SC-2 source.** SC-2 counts real-traffic days per `source_dialect` in
  `spans_real`. An agent that emits nothing produces no days.
- **It explains the fixture.** the `langgraph-python` manifest in this repository reads
  `provenance: constructed` — there was never a real emitter to capture from.

### This corrects `#153`, which I wrote today

F3E-02 says: *"Two of the three emitters carry no blocker — the LangGraph adjudicator and
the .NET agent are first-party, with no beta gate and no nested-authentication
constraint."*

The **access** claim is true — no beta gate, no auth constraint. The **implication** is
wrong: I presented two captures as reachable now, and they are not, because there is
nothing emitting to capture. Instrumenting the agents is F4 work by the Project Brief's own
phase list (*"F4 Dogfooding + demo: instrument both real agents + Claude Code source"*).

The harness built in `#153` is still correct and still needed. **It runs later than I
implied.**

---

## 1.1 — Output form: JSON, over HTTP, from a FastAPI endpoint

`src/aiqs/api/schemas.py` → `AdjudicateResponse` (Pydantic v2). The graph's internal state
is `src/aiqs/graph/state.py` → `AdjudicationState`; the API response is the narrower,
public contract and is what P1 should fix.

## 1.2 — Field list (`AdjudicateResponse`)

| Field | Type | Required |
|---|---|---|
| `item_id` | `str` | yes |
| `decision` | `str \| None` | nullable |
| `resolved_by` | `str \| None` | nullable |
| `pending_human` | `bool` | yes |
| `calibrated_p` | `float \| None` | nullable |
| `tier1_decision` | `str \| None` | nullable |
| `applied_target_prevalence` | `float \| None` | nullable |
| `pi_source` | `float \| None` | nullable |
| `expected_costs` | `dict[str, float] \| None` | nullable |
| `indifference_points` | `dict[str, float] \| None` | nullable |
| `vlm` | `VLMInfo \| None` | nullable |
| `run_guard_warnings` | `list[str]` | yes, defaults `[]` |

`VLMInfo`: `fired: bool`, `verdict`, `confidence`, `reasoning`, `tokens_in`, `tokens_out`.

## 1.3 — Enums, and an asymmetry worth fixing before it is frozen

The allowed sets are **documented in `description=` strings, not enforced by types**:

- `decision` — `str | None`, described as `'pass' | 'fail' | 'pending_human'`
- `resolved_by` — `str | None`, described as `'policy' | 'vlm' | 'human'`
- `tier1_decision` — `str | None`, described as the `PASS/FAIL/ESCALATE` call
- `VLMInfo.verdict` — `str | None`, and the prompt requires `defect | clean | unsure`

**The request side does it properly:** `HumanVerdictRequest.decision` is
`Literal["pass", "fail"]`. So the same repo types its inputs and leaves its outputs as bare
strings.

For R3 (*"enum values in allowed set"*) this means **the contract is by convention**. Two
readings for the session: freeze P1 against the documented sets as they stand, or ask the
Adjudicator to make them `Literal` first so the contract is enforced where it is produced.
The second is better and is not plumbline's to demand.

**Also note the vocabulary shifts across the pipeline.** The VLM answers
`defect | clean | unsure`; `vlm_decision` becomes `pass | fail | escalate`; `final_decision`
is `pass | fail`. Three vocabularies, one flow — R5 (P4) will need to know which layer it
is asserting about.

## 1.4 — The verdict is **discrete**. Not scenario C.

`decision` takes three values. `final_decision` in the graph state is `pass|fail`, with
`pending_human` carrying the third state at the API boundary.

**So the A/B/C branch in [`freeze-a-prep.md`](../specs/freeze-a-prep.md) §4.1 lands on A or
B, and which one turns on ground truth — question 4.1 of the intake, which this repo does
not answer.** That is still yours.

## 1.5 — There is a designed abstain path

`escalate` / `pending_human` is a first-class outcome, not an error: the graph routes
`cost_policy → vlm_second_look → vlm_abstain_rule → human_interrupt`. R3 must treat a
`pending_human` response as **well-formed**, not as a contract failure — otherwise the
deterministic endpoint would penalise the agent for doing the thing it is designed to do.

## 5.1 — One item = one adjudication

`AdjudicateRequest`: one `anomaly_score`, one image (`image_path` or `image_b64`), optional
cost-matrix override. The unit is clean and matches §5.1's *"one task instance"*.

## 6.1 — **D2 is applicable.** The prompt has a separable constraint section.

`src/aiqs/vlm/prompt.py` holds two constants:

- `SYSTEM_PROMPT` — the role, the task, and the constraint sentences: *"Do not assume the
  detector is right. Be calibrated: reserve high confidence for clear cases and say
  'unsure' when the evidence is ambiguous."*
- `QUESTION` — the output contract: the JSON shape and the verdict definitions.

**That split is exactly what D2 needs.** The calibration/constraint sentences can be removed
from `SYSTEM_PROMPT` as a single-factor change, leaving `QUESTION` intact — so the output
stays well-formed and only judgement quality degrades, which is what §7.2 calls *"the
hardest realistic regression"*.

**D5 is applicable too** — there is a VLM backend call to make fail. **D4 needs a check**:
one item carries one image plus an optional crop, so *"context truncated to 1 item"* may
not have a second item to remove.

---

## What is still open after this read

| | |
|---|---|
| **4.1 ground truth** | Not answerable from the repo. Decides scenario **A vs B** |
| **C-4 volume** | Not in the repo; `results/` may hold run sizes but real case volume is operational |
| **Instrumentation** | The blocker this read found. F4 by the Brief's phase list |
| **D4 applicability** | One image per item — likely not applicable as written |
