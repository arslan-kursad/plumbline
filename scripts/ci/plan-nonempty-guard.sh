#!/usr/bin/env bash
#
# Empty-plan guard (F2 directive W3C.1).
#
#     scripts/ci/plan-nonempty-guard.sh <plan.tfplan|plan.json>
#     scripts/ci/plan-nonempty-guard.sh --self-test
#
# Refuses to arm a wave whose plan would apply nothing, and prints the change
# counts the approval summary carries when it would.
#
# Separate from terraform-plan-guard.sh on purpose. That guard asserts properties
# *of* the changes a plan makes — allowlist, scaling, region, ingress, invoker —
# and every one of them is vacuously true of a plan with no changes. This one
# asserts that there are changes at all, which is a different question and the
# one that went unasked while two dispatches reached the approval gate proposing
# nothing (decision log W3C.1).
#
# Exits non-zero with the ref and commit the plan was computed against, because
# "which commit did this plan come from" is the question a reviewer needs
# answered and the failure that motivated this guard was a stale ref.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

usage() {
  printf 'usage: %s <plan.tfplan|plan.json>\n       %s --self-test\n' "$0" "$0" >&2
  exit 2
}

[ "$#" -eq 1 ] || usage

analyse() {
  # $1 — path to a plan in JSON form.
  python3 scripts/ci/plan_nonempty.py "$1"
}

workdir=""

cleanup() {
  if [ -n "$workdir" ]; then
    rm -rf "$workdir"
  fi
}
trap cleanup EXIT

self_test() {
  # Both directions, and the passing case is not optional: a guard verified only
  # against plans it rejects cannot be told apart from one that rejects
  # everything, and that failure mode blocks every wave rather than none.
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
      printf '    SELF-TEST FAILED: a plan with real changes was refused\n'
      failures=$((failures + 1))
    elif [ "$expectation" = "fail" ] && [ "$status" -eq 0 ]; then
      printf '    SELF-TEST FAILED: a plan that applies nothing was accepted\n'
      failures=$((failures + 1))
    else
      printf '    as expected\n'
    fi
  done <<'FIXTURES'
plan-wave3.json pass
plan-wave2.json pass
plan-noop.json fail
plan-empty.json fail
FIXTURES

  printf '\n'
  if [ "$failures" -gt 0 ]; then
    printf '%d self-test(s) failed\n' "$failures"
    exit 1
  fi
  printf 'empty-plan guard self-test passed\n'
}

if [ "$1" = "--self-test" ]; then
  self_test
  exit 0
fi

[ -f "$1" ] || { printf 'no such plan file: %s\n' "$1" >&2; exit 2; }

case "$1" in
  *.json)
    analyse "$1"
    ;;
  *)
    # A binary plan file needs `terraform show` and therefore an initialised
    # working directory; the caller in deploy.yml already has the JSON, so this
    # branch exists for local use.
    workdir="$(mktemp -d)"
    terraform -chdir=infra/terraform show -json "$1" > "$workdir/plan.json"
    analyse "$workdir/plan.json"
    ;;
esac
