-- spans — the base table (architecture §4.1).
--
-- Terraform owns this object in the cloud; this file exists so the local BigQuery
-- stand-in has the same shape, and so the column set is reviewable as a schema rather
-- than as an HCL block.
--
-- Written only through the Storage Write API. The legacy streaming-insert path is
-- forbidden as a cost invariant (§2.3, §7) and is unreachable from this repository —
-- Gate A refuses the client package that exposes it.
CREATE TABLE IF NOT EXISTS `plumbline.spans`
(
  -- OTLP structure. Timestamps are microseconds: BigQuery TIMESTAMP has no nanoseconds,
  -- and the remainder of an OTLP nanosecond timestamp is floored away at this boundary.
  start_time                TIMESTAMP NOT NULL,
  end_time                  TIMESTAMP NOT NULL,
  trace_id                  STRING NOT NULL,
  span_id                   STRING NOT NULL,
  parent_span_id            STRING,
  name                      STRING NOT NULL,
  kind                      STRING NOT NULL,
  status_code               STRING NOT NULL,
  status_message            STRING,

  -- Provenance.
  service_name              STRING,
  source_dialect            STRING NOT NULL,   -- worker-detected; authoritative (§5)
  api_key_id                STRING,
  schema_url                STRING,            -- as declared by the payload; NULL is a measurement
  synthetic                 BOOL NOT NULL,     -- walled-off flag; spans_real excludes it

  -- Normalized GenAI columns, semconv v1.41. Scalars only; array-valued attributes stay
  -- in the lossless JSON below.
  gen_ai_provider_name      STRING,
  gen_ai_operation_name     STRING,
  gen_ai_request_model      STRING,
  gen_ai_response_model     STRING,
  gen_ai_response_id        STRING,
  gen_ai_conversation_id    STRING,
  gen_ai_agent_name         STRING,
  gen_ai_tool_name          STRING,
  gen_ai_tool_call_id       STRING,
  gen_ai_usage_input_tokens  INT64,
  gen_ai_usage_output_tokens INT64,
  gen_ai_request_max_tokens  INT64,
  gen_ai_request_temperature FLOAT64,
  gen_ai_request_top_p       FLOAT64,
  gen_ai_output_type        STRING,

  -- Lossless remainder: every attribute the payload carried, at all three levels
  -- ({resource, scope, span}), including the ones promoted to columns above.
  attributes                JSON NOT NULL,
  events                    JSON NOT NULL,
  links                     JSON NOT NULL,

  ingest_time               TIMESTAMP NOT NULL  -- worker write time; stamped by the sink
)
PARTITION BY DATE(start_time)
CLUSTER BY trace_id, span_id
OPTIONS (
  require_partition_filter = TRUE,
  description = 'Normalized OTLP spans. Consumers read spans_deduped or spans_real, never this table.'
);
