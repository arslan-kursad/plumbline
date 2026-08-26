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

workdir=""
plan_json=""

cleanup() {
  # An `if` rather than a `[ ... ] && ...` chain: the latter returns 1 when the
  # variable is empty, and an EXIT trap's status becomes the script's status.
  if [ -n "$workdir" ]; then
    rm -rf "$workdir"
  fi
}
trap cleanup EXIT

convert_plan() {
  # Sets plan_json. Deliberately not a function that prints a path: it also
  # allocates a temporary directory, and a command substitution would allocate it
  # in a subshell the caller cannot clean up.
  local plan="$1"

  if head -c 1 "$plan" | grep -q '{'; then
    plan_json="$plan"
    return
  fi

  local dir
  dir="$(cd "$(dirname "$plan")" && pwd)"

  # A directory with a fixed filename inside, rather than a template with a
  # suffix: mktemp only substitutes trailing X's, so "plan.XXXXXX.json" is a
  # literal name. It works once and collides on every run after that — a failure
  # that only appears the second time anyone uses this.
  workdir="$(mktemp -d "${TMPDIR:-/tmp}/plan-guard.XXXXXX")"
  plan_json="${workdir}/plan.json"

  if ! (cd "$dir" && terraform show -json "$(basename "$plan")") > "$plan_json"; then
    printf 'could not convert %s with terraform show -json\n' "$plan" >&2
    exit 2
  fi
  if [ ! -s "$plan_json" ]; then
    printf 'terraform show -json produced nothing for %s\n' "$plan" >&2
    exit 2
  fi
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
plan-wave2.json pass
plan-amendment-2.json pass
plan-forbidden-type.json fail
plan-scaling.json fail
plan-region.json fail
plan-topic-retention.json fail
plan-two-budgets.json fail
plan-ingress-inverted.json fail
plan-ingress-undeclared.json fail
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

convert_plan "$1"
analyse "$plan_json"
