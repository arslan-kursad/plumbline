# C-2 dossier — Apartment Triage, filled copy, 2026-09-03

**Form:** [`c-1-adjudicator-dossier.md`](../specs/c-1-adjudicator-dossier.md) v0.1, applied to the second agent
**Filled by:** Lane A, from repository reads only · **Status:** partial — see §7
**Source for every sourced field:** `github.com/arslan-kursad/apartment-triage` @
`15c1d6ebdeef43d22c76bf32e7198966083c937f`, committed 2026-07-13T16:59:52Z, read 2026-09-03.
Instrumentation detail in [`c2-triage-readout.md`](c2-triage-readout.md).

**This is not a completed dossier.** Four fields are `UNKNOWN` and §7 lists them with which
of the form's four reasons applies. Two of the four are work.

> **The form was written for the Adjudicator and transfers cleanly, but the two agents are
> not in the same state.** Where C-2 differs from C-1 the difference is called out, because
> P2 is not P1 with different nouns — the label story in particular is weaker here and the
> degradation story is stronger.

---

## Section A — Output contract

### A1 — Output serialization

**Structured JSON over an Anthropic model call.** Schema:
`src/ApartmentTriage.Application/Agents/Classifier/ClassifierOutput.cs` — a sealed C# record.

Enforced at runtime by `System.Text.Json` in `ClassifierAgent.cs`:16,21 with
`PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower` and
`new JsonStringEnumConverter(JsonNamingPolicy.SnakeCaseLower)`. The prompt declares the same
shape independently at `agents/classifier/prompts/classifier.v2.md`:72-91.

**Two declarations of one contract**, which matters for A3.

### A2 — Field inventory

`ClassifierOutput`:

| Field name | Type | Required | Finite value set? |
|---|---|---|---|
| `Category` | `TicketCategory` | yes | **yes — 14** |
| `Severity` | `TicketSeverity` | yes | **yes — 4** |
| `CategoryConfidence` | `ConfidenceLevel` | yes | **yes — 3** |
| `IsEmergency` | `bool` | yes | yes — boolean |
| `EmergencyConfidence` | `ConfidenceLevel` | yes | **yes — 3** |
| `LocationHint` | `string?` | nullable | no |
| `SecondaryIssues` | `IReadOnlyList<ClassifierSecondaryIssue>` | yes | no (nested) |
| `AmbiguityReasons` | `IReadOnlyList<AmbiguityReason>` | yes | **yes — 9 in the enum** |
| `Rationale` | `string?` | nullable | no |

**Non-nullable enums, unlike C-1.** The Adjudicator's `AdjudicateResponse` widens every
enumerated field to `str | None`; here the C# types are the enums themselves. The contract is
enforced by the type system at the boundary rather than described in a comment.

### A3 — Enumerations, as emitted

**Answered, and it produced the sharpest finding in this dossier.**

The wire is **snake_case**, because `JsonStringEnumConverter(JsonNamingPolicy.SnakeCaseLower)`
governs both directions. The C# names are PascalCase; A3 asks for what goes on the wire.

| Field | Emitted set, exact | Source |
|---|---|---|
| `category` | `plumbing` `electrical` `gas` `heating_cooling` `elevator` `structural` `common_area` `pest` `noise` `neighbor_dispute` `billing` `security` `announcement` `other` | `Enums/TicketCategory.cs`; prompt :4-18 |
| `severity` | `low` `medium` `high` `urgent` | `Enums/TicketSeverity.cs`; prompt :27 |
| `category_confidence`, `emergency_confidence` | `low` `medium` `high` | `Enums/ConfidenceLevel.cs`; prompt :31 |
| `ambiguity_reasons` | **see below — the two declarations disagree** | — |

#### The finding: three enum values the model is never told exist

`Enums/AmbiguityReason.cs` declares **nine** values. The prompt (`classifier.v2.md`:47) lists
**six**:

> `missing_location, missing_severity, category_ambiguous, language_unclear, needs_visual, non_actionable`

Absent from the prompt, present in the enum: **`InsufficientDetail`, `UnclearUrgency`,
`MultipleCategories`.**

The model is instructed with the six. It cannot emit the other three, because nothing tells it
they exist. They are reachable in C# and unreachable on the wire.

**And one of the three is expected by a label file.** `evals/edge_cases.jsonl` case `ec-0001`
carries `"expected_ambiguity_reasons": ["InsufficientDetail", "MissingLocation"]`. That case
expects a value the agent has no way to produce, so it would fail for a reason that is not a
model failure.

**A second, smaller mismatch in the same file.** `edge_cases.jsonl` writes ambiguity reasons in
**PascalCase** (`InsufficientDetail`) while the wire is snake_case (`insufficient_detail`) and
the *wired* corpus `classifier_eval_cases.json` writes lowercase snake correctly
(`"category": "plumbing"`). So `edge_cases.jsonl` is authored in enum-name space rather than
wire space.

> This is the same class of finding as C-1's A3 — where documented `PASS/FAIL/ESCALATE` were
> the Python attribute names and the wire carried `pass/fail/escalate`. **The form asks for
> exact strings and exact casing precisely because two declarations of one contract drift.**
> Here they have drifted in vocabulary as well as casing.

### A4 — Contract stability

**`UNKNOWN` — not looked up, and it cannot be looked up from this repository.**

C-1 answered A4 by measurement: 480 emissions in an archived run file, nothing outside the
set. **Apartment Triage has no equivalent artefact.** There is no `results/` directory and no
stored run output; the eval harness (below) writes its scores to the test runner, not to a
committed file.

Answering A4 therefore needs a run, not a read. Recorded as a measurement that has not been
made rather than as an opinion, per the form's rule 2.

**What can be said without it:** three structural enforcement points make out-of-set values
unlikely at the C# boundary — non-nullable enum fields (A2), a strict converter (A1), and a
`Semantic` error on any deserialization failure (A5). None of them constrains what the *model*
returns; they constrain what survives parsing.

### A5 — Failure and refusal shape

**Answered, and this is where Triage is materially ahead of the Adjudicator.**

`AgentErrorKind` (`Agents/AgentErrorKind.cs`) is a **typed, four-valued error kind**:

| Value | Meaning, per its own comment |
|---|---|
| `Transient` | network timeout, 429, 5xx — retry eligible |
| `Semantic` | bad JSON, missing required field — no retry |
| `Escalation` | agent signals need for a stronger model |
| `Cancelled` | `CancellationToken` triggered before completion |

Failure paths in `ClassifierAgent.cs`, each carrying one of those kinds:

| Path | Line | Kind |
|---|---|---|
| retryable `HttpRequestException` | :55-58 | `Transient` |
| non-retryable `HttpRequestException` | :60-63 | `Semantic` |
| `TaskCanceledException` | :65-68 | `Cancelled` |
| no JSON object found in the response | :81-86 | `Semantic` |
| `JsonException` on deserialize | :94-98 | `Semantic` |
| deserialized output was null | :102-103 | `Semantic` |

**The comparison is the point.** [`f3-t3-01-400-discriminator.md`](f3-t3-01-400-discriminator.md)
found the Adjudicator returns **eight distinct causes behind one HTTP 400**, discriminable only
by prefix-matching prose. Triage returns a **typed kind on every failure**, and `Transient`
versus `Semantic` is exactly the harness-error-versus-agent-failure split that
[`eval-plan.md`](../eval-plan.md) §5.1 requires and the Adjudicator cannot supply.

**Well-formed non-answers, which are not failures.** Non-empty `AmbiguityReasons` routes to a
clarification message (`TriageResult`, `Orchestration/TriageResult.cs`), and category
`announcement` is explicitly *"NOT a ticket"* (prompt :17). Both are successful outputs and R3
must score them as such — the same trap C-1 records for `pending_human`.

**One asymmetry recorded, not resolved.** `ClassifierAgent.cs`:36 is
`ShouldEscalate(...) => false` — the classifier never raises `Escalation` — while
`TriageResult` carries an `EscalatedToSonnet` flag. Escalation happens somewhere else in the
pipeline, and this dossier did not trace where.

---

## Section B — Trace observability

### B1 — Does the output reach a span attribute?

**No. There is no instrumentation at all.** Verified four ways on 2026-09-03 and recorded in
full at [`c2-triage-readout.md`](c2-triage-readout.md): zero `OpenTelemetry.*` among 24
`PackageReference`s across five projects; zero files naming `ActivitySource`,
`System.Diagnostics`, `StartActivity` or `TracerProvider`; zero telemetry-named paths among 310
tree entries; zero `otlp` / `OTEL_` / `4317` in configuration. Controls over the same tree:
`Serilog` 15, `using System` 46, `ILogger` 18.

### B2 — Is it complete?

**Not applicable while B1 is no.** Recorded as not-applicable rather than `UNKNOWN`, per the
form's rule 4: there is no attribute value to be truncated.

### B3 — Is the input case on the trace?

**No**, same reason as B1.

### B4 — What change makes B1 and B3 yes?

Add OpenTelemetry instrumentation: the packages, a tracer, and span attributes carrying the
request and the response.

**Lane: outside plumbline entirely**, by the form's rule — a change to a different repository,
so no plumbline lane covers it. Identical to C-1's B4.

**Size: `UNKNOWN — not decided`**, and the same design choice governs it: how much of the
state is exported. **This is work, and it is the second of two such projects**, which is the
fact `#183` exists to record.

**What is cheaper here than in C-1, stated without sizing it.** The composition root is
conventional and single — `builder.Host.UseSerilog(...)` in `src/ApartmentTriage.Web/Program.cs`
— and `ILogger` is already threaded through 18 files, so the injection points exist. That is an
observation about shape, not an estimate.

---

## Section C — Reference labels

### C1 — Per enumerated field: does a reference label exist?

| Field (from A3) | Label |
|---|---|
| `category` | **exists** — 15 cases in the wired corpus, 33 in the unwired one |
| `severity` | **exists** — same two corpora |
| `is_emergency` | **exists**, and it is the field with the strictest gates (below) |
| `ambiguity_reasons` | **exists in the unwired corpus only**, and see A3's finding |
| `category_confidence` | **exists in the unwired corpus only** — but it labels a *self-report*, not a fact about the world |
| `emergency_confidence` | **neither** |

**Two corpora, and only one of them runs.**

| File | Cases | Wired to a test? |
|---|---|---|
| `tests/ApartmentTriage.Tests/Fixtures/classifier_eval_cases.json` | **15** | **yes** — embedded resource, loaded by `ClassifierEvalTests.LoadCases()` |
| `evals/edge_cases.jsonl` | **33** | **no** — grep across the whole tree finds no reference to it |

**There is a real scoring harness with thresholds**, which C-1 has no counterpart to.
`tests/ApartmentTriage.Tests/Eval/ClassifierEvalTests.cs`:79-83:

- `CategoryAccuracy ≥ 0.80`
- `EmergencyRecall ≥ 0.95`
- `EmergencyPrecision ≥ 0.70`

Gated behind `ANTHROPIC_API_KEY` with a silent return when absent (:21-22) and a
`Trait("Category", "Eval")` filter for CI.

### C2 — Label source, and its independence

**Hand-authored by the project's own team, in-repo. This is the weakest field in the dossier
and the sharpest difference from C-1.**

`edge_cases.jsonl` records authorship per case — `"added_by": "qa_hunter"`, with a date. The
wired corpus carries no author field at all.

> The form's warning is that *"the Adjudicator's own prior output is not a reference label"*.
> **That line is not crossed here** — these labels are not the agent's output. But independence
> is much weaker than C-1's, and the difference is categorical rather than one of degree:
> C-1's labels are **MVTec AD**, published with the benchmark and predating the agent entirely.
> C-2's labels were written **for this agent, by the people building it, after it existed.**

That does not make them wrong. It makes them a different kind of evidence, and any accuracy
figure computed against them inherits the authors' understanding of the taxonomy — which is
the same document (`config/taxonomy.v*.yaml`, `classifier.v2.md`) the agent is instructed with.

### C3 — Production cost per item, and who can produce it

**Low per item — a short Turkish message and four expected values.** Who can produce them is
`UNKNOWN — not decided`: authoring requires knowing the 14-category taxonomy and the emergency
rule, which is a small number of people and is not written down as a role anywhere in the repo.

### C4 — Available or producible label volume

**48 labelled cases exist today: 15 wired + 33 unwired.** Read 2026-09-03 by counting both
files.

**Against the plan's own sizing this is far short.** Using
[`eval-plan.md`](../eval-plan.md) §7.5's parameters, the same method
[`p3-volume-mde-table.md`](p3-volume-mde-table.md) validates against the plan's anchors:

| Corpus | n | Achieved MDE |
|---|---:|---:|
| wired only | 15 | **40.2 pp** |
| unwired only | 33 | **25.2 pp** |
| both, if the unwired one were repaired and wired | 48 | **20.1 pp** |

Against `N_gate ≥ 160` and a δ target of 0.10, **all three are an order of magnitude away.**
Producible volume is `UNKNOWN — not decided`, and it is a decision about how much labelling
effort the project will spend, not a lookup.

### C5 — Label agreement

**`UNKNOWN` in the strict sense, and the honest reading is n = 1.**

`edge_cases.jsonl` attributes every case it labels to a single `added_by` value in the records
inspected; the wired corpus records no author. Nothing in the repository carries inter-rater
data.

**This is the ceiling C5 exists to warn about, and unlike C-1 it applies.** C-1 escaped it
because MVTec's annotations are a published benchmark's. Here a single-annotator reference sets
an unmeasured ceiling on every accuracy figure — including the three thresholds in
`ClassifierEvalTests`, which are asserted against it.

### 4.1 Scenario derivation

Per field, per the form. Do not infer across fields.

| Field | Scenario | Reason |
|---|---|---|
| `category` | **A** | finite (14) **and** an independent-of-the-agent label exists |
| `severity` | **A** | finite (4), label exists |
| `is_emergency` | **A** | boolean, label exists, and it carries the strictest gates |
| `ambiguity_reasons` | **B** | finite, but the only labels are in the unwired corpus and expect an unreachable value (A3) |
| `category_confidence` | **B** | finite, and what is labelled is a self-report rather than a fact |
| `emergency_confidence` | **B** | finite, no label |
| `rationale`, `location_hint` | E2 territory | free text |

**Overall reading: Scenario A**, carried by `category`, `severity` and `is_emergency`.

**Under-determined because:** nothing — the A/B/C question is determined, as it was for C-1.
**What is under-determined is the strength of the A.** C-1's Scenario A rests on a published
benchmark; C-2's rests on 48 team-authored cases with n = 1 agreement. Both are Scenario A by
the form's test, and they are not equally strong evidence. **Recording that here rather than
letting one word carry both.**

---

## Section D — Degradation vector

### D1 — Is there a separable constraint section?

**Yes, and the separation is stronger than C-1's.**

The prompt is a **standalone versioned file**, not a module constant:
`agents/classifier/prompts/classifier.v2.md`, 91 lines, referenced by
`agents/classifier/manifest.yaml`:

```yaml
agent_id: classifier
model: claude-haiku-4-5-20251001
prompt_version: "v2.0.0"
system_prompt_path: agents/classifier/prompts/classifier.v2.md
```

Loaded at startup by `AgentManifestLoader`. **`classifier.v1.md` (57 lines) is still present**,
so a prior version exists on disk beside the current one.

Separable blocks with their own headers, each removable without touching `OUTPUT FORMAT`
(:72-91):

| Block | Line | What it constrains |
|---|---|---|
| `ELECTRICAL CLASSIFICATION` | :20 | Turkish signals that force `category=electrical` |
| `EMERGENCY` | :36 | when `is_emergency=true` is permitted |
| `CONSTRAINT — non_actionable` | :49 | when `non_actionable` may **not** be used |
| `EXAMPLES` | :58 | four worked classifications |

### D2 — Can it be degraded controllably?

**Yes, on all four of the form's criteria, and better than C-1 on two of them.**

| Criterion | C-2 |
|---|---|
| Reversible | **yes** — change one line in `manifest.yaml` |
| Version-pinned | **yes, explicitly** — `prompt_version: "v2.0.0"`, a field C-1 has no equivalent of |
| Expressible as a diff | **yes** — a separate file, so the degradation is a file diff rather than a source edit |
| Output stays well-formed | **yes** — every block above is removable while `OUTPUT FORMAT` stands |

**The v1→v2 delta is a natural experiment already on disk.** 57 lines to 91: the electrical
signal block, the `non_actionable` constraint and the worked examples are the growth. Removing
them is not a hypothetical single-factor change — it is approximately reverting to v1, and both
endpoints are committed.

**Consequence worth carrying:** for `eval-plan.md` §7.2's D2 (*"remove the constraint/rubric
section of the system prompt"*), Apartment Triage offers a **cleaner instrument than the
primary subject**. C-1's D2 requires editing `SYSTEM_PROMPT` inside `src/aiqs/vlm/prompt.py`;
C-2's requires pointing a manifest at a different file. That does not make Triage the primary
subject — [`eval-plan.md`](../eval-plan.md) §7.1 fixes that and this dossier does not reopen it
— but it is a real property of the replication candidate.

### D3 — Alternative vector

**Not applicable; D1 is yes.**

---

## Section E — Input shape, stratification, volume

### E1 — Input case schema

`Agents/Classifier/ClassifierInput.cs`:

| Field | Type | Note |
|---|---|---|
| `ResidentId` | `Guid` | identity, not content |
| `RawText` | `string` | the message — the substantive input |
| `ChannelType` | `ChannelType` enum | WhatsApp / Telegram / … |
| `EmergencySuspected` | `bool` | **pre-classification signal**, set upstream by phrase matching |
| `MatchedPhrases` | `IReadOnlyList<string>` | which emergency phrases fired |
| `ImageData`, `ImageMimeType` | `byte[]?`, `string?` | optional attachment |

**One case = one incoming resident message.** Clean, and it matches [`eval-plan.md`](../eval-plan.md) §5.1's *"one task
instance"* the same way C-1's does.

**`EmergencySuspected` and `MatchedPhrases` are worth flagging**: they are a deterministic
pre-filter's output fed into the model's input, sourced from `config/emergency_phrases.v2.json`.
Any experiment that degrades the prompt while leaving that filter in place is measuring the
model's marginal contribution over a rule engine, not the model alone.

### E2 — Stratification keys

Candidates, all present in the input or the corpus:

| Key | Source | On the trace? |
|---|---|---|
| `tags` | wired corpus: `normal` 9, `emergency` 3, `false_positive` 2, `edge` 1 | **no** |
| `category` | expected label | **no** |
| `channel_type` | input | **no** |
| `emergency_suspected` | input | **no** |

**`tags` is the natural key** and it is the one C-1 has no counterpart to — the corpus is
already stratified by scenario type, including a `false_positive` class.

**None of them is on the trace**, because B3 is no. Per the form's note, *a stratification key
that exists in the source but not on the trace is not usable by a trace-computed gate.* Every
candidate is blocked behind B4.

### E3 — Real case volume over the window

**`UNKNOWN` — not looked up.** Operational, and the repository holds no run archive to count
from (the same absence that leaves A4 open).

**Sourcing procedure, recorded instead of a constant** per the form's own §0 rule ([`c-1-adjudicator-dossier.md`](../specs/c-1-adjudicator-dossier.md) §0): the system
persists `Ticket` and `Message` entities to PostgreSQL and records `ApiUsageRecord` per call,
so real volume over any window is a database count once an instance is running. Nothing in the
repository fixes it.

**What is known is the labelled volume, and it is C4's 48** — not a substitute for E3, and
recorded separately so the two are not conflated.

---

## 7. Completion test

**Blocking `UNKNOWN`s:**

| Field | Reason | Is it work? |
|---|---|---|
| A4 (out-of-set values ever emitted) | **not looked up** — no run archive exists in the repository; answering needs a run | **yes**, and small |
| B4 (size of the instrumentation change) | **not decided** — depends on how much state is exported | **yes, and it is the largest item here** |
| C3 / C4 (producible label volume) | **not decided** — how much labelling effort the project will spend | **yes**, and it is the one that decides whether Triage can be a gate subject at all |
| E3 (real case volume) | **not looked up** — operational; procedure recorded | no, until an instance is running |

**Rules 1–3 satisfied:** every field carries an answer or an `UNKNOWN` with one of the four
stated reasons, and every answer names its source. **Rule 4 observed:** B2 is recorded
not-applicable rather than inferred, and C1 is answered per field.

### What this dossier locates

**Three things C-1 did not have, and one it had that this lacks.**

Ahead of C-1: a typed error kind that already supplies [`eval-plan.md`](../eval-plan.md) §5.1's
harness-versus-agent split (A5);
a version-pinned prompt file that makes D2 a manifest change rather than a source edit (D1/D2);
and a scoring harness with three thresholds already asserted (C1).

Behind C-1: **the labels.** 48 team-authored cases with n = 1 agreement, against a published
benchmark with independent annotations. Both are Scenario A; they are not equally strong, and
C4's arithmetic — 20.1 pp achieved MDE at the full 48 — says Triage cannot carry a gate at the
plan's δ without a labelling decision nobody has taken.

**And one defect found by filling the form**, which is what the form is for: three
`AmbiguityReason` values are unreachable from the prompt, and an unwired label file expects one
of them.
