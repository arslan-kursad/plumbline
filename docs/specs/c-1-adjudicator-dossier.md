# C-1 — Anomaly Adjudicator Dossier

**Version:** 0.1 (template, unfilled) · **Status:** Proposed · **Date:** 2026-09-02
**Owner:** Human (Lane C) · **Feeds:** P1, P6, and the D2 primary experimental case

This document is a form. Filling it is the precondition; it is not itself a decision.
Nothing here edits `docs/eval-plan.md`.

> **Reference convention, applied to this file itself.** Every `§` below that means another
> document names it — `freeze-a-prep.md` §5, `eval-plan.md` Appendix A. A bare `§` is this
> document's own. Two references in the authored draft read `§5(a)`/`§5(b)` meaning the
> freeze decision, while **this** document's §5 is Section D; both now name their document.
> The completion note's §5 identifier rule, applied to the form written to prevent that
> class of defect.

---

## 0. How to fill this

Four rules. The first three exist because a blank field and an unanswerable field look
identical on the page, and this project has paid for that confusion four times.

1. **Every field is answered.** `UNKNOWN` is a valid answer. A blank is not.
2. **`UNKNOWN` states why**, in one line: not looked up, not observable, not decided, or
   does not exist. These four have different consequences and only one of them is work.
3. **Every answer names where it was read** — file and line, a repository path, an API
   response, or a direct observation with its date. "I know this" is not a source.
4. **Do not infer across fields.** If A3 is unknown, C1 is unknown too. An inferred answer
   propagates and is indistinguishable from a read one.

**A value that the project does not own cannot be frozen.** Where a field asks for a number
whose source is external or drifting, record the *sourcing procedure plus a dated
observation* instead of the constant. This is the treatment already applied to `Q` on
2026-09-02 ([`freeze-a-prep.md`](freeze-a-prep.md) §2.1); it is a simplification, not a
concession.

---

## 1. Field index

| Field | Question | Feeds | Blocking |
|---|---|---|---|
| A1–A5 | Output contract | P1 | Yes |
| B1–B4 | Trace observability | R3, E1 | B1 yes; B2–B4 conditional |
| C1–C5 | Reference labels | P6, scenario | Yes |
| D1–D3 | Degradation vector | D2 | Yes |
| E1–E3 | Input shape, stratification, volume | P3, P6 | E1–E2 yes; E3 by procedure |

"Blocking" means: unresolved, it blocks Freeze A. Per `eval-plan.md` Appendix A a
placeholder does not degrade into a default, so a blocking field left `UNKNOWN` is a
[`freeze-a-prep.md`](freeze-a-prep.md) §5(a) or §5(b) event, not a note.

---

## 2. Section A — Task definition and output contract (P1)

**A1 — Output serialization.** Structured (JSON/typed object), free text, or mixed?
If a schema exists, its path. If it is enforced at runtime, by what.

**A2 — Field inventory.** For every field the agent emits: name, type, required or
optional, and whether its value set is finite.

| Field name | Type | Required | Finite value set? |
|---|---|---|---|

**A3 — Enumerations, verbatim.** For every field marked finite in A2, the complete value
set as the agent actually emits it — exact strings, exact casing.

**A4 — Contract stability.** Has the agent ever emitted a field or a value outside A2/A3?
If never checked, that is `UNKNOWN — not looked up`, and it is a measurement, not an
opinion.

**A5 — Failure and refusal shape.** What the output looks like when the agent cannot
answer, times out, or declines. This is not a corner case: contract-pass-rate cannot
distinguish a malformed output from a valid refusal unless the refusal has a declared
shape, and E1 scores both.

---

## 3. Section B — Trace observability (R3, E1)

P1 asks what the contract is. It does not ask whether the contract is observable. R3 is
computed from the trace, so an output that never reaches a span makes R3 uncomputable and
costs E1 a component.

**B1 — Does the output reach a span attribute?** Which span, which attribute key.

**B2 — Is it complete?** Any truncation, size cap, sampling, or redaction between the
agent's output and the attribute value.

**B3 — Is the input case on the trace?** Which span, which attribute key. Needed for
stratification (E2) and for joining a span to its reference label (C1).

**B4 — If B1 or B3 is "no": what change makes it yes?** Name the change, its size, and
**its lane** — determined by the strongest permission its execution requires, not by who
would write it.

A "no" at B1 is not a dead end. It converts an unmeasurable criterion into a scoped task,
and that conversion is the point of asking.

---

## 4. Section C — Reference labels (P6)

**C1 — Per enumerated field from A3: does a reference label exist, or can one be produced?**
Answer per field, not for the output as a whole.

| Field (from A3) | Label exists / producible / neither |
|---|---|

**C2 — Label source, and its independence.** Where the label comes from, and whether that
source is independent of the Adjudicator.

> The Adjudicator's own prior output is not a reference label, however it was reviewed. A
> label derived from the system under test measures self-consistency and reports it in the
> grammar of accuracy.

**C3 — Production cost per item, and who can produce it.** If only one person can, say so —
that binds the label volume to the same human already on the critical path.

**C4 — Available or producible label volume.** A number with its date, or — if the volume
depends on something the project does not control — the sourcing procedure plus a dated
observation.

**C5 — Label agreement.** If labels are human-produced: is there inter-rater data, or is
n = 1? A single-annotator reference sets an unmeasured ceiling on every accuracy figure the
gate reports. `UNKNOWN` is acceptable here; unstated is not.

### 4.1 Scenario derivation

Derived from the fields above, per field. Do not assert the scenario independently — if the
fields do not determine it, that under-determination is the finding.

1. **Is this field's value set finite (A2/A3)?**
   - No → the field is E2 territory. Continue to the next field.
   - Yes → step 2.
2. **Does a reference label exist or is it producible, from a source independent of the
   Adjudicator (C1, C2)?**
   - Yes → **Scenario A** for this field. E1 viable as primary.
   - No → **Scenario B** for this field. Contract-pass-rate only.
3. **If no field reaches step 2 with "yes" → Scenario C.** E2 becomes primary and the
   endpoint architecture is affected, which is an ADR rather than a placeholder fill.

**A mixed output is normal and is not automatically C.** A structured verdict beside a
free-text rationale yields A or B on the verdict field and E2 on the rationale. Classifying
the whole output as C because part of it is prose restructures the architecture for no
reason.

**Result:**

| Field | Scenario | Reason |
|---|---|---|

**Overall reading:** _____ · **Under-determined because:** _____

---

## 5. Section D — Degradation vector (D2)

The primary experimental case assumes the system prompt contains a separable constraint
section that can be degraded. If it does not, the primary case is redesigned — a
[`freeze-a-prep.md`](freeze-a-prep.md) §5(b) event, not an adjustment.

**D1 — Is there a separable constraint section?** Where it lives; whether it is versioned.

**D2 — Can it be degraded controllably?** Reversible, version-pinned, and with the
degradation expressible as a diff rather than a rewrite.

**D3 — If D1 is "no": what is the alternative degradation vector?** Named, with the reason
it is expected to produce a detectable effect. "Some other change" is `UNKNOWN`.

---

## 6. Section E — Input shape, stratification, volume (P3, P6)

**E1 — Input case schema.** What one case is: fields, types, and where cases come from.

**E2 — Stratification keys.** Which input fields the gate could stratify on, and whether
each is present on the trace (cross-check against B3). A stratification key that exists in
the source but not on the trace is not usable by a trace-computed gate.

**E3 — Real case volume over the window.** A number with its date, or the sourcing
procedure plus a dated observation. Feeds `N_gate` and the achieved MDE.

> Recorded on 2026-09-02 alongside the sizing table ([`freeze-a-prep.md`](freeze-a-prep.md)
> §4.4): the calculation is conservative by an amount not knowable before calibration, and
> `p_baseline = 0.90` is an assumption, not a measurement. Both carry into whatever E3
> produces.

---

## 7. Completion test

This dossier is complete when:

1. Every field carries an answer or an `UNKNOWN` with one of the four stated reasons.
2. Every answer names its source.
3. §4.1's derivation table is filled per field, and the overall reading is either a scenario
   or an explicit statement of what leaves it under-determined.
4. Every `UNKNOWN` on a blocking field is listed together in one place, so the freeze
   decision is made against a list rather than against an impression.

**Blocking `UNKNOWN`s at completion:**

| Field | Reason | Is it work? |
|---|---|---|

A dossier where every field is answered and the scenario is still under-determined is a
**successful** dossier. It has located the gap. A dossier where the gap is invisible because
the fields were inferred is the failure this form is shaped to prevent.

---

## 8. Provenance

Derived on 2026-09-02 from: the Freeze A session findings of 2026-09-02 (C-1's two parts —
trace observability, and the D2 precondition — and the `Q` treatment reused in §0); the
scenario A/B/C framing carried since 2026-08-19; `docs/eval-plan.md` Appendix A as quoted in
the C-6 readout of 2026-09-01.

No line in this template is a measurement, and a filled copy is evidence only for the fields
whose sources it names.

**Several fields already have sourced answers.**
[`c1-adjudicator-readout.md`](../evidence/c1-adjudicator-readout.md) read the Adjudicator at
`aiqs-agent` @ `0779c04f` on 2026-09-02 and answers A1, A2, A3, A5, B1, D1, D2, E1 with file
and line. **Those answers are not copied into this template**, because a form and a filled
copy are different artefacts and merging them would make the template unusable for the
second agent. A filled copy should cite the readout rather than re-derive it.
