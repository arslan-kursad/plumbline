# Freeze A decision package — proposed values for P1–P7 and P11, prepared not applied

**Prepared:** 2026-09-05 · **Lane:** A, under the maintainer's delegation of the same day
**Target:** [`docs/eval-plan.md`](../eval-plan.md) v0.2 · **Session:** Freeze A session 2
(plan W1-1) · **Companion:** [`completion-plan.md`](../specs/completion-plan.md) §5 CP-1, CP-11

> **NOT APPLIED, and Lane A may not apply it.** `eval-plan.md` is a pre-registration
> document, human-only, Class 3. Every value below is a proposal for the human to transcribe,
> amend or reject in the session. Where a value is a judgement rather than a transcription
> the row says **judgement**, so the session spends its minutes there and nowhere else.
>
> The package differs from [`freeze-a-items-2-6.md`](freeze-a-items-2-6.md) in one respect:
> that file prepared diffs whose content was already decided elsewhere; this one proposes
> the decisions themselves, because the maintainer delegated them. A proposed value and an
> approved one look identical once they are in `eval-plan.md`, which is why nothing here is
> in `eval-plan.md`.

---

## 0. Grounding, read 2026-09-05

Every input the placeholders need now exists in the repository:

| Input | Where |
|---|---|
| Adjudicator contract, enums as emitted, failure shapes, labels, degradation vector | [`c-1-dossier-filled-2026-09-02.md`](../evidence/c-1-dossier-filled-2026-09-02.md) |
| Triage contract, enums, error kinds, labels, degradation vector | [`c-2-dossier-filled-2026-09-03.md`](../evidence/c-2-dossier-filled-2026-09-03.md) |
| Case volume and the MDE each selection buys | [`p3-volume-mde-table.md`](../evidence/p3-volume-mde-table.md) |
| Observed behaviour rubric anchors must discriminate | [`p5-rubric-inputs.md`](../evidence/p5-rubric-inputs.md) |
| The 400 discriminator, eight paths | [`f3-t3-01-400-discriminator.md`](../evidence/f3-t3-01-400-discriminator.md) |
| What each E1 conjunct consumes | [`e1-predicate-readout.md`](../evidence/e1-predicate-readout.md) |
| Exit items 2–6, as diffs | [`freeze-a-items-2-6.md`](freeze-a-items-2-6.md) |
| P11's measurement | `normalization/mappings/v1.41/claude-code.yaml`:19-20 |

Both agent repositories were also read on this host at their pinned commits
(`aiqs-agent @ 0779c04f`, `apartment-triage @ 15c1d6e`); one reading corrects a dossier
finding and is flagged in §2.

---

## 1. P1 — Anomaly Adjudicator task definition and output contract

**Source to record in v0.2 §4:** `github.com/arslan-kursad/aiqs-agent` at
`0779c04ff98a744285b8b1c93ce35f4efd4a89b2` (committed 2026-07-18). The dossier asked for
this line explicitly; without it P1 names a description, not an identity.

**Task.** One item is one adjudication of one image with one detector score
(`AdjudicateRequest`: `anomaly_score`, `image_path` or `image_b64`, optional
`target_prevalence`, `cost_matrix`, `lam`). The output is `AdjudicateResponse`.

**Output contract — transcription of dossier A2 and A3.**

| Field | Type | Emitted set |
|---|---|---|
| `item_id` | string, required | — |
| `decision` | string, nullable | `pass` · `fail` · `pending_human` |
| `resolved_by` | string, nullable | `policy` · `vlm` · `human` |
| `pending_human` | bool, required | — |
| `calibrated_p` | float, nullable | `[0, 1]` |
| `tier1_decision` | string, nullable | `pass` · `fail` · `escalate` (lowercase on the wire) |
| `applied_target_prevalence`, `pi_source` | float, nullable | — |
| `expected_costs`, `indifference_points` | map, nullable | — |
| `vlm` | `VLMInfo`, nullable | `fired` bool; `verdict` ∈ `defect` · `clean` · `unsure`; `confidence` ∈ `[0, 1]`; `reasoning` free text; `tokens_in`, `tokens_out` |
| `run_guard_warnings` | list of string | — |

**Well-formedness, frozen with the contract.** (1) `decision = pending_human` with
`resolved_by` null is a **well-formed abstain**, never a contract failure (dossier A5).
(2) A rejected input — HTTP 400 from paths 1–4 and 8 of the T3-01 table — produces no
`AdjudicateResponse` and is a **harness error**: it leaves the denominator under
`eval-plan.md` §5.1. (3) A model failure — paths 5–7, `VLMParseError` — is an **agent
failure** and stays in the denominator. The contract makes the split observable through
one attribute, `aiqs.error.kind`
([`emitter-instrumentation-contract.md`](../specs/emitter-instrumentation-contract.md) §2.4),
so `eval-plan.md` §5.1 needs no wording that the telemetry cannot support.

**B0's run configuration is part of P1, and it is a judgement.** At the Adjudicator's
default `target_prevalence = 0.02`, all 160 measured items are `pass` and nothing reaches the
VLM (dossier A4); D2 ablates the VLM prompt and would then change nothing. Proposed: B0 is
`aiqs-serve --provider anthropic --model claude-sonnet-4-6` with the artifact's
**realistic cost matrix** — the configuration that produced the `decision_target_realistic`
column (152 escalations of 160) — `lam` at its default, temperature 0 (the backend's
default), `max_tokens 512`. The session confirms the exact flags from the run metadata under
`results/runs/` rather than from this file. **Judgement:** the alternative, the native
configuration (41 escalations), keeps most items on the policy path where D2 cannot act.

---

## 2. P2 — Apartment Triage task definition and output contract, filled minimally

**Disposition: option 3 of [`freeze-a-prep.md`](../specs/freeze-a-prep.md) §2 — fill P2
minimally**, enough for `triage-v1` and P4's R5, and defer the replication decision to F4
as a budget call. Reason: with 48 team-authored labels the achieved MDE is 20.1 pp (dossier
C4), an order of magnitude from the plan's δ, so Triage cannot carry a gate at Freeze A
whatever P2 says. **Judgement**, and the cheapest of the three.

**Source to record:** `github.com/arslan-kursad/apartment-triage` at
`15c1d6ebdeef43d22c76bf32e7198966083c937f` (committed 2026-07-13).

**Task.** One item is one incoming resident message (`ClassifierInput`: `RawText`,
`ChannelType`, `EmergencySuspected`, `MatchedPhrases`, optional image). The output is
`ClassifierOutput`, snake_case on the wire.

| Field | Emitted set |
|---|---|
| `category` | 14 values: `plumbing` `electrical` `gas` `heating_cooling` `elevator` `structural` `common_area` `pest` `noise` `neighbor_dispute` `billing` `security` `announcement` `other` |
| `severity` | `low` `medium` `high` `urgent` |
| `category_confidence`, `emergency_confidence` | `low` `medium` `high` |
| `is_emergency` | bool |
| `ambiguity_reasons` | subset of the nine `AmbiguityReason` values — see the correction below |
| `secondary_issues` | list; each with `category`, `severity`, `snippet`, `location_hint`, `causal_relation` ∈ `independent` `effect_of_primary` `cause_of_primary` |
| `location_hint`, `rationale` | free text, nullable |

**Well-formedness.** Non-empty `ambiguity_reasons` (a clarification) and
`category = announcement` are successful outputs. Failures carry a typed
`AgentErrorKind`: `Transient` and `Cancelled` are harness errors and leave the
denominator; `Semantic` is an agent failure and stays; `Escalation` is a well-formed
hand-off, not a failure.

**A correction candidate for the C-2 dossier, found by reading the code rather than the
prompt file.** Dossier A3 records that the prompt lists six `AmbiguityReason` values and
the enum nine, so three are unreachable. `ClassifierAgent.cs` carries a `SystemPrompt`
constant — the one it passes to the model — whose *"AMBIGUITY REASONS"* line lists **all
nine**, including `insufficient_detail`, `unclear_urgency` and `multiple_categories`.
`classifier.v2.md`, which the dossier read, lists six. Which text the running agent sends
is settled by the first capture (plan W2-1), not by reading; until then P2 records the
nine-value set with this note. It also bears on D2: if the constant is what runs, the
Triage degradation is a source edit rather than the manifest change the dossier describes.

**Dataset `triage-v1`:** the 15 wired cases plus the 33 unwired cases once
`edge_cases.jsonl` is rewritten into wire vocabulary, 48 in total; split by the `eval-plan.md` §5.2 rule.

---

## 3. P3 — case volume, `N_gate`, achieved MDE

**Proposed selection: D — `mvtec-screw` + `mvtec-capsule`, 292 items, MVTec AD only.**

**The P3 table needs one correction before it is used, and it changes the answer.** Its
*N per arm* column takes the whole category as the gate arm. `eval-plan.md` §5.2 splits
every dataset dev 30 % / gate 70 % first. Recomputed with the plan's own formula (validated
against its `n ≈ 157`):

| Selection | Items | `gate` after the split | MDE on the gate split |
|---|---:|---:|---:|
| A — screw only | 160 | 112 | **12.1 pp — misses δ = 0.10** |
| B — capsule only | 132 | 92 | 13.6 pp — misses |
| **D — both MVTec** | **292** | **204** | **8.6 pp — meets** |
| G — all three, crossing into VisA | 452 | 316 | 6.7 pp — meets, but see the P3 table's point 4 |

So A, the only single-category selection the P3 table shows as meeting the target, does not
meet it once the plan's split is applied. D is the largest selection inside one dataset and
one detector regime (AUROC 0.976 / 0.977) and clears δ with margin. VisA is excluded on the
P3 table's own point 4 — a 0.739 detector is not the same population.

**To record:** `adjudicator-v1` = MVTec AD `screw` (160) + `capsule` (132); `N_gate = 204`
(dev ≈ 88); achieved MDE **8.6 pp** on the unpaired upper bound, `p_baseline = 0.90`
assumed and re-derived at Freeze B; the per-item hash for the split seeded with the dataset
id; **category is a stratification key and the instrumentation contract puts it on the
trace** (`aiqs.category`), so pooling costs no stratification.

---

## 4. P4 — R5 task-specific rule set

Definitions frozen here; rule bodies are F3 implementation (`eval-plan.md` §8.1).

**Adjudicator (`adjudicator-v1`), evaluated on the `aiqs.adjudicate` span's attributes:**

| Rule | Definition |
|---|---|
| R5.A1 | `decision` ∈ {`pass`, `fail`, `pending_human`} |
| R5.A2 | `pending_human` is true iff `decision = pending_human` and `resolved_by` is null |
| R5.A3 | when not pending, `resolved_by` ∈ {`policy`, `vlm`, `human`} |
| R5.A4 | `resolved_by = policy` ⇒ `tier1_decision` ∈ {`pass`, `fail`} and `decision = tier1_decision` |
| R5.A5 | `vlm.fired` ⇒ `verdict` ∈ {`defect`, `clean`, `unsure`} and `0 ≤ confidence ≤ 1` |
| R5.A6 | `calibrated_p` ∈ [0, 1] |
| R5.A7 | an item whose span carries `aiqs.error.kind = harness` is excluded from the denominator; `agent` stays and fails R3 |
| **R5.A8 — judgement** | when `decision` ∈ {`pass`, `fail`}, it agrees with the MVTec label (`label 0 → pass`, `label 1 → fail`); abstains are excluded from A8 |

**R5.A8 is the ground truth entering E1, and it needs an edit to `eval-plan.md` §7.4** — see E-2 below.
Scenario A was determined precisely because a per-item label exists; a contract-only E1
would leave that label unused and make D2 undetectable by the deterministic endpoint.

**Triage (`triage-v1`), evaluated on the `invoke_agent classifier` span:**

| Rule | Definition |
|---|---|
| R5.T1 | `category` in the 14-value set; `severity` in the 4-value set; both confidences in the 3-value set |
| R5.T2 | `ambiguity_reasons` ⊆ the nine-value set as measured on the wire at first capture |
| R5.T3 | `missing_severity` ∈ `ambiguity_reasons` ⇒ `severity = medium`, unless `category = electrical` or `is_emergency` (the agent's own constraint) |
| R5.T4 | `triage.error.kind = Transient` or `Cancelled` ⇒ excluded; `Semantic` ⇒ fails R3 |
| R5.T5 | when a label exists, `category` and `is_emergency` agree with it |

---

## 5. P5 — rubric anchors, proposed text

The dimensions, scale and constraints are fixed by `eval-plan.md` §8.2 and transcribed in
[`rubric-v1.md`](../eval/rubric-v1.md). What follows is anchor **text**, which is human
authoring; it is written here as a proposal so the session edits rather than composes, and
it is not written into `rubric-v1.md`. Constraints honoured: points 2 and 3 are separated
by a rule; each anchor applies to one output seen alone; no comparatives; the four steps are
meant to be equidistant.

**J1 — groundedness.** *Does the stated rationale rest on evidence present in the trace
inputs?* (inputs: the image, the detector score, the calibrated probability, the crop if any)

| Point | Anchor |
|---|---|
| 4 | Every claim in the rationale is traceable to an input on the trace, and the stated confidence matches the strength of the evidence the rationale itself cites |
| 3 | Every claim is traceable to an input, but one claim is stated with more certainty than the cited evidence supports, **or** one input that bears on the verdict is present and unmentioned |
| 2 | At least one claim has no support in the inputs — an invented detail or a misread input — while the verdict still follows from the claims that are supported |
| 1 | The verdict rests on a claim that is absent from or contradicted by the inputs, or the rationale is empty or generic enough to fit any item |

**J2 — instruction adherence.** *Against the pinned task contract, including the
calibration instruction the system prompt carries* (P5 inputs, item 3).

| Point | Anchor |
|---|---|
| 4 | Output is well-formed per the contract, the vocabulary is exact, and the calibration instruction is followed: high confidence only with clear evidence, `unsure` when the rationale itself describes ambiguity |
| 3 | Well-formed and exact, but confidence and rationale disagree in one direction — a hedged rationale with high confidence, or clear evidence with low confidence |
| 2 | Well-formed, but the calibration instruction is ignored: a confident verdict whose rationale admits ambiguity, or `unsure` whose rationale names clear evidence |
| 1 | Not well-formed — a missing field, a value outside the vocabulary, prose instead of the JSON contract — or the rationale assumes the detector is right without inspecting the image |

**Presentation template (fixed order, identical whitespace, no item id, no variant label,
no baseline):** (1) the task contract excerpt — the `QUESTION` text; (2) the trace inputs as
a fixed key list; (3) the agent output JSON verbatim; (4) the two anchor tables; (5) the
answer format `{"J1": n, "J2": n}` and nothing else.

**What the anchors cannot yet be checked against:** no `VLMInfo.reasoning` instance has
been read (P5 inputs, gap 1). The session should accept them provisionally and re-read them
against the first ten captured rationales before Freeze B; that re-read is a rubric edit and
is recorded as one only if it changes text.

---

## 6. P6 — reference-label sourcing and stratification keys

**Source:** MVTec AD's per-image annotation, carried per item in the run artifact's
`decision_scores.csv` `label` column (`0` good, `1` defective); independent of the agent
because it predates it (dossier C2). **Cost:** zero for benchmark items.

**Stratification keys:** `category` ∈ {`screw`, `capsule`}; `label` ∈ {good, defective};
B0's `tier1_decision` route ∈ {`pass`, `fail`, `escalate`}. The first two are on the trace
under the contract (`aiqs.category`; the label is joined from the dataset by `item_id`);
the third is emitted.

**Human reference subset (`eval-plan.md` §8.4):** 50 items drawn from `gate` by seeded hash, proportional
across `category × label` (four cells); scored by the maintainer on J1 and J2 **before any
judge output exists**; second blind pass ≥ 7 days later for A4. The reference is a rubric
score, not a defect label — the defect label is R5.A8's, already present.

---

## 7. P7 — judge tiers and the daily cap `Q`

**T1 — local Ollama, on the maintainer's machine.** Read 2026-09-05: Ollama is not
installed on this host and the host has two cores and no GPU (the Adjudicator's README
says the same of its own host). T1 is therefore sized to what runs unattended overnight:
292 items × 3 repeats ≈ 900 judgments of ~200 output tokens. **Proposed:** the smallest
current instruct model in Ollama's library at `Q4_K_M` quantization (a 3–4 B parameter
class), chosen at install, with `ollama show` recording the exact id and digest into v0.2.
**Judgement**, and the plan's CP-11 records why T1 is kept rather than dropped.

**T2 — a stable, non-preview Gemini Flash model.** The models page, read 2026-09-05 (page
dated 2026-09-04), lists nine Flash ids: `gemini-3.8-flash`, `gemini-3.7-flash`,
`gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`
(stable), `gemini-3-flash-preview` (preview, excluded), `gemini-2.5-flash` and
`gemini-2.5-flash-lite` (stable). **Proposed: `gemini-3.6-flash`** — stable, mid-generation,
so neither the newest (whose free-tier cap is the tightest and least settled) nor the
oldest (the first to be deprecated inside a three-month measurement). Fallback if it is not
on the free tier on the session day: `gemini-2.5-flash`. **Judgement**; the session re-reads
the page and records the date.

**`Q` — recorded as a dated observation, not frozen.** The rate-limits page, read
2026-09-05 (dated 2026-09-02), publishes no numeric free-tier figure; limits are per project
and shown only in Google AI Studio. This is exactly
[`freeze-a-prep.md`](../specs/freeze-a-prep.md) §2.1's finding, and its resolution is adopted: Appendix A's P7 row is edited so that `Q` is
*"the free-tier daily request cap shown in AI Studio for T2's model, read on <date>"*, and
`eval-plan.md` §8.3's quota-exhaustion rule carries the validity.

**Where each tier runs (E-8 below):** T1 in Experiment mode only, on the maintainer's
machine; Nightly runs E1 and E3 plus T2's seeded 20 % sample within `Q`.

---

## 8. P11 — Claude Code emitter scope markers

**Transcription, not a decision.** Instrumentation scope
`com.anthropic.claude_code.tracing`, version `1.0.0`, measured across three captures and
two builds (2.1.197, 2.1.229) — `normalization/mappings/v1.41/claude-code.yaml`:19-20,
`architecture.md` §10 OQ-4. Two span types (`claude_code.interaction`,
`claude_code.llm_request`) and one event are measured; `claude_code.tool` and
`claude_code.hook` spans are **unobserved** until plan W1-6 runs. P11 records both halves.

---

## 9. Exit items 2–6

The diffs are in [`freeze-a-items-2-6.md`](freeze-a-items-2-6.md) and are not repeated.
Two of them carry a judgement, and the proposal for each:

- **Item 3, row 1.4's threshold wording:** *"0 emitted attribute names found in neither the
  vendored registry nor `external-allowlist.yaml`"*, checked against the vendored copy and
  never against upstream at query time (`#36`'s own wording).
- **Item 6, the `architecture.md` pin:** `architecture.md` reads **v0.17** on 2026-09-05.
  Re-read it on the session day, and re-verify the §7 citation first — the burn-line rule
  changed twice on 2026-09-02.

---

## 10. Additional v0.2 edits this package proposes

| ID | Where | Proposed | Why |
|---|---|---|---|
| E-1 | `eval-plan.md` §9 mode table, *Nightly* row | trigger: *"scheduled job — CI cron in F3, Cloud Scheduler from F4"* | plan CP-7 |
| **E-2 — judgement** | `eval-plan.md` §7.4, E1's definition | `task_pass_rate` over `R1 ∧ R2 ∧ R3 ∧ R4 ∧ R5`, with R5.A8 the only ground-truth-bearing conjunct | Scenario A's label is otherwise unused; §4 above |
| E-3 | SC-3 verdict rule | add: *"If the primary subject is not emitting E1's inputs by 2026-09-12, SC-3 is evaluated in F4 and F3 exits on the gate mechanism proven against a replay corpus (ADR-0010 D6-2)"* | ADR-0010 §6.4 says this edit is due |
| E-4 | SC-2, below row 2.4 | *"Row 2.1 is the definition of 'uninterrupted' for this project; it is a staffing commitment — one of the three sources emits only when a human runs a session"* | `#138`, before 2026-10-05 |
| E-5 | `eval-plan.md` header and §4 | version 0.2; status *FROZEN A, <date>*; both agent repositories named with their commits | the dossiers' first line |
| E-6 | Appendix A, P7 and P10 | P7's `Q` as a dated observation (§7 above); P10's L1 defined as *"the calibration corpus replayed at a fixed rate for ten minutes"* with the rate set at Freeze B | §7; plan W3-7 |
| E-7 | `eval-plan.md` §5.2 | dataset rows: `adjudicator-v1` = MVTec `screw` + `capsule`, 292 items; `triage-v1` = 48 cases | §3, §2 |
| E-8 | `eval-plan.md` §8.3 | *"T1 runs in Experiment mode on the maintainer's machine; Nightly runs E1 and E3 and T2's sample within `Q`"* | CP-11 |
| E-9 | `eval-plan.md` §5.1 | the `error` verdict is assigned from the emitter's error-kind attribute (`aiqs.error.kind`, `triage.error.kind`), never inferred from a status code | T3-01 finding 1; [`emitter-instrumentation-contract.md`](../specs/emitter-instrumentation-contract.md) §1.7 |

---

## 11. The §5 choice

**(a) — one dated second session**, proposed for **Monday 2026-09-08, 10:00–13:00
Europe/Istanbul**, agenda in [`freeze-a-prep.md`](../specs/freeze-a-prep.md) §4 with every
slot reading this package instead of deriving. If P5 is not accepted by T+150, the session
records (b) with its date, as the brief requires; (c) is not available.

---

## 12. Provenance

Derived 2026-09-05 from the files in §0 at `main @ b7b3cf9`, from both agent repositories
on this host at the commits named in §1 and §2, from the Gemini models and rate-limits pages
read the same day, and from the MDE recomputation in §3 (the plan's formula, validated
against its own `n ≈ 157`). No value here is a measurement of the frozen plan; the frozen
plan is what the session writes.
