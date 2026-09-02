# T3-01 — what distinguishes the 400s, read from the Adjudicator

**Read:** 2026-09-02 · **Lane:** A · **Source:** `github.com/arslan-kursad/aiqs-agent`
**Pinned at** `0779c04ff98a744285b8b1c93ce35f4efd4a89b2`, committed 2026-07-18T18:20:33Z.
**Task:** [`F3-prerequisite-directive.md`](../specs/F3-prerequisite-directive.md) T3-01
**Charter:** [`c-1-dossier-filled-2026-09-02.md`](c-1-dossier-filled-2026-09-02.md):140

**This is a read, not a run.** Nothing here executes the Adjudicator. Where a claim would
need execution to settle, it is marked as such rather than assumed.

---

## What was already settled, and what this adds

The dossier closed the **status-code** question: a malformed image and an unparseable model
response both return `400`, so from outside the API they are indistinguishable by code. It
did not record the **bodies**. That is the whole of this task.

## Every path that produces a 400

Eight, not two.

| # | Site | Cause | Response body `detail` | [`eval-plan.md`](../eval-plan.md) §5.1 class |
|---|---|---|---|---|
| 1 | `api/main.py:66` | `image_b64` is not valid base64 | `"image_b64 is not valid base64: {e}"` | harness — **leaves** the denominator |
| 2 | `api/main.py:73-75` | `image_path` given but no `--image-root` configured | `"image_path serving is disabled on this server (no --image-root configured); use image_b64 instead."` | harness |
| 3 | `api/main.py:78` | `image_path` escapes `--image-root` | `"image_path escapes the configured --image-root."` | harness |
| 4 | `api/main.py:80` | `image_path` not found | `"image_path not found under --image-root: {image_path!r}"` | harness |
| 5 | `api/main.py:179` ← `vlm/backend.py:50` | empty model response | `"empty model response"` | **agent — stays in** |
| 6 | `api/main.py:179` ← `vlm/backend.py:62` | response is not valid JSON | `"response is not valid JSON: {e}\n---\n{raw!r}"` | **agent — stays in** |
| 7 | `api/main.py:179` ← `vlm/backend.py:66` | response failed schema validation | `"response failed schema validation: {e}\n---\n{raw!r}"` | **agent — stays in** |
| 8 | `api/main.py:179` ← `graph/nodes.py:47` | `detector_score` is NaN or infinite | `"detector_score must be finite, got {score!r}"` | harness — **leaves** the denominator |

Rows 1–4 are raised directly in `resolve_image_path`. Rows 5–8 all arrive through the same
clause, `api/main.py:178-179`:

```python
except ValueError as e:
    raise HTTPException(400, str(e)) from e
```

## Three findings

### 1. The split §5.1 needs runs *through* one exception handler, not between two

`VLMParseError` subclasses `ValueError` (`vlm/backend.py:39`), so it is caught there. So is
the bare `ValueError` at `graph/nodes.py:47`, raised by the `ingest` node — whose docstring
reads *"Input hygiene only"*. **One handler therefore returns both an input-validation
failure and three agent failures**, and `eval-plan.md` §5.1 requires those on opposite sides
of the denominator.

This is stronger than the dossier's finding. It is not that two causes share a status code;
it is that a *harness error and an agent failure share a single `except` clause*, so no
change at the HTTP layer alone can separate them.

*Not settled by this read:* whether a non-finite `anomaly_score` reaches `nodes.py:47` at
run time, or is refused earlier by Pydantic. `AdjudicateRequest.anomaly_score` is a plain
`float` (`api/schemas.py:22`). The guard exists and its node is documented as input hygiene,
which is evidence the author expected such input to arrive — but confirming it needs a
request, and this task may not make one.

### 2. A discriminator exists, and it is prose

Every 400 carries a distinct, prefix-stable `detail` string, so an evaluator **can** branch
on it. What does not exist is anything better: no error code, no `type` field, no
machine-readable marker. FastAPI renders `HTTPException(400, "…")` as `{"detail": "<string>"}`
and nothing more.

So the honest answer is neither of the two the task anticipated. It is not "no discriminator
exists", and it is not a usable one either: **branching requires prefix-matching
human-facing prose that carries no stability contract.** A reworded message is a silent
change in what the evaluator counts.

### 3. The codebase already has the structured form — the 400s just do not use it

This is what makes the finding actionable and small. Both `409` responses return a
structured body:

```python
raise HTTPException(409, detail={
    "message": "item_id already adjudicated" if done
              else "item_id already pending human review",
    "item_id": item_id,
    "see": (…),
})
```

— `api/main.py:153-159`, and again at `:190-191`. The pattern is established in the same
file. Every `400` returns a bare string instead. **Nothing needs inventing; the existing
convention needs extending to five call sites.**

## What §5.1 can therefore be written to say

The task's bound is to determine this, not to write it — the edit is human-only and Class 3.

**It can be written to say what it already says.** §5.1's rule is sound as pre-registered:
*"`error` (harness or quota failure) is never silently coerced to `fail`; it is reported
separately and excluded from the denominator only if `error_rate ≤ 2%`, otherwise the run is
void."* Note that clause — both v0.1 of the directive and the dossier quote this sentence
without the `≤ 2%` condition, and the condition is what makes a high harness-error rate void
a run rather than shrink it.

**What cannot be written is a rule the telemetry supports.** A wording that instructs the
evaluator to separate harness errors from agent failures is not implementable against this
API today except by prose prefix-matching. Saying so plainly is what this task is for:
**the required change is not in the eval-plan's words. It is in the Adjudicator.**

That relocation puts it with B4 in
[`c-1-dossier-filled-2026-09-02.md`](c-1-dossier-filled-2026-09-02.md) — the instrumentation
item — which the dossier already records as *"the largest item in this dossier"* and which
[`#177`](https://github.com/arslan-kursad/plumbline/issues/177) puts on F3's critical path.
This adds a second, much smaller item to the same external change: give the 400s a
structured `detail`, as the 409s already have.

## One thing noticed in passing

Rows 6 and 7 embed the raw model response in the error body — `{raw!r}`. Any harness that
logs a 400 body therefore logs whatever the model emitted. Recorded here because this
repository is public and its redaction boundary (ADR-0006) is about what reaches a stored
row; an eval harness that persists error bodies would be a second path in. It is a property
of the Adjudicator, not of plumbline, and it is named rather than acted on.

## Provenance

Every row cites a file and line read at `0779c04f` through the GitHub contents API on
2026-09-02. Files read: `src/aiqs/api/main.py` (265 lines), `src/aiqs/vlm/backend.py`,
`src/aiqs/graph/nodes.py`, `src/aiqs/api/schemas.py`. No line here is a measurement of
running behaviour.
