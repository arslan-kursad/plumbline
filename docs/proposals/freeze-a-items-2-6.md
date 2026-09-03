# Freeze A exit items 2–6 — diff proposals, prepared not applied

**Prepared:** 2026-09-03 · **Lane:** A · **Task:** F3 Unblock dispatch U-07
**Target:** [`docs/eval-plan.md`](../eval-plan.md) · **Items:**
[`freeze-a-prep.md`](../specs/freeze-a-prep.md) §7, exit conditions 2 through 6

> **NOT APPLIED, and Lane A may not apply them.** `eval-plan.md` is a pre-registration
> document, human-only, Class 3. Every block below is a proposal for a human to apply
> during the Freeze A session. Each names the current text read at 2026-09-03 and the
> replacement, so the session transcribes rather than derives.

---

## The prohibition question, stated once so it is not re-litigated

The dispatch notes that external context lists the `"F1 entry gate"` string under
*Do-not-fix*, and asks that the reconciliation be explicit.

**The repository says the same thing, and says why.**
[`F3-entry-directive.md`](../specs/F3-entry-directive.md) §2 excludes *"any edit to
`docs/eval-plan.md`"* and names *"the SC-1 row 1.1 path defect and the stale
`architecture.md` pin in §4"* specifically — then adds that both are **"Freeze A exit
conditions, `freeze-a-prep.md` §7 items 5 and 6."**

So the prohibition and the authorisation are in the same sentence. The edits are forbidden
**to Lane A, at any time** — this is a lane boundary, not a schedule — and they are
**required of the human at Freeze A**, because [`freeze-a-prep.md`](../specs/freeze-a-prep.md)
§7 lists them as conditions the freeze cannot complete without.

**Nothing about that changes on the day of the session.** Freeze A is not the moment a
prohibition lifts; it is the moment the person who was always allowed to make these edits
makes them. Preparing the diffs is Lane A work and is what this file is. Applying them is
not, and this file does not.

---

## Item 2 — reconcile §2's "F1 entry gate"

**Two occurrences, both read 2026-09-03.**

### 2a · `eval-plan.md`:25

```
-require a baseline variance estimate, and no agent data exists at the F1 entry gate.
+require a baseline variance estimate, and no agent data exists at the F3 entry gate.
```

### 2b · `eval-plan.md`:31 — the stage table

```
-| **Freeze A** | F1 entry gate (human action) | Criteria, metrics, …
+| **Freeze A** | F3 entry gate (human action) | Criteria, metrics, …
```

**Grounding, so the replacement is not a guess.** [`project-brief.md`](../project-brief.md):85
states it directly: *"Freeze A now happens at the **F3 entry gate**: F1's code reads no
evaluation criterion, and what the freeze protects is the seeded-regression experiment in
F3."* The brief also records that the plan *"still says 'F1 entry gate' and is stale on that
line"* — so the correction is already reasoned in the repository and only needs applying.

**Note on 2a's sentence.** It reads *"no agent data exists at the F1 entry gate"*, which was
true and is the original argument for the two-stage freeze. Changing it to `F3` keeps the
argument valid — no agent data exists at the F3 entry gate either, which is exactly what
[`#177`](https://github.com/arslan-kursad/plumbline/issues/177) records. **The sentence
survives the change; if it did not, this would be a rewrite rather than a reconciliation and
would need the human's judgement rather than a diff.**

## Item 3 — discharge `#36`: SC-1 row 1.4 names the allowlist too

**Current, `eval-plan.md`:114:**

```
| 1.4 | **Semconv conformance** | Every emitted `gen_ai.*` / normalized column name
validated against a machine-readable copy of the pinned v1.41 registry vendored in-repo |
`normalization/semconv/v1.41/` | 0 non-conforming names |
```

**Proposed:**

```
| 1.4 | **Semconv conformance** | Every emitted `gen_ai.*` / normalized column name
validated against a machine-readable copy of the pinned v1.41 registry vendored in-repo,
**or present in the vendored external allowlist** |
`normalization/semconv/v1.41/registry.yaml` + `external-allowlist.yaml` | 0 names in
neither |
```

**Verified 2026-09-03:** `normalization/semconv/v1.41/` contains `registry.yaml`,
`spans.yaml`, `events.yaml`, `metrics.yaml`, `deprecated/`, **and `external-allowlist.yaml`**.
The row currently names the directory and the registry concept only, so a name that is
legitimately allowlisted reads as non-conforming against the criterion as written.

**Open, and the human must settle it:** the threshold wording. *"0 non-conforming names"*
becomes ambiguous once two sources exist. The proposal above says *"0 names in neither"*;
whether that is the intended semantics is `#36`'s substance and is not Lane A's to decide.

## Item 4 — discharge `#10`'s eval-plan half: `redacted_fields` in row 1.2

**Current, `eval-plan.md`:112**, manifest field set:

> capture origin, emitter SDK + version, the semconv version **actually emitted**, the
> `OTEL_SEMCONV_STABILITY_OPT_IN` value (recorded as `unset` when absent) and the capture
> date

**Proposed:** add `redacted_fields` to that list.

**Grounding.** `#10`'s blocking finding is that the Claude Code emission carries personal
data — `user.id`, `user.email`, `organization.id`, `user.account_uuid`, `session.id`,
`terminal.type`, `workspace.host_paths`. A redacted capture is **not raw emitter output**,
and row 1.3's losslessness check has to say which artefact it validates against.

**Already true in practice, which makes this a record correction rather than a change.**
`redacted_fields` is present in all four existing manifests, and
`scripts/capture/manifest_validate.py` already covers it. The criterion is behind the
artefacts.

## Item 5 — correct SC-1 row 1.1's data source

**Current, `eval-plan.md`:111:**

```
| 1.1 | Golden-file test pass rate | CI job, per dialect | `normalization/testdata/<dialect>/` | 100%, ≥3 dialects |
```

**Proposed:**

```
| 1.1 | Golden-file test pass rate | CI job, per dialect | `testdata/fixtures/<dialect>/` | 100%, ≥3 dialects |
```

**Grounding, re-derived 2026-09-03.** `freeze-a-prep.md` §7.1 finding 1 records that
`normalization/testdata/<dialect>/` *"occurs once in the whole repository, in this row"*.
Confirmed: the corpus is at `testdata/fixtures/<dialect>/`, which is what the tests read —
`worker/Plumbline.Normalization.Tests/FixtureCorpus.cs:80` and
`worker/Plumbline.Worker.Tests/IngestionEndpointTests.cs:152`.

**This is the cheapest of the five and the most consequential if missed.** Freezing a path
that does not exist would pre-register a criterion against a directory nothing writes to.

## Item 6 — refresh §4's `architecture.md` pin

**Current, `eval-plan.md`:54:**

```
-- `docs/architecture.md` v0.3 — §3.3 (dedup), §4.1 (`spans_deduped`, `spans_real`,
+- `docs/architecture.md` v0.16 — §3.3 (dedup), §4.1 (`spans_deduped`, `spans_real`,
```

**Read 2026-09-03:** `architecture.md` is at **v0.16**. The pin reads v0.3 — thirteen
versions stale, not ten as `freeze-a-prep.md` §7.1 recorded on 2026-09-01, because
`architecture.md` has moved since (v0.15 on 09-02, v0.16 on 09-03 with the ADR-0009 index
row).

**Two cautions for the session.**

1. **Re-read the version at the moment of the edit.** `architecture.md` is under active
   change and this number has moved twice in two days. Pinning a number read from *this
   file* rather than from `architecture.md` would reproduce the defect being fixed.
2. **The pin is a claim about content, not only a number.** `freeze-a-prep.md` §7.1 verified
   on 2026-09-01 that every `architecture.md` section the plan cites still says what the
   plan says it says. That audit predates v0.15 and v0.16. **v0.15 changed §7's escape
   hatch into a burn-line trajectory test** — which the plan cites as *"§7 (cost)"* — so
   this specific citation should be re-verified before the pin is bumped, not assumed to
   have survived.

---

## Summary for the session

| Item | Edit | Risk if wrong |
|---|---|---|
| 2 | `F1` → `F3` entry gate, two sites | low — grounded in `project-brief.md`:85 |
| 3 | row 1.4 names the allowlist | **threshold wording is a decision**, not a transcription |
| 4 | row 1.2 gains `redacted_fields` | low — artefacts already comply |
| 5 | row 1.1 path corrected | low to apply, **high if skipped** |
| 6 | pin v0.3 → v0.16 | **re-read the version and re-verify §7's content first** |

Items 3 and 6 carry a judgement each and are not pure transcription. Items 2, 4 and 5 are.
