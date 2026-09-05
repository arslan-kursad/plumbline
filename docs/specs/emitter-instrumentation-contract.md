# Emitter instrumentation contract — what each source must put on the wire

**Version:** 0.1 · **Status:** Proposed · **Date:** 2026-09-05 · **Lane:** A authored;
executed outside this repository (D5: the lane is the strongest permission the work needs,
and a write to another repository is outside every plumbline lane)
**Charter:** `#177` disposition (a) + (c); `#183`; ADR-0010 D6-3; plan
[`completion-plan.md`](completion-plan.md) CP-2 to CP-5
**Read against:** `aiqs-agent @ 0779c04f` and `apartment-triage @ 15c1d6e`, both checked
out on this host; `normalization/mappings/v1.41/`; [`e1-predicate-readout.md`](../evidence/e1-predicate-readout.md)

> **What this is.** The minimum each of the three emitters must emit so that (1) the worker
> detects its dialect, (2) every conjunct of E1 has an input on the trace, (3) nothing
> personal reaches a public repository or a seven-day dead-letter queue, and (4) a capture
> can become an admissible fixture under `eval-plan.md` SC-1 row 1.2.
>
> **What it is not.** Not the F3 spec, not the rule bodies, not a mapping edit. The
> plumbline-side changes it implies are listed in §6 and land as plan W2-2 and W2-3, from
> the captured bytes rather than from this text.

---

## 1. Common to every emitter

### 1.1 Transport

OTLP/HTTP with protobuf encoding, to the collector's `/v1/traces`. The cloud collector is
HTTP-only through F4 (plan CP-6), so gRPC is not an option and must not be the SDK default
left in place.

```
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_ENDPOINT=<collector base URL>      # capture: http://127.0.0.1:4318
OTEL_EXPORTER_OTLP_HEADERS=x-plumbline-api-key=<key>   # cloud only; the key is Lane C custody
```

The cloud base URL is read from `gcloud run services describe collector
--format='value(status.url)'` and is never written into a repository file. Export is **off
by default** in both agents: it turns on only when `OTEL_TRACES_EXPORTER=otlp` is set.

### 1.2 Resource attributes

| Attribute | Value | Set by |
|---|---|---|
| `service.name` | `anomaly-adjudicator` / `apartment-triage` (Claude Code sets its own) | the agent |
| `service.version` | the agent's git commit SHA | the agent |
| `deployment.environment` | `local` · `production` · `eval` | the agent, from its environment |
| `telemetry.sdk.language` | `python` / `dotnet` | the SDK, automatically — it is the mapping's corroborating marker |
| `synthetic` | `true` | **replay only**, stamped by `scripts/e2e/replay.py` at send time, never by the agent |
| `plumbline.e2e_run_id`, `plumbline.variant_id`, `plumbline.dataset_id`, `plumbline.plan_sha256` | run identity | replay only, same |

Production traffic therefore carries no `synthetic` attribute, lands with `synthetic =
false`, and counts in `spans_real`; every replayed or load-generated row is walled off.

### 1.3 The content gate

`PLUMBLINE_CAPTURE_CONTENT=1` turns **content attributes** on; unset or `0` leaves them
off. A content attribute is any attribute whose value is user-provided text, a file path, an
image, or a model's free text. Production never sets the variable. Eval replay sets it,
because the eval corpora — MVTec images and the 48 team-authored Triage cases — contain no
real person. For the Adjudicator the gate also drives OpenInference's own switches:
`OPENINFERENCE_HIDE_INPUTS` and `OPENINFERENCE_HIDE_OUTPUTS` are the inverse of it.

### 1.4 Never on the wire

Resident identifiers, phone numbers, channel user ids, emails, API keys, image bytes
(only MIME type and byte length), and host paths outside the content gate. This is a
property of the emitter, not of plumbline's redaction stage: ADR-0006's stage runs after
deserialization, and bytes it never sees still transit Pub/Sub and rest in `traces-dlq`.

### 1.5 Naming

`gen_ai.*` names are the pinned v1.41 names where the emitter writes them itself.
Emitter-private attributes are namespaced — `aiqs.*`, `triage.*` — and land in the
lossless `attributes` JSON under `span`, where the eval engine reads them by JSON path. No
new typed column is required by this contract; adding one is a mapping-schema change and
is decided in the F3 spec.

### 1.6 Timestamps

Nanosecond OTLP timestamps as the SDK produces them. Truncation to microseconds is the
worker's (ADR-0007 D7) and needs nothing from the emitter.

### 1.7 Errors, and the denominator rule

A failed item ends its span with status `ERROR` and `error.type`, plus one attribute the
eval engine reads to apply `eval-plan.md` §5.1's split: `aiqs.error.kind` ∈ {`harness`,
`agent`} for the Adjudicator, `triage.error.kind` = the `AgentErrorKind` name for Triage.
A status code is never the discriminator — T3-01 measured that it cannot be.

---

## 2. Anomaly Adjudicator (`aiqs-agent`, Python, LangGraph + FastAPI)

### 2.1 Packages and wiring

Added with `uv add`: `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`,
`openinference-instrumentation-langchain`, `openinference-instrumentation-anthropic`.
`langfuse` already pulls the OpenTelemetry API transitively, so nothing new caps `protobuf`
further than it is capped today. One new module, `src/aiqs/telemetry.py`, builds the tracer
provider, the OTLP exporter and the two instrumentors; `aiqs-serve` and `aiqs-graph` call it
once at start-up when `OTEL_TRACES_EXPORTER=otlp`, and do nothing otherwise. No FastAPI
instrumentation: the request span below is the trace root, so the HTTP layer adds no
fourth scope the mapping would have to know about.

### 2.2 Scopes on the wire

| Scope name | Emits | Maps to |
|---|---|---|
| `openinference.instrumentation.langchain` | the graph run and its seven nodes as `CHAIN` spans, with `input.value` / `output.value` behind the content gate | `langgraph-python` — already the mapping's primary key |
| `openinference.instrumentation.anthropic` | the VLM call as an `LLM` span: `llm.model_name`, `llm.provider`, `llm.token_count.prompt`, `llm.token_count.completion`, `llm.invocation_parameters` | `langgraph-python` — to be added to `scope_names` (plan W2-2) |
| `aiqs.adjudicator` | the request span and the output attributes (§2.4) | `langgraph-python` — to be added |

Whether the first scope emits `openinference.span.kind` with exactly the six values the
mapping maps is **measured at the first capture**; a difference is `#42`'s finding and is
recorded, not adjusted away.

### 2.3 Span tree, one adjudication

```
aiqs.adjudicate                      (root; scope aiqs.adjudicator; one per POST /adjudicate)
└── LangGraph                        (CHAIN; scope openinference…langchain)
    ├── ingest · calibrate · cost_policy            (CHAIN each)
    ├── vlm_second_look                             (CHAIN)
    │   └── Messages / claude-sonnet-4-6            (LLM; scope openinference…anthropic)
    ├── vlm_abstain_rule · human_interrupt          (CHAIN)
    └── finalize                                    (CHAIN)
```

`POST /human-verdict/{item_id}` opens its own root, `aiqs.human_verdict`, carrying
`aiqs.item_id` so the two traces join on it. The Adjudicator calls no tools, so R4's
tool-call count is zero by construction and its loop-detection input is not applicable;
the contract states this rather than emitting an empty list.

### 2.4 Attributes on `aiqs.adjudicate`

Set in `api/main.py` after `_to_response`, from the response object — not from the graph
state, so what the trace carries is what the caller received.

| Attribute | Type | Always | Source |
|---|---|---|---|
| `aiqs.item_id` | string | yes | request |
| `aiqs.category`, `aiqs.run_id` | string | yes | `artifact.category`, `artifact.run_id` — P6's stratification key |
| `aiqs.decision`, `aiqs.resolved_by`, `aiqs.tier1_decision` | string | yes (null-able) | response |
| `aiqs.pending_human`, `aiqs.vlm.fired` | bool | yes | response |
| `aiqs.calibrated_p`, `aiqs.applied_target_prevalence`, `aiqs.lam` | double | yes | response / request |
| `aiqs.vlm.verdict` | string | when fired | response |
| `aiqs.vlm.confidence` | double | when fired | response |
| `aiqs.vlm.tokens_in`, `aiqs.vlm.tokens_out` | int | when fired | response |
| `aiqs.input.anomaly_score` | double | yes | request — a number, not content |
| `aiqs.input.has_image` | bool | yes | request |
| `aiqs.error.kind` | `harness` · `agent` | on error | §1.7; T3-01 paths 1–4 and 8 are `harness`, 5–7 `agent` |
| `aiqs.error.detail` | string | on error, **content-gated** | the 400 body's `detail` |
| `aiqs.vlm.reasoning` | string | **content-gated** | response |
| `aiqs.input.image_path` | string | **content-gated** | request — a host path |

The split in `aiqs.error.kind` is set where the exceptions are already distinguishable —
`resolve_image_path` and the `ingest` guard raise the harness cases, the `except ValueError`
around `graph.invoke` catches the agent ones — so it needs no change to the API's status
codes, which is the "in the harness or the emitter" relocation T3-01 anticipated.

### 2.5 Where each E1 conjunct reads

| Conjunct | Input | Where it lands |
|---|---|---|
| R1 root present, no orphans, terminal status | span structure | `parent_span_id`, `status_code` columns |
| R1 ≥ 1 `gen_ai` operation span | `openinference.span.kind = LLM` on the VLM span | `gen_ai_operation_name = chat` via the mapping |
| R2 names in registry, required attributes | the LLM span's `llm.*` | `gen_ai_request_model`, `gen_ai_usage_*` columns |
| R3 output parses, fields, enums | §2.4 | `JSON_VALUE(attributes, '$.span."aiqs.decision"')` and siblings |
| R4 token and latency budgets | LLM span, timestamps | columns |
| R5 (package P4) | §2.4 plus the dataset label joined on `aiqs.item_id` | `attributes`, dataset |

### 2.6 Redaction on the plumbline side

`normalization/redaction/v1/langgraph-python.yaml`, written from the first capture's
refusal list (plan W2-3), is expected to cover at least `aiqs.input.image_path`,
`aiqs.error.detail`, `input.value` and `output.value`. If a capture with the gate off
carries none of them, the file records that and covers them anyway — issue `#11`'s rule.

---

## 3. Apartment Triage (`apartment-triage`, .NET 8)

### 3.1 Packages and wiring

`OpenTelemetry`, `OpenTelemetry.Extensions.Hosting`,
`OpenTelemetry.Exporter.OpenTelemetryProtocol`. No ASP.NET Core instrumentation: webhook
spans would carry channel identifiers and would push the trace root outside the agent
pipeline. Composition root: `src/ApartmentTriage.Web/Program.cs`, after `UseSerilog`,
`AddOpenTelemetry().WithTracing(t => t.AddSource("ApartmentTriage.Agents").AddOtlpExporter())`,
registered only when `OTEL_TRACES_EXPORTER=otlp`. One static `ActivitySource` in
`src/ApartmentTriage.Application/Agents/AgentTelemetry.cs`, named
`ApartmentTriage.Agents`, versioned with the assembly's informational version.

### 3.2 Scope, and the mapping change it forces

The scope is **`ApartmentTriage.Agents`**. The constructed fixture assumed
`Experimental.Microsoft.Extensions.AI`, a framework the agent rejects by name (C-2 method
4); that name is retired from `dotnet-agent.yaml`'s `detection.scope_names` in plan W2-2 and
this one replaces it. The agent emits the pinned v1.41 names directly, so the fixture's
"version drift" story (`gen_ai.system`, schema 1.28.0) is expected to be falsified by the
first capture — recorded as a finding under `#42`, which is what row 1.2 exists for.

### 3.3 Span tree, one incoming message

```
invoke_workflow triage                  (root; TriageOrchestrator, one per message)
├── invoke_agent classifier             (AgentBase.ExecuteAsync)
│   └── chat claude-haiku-4-5           (AnthropicClient.CompleteAsync)
├── invoke_agent enricher
│   └── chat …
└── invoke_agent router
    └── chat …                          (present when the router calls the model)
```

| Span | Attributes |
|---|---|
| root | `gen_ai.operation.name = invoke_workflow`; `gen_ai.conversation.id` = the ticket id (a Guid, not a person); `triage.escalated_to_sonnet` bool from `TriageResult` |
| `invoke_agent <name>` | `gen_ai.operation.name = invoke_agent`; `gen_ai.agent.name`; `gen_ai.agent.id = AgentId` |
| `chat <model>` | `gen_ai.operation.name = chat`; `gen_ai.provider.name = anthropic`; `gen_ai.request.model`; `gen_ai.request.max_tokens`; `gen_ai.response.model`; `gen_ai.response.id`; `gen_ai.usage.input_tokens`; `gen_ai.usage.output_tokens`; `gen_ai.response.finish_reasons` (array — stays lossless, no column) |

Token counts come from the Anthropic response's usage block inside `AnthropicClient`, which
is the one seam plan CP-4 names; `UsageRecordingAnthropicClient` already reads it for cost
accounting, so the number exists.

### 3.4 Attributes on `invoke_agent classifier`

| Attribute | Type | Always |
|---|---|---|
| `triage.category`, `triage.severity`, `triage.category_confidence`, `triage.emergency_confidence` | string, wire casing | yes |
| `triage.is_emergency` | bool | yes |
| `triage.ambiguity_reasons` | string array, wire casing | yes |
| `triage.secondary_issue_count` | int | yes |
| `triage.input.channel_type` | string | yes |
| `triage.input.emergency_suspected`, `triage.input.has_image` | bool | yes |
| `triage.input.text_length` | int | yes |
| `triage.error.kind` | `Transient` · `Semantic` · `Escalation` · `Cancelled` | on failure |
| `triage.rationale`, `triage.location_hint` | string | **content-gated** |
| `triage.input.raw_text`, `triage.input.matched_phrases` | string / array | **content-gated** |

`ResidentId`, phone numbers and chat user ids are never attributes, gated or not.

### 3.5 Where each E1 conjunct reads

R1 and R2 from the `chat` span's `gen_ai.*` names through the existing `dotnet-agent`
columns; R3 and R5 from §3.4 by JSON path; R4's tool-call count from the `invoke_agent`
spans (the orchestrator's agents are the "tools"), token and latency budgets from columns.

### 3.6 Redaction on the plumbline side

`normalization/redaction/v1/dotnet-agent.yaml` (plan W2-3), covering at least
`triage.input.raw_text`, `triage.input.matched_phrases`, `triage.rationale` and
`triage.location_hint`, because a replay corpus captured from production would carry them
if the gate were ever on there.

---

## 4. Claude Code

The environment block in [`claude-code-capture.md`](../runbooks/claude-code-capture.md) §4.3,
with the endpoint and header lines from §1.1 for the cloud. `OTEL_LOG_USER_PROMPTS`
stays unset, so prompt text arrives as the emitter's own placeholder. The identity block on
every span is removed by the existing redaction rules (`normalization/redaction/v1/claude-code.yaml`).
Claude Code is an SC-1 and SC-2 source only; it is not a gate subject
(`eval-plan.md` §7.1) and this contract adds nothing to it.

---

## 5. Acceptance, per emitter

An emitter satisfies this contract when all five hold, each recorded with its date:

| | Check | How |
|---|---|---|
| (a) | A local capture exists and is admissible | `scripts/capture/capture.sh <dialect>`, one real interaction, then `manifest_validate.py` admits the manifest with `provenance: captured` |
| (b) | The worker detects the dialect | a golden test on the captured fixture asserts `source_dialect` is the dialect and `DetectionBasis.ScopeName` |
| (c) | Every E1 input is on the trace | §2.5 / §3.5 read against the captured rows; the output attribute is non-null on every non-error item |
| (d) | The redaction gate passes and nothing personal is present | `redact.py` accepts the capture with the dialect's rule file; a grep over the capture for the never-on-the-wire classes finds nothing |
| (e) | Cloud ingest proven | one replay through the deployed collector lands in `spans_deduped` under its run id with the right `source_dialect`; the `attributes` JSON read back equals the fixture's (this is F3E-01c, plan W2-7) |

**The D6-1 evaluation on 2026-09-12** (plan W1-7) asks exactly (a)–(c) of the Adjudicator
and records the answer either way.

---

## 6. What changes in plumbline because of this contract

| Change | Plan task |
|---|---|
| `langgraph-python.yaml` `detection.scope_names` gains `openinference.instrumentation.anthropic` and `aiqs.adjudicator` | W2-2 |
| `dotnet-agent.yaml` `detection.scope_names` becomes `ApartmentTriage.Agents` | W2-2 |
| Fixtures and expected rows regenerated from captures; manifests flip to `captured`; every golden diff recorded | W2-2, `#42` |
| Two redaction rule files | W2-3 |
| `scripts/e2e/replay.py` stamps §1.2's replay-only resource attributes | W2-6 |

Nothing in this contract requires a new typed column, a DDL change or a Terraform change.

---

## 7. Sizing, and the residual uncertainty

| Emitter | Estimate | The uncertain part |
|---|---|---|
| Adjudicator | ~6 h | whether the LangChain instrumentor's `span.kind` values and scope name match the mapping — measured at capture |
| Triage | ~6 h | reading usage from the Anthropic response inside `AnthropicClient`; the enricher and router spans if their model calls differ in shape |
| Claude Code | ~10 min of maintainer time | tool and hook spans, unobserved until the run |

The estimates are the first written for this work (dossier B4 recorded it as
`UNKNOWN — not decided`) and are recorded so they can be wrong in public.

## 8. Provenance

Read 2026-09-05: `src/aiqs/api/main.py`, `graph/build.py`, `graph/nodes.py`,
`vlm/backend.py`, `pyproject.toml` in `aiqs-agent @ 0779c04f`; `Program.cs`,
`ClassifierAgent.cs`, the five `.csproj` files and the `Anthropic/` directory in
`apartment-triage @ 15c1d6e`; `normalization/mappings/v1.41/*.yaml`,
`worker/Plumbline.Normalization/Detection/DialectDetector.cs`, the three fixture manifests
and the E1 readout in this repository at `main @ b7b3cf9`.
