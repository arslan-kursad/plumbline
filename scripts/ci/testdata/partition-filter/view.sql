-- A view definition reads the base table with no predicate, deliberately: the consumer's
-- start_time filter is pushed below the window (ADR-0007 D2). Requiring one here would
-- mean requiring the real views to be wrong.
CREATE OR REPLACE VIEW `plumbline.example_view` AS
SELECT *
FROM `plumbline.spans`;
