#!/usr/bin/env bash
#
# Every query against the spans dataset must constrain start_time (T1-05).
#
#     scripts/ci/partition-filter-check.sh              # scan, print findings, exit 0
#     scripts/ci/partition-filter-check.sh --self-test  # prove it fails, and stays quiet
#
# `require_partition_filter` is enforced by BigQuery in the cloud and by nothing locally:
# the stand-in cannot create a partitioned table, so the local table carries no such
# requirement. The gap that leaves is recorded in f3e-01b-rejection-probe.md -- a query
# written outside the e2e path meets no local objection. This constrains the repository
# where the engine cannot be constrained. It does not restore emulator fidelity.
#
# Non-blocking by design, on the same reasoning as the cross-reference check: shipping a
# check and gating on it are two decisions, and the second is Class 3. The self-test is
# not non-blocking -- a checker that cannot fail on a known-bad corpus is decoration.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
corpus="$here/testdata/partition-filter"

if [ "${1:-}" = "--self-test" ]; then
  echo "partition-filter self-test — corpus: scripts/ci/testdata/partition-filter/"
  echo

  out="$(python3 "$here/partition_filter.py" "$corpus" 2>&1 || true)"
  echo "$out"
  echo

  fail=0
  expect() {
    local pattern="$1" want="$2" got
    got="$(printf '%s\n' "$out" | grep -c -- "$pattern" || true)"
    if [ "$got" -ne "$want" ]; then
      echo "  FAIL  expected $want match(es) for '$pattern', got $got"
      fail=1
    else
      echo "  ok    $want × $pattern"
    fi
  }

  # It can fail, in both languages it reads.
  expect 'queries.py:20  UNFILTERED' 1
  expect 'report.sql:2  UNFILTERED' 1

  # And it must stay quiet on the four cases that look like defects and are not. Each of
  # these, reported, would make the check worse than nothing: it would be asking for the
  # views to be wrong, or for the most rigorously filtered path in the repository to be
  # rewritten, or for a deliberate probe to delete the case it exists to measure.
  expect '1  view-definition' 1
  expect '1  interpolated-predicate' 1
  expect '1  declared-absent' 1
  expect '2  filtered' 1

  # A scanner that stops finding sites reports success forever. The corpus has seven, and
  # the eighth query in it is against another table and must not be counted.
  expect '7 query site(s)' 1

  echo
  if [ "$fail" -ne 0 ]; then
    echo "partition-filter self-test: FAIL"
    exit 1
  fi
  echo "partition-filter self-test: ok"
  exit 0
fi

cd "$repo"
python3 "$here/partition_filter.py" "$@" || true
