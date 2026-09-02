# Runbook — capturing a first-party agent emitter

**Lane C runs this.** Lane A built the harness and cannot run it: a capture needs a real
agent driven by a human, and the artefact lands outside the repository by design.

**Scope: `langgraph-python` (Anomaly Adjudicator) and `dotnet-agent` (Apartment Triage).**
Both are first-party, with no beta gate and no nested-authentication constraint —

> **Before you run this: the agents do not emit yet.** Read 2026-09-02, the Adjudicator
> (`aiqs-agent` @ `0779c04f`) carries **no OpenTelemetry instrumentation** — see
> [`c1-adjudicator-readout.md`](../evidence/c1-adjudicator-readout.md). A receiver with
> nothing pointed at it captures nothing. **Instrumenting the agents is F4 work**; this
> runbook is what you follow once they emit.


[`claude-code-capture.md`](claude-code-capture.md) owns the third, which is blocked on #10.

## Why this exists

`eval-plan.md` SC-1 row 1.2 requires *"≥1 fixture per dialect **captured from a real
emitter**, not hand-authored"*. Read 2026-09-02, no manifest in the corpus claims it:
three read `provenance: constructed` and `claude-code` reads
`derived-from-measured-evidence`. **Two thirds of that gap is reachable without waiting on
anything** — which is the whole reason this runbook is separate from the Claude Code one.

## 1. Start the receiver

```bash
scripts/capture/capture.sh langgraph-python
```

It prints the exporter environment, creates a dated output directory **outside the
repository**, and runs `otlp-file-receiver.py`, which persists request bodies byte for byte
without decoding them.

## 2. Point the agent at it, and change nothing else

```
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318
```

**Do not set `OTEL_SEMCONV_STABILITY_OPT_IN`.** Row 1.2 records the value *as emitted*, and
exporting it here would record this run's setting instead of the emitter's default. The
manifest says `unset` when it was not exported, and `unset` is a value rather than an
absence.

Drive **one** real interaction. The corpus needs a real shape, not volume.

## 3. Redact — and expect it to refuse the first time

```bash
python3 scripts/capture/redact.py <capture>.otlp.json \
  --rules normalization/redaction/v1/langgraph-python.yaml \
  --out testdata/fixtures/langgraph-python/happy-path/request.otlp.json
```

**There is no rule file for either agent yet, and there cannot be one before the capture.**
A denylist for an emitter nobody has observed is a statement about the list, not about the
data. So `redact.py` scans for key and value shapes that are personal in any dialect, and
**refuses**, naming everything it found.

That refusal is the deliverable of the first run. Write
`normalization/redaction/v1/<dialect>.yaml` from the named list, each key with its reason,
in the shape [`claude-code.yaml`](../../normalization/redaction/v1/claude-code.yaml) already
uses. Then re-run.

`--allow <key>` exists for a key you have reviewed and judged safe. Every use is a human
decision and its reason belongs in the manifest, not only in shell history.

**The raw capture never enters the repository.** Keep it where the script put it, and
delete it when the fixture is accepted.

## 4. Fill the manifest, then let the validator decide

```bash
python3 scripts/capture/manifest_validate.py testdata/fixtures/langgraph-python/manifest.yaml
```

Admissibility under row 1.2 needs `provenance: captured` **and** all of
`capture_origin`, `captured_on`, `otel_sdk_version`, `semconv_version_emitted`,
`otel_semconv_stability_opt_in`, `redacted_fields`, `redaction_rules`.

The validator reports the two failure kinds separately, because *"we have no capture"* and
*"we have a capture we cannot audit"* are different problems with different owners.

`scripts/capture/testdata/admissible/manifest.yaml` is a complete example. It is validator
test data, not a corpus fixture, and it says so.

## 5. What closes, and what does not

A captured fixture per agent moves SC-1 row 1.2 from **0 of 3 dialects** to **2 of 3**. It
does not close SC-1: the third dialect is `claude-code`, and `#10` owns it.

Record the outcome against `#42`. If a capture cannot be obtained, that is a finding about
the emitter and is written down as one — the failure mode this harness exists to prevent is
spending a human attempt and learning nothing.
