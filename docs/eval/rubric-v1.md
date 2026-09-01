# Judge rubric v1 — **SKELETON, NOT FREEZABLE**

**Status:** **UNFILLED — eight anchors are placeholders (P5).** This file must not be
hashed at Freeze A in this state.
**Date:** 2026-09-01 · **Owner of the content:** Human (`eval-plan.md` Appendix A, P5)
**Governed by:** [`eval-plan.md`](../eval-plan.md) §8.2 · **Feeds:** endpoint E2, §7.4

> **Why this file exists before its content does.** §8.2 requires the rubric to be a
> frozen artefact at this exact path, hashed at Freeze A, and `docs/eval/` did not exist.
> A directory that has to be created during a zero-slack session is five minutes nobody
> budgeted. The structure below is transcribed from §8.2, §7.4 and §8.4 — every constraint
> it states is already pre-registered elsewhere and is copied here, not decided here.
>
> **The anchors are not transcribed, because they are not written anywhere.** They are
> P5, they are a human decision, and Appendix A's rule applies to them: *no placeholder is
> filled by assumption.* Every unfilled anchor below is marked `**(P5 — unfilled)**` so
> that a hash taken over this file is visibly a hash of an unfilled rubric.

---

## 1. Fixed structure — transcribed from `eval-plan.md` §8.2

Not open for decision at Freeze A. Changing any of it is a change to §8.2 and requires an
ADR under §12.

| Property | Value | Source |
|---|---|---|
| Scale | Ordinal, **4-point**, **no neutral midpoint** | §8.2 |
| Anchors | Written, one per point, per dimension | §8.2 |
| Dimensions | **J1 groundedness**, **J2 instruction adherence** | §8.2 |
| Aggregation | `judge_mean_score` = mean of J1 and J2 | §8.2 |
| Judge inputs | Task input and agent output **only** | §8.2 |
| Withheld from judges | The variant label; the baseline output | §8.2 |
| Presentation | Fixed template, to limit position and verbosity confounds | §8.2 |
| Change control | A rubric edit is a measurement-instrument change and requires an ADR | §8.2 |

**J1 — groundedness.** Does the stated rationale rest on evidence present in the trace
inputs?

**J2 — instruction adherence.** Measured against the pinned task contract — P1 for the
Adjudicator, P2 for Triage. Both are unfilled at the time of writing, so J2's anchors
cannot be finalised before P1 and P2 are.

---

## 2. The anchors — P5

Eight anchors: two dimensions, four points each. **None is filled.**

### J1 — groundedness

| Point | Anchor |
|---|---|
| 4 | **(P5 — unfilled)** |
| 3 | **(P5 — unfilled)** |
| 2 | **(P5 — unfilled)** |
| 1 | **(P5 — unfilled)** |

### J2 — instruction adherence

| Point | Anchor |
|---|---|
| 4 | **(P5 — unfilled)** |
| 3 | **(P5 — unfilled)** |
| 2 | **(P5 — unfilled)** |
| 1 | **(P5 — unfilled)** |

### Presentation template

**(P5 — unfilled.)** §8.2 requires it to be fixed and names its purpose: limiting position
and verbosity confounds. The template is part of the frozen instrument, not an
implementation detail of the harness.

---

## 3. Constraints the anchors have to satisfy

Derived from what already depends on this file. Recorded here so the constraints are in
front of whoever writes the anchors, rather than discovered when the numbers fail to
behave.

**3.1 — Points 2 and 3 carry the whole discriminative burden.** A 4-point scale with no
neutral midpoint is forced-choice: 1 and 4 are the easy calls. If the anchors at 2 and 3
are not separable by a rule a judge can apply without seeing the other arm, the scale
degenerates to binary and E2 loses most of its resolution.

**3.2 — `ε_min(E2)` is `max(0.25 rubric points, 2·σ0(E2))` (§7.4).** `judge_mean_score` is
the mean of two integer 4-point scores, so **for a single item it moves in steps of 0.5**.
The 0.25-point floor is therefore half of the smallest per-item increment, and is only
resolvable because E2 is a mean across items. Anchors that make judges cluster on two of
the four points shrink the attainable range and make that floor harder to clear —
not by making the gate stricter, but by making a real regression indistinguishable from
none.

**3.3 — The scale must be genuinely ordinal, with meaningful distance.** §8.4 scores
agreement with **quadratic-weighted** κ (A1, A3), which penalises disagreements by the
square of the distance between them. That is only interpretable if the step from 1 to 2
means something comparable to the step from 3 to 4. Anchors written as four unrelated
categories will produce a κ that reads as a number and means nothing.

**3.4 — Anchors must be applicable by a judge seeing one output in isolation.** §8.2
withholds the variant label and the baseline output. Any anchor phrased comparatively
("better than…", "more complete than…") is unusable by construction.

**3.5 — Self-consistency across 3 repeats is measured (§8.4, A2).** Anchors that require
a judgement call the same judge would make differently twice will show up as low A2, and
A2 is reported.

**3.6 — J2 cannot be finalised before P1 and P2.** It is defined against the pinned task
contract, and both contracts are themselves Freeze A placeholders.

---

## 4. Freeze checklist

This file is ready to be hashed when, and only when:

1. All eight anchors are written; no `(P5 — unfilled)` marker remains in the document.
2. The presentation template is written.
3. P1 and P2 are fixed, so J2's anchors reference a contract that exists (§3.6).
4. The `**SKELETON, NOT FREEZABLE**` title and the status line are replaced with the
   frozen designation and the date.

Until item 4 is done, the title states the file's own condition. That is deliberate: a
partially-filled measurement instrument that looks finished is the failure this project
keeps finding, and the cheapest place to refuse it is in the artefact's own first line.
