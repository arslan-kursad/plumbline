#!/usr/bin/env bash
#
# The generated BigQuery schema must match the DDL it was generated from
# (F2 spec §6 Wave 1, decision D4; decision log W1.2).
#
#     scripts/ci/bq-schema-guard.sh [<table.sql> <schema.json>]
#     scripts/ci/bq-schema-guard.sh --self-test
#
# With no arguments it checks the real pair. The generated file is committed
# because Terraform reads it with file(); this guard is what stops it from being
# a second hand-maintained copy of the column set.
#
# Exits non-zero with the diff when they disagree. Regenerate with:
#
#     python3 scripts/ci/bq_schema.py analytics/sql/001_spans_table.sql \
#       > infra/terraform/generated/spans-schema.json

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

DDL="analytics/sql/001_spans_table.sql"
JSON="infra/terraform/generated/spans-schema.json"

compare() {
  # $1 — DDL path. $2 — generated JSON path.
  local ddl="$1" json="$2" generated status

  set +e
  generated="$(python3 scripts/ci/bq_schema.py "$ddl" 2>&1)"
  status=$?
  set -e

  if [ "$status" -ne 0 ]; then
    printf 'schema guard: %s could not be parsed\n' "$ddl"
    printf '%s\n' "$generated" | sed 's/^/  /'
    return 2
  fi

  if [ ! -f "$json" ]; then
    printf 'schema guard: %s does not exist\n' "$json"
    return 1
  fi

  if diff -u "$json" <(printf '%s\n' "$generated") > /tmp/schema-guard-diff 2>&1; then
    printf 'schema guard: %s matches %s\n' "$json" "$ddl"
    return 0
  fi

  printf 'schema guard: %s does not match %s\n' "$json" "$ddl"
  sed 's/^/  /' /tmp/schema-guard-diff
  printf '  regenerate: python3 scripts/ci/bq_schema.py %s > %s\n' "$ddl" "$json"
  return 1
}

self_test() {
  # Proven against inputs that violate it, on the same reasoning as the gate
  # proofs: a guard only ever run against a matching pair is unverified.
  local failures=0 ddl json expectation output status

  while read -r ddl json expectation; do
    [ -n "$ddl" ] || continue

    printf '\n--- %s + %s (expect %s)\n' "$ddl" "$json" "$expectation"

    set +e
    output="$(compare "scripts/ci/testdata/schema/${ddl}" "scripts/ci/testdata/schema/${json}" 2>&1)"
    status=$?
    set -e

    printf '%s\n' "$output" | sed 's/^/    /'

    case "$expectation" in
      pass) [ "$status" -eq 0 ] || { printf '    SELF-TEST FAILED: matching pair rejected\n'; failures=$((failures + 1)); continue; } ;;
      fail) [ "$status" -eq 1 ] || { printf '    SELF-TEST FAILED: mismatch accepted (status %d)\n' "$status"; failures=$((failures + 1)); continue; } ;;
      unparseable) [ "$status" -eq 2 ] || { printf '    SELF-TEST FAILED: unparseable DDL not reported as such (status %d)\n' "$status"; failures=$((failures + 1)); continue; } ;;
    esac
    printf '    as expected\n'
  done <<'FIXTURES'
matching.sql matching.json pass
matching.sql stale.json fail
unreadable-column.sql matching.json unparseable
unknown-type.sql matching.json unparseable
FIXTURES

  printf '\n'
  if [ "$failures" -gt 0 ]; then
    printf '%d self-test(s) failed\n' "$failures"
    exit 1
  fi
  printf 'schema guard self-test passed\n'
}

case "${1:-}" in
  --self-test) self_test ;;
  "")          compare "$DDL" "$JSON" ;;
  *)
    [ "$#" -eq 2 ] || { printf 'usage: %s [<table.sql> <schema.json>]\n       %s --self-test\n' "$0" "$0" >&2; exit 2; }
    compare "$1" "$2"
    ;;
esac
