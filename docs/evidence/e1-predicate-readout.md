# E1 — what each conjunct consumes, and what the langgraph-python mapping can produce

**Read:** 2026-09-03 · **Lane:** A · **Repo:** `main`, SHA recorded at execution
**Task:** F3 Unblock dispatch U-02
**Sources:** [`eval-plan.md`](../eval-plan.md) §8.1;
[`normalization/mappings/v1.41/langgraph-python.yaml`](../../normalization/mappings/v1.41/langgraph-python.yaml);
[`analytics/sql/001_spans_table.sql`](../../analytics/sql/001_spans_table.sql)

---

## First: the predicates do not exist yet, and writing them is a stop condition

U-02 asks for *"the exact predicate"* per conjunct. There is none to quote.
[`eval-plan.md`](../eval-plan.md) §8.1 is a table of **families and examples**, and says so
in the sentence directly beneath it:

> Exact rule bodies are F3 implementation; their **definitions** and the composite contract
> R1∧R2∧R3∧R4 are frozen at Freeze A.

So the rule bodies are T1 — an F3 deliverable — and the dispatch's own stop conditions
forbid writing them. What this readout does instead is the part that is a read: take §8.1's
**examples** as the statement of what each conjunct consumes, resolve each to concrete span
and attribute inputs, and check those against the mapping table. That is the input an
instrumentation contract needs, and it does not require the predicate to be written first.

---

## Per conjunct

### R1 — trace structural validity

§8.1's examples: *root span present, ≥1 `gen_ai` operation span, no orphan spans, terminal
`status_code` set.*

| Input required | Source | Mapping can produce it? |
|---|---|---|
| root span present | `parent_span_id IS NULL` | **Yes** — OTLP structure, dialect-independent |
| no orphan spans | `parent_span_id` resolves within `trace_id` | **Yes** — same |
| terminal `status_code` set | `status_code`, `NOT NULL` in the table | **Yes** — same |
| ≥1 `gen_ai` operation span | `gen_ai_operation_name IS NOT NULL` | **Yes**, from `openinference.span.kind` via the six-value map |

**R1 is fully producible** — every input is structural, and the one dialect-dependent input
has a mapping rule. Its only precondition is that spans are emitted at all.

**One boundary worth naming:** the operation-name map covers six OpenInference kinds
(`LLM`, `TOOL`, `CHAIN`, `AGENT`, `RETRIEVER`, `EMBEDDING`) and the mapping states that a
value outside the map *"yields nothing rather than a guess"*. A span whose kind is unmapped
produces a null `gen_ai_operation_name` and would read to R1 as not a `gen_ai` operation
span. That is correct behaviour and a fact the instrumentation contract must know.

### R2 — telemetry schema conformance

§8.1's examples: *required v1.41 attributes present for the operation type; names in
registry.*

The **names-in-registry** half is already enforced in this repository and needs nothing new:
`normalization/semconv/v1.41/` is vendored and `SemconvRegistryTests` asserts every mapped
column targets a name the pin defines.

The **required-for-the-operation-type** half is where the gap is. The mapping produces eight
columns:

`gen_ai_provider_name`, `gen_ai_operation_name`, `gen_ai_request_model`,
`gen_ai_response_model`, `gen_ai_usage_input_tokens`, `gen_ai_usage_output_tokens`,
`gen_ai_tool_name`, `gen_ai_conversation_id`.

The table declares seven more that this dialect maps to nothing: `gen_ai_response_id`,
`gen_ai_agent_name`, `gen_ai_tool_call_id`, `gen_ai_request_max_tokens`,
`gen_ai_request_temperature`, `gen_ai_request_top_p`, `gen_ai_output_type`.

**Three of those are unmapped for a stated reason, not an oversight.** The mapping's closing
comment records that `temperature` and `max_tokens` arrive inside
`llm.invocation_parameters`, a JSON *string*, and that the normalizer does not parse
embedded JSON — *"a mapping that reaches inside an opaque string value is no longer a
mapping table, it is a parser with a configuration file"*. They stay null and the string
survives verbatim in the lossless `attributes` column. **Extracting them is a mapping-schema
change, not a value fix**, and if R2 ends up requiring them for `chat`, that schema change
is on F3's path.

**Whether R2 passes therefore cannot be answered here**, because which attributes v1.41
marks required per operation type is exactly the definition Freeze A freezes. This readout
records the supply side; the requirement side is P4/Freeze A.

### R3 — output contract

§8.1's examples: *output parses; required fields present; enum values in allowed set.*

**This is the conjunct with no supply at all, and the finding is sharper than "the agent
does not emit".**

The Adjudicator's output contract is `AdjudicateResponse` — `decision`, `resolved_by`,
`tier1_decision`, `VLMInfo.verdict`, with enumerated values measured over 480 emissions
([`c-1-dossier-filled-2026-09-02.md`](c-1-dossier-filled-2026-09-02.md) A3/A4).

| Question | Answer |
|---|---|
| Does the agent put its output on a span attribute? | **No.** It emits nothing at all (B1) |
| If it did, does the mapping have a rule promoting it to a column? | **No.** No rule in this dialect names an output field |
| Is there a table column for it? | **No.** The 15 `gen_ai_*` columns carry request/response *metadata*, not the agent's answer |
| Where would it land once emitted? | The lossless `attributes` JSON — queryable, but only if the emitter writes it there |

**So R3 has two blockers, not one**, and only the first is commonly stated. Instrumenting
the Adjudicator makes the output *exist* on the trace; it does not make it *reachable as a
typed column*. R3's rule body would have to read `JSON_VALUE(attributes, …)` against an
attribute key that does not exist yet and is not named anywhere in this repository.

**That key is the instrumentation contract's central deliverable**, and it is the thing
neither `#177` nor the C-1 dossier names, because both stop at "does it emit". It has to be
chosen — by whoever writes the instrumentation — and then either (a) left in `attributes`
and read by JSON path, or (b) added to the mapping and the table as a typed column, which is
a mapping-schema change plus a DDL change plus a Terraform change.

### R4 — behavioral invariants

§8.1's examples: *tool-call count within bounds; no identical tool call repeated > k times
(loop detection); token and latency budgets.*

| Input required | Source | Mapping can produce it? |
|---|---|---|
| tool-call count | count of spans with `gen_ai_operation_name = 'execute_tool'` | **Yes** — from `openinference.span.kind: TOOL` |
| token budgets | `gen_ai_usage_input_tokens`, `gen_ai_usage_output_tokens` | **Yes** — from `llm.token_count.prompt` / `.completion` |
| latency budgets | `end_time - start_time` | **Yes** — OTLP structure |
| **identical tool call repeated > k** | tool **name plus arguments** | **Partly.** `gen_ai_tool_name` yes, from `tool.name`. **Arguments: no rule, no column** |

**Loop detection is the half that does not survive.** Identity of a tool *call* needs its
arguments; the mapping carries only the name. Two different calls to the same tool are
indistinguishable in the typed columns, so a loop-detection predicate written against them
would fire on legitimate repetition and miss nothing else. Like R3, the arguments would have
to reach `attributes` and be read by JSON path — and the emitter has to be told to put them
there.

---

## Summary — the instrumentation contract this implies

Ordered by how much of it is already solved:

| Conjunct | Supply state | What instrumentation must add |
|---|---|---|
| **R1** | **complete** | nothing beyond emitting spans with correct parent/status |
| **R4** | **3 of 4 inputs complete** | tool-call **arguments**, as an attribute |
| **R2** | supply known, requirement unfrozen | possibly `temperature`/`max_tokens`, which needs a mapping-schema change |
| **R3** | **no supply** | the agent's **output**, as a named attribute — the central item |

**Two attributes carry almost the whole gap: the agent's output, and tool-call arguments.**
Both are absent from the emitter and unnamed in the mapping. Naming them is the first
concrete deliverable of any instrumentation work, and it is a design decision that belongs
with whoever owns T2-01's disposition — Lane A does not take it.

**What this readout does not do:** it does not propose attribute keys, does not write rule
bodies, and does not edit the mapping. All three are F3 deliverables or Class 3 edits.
