#!/usr/bin/env bash
#
# Rejection probe — does production refuse what the local stack accepts? (F3E-01b)
#
#     scripts/probe/rejection-probe.sh
#
# Scoped by the F3 entry directive and **not wideable during execution**: `bq query
# --dry_run` and read-only queries only. Nothing here writes a row or creates a table. The
# moment a probe needs either it belongs to F3E-01c, which is Lane C.
#
# A dry run creates nothing — the precedent is decision log W2.17, where the same
# mechanism settled the comment-parsing question at no mutation.
#
# **Why this shape rather than a row diff.** F3E-01a found that rows are identical by
# construction: timestamp truncation happens in the worker before either path is chosen,
# and the column set is generated from one DDL under a CI diff. What differs is what each
# side *refuses*. A diff of stored rows sees none of that and comes back clean.
#
# Not a CI job. It needs cloud credentials and it is not a gate; it is a Lane A instrument
# run on demand, and its findings are written up as evidence.
set -uo pipefail

PROJECT="${PLUMBLINE_PROJECT:-plumbline-19458}"
fail=0

run() {
  local label="$1" expect="$2" sql="$3" out verdict
  out="$(printf '%s\n' "$sql" | bq query --project_id="$PROJECT" --use_legacy_sql=false --dry_run 2>&1)"
  if printf '%s' "$out" | grep -q 'successfully validated'; then verdict=VALIDATED
  elif printf '%s' "$out" | grep -qi 'error'; then verdict=REJECTED
  else verdict=UNKNOWN; fi

  if [ "$verdict" = "$expect" ]; then
    printf '  ok        %-46s %s\n' "$label" "$verdict"
  else
    printf '  CHANGED   %-46s expected %s, got %s\n' "$label" "$expect" "$verdict"
    printf '%s\n' "$out" | sed 's/^/              /' | head -4
    fail=1
  fi
}

echo "rejection probe — project $PROJECT, dry run only (creates nothing)"
echo

# S1 — require_partition_filter. The cloud table is partitioned on start_time and requires
# a filter; the local table is created by seed.py with columns only and no timePartitioning,
# so BigQuery semantics cannot enforce one there. Production is measured here; the local
# side is settled by construction and is NOT executed by this script.
# partition-filter: intentionally-absent -- the missing predicate IS the measurement.
# This query exists to be refused; adding a filter would delete the case.
run "S1  spans, no partition predicate"        REJECTED \
    'SELECT COUNT(*) FROM `'"$PROJECT"'.plumbline.spans`'

# The control. A probe that only ever sees rejection is not measuring the constraint, it is
# measuring that the table exists.
run "S1  spans, with partition predicate"      VALIDATED \
    'SELECT COUNT(*) FROM `'"$PROJECT"'.plumbline.spans` WHERE start_time >= "2026-08-01"'

# partition-filter: intentionally-absent -- same, through the view: this is what proves
# the base table's requirement reaches consumers that never name the base table.
run "S1  spans_deduped, no partition predicate" REJECTED \
    'SELECT COUNT(*) FROM `'"$PROJECT"'.plumbline.spans_deduped`'

# S3 — comment handling. The emulator scans statement text for partitioning keywords and
# matches them inside `--` comments (W2.16). Production is expected to parse correctly,
# which W2.17 measured; this re-asserts it so a regression would surface.
run "S3  comment naming PARTITION BY"          VALIDATED \
    '-- PARTITION BY is named in this comment, which the emulator misparses (W2.16).
SELECT start_time FROM `'"$PROJECT"'.plumbline.spans` WHERE start_time >= "2026-08-01" LIMIT 1'

echo
echo "not probed here, and why:"
echo "  S2  write-stream semantics   — needs a write; F3E-01c, Lane C"
echo "  S4  JSON round-trip          — needs a row written and read back; F3E-01c, Lane C"
echo "  S5  column-name matching     — same"
echo "  local side of S1 and S3      — needs the emulator running; no container runtime on"
echo "                                 the Lane A host. Derived from seed.py, not executed."
echo

[ "$fail" -eq 0 ] || { echo "PROBE: an outcome changed — read it before trusting anything downstream."; exit 1; }
echo "probe: 4 cases, all as recorded"
