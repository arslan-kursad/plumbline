-- spans_real — deduplicated spans, excluding synthetic traffic.
--
-- The `synthetic` flag is walled off rather than filtered ad hoc (§4.1): the load
-- generator's traffic is real data about the pipeline and false data about the agents, so
-- it has to be excludable in one place that every consumer inherits. A measurement
-- published from a dataset where the two were mixed would be indefensible, and the
-- mixing would be invisible in the result.
CREATE OR REPLACE VIEW `plumbline.spans_real` AS
SELECT *
FROM `plumbline.spans_deduped`
WHERE synthetic = FALSE;
