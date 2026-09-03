# P5 — observed behaviour that rubric anchors would have to describe

**Derived:** 2026-09-03 · **Lane:** A · **Task:** F3 Unblock dispatch U-09
**Source:** [`c-1-dossier-filled-2026-09-02.md`](c-1-dossier-filled-2026-09-02.md), A4 and A5

> **No anchor text is written here, and that is deliberate.** P5 is the four-point anchor
> text for `docs/eval/rubric-v1.md`, and it is human authoring. A drafted anchor is
> indistinguishable from an approved one once it is in a file — the same shape as a ready
> form and a filled form looking identical, which is this project's recorded central defect
> class. What follows is the **observed behaviour** anchors would have to discriminate
> between, so the authoring session reads instead of derives.

The rubric's dimensions are already fixed by [`eval-plan.md`](../eval-plan.md) §8.2 —
**J1 groundedness** and **J2 instruction adherence**, ordinal 4-point, no neutral midpoint.
P5 supplies the anchors, not the dimensions.

---

## Input 1 — the output vocabulary is measured, not assumed

`{pass, fail, escalate}`, lowercase on the wire, from a `Decision(str, Enum)`. Measured over
**480 emissions** across 160 items and three decision columns: **nothing outside the set**
(dossier A4).

**Why an anchor author needs this:** a rubric point that describes a "malformed verdict" is
describing something that has never been observed in 480 emissions, and three structural
enforcement points make it unlikely — a typed enum, a `Literal` whose parser raises, and a
state model that forbids extra fields. Anchors spending a point on malformed output would
spend it on an empty cell.

## Input 2 — three failure shapes, and only one is the agent declining

From dossier A5. These are the states a judge will actually encounter.

| Shape | What it looks like | Is it the agent failing? |
|---|---|---|
| **Abstain** | `decision = pending_human`, `resolved_by` null; a designed route `cost_policy → vlm_second_look → vlm_abstain_rule → human_interrupt` | **No** — a first-class outcome |
| **Rejected input** | HTTP 400, **no `AdjudicateResponse` at all** | **No** — an absent output |
| **Model failure** | `VLMParseError` → HTTP 400 | **Yes** |

**The distinction anchors must not collapse:** an abstain is the agent working. Treating it
as a low score would penalise the behaviour the system prompt explicitly asks for — see
input 3. And the second and third shapes are indistinguishable by status code, which
[`f3-t3-01-400-discriminator.md`](f3-t3-01-400-discriminator.md) measured; a judge scoring
from the API boundary alone cannot separate them.

## Input 3 — the constraint the agent is instructed to follow is quotable

`src/aiqs/vlm/prompt.py`, `SYSTEM_PROMPT` (dossier D1):

> Do not assume the detector is right. Be calibrated: reserve high confidence for clear
> cases and say 'unsure' when the evidence is ambiguous.

**This is directly relevant to J2 (instruction adherence)** because it is *the* instruction
the primary degradation D2 removes. The seeded regression ablates exactly these sentences,
leaving output well-formed and only judgement degraded — `eval-plan.md` §7.2's *"hardest
realistic regression"*. **J2 anchors that cannot separate calibrated hedging from confident
guessing will not detect D2**, which is the experiment's primary case.

## Input 4 — the verdict distribution moves with a configuration prior

Recorded in dossier A4 as a carried observation. On the same 160 items:

| Column | Distribution |
|---|---|
| `decision_native` | `escalate` × 41, `fail` × 119 |
| `decision_target` (at default `target_prevalence = 0.02`) | `pass` × **160** |
| `decision_target_realistic` | `escalate` × 152, `pass` × 8 |

**Why this matters to anchors and not only to P3:** a baseline run whose verdict column is
constant gives a judge no variance to score against. An anchor set calibrated on
`decision_target` at the default prior would be calibrated on a column that never varies.
The dossier notes this *"does not affect E1"*, which scores the contract rather than the
verdict — but J1/J2 are judge dimensions and they do read the verdict and its rationale.

## Input 5 — the free-text field the judge actually reads

`VLMInfo.reasoning` is the only free-text field in the contract, and the dossier's scenario
derivation places it in **E2 territory** — no reference label exists or can, by construction.

**So J1 groundedness is scored against this field**, and it is the one field with no ground
truth to check against. Anchors for J1 have to describe the *relationship* between the
rationale and the trace inputs — which is what §8.2 already says (*"does the stated
rationale rest on evidence present in the trace inputs"*) — rather than the rationale's
correctness.

---

## What is missing before anchors can be written

| Gap | Consequence |
|---|---|
| No observed sample of `VLMInfo.reasoning` text | Anchors for J1 would describe a field nobody has read an instance of |
| No inter-rater data (dossier C5, `UNKNOWN`) | An anchor set with one author sets an unmeasured ceiling on every judge figure |
| The trace does not carry the output (B1) | A judge reading *"trace inputs"* per §8.2 has no trace to read |

**The third is the same blocker as E1's**, and it means rubric anchors can be authored but
not exercised until the Adjudicator emits. Authoring them early is still useful — they are a
Freeze A exit item — but they cannot be validated against a real trace at the time of
writing, and that limitation belongs in `rubric-v1.md` when it is created.
