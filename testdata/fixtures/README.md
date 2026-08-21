# Fixture corpus

Raw OTLP payloads and the normalized rows they must produce. These files are the
enforcement mechanism of ADR-0001 §3.1: the project does not store raw protobuf, so
fidelity of raw → normalized is a *tested* property, and this is what tests it.

## Layout

```
testdata/fixtures/<dialect>/
  manifest.yaml                  provenance, emitter, semconv version emitted, redactions
  <case>/
    request.otlp.json            human-readable twin — the authored source
    request.pb                   binary ExportTraceServiceRequest — generated from the twin
    expected-rows.json           the rows normalization must produce
```

`<dialect>` is the value that lands in the `source_dialect` column, so the fallback
directory is `unknown` rather than a longer description of it.

## The twin is the source; the binary is derived

`request.pb` is generated from `request.otlp.json` by `worker/Plumbline.Fixtures`, never
edited by hand. That ordering is what keeps a fixture reviewable — a diff on the binary
says nothing, a diff on the twin says what changed — and a test asserts the two still
correspond, so a hand-edited binary fails rather than drifting.

```bash
dotnet run --project worker/Plumbline.Fixtures            # regenerate
dotnet run --project worker/Plumbline.Fixtures -- --check # verify, exit 1 on drift
```

The twins are **OTLP/JSON**: trace and span ids in lowercase hex, exactly as an
OTLP/HTTP JSON exporter would send them. Canonical protobuf JSON would require base64 in
those fields; the generator re-encodes them so the authored form stays readable.

## Cases

Every dialect carries three, and each answers a different question.

| Case | Question |
| --- | --- |
| `happy-path` | Does a multi-span trace with GenAI attributes normalize to exactly these rows? |
| `unmapped-attributes` | Do attributes the mapping does not know survive verbatim in the lossless `attributes` JSON? |
| `poison` | Does an undeserializable payload reach the DLQ instead of being dropped quietly? |

`poison/request.pb` is the first 96 bytes of that dialect's happy-path payload,
truncated inside a length-delimited field. It has no twin and no expected rows, because
it must never produce a row. A test asserts it genuinely fails to parse: truncation
landing on a field boundary would yield a valid shorter message and would test nothing.

The `unknown` directory has only `happy-path` — it is the detection fallback, not an
emitter, so there is no second dialect-specific poison payload worth carrying.

## Provenance is stated, not implied

No fixture in this corpus was promoted from bytes a real emitter sent. Each manifest says
which class it belongs to and what that costs:

| Dialect | Provenance | What is not proven |
| --- | --- | --- |
| `langgraph-python` | `constructed` | Detection fidelity — the scope marker comes from documentation |
| `dotnet-agent` | `constructed` | Detection fidelity — same |
| `claude-code` | `derived-from-measured-evidence` | Tool and hook spans, and every event type but one, were never observed |
| `unknown` | `constructed` | Nothing; it is synthetic by design |

Golden tests over constructed fixtures are valid **normalization contract** tests. They
are not evidence that a real emitter is detected correctly. F4 (dogfooding) re-validates
against real captures; for claude-code, `docs/runbooks/claude-code-capture.md` is ready
to run now.

## Content rules

The repository is public. Every value in every fixture is synthetic: no real user ids,
no real email addresses, no host paths, no API keys, no customer data. The claude-code
fixtures use `example.invalid` and all-zero identifiers precisely because they imitate an
emitter that really does carry personal data.
