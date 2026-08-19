# Evidence — Claude Code OTLP capture (dialect markers)

**Status:** Evidence, not a fixture · **Date:** 2026-08-19 · **Work package:** F0 housekeeping
**Answers:** `docs/architecture.md` §10 open question 4 (OQ-4) · informs `docs/eval-plan.md`
Appendix A placeholder P11 · related issues: #10 (capture procedure), #11 (redaction boundary)

This file records what a real Claude Code emitter actually put on the wire, measured
against a local receiver. It is deliberately **not** a normalization fixture: the official
Claude Code fixture is born in F1 with its own golden-file tests and its own manifest
(`docs/eval-plan.md` SC-1 row 1.2). The raw capture is not in this repository and never
was — see §5.

---

## 1. Manifest

Every field is populated. `unknown` means measured-and-not-determinable, never omitted.

| Field | Value |
|---|---|
| Emitter | Claude Code |
| Emitter version | `2.1.197` and `2.1.229` — two builds captured, see §3 |
| Emitter version source | `service.version` resource attribute, cross-checked against `claude --version` |
| OTel SDK version | `OTel-OTLP-Exporter-JavaScript/0.208.0` — the exporter package version, taken from the request `User-Agent`. The SDK/API package versions are not on the wire: **unknown** |
| Instrumentation scope | `com.anthropic.claude_code.tracing`, version `1.0.0` |
| Semconv version actually emitted | **Undeclared.** No `schemaUrl` field is present at any level of the payload (0 occurrences across all captures), so the emitter declares no semantic-convention version. A small number of `gen_ai.*` keys are emitted (§4.4); the rest of the attribute set is emitter-private |
| `schema_url` value | **Absent** — the field is not emitted at all, which is distinct from being emitted empty |
| `OTEL_SEMCONV_STABILITY_OPT_IN` | **unset** — not exported into the capture environment, and not otherwise present |
| Capture date | 2026-08-19 (UTC) |
| Receiver | Local single-file HTTP sink on `127.0.0.1:4318`, `POST /v1/traces`, writing each request body verbatim to disk. Handles `Transfer-Encoding: chunked` (the exporter uses it) and gzip |
| Transport observed | OTLP/HTTP, `Content-Type: application/json`, chunked, uncompressed |
| Runs | 3 — identical marker shape in all three (§3) |

---

## 2. Capture procedure

Reproducible as follows. Paths are placeholders; nothing from this procedure is committed.

1. Start a local OTLP/HTTP receiver on `127.0.0.1:4318` that appends every received
   `POST /v1/traces` body to a file outside the repository. A debug-exporter collector
   config is equally sufficient; the requirement is only that the received
   `ExportTraceServiceRequest` is preserved verbatim.
2. Run Claude Code with span export enabled, in a throwaway working directory:

   ```
   CLAUDE_CODE_ENABLE_TELEMETRY=1 \
   CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1 \
   OTEL_TRACES_EXPORTER=otlp \
   OTEL_EXPORTER_OTLP_PROTOCOL=http/json \
   OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/json \
   OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318 \
   OTEL_TRACES_EXPORT_INTERVAL=1000 \
   claude -p '<prompt>' --allowedTools 'Write' 'Read' 'Bash(echo:*)'
   ```

3. Redact (§5), then extract the marker inventory (§4).

**Flag names verified at capture time** against the Claude Code monitoring documentation:
`CLAUDE_CODE_ENABLE_TELEMETRY`, `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA` and
`OTEL_TRACES_EXPORTER` are all three required for spans; the beta gate confirms the
finding recorded in issue #10 §1 and holds at the versions captured here.

`http/json` was chosen over `http/protobuf` so that the receiver needs no protobuf
toolchain. This is an encoding of the same `ExportTraceServiceRequest` message; it does
not change which attributes the emitter produces. A protobuf capture is the correct choice
for the F1 fixture, where the bytes themselves are the artefact.

**Attribute-suppression flags were deliberately left at their defaults**
(`OTEL_METRICS_INCLUDE_SESSION_ID`, `OTEL_METRICS_INCLUDE_ACCOUNT_UUID`, and the
content-logging gates in §5.2). Issue #10 requires the F1 *fixture* procedure to turn off
what can be turned off; this capture is evidence about the **default** emission surface,
which is what issue #11 needs in order to decide the redaction boundary. Suppressing
attributes here would have hidden the exposure being documented.

---

## 3. Coverage — what this capture does and does not observe

Stated explicitly, because evidence that overstates its reach is worse than none.

**Observed.** `claude_code.interaction` (root) and `claude_code.llm_request` (child),
resource attribute set, instrumentation scope, span attributes on both span types, one
span event, status shape, absence of `schemaUrl`.

**Not observed.**

- `claude_code.tool`, `claude_code.tool.execution`, `claude_code.tool.blocked_on_user`
  and `claude_code.hook` spans.
- All documented `claude_code.*` **events** (`user_prompt`, `assistant_response`,
  `tool_result`, `tool_decision`, `api_request`, …) — see §4.5.
- `workspace.host_paths`, which the documentation places on events. Because no event other
  than `gen_ai.request.attempt` was produced, this attribute never appeared. Its exposure
  is therefore documented-but-unmeasured, and issue #11 must continue to treat it as
  present until a capture shows otherwise.

**Why.** All three runs were non-interactive (`claude -p`) and every LLM request failed
authentication: the captured session ran as a child process of an environment whose
credential is held by the host application and is not resolvable from a plain nested CLI
(`Could not resolve authentication method …` on the CLI on `PATH`; `OAuth session expired
and could not be refreshed` on the host-bundled build). The agent loop therefore never
reached a tool call. Extending coverage requires a capture from an interactively
authenticated Claude Code session; the procedure in §2 is unchanged.

**What this costs.** OQ-4 asks for the resource/scope markers that dialect detection keys
on. Those are fully observed and, per the two-build comparison below, stable. The
unobserved material affects the *mapping* (which span and event types exist, and their
attribute sets) and the PII inventory for events — F1 work, not OQ-4.

**Two-build cross-check.** Builds `2.1.197` and `2.1.229` emitted the identical scope name
and scope version `1.0.0`, and the identical resource attribute key set. `service.version`
differed between them, as expected.

---

## 4. Redacted marker inventory

### 4.1 Resource attributes — the complete set, at defaults

| Key | Type | Value |
|---|---|---|
| `service.name` | string | `claude-code` |
| `service.version` | string | emitter version (`2.1.197` / `2.1.229`) |
| `os.type` | string | `darwin` |
| `os.version` | string | host kernel version |
| `host.arch` | string | `amd64` |

`droppedAttributesCount: 0`. No `schemaUrl`. **No identity attributes at resource level** —
see §6 and §7.

### 4.2 Instrumentation scope

```
name:    com.anthropic.claude_code.tracing
version: 1.0.0
```

One scope only. No `schemaUrl` on the scope either.

### 4.3 Span names observed

| Span | Role | `span.type` attribute |
|---|---|---|
| `claude_code.interaction` | root, one per user prompt | `interaction` |
| `claude_code.llm_request` | child of the interaction | `llm_request` |

`kind: 1` (internal) on both. Every span carries `span.type`, repeating the name minus the
`claude_code.` prefix.

### 4.4 Span attributes

Identity block, present on **every** span observed:

```
user.id            = <REDACTED:user.id>
user.email         = <REDACTED:user.email>
organization.id    = <REDACTED:organization.id>
user.account_uuid  = <REDACTED:user.account_uuid>
user.account_id    = <REDACTED:user.account_id>
session.id         = <REDACTED:session.id>
terminal.type      = non-interactive
```

`claude_code.interaction` adds:

```
user_prompt             = <REDACTED>      # the emitter's own placeholder, see §5.2
user_prompt_length      = 133             # true length of the suppressed text
interaction.sequence    = 1
interaction.duration_ms = 216
```

`claude_code.llm_request` adds:

```
gen_ai.system        = anthropic
gen_ai.request.model = <model id>
model                = <model id>         # duplicate of gen_ai.request.model, bare key
llm_request.context  = interaction
speed                = normal
duration_ms          = 9
success              = false
error                = <SDK error string>
attempt              = 1
client_request_id    = <REDACTED:client_request_id>
```

Only `gen_ai.system` and `gen_ai.request.model` are semconv-shaped. Everything else is a
bare, un-namespaced key (`model`, `speed`, `success`, `error`, `attempt`, `duration_ms`) or
an emitter-private namespace (`span.type`, `llm_request.*`, `interaction.*`, `user_prompt*`).

### 4.5 Events

One event observed:

```
name: gen_ai.request.attempt
attrs: attempt, client_request_id
```

Note that this name appears in neither the documented event list nor issue #10 — the
documented events are all `claude_code.*`. None of those was produced by these runs (§3).

### 4.6 Status

`status.code: 0` on the interaction; `status.code: 2` with a `message` on the failed
`llm_request` spans. `droppedEventsCount`, `droppedLinksCount`, `droppedAttributesCount`
all `0`; `links: []`; `flags: 257`.

---

## 5. Redaction record

### 5.1 What this project redacted

Applied to the capture before anything reached git. Shape is preserved; every removed value
is replaced by a `<REDACTED:field>` marker so the key, its position and its type stay
visible.

| Redacted | Reason |
|---|---|
| `user.id`, `user.email`, `user.account_uuid`, `user.account_id` | personal data |
| `organization.id` | account identifier |
| `session.id`, `client_request_id` | session-correlatable identifiers |
| `traceId`, `spanId`, `parentSpanId` | session-correlatable identifiers |
| absolute filesystem paths — home directories, temp roots | host paths; none in fact occurred |
| `workspace.host_paths` | in the redaction rule set, though never observed (§3) |

Not redacted, because they are neither personal nor host-identifying and are the evidence
itself: `service.*`, `os.*`, `host.arch`, `span.type`, model ids, `gen_ai.*`, timings,
counters, and the SDK error string.

**The raw capture is not in this repository.** It was written to a session scratchpad
outside the working tree, was never added to the index, and is not pasted into the pull
request or into any issue. Only this file's redacted inventory left the scratchpad.

### 5.2 What the emitter already redacts by itself

Measured, and it changes the risk picture: `user_prompt` arrived with the literal value
`<REDACTED>` while `user_prompt_length` carried the true length (133). Prompt text is
therefore **not** in the default emission — the emitter gates it behind
`OTEL_LOG_USER_PROMPTS`, with `OTEL_LOG_ASSISTANT_RESPONSES`, `OTEL_LOG_TOOL_DETAILS`,
`OTEL_LOG_TOOL_CONTENT` and `OTEL_LOG_RAW_API_BODIES` gating responses, tool parameters,
tool input/output and raw API bodies respectively. All are disabled by default.

Two consequences. The `<REDACTED>` markers in §4.4 come from *two different sources* — the
emitter's own placeholder and this project's redaction step — and a fixture manifest must
not conflate them. And the identity attributes are the part that no flag turns off:
`user.id` and `user.email` are documented as always included, and were.

---

## 6. Detection implications

What dialect detection can safely key on, in decreasing order of confidence:

1. **`com.anthropic.claude_code.tracing` (instrumentation scope name) — the primary key.**
   Vendor-namespaced, identical across two emitter builds, and versioned independently of
   the application (`1.0.0` while `service.version` moved). This is the answer to OQ-4:
   detection keys on the scope name, and records the scope version alongside it.
2. **`service.name = claude-code` (resource) — corroborating, not primary.** It is a
   resource attribute an operator can override via `OTEL_RESOURCE_ATTRIBUTES`, so it is a
   weaker signal than the scope name the instrumentation sets itself.
3. **`span.type` present on every span, plus `claude_code.` span-name prefix** —
   confirmatory at span level; useful for the unknown-dialect fallback test
   (`docs/eval-plan.md` SC-1 row 1.5) because a payload with the prefix but an unregistered
   scope is exactly that test's input.
4. **Do not key on `service.version`** (moves every release) or on `gen_ai.*` presence
   (too few keys, and shared with every other GenAI emitter).

Two facts the F1 mapping must absorb: the dialect **declares no `schemaUrl`**, so its
emitted convention version cannot be read off the payload and the manifest field is
`undeclared` by measurement rather than by omission; and the identity attributes sit on
**span** attributes, not on the resource, which is where §7 and issue #11 meet.

---

## 7. Divergences from the design-layer assumptions — raised, not resolved

Recorded here because `docs/` is the source of truth and these are measurements, not
decisions. None of them is resolved in this file.

1. **Identity attributes are span-level, not resource-level.** Issues #10 and #11, and the
   monitoring documentation's own table, describe `user.id`, `user.email`,
   `organization.id`, `user.account_uuid`, `user.account_id` and `session.id` as *resource*
   attributes. In this capture the resource carries only `service.*`, `os.*` and
   `host.arch`; the identity block is repeated on **every span**. This matters directly to
   issue #11: a resource-level attribute denylist would not remove any of it, and a
   key-level drop would have to run per span, on every span.
2. **The dialect does emit `gen_ai.*`.** Issue #10 §2 states it does not.
   `gen_ai.system = anthropic` and `gen_ai.request.model` are present on
   `claude_code.llm_request`, and the one observed event is named `gen_ai.request.attempt`.
   The substance of #10 §2 survives — the dialect is overwhelmingly emitter-private and
   cannot be normalized by assuming semconv shapes — but the blanket claim does not.
3. **Prompt and response content is gated off by default** (§5.2). Issue #11's premise
   that the emission carries PII by default holds for identity attributes only.
4. **The documented span and event lists are wider than issue #10 records** — the
   documentation now also lists `claude_code.tool.execution` and
   `claude_code.tool.blocked_on_user` spans, and fifteen `claude_code.*` events. Neither
   list was exercised by these runs (§3).

---

## Changelog

**v0.1 — 2026-08-19** — first capture. Answers OQ-4 on scope markers; tool/hook spans and
event-level attributes unobserved (§3).
