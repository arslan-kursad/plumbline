-- A miniature of the real table: enough shapes to exercise the parser.
CREATE TABLE IF NOT EXISTS `plumbline.example`
(
  -- A comment inside the column list, which the parser skips.
  start_time    TIMESTAMP NOT NULL,
  trace_id      STRING NOT NULL,   -- trailing comment
  parent_id     STRING,
  synthetic     BOOL NOT NULL,
  token_count   INT64,
  temperature   FLOAT64,
  attributes    JSON NOT NULL
)
PARTITION BY DATE(start_time)
CLUSTER BY trace_id
OPTIONS (
  require_partition_filter = TRUE
);
