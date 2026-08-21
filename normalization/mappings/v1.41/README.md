# Normalization mappings — GenAI semconv v1.41

One YAML per emitter dialect, mapping what the emitter actually sends to the typed
`gen_ai_*` columns of the `spans` table. The directory is versioned by the **semconv
pin**: moving the pin creates `v1.42/` rather than editing here, so the mappings that
produced historical rows stay readable next to those rows (ADR-0003 §4).

These files are embedded into the worker binary at build time. There is no runtime
configuration store, and a mapping change is a code change: branch, pull request, golden
tests in the same commit (ADR-0003 §1, §3). What that buys is attribution — image tag →
binary → embedded mapping → rows — and it is why "which mapping produced this row" is
answerable from a commit hash rather than from a running revision.

## File shape

```yaml
dialect: langgraph-python          # the value that lands in the source_dialect column
semconv_version: "1.41.0"

detection:
  scope_names:                     # primary key: the instrumentation sets it itself
    - openinference.instrumentation.langchain
  resource_markers:                # corroborating only; an operator can override these
    telemetry.sdk.language: [python]

columns:
  - column: gen_ai_request_model   # must exist in GenAiColumns
    semconv: gen_ai.request.model  # must be defined by the vendored registry
    type: string                   # string | int | double
    rules:                         # precedence order: first rule that yields a value wins
      - from: gen_ai.request.model
      - from: llm.model_name
```

### Rules

A rule fills a column one of three ways.

| Form | Meaning |
| --- | --- |
| `from: <attribute>` | Copy the span attribute's value, coerced to the column's type |
| `from: <attribute>` + `map:` | Copy through a value translation; a value absent from the map yields **nothing** |
| `from_span_name:` | A constant chosen by the span's name, for dialects that state a span's role only there |

**Order is the precedence.** The first rule that produces a value wins and the rest are
not consulted, which is what lets a mapping put a current semconv name above a deprecated
fallback and stop rewriting the moment the emitter upgrades.

**An unmapped value produces null, not a pass-through.** Handing an emitter's own vocabulary
straight into a column the eval engine reads as a v1.41 enum member would be worse than a
null: it looks conformant and is not.

### Type coercion

`string` accepts any scalar. `int` and `double` accept the matching OTLP value case, and
an int is accepted for a double column because a whole-number temperature is not an error.
Anything else leaves the column null and adds a `coercion_failed` note that the worker
logs — the original value is still in the lossless `attributes` JSON, so nothing is lost,
only untyped.

## What the mappings are checked against

`SemconvRegistryTests` in `worker/Plumbline.Normalization.Tests/` fails when:

- a column's `semconv` target is not defined in `normalization/semconv/v1.41/` and is not
  in that directory's `external-allowlist.yaml` — the executable form of
  `docs/eval-plan.md` SC-1 row 1.4;
- a `from:` in the `gen_ai.` namespace is neither a current nor a deprecated v1.41
  attribute — a typo wearing a semconv name;
- a column name is not in the typed column set, or disagrees with it about the attribute
  or the type;
- two dialects claim the same instrumentation scope name, which would make detection
  ambiguous;
- a dialect has a mapping but no fixtures, or fixtures but no mapping.

## Losses that are decided rather than accidental

Stated here because a reader who finds a null column deserves to know which kind of null
it is.

- **Timestamps lose their nanosecond remainder.** BigQuery `TIMESTAMP` holds
  microseconds; OTLP is nanoseconds. The last three digits are floored away and kept
  nowhere. A fixture ends on a sub-microsecond boundary so this appears in a golden file
  rather than only in this paragraph.
- **Array-valued GenAI attributes have no typed column.** `gen_ai.response.finish_reasons`
  is the one this project's dialects emit; it stays in the lossless attributes.
- **Embedded JSON is not parsed.** `llm.invocation_parameters` carries temperature and
  max_tokens inside a JSON *string*. A mapping that reaches inside an opaque value is no
  longer a mapping table, so those columns stay null. Extracting them is a schema change
  to this format, not a value fix.
- **claude-code has no token counts.** The emitter sends none at the captured version.
  That is a measured property of the emitter, not a gap in its mapping file.

## Unknown dialects

There is no `unknown.yaml`. The generic mapping is generated in code from the typed column
set, filling each column from the v1.41 attribute it stands for, so it cannot drift from
the column set it is generic over. An unrecognised payload is normalized with it,
`source_dialect` is `unknown`, a note is raised, and nothing is dropped (architecture §5,
ADR-0003 §6).
