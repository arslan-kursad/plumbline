#!/usr/bin/env bash
#
# Plan-diff guard (F0 spec §W5, architecture §7.1).
#
#     scripts/ci/terraform-plan-guard.sh <plan.tfplan|plan.json>
#     scripts/ci/terraform-plan-guard.sh --self-test
#
# Asserts, against a Terraform plan, that:
#
#   1. every resource type is in the architecture §7.1 allowlist;
#   2. Cloud Run and Cloud Functions scaling stays min = 0, max <= 2;
#   3. everything carrying a region or location is us-central1;
#   4. no Pub/Sub topic declares message retention (a paid feature).
#
# The allowlist is not duplicated here: it is parsed out of docs/architecture.md
# §7.1, which `CLAUDE.md` and the F0 spec both name as the authority. One source
# of truth, so there is no drift for a later gate to detect.
#
# Exits non-zero listing every violation found, not just the first.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

usage() {
  printf 'usage: %s <plan.tfplan|plan.json>\n       %s --self-test\n' "$0" "$0" >&2
  exit 2
}

[ "$#" -eq 1 ] || usage

analyse() {
  # $1 — path to a plan in JSON form.
  python3 scripts/ci/plan_guard.py docs/architecture.md "$1"
}

to_json() {
  # Accepts either a JSON plan or a binary plan file; binary plans are converted
  # with `terraform show -json`, run in the directory that produced them.
  local plan="$1"

  if head -c 1 "$plan" | grep -q '{'; then
    printf '%s' "$plan"
    return
  fi

  local dir json
  dir="$(cd "$(dirname "$plan")" && pwd)"
  json="$(mktemp "${TMPDIR:-/tmp}/plan.XXXXXX.json")"
  (cd "$dir" && terraform show -json "$(basename "$plan")") > "$json"
  printf '%s' "$json"
}

self_test() {
  # Every assertion is proven against a fixture that violates it, on the same
  # reasoning as the gate proofs: a check verified only against a passing plan is
  # unverified (F0 spec §6).
  local failures=0 fixture expectation

  while read -r fixture expectation; do
    [ -n "$fixture" ] || continue

    printf '\n--- %s (expect %s)\n' "$fixture" "$expectation"

    set +e
    output="$(analyse "scripts/ci/testdata/${fixture}" 2>&1)"
    status=$?
    set -e

    printf '%s\n' "$output" | sed 's/^/    /'

    if [ "$expectation" = "pass" ] && [ "$status" -ne 0 ]; then
      printf '    SELF-TEST FAILED: clean plan rejected\n'
      failures=$((failures + 1))
    elif [ "$expectation" = "fail" ] && [ "$status" -eq 0 ]; then
      printf '    SELF-TEST FAILED: violating plan accepted\n'
      failures=$((failures + 1))
    else
      printf '    as expected\n'
    fi
  done <<'FIXTURES'
plan-clean.json pass
plan-forbidden-type.json fail
plan-scaling.json fail
plan-region.json fail
plan-topic-retention.json fail
FIXTURES

  printf '\n'
  if [ "$failures" -gt 0 ]; then
    printf '%d self-test(s) failed\n' "$failures"
    exit 1
  fi
  printf 'plan guard self-test passed\n'
}

if [ "$1" = "--self-test" ]; then
  self_test
  exit 0
fi

[ -f "$1" ] || { printf 'no such plan file: %s\n' "$1" >&2; exit 2; }
analyse "$(to_json "$1")"
