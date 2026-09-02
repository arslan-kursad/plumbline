#!/usr/bin/env bash
#
# Cross-reference check for docs/ (F3 entry directive F3E-04, issue #7).
#
#     scripts/ci/xref-check.sh              # scan docs/, print findings, always exit 0
#     scripts/ci/xref-check.sh --self-test  # prove the check can fail, and can stay quiet
#
# Non-blocking by design. It ships emitting findings rather than gating on them, because
# flipping a check to blocking changes what CI asserts and is a separate decision
# (F3E-04 acceptance criterion 5). The self-test is *not* non-blocking: a checker that
# cannot fail on a known-bad corpus is not evidence of anything, so --self-test exits
# non-zero when the corpus stops behaving as recorded.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
corpus="$here/testdata/xref"

if [ "${1:-}" = "--self-test" ]; then
  echo "xref self-test — corpus: scripts/ci/testdata/xref/"
  echo

  out="$(python3 "$here/xref_check.py" --docs "$corpus/docs" --root "$corpus" || true)"
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

  # The check can fail: three seeded defects in one file.
  expect 'broken.md:5  §9.1' 1
  expect 'broken.md:11  §4.3' 1
  expect 'broken.md:15  ../../../nowhere/keyctl' 1

  # And it can stay quiet: the decoys are legitimate cross-document references, and a
  # check that reports them has traded one manual pass for another.
  expect 'qualified.md' 0
  expect 'borrowed.md' 0
  expect 'architecture.md' 0

  echo
  if [ "$fail" -ne 0 ]; then
    echo "xref self-test FAILED — fix the check, not the corpus (F3E-04 criterion 4)"
    exit 1
  fi
  echo "xref self-test passed — the check fails on the seeded defects and is silent on the decoys"
  exit 0
fi

python3 "$here/xref_check.py" --docs "$repo/docs" --root "$repo" "$@"
