#!/usr/bin/env bash
#
# Refuses a deployment environment that does not carry a required reviewer
# (F2 spec §2, decision D1; decision log W1.1).
#
#     scripts/ci/environment-guard.sh <environment.json|->
#     scripts/ci/environment-guard.sh --self-test
#
# Input is the body of `GET /repos/{owner}/{repo}/environments/{name}`.
#
# Why this exists as a script rather than four lines inside the workflow: naming
# an environment that does not exist creates it on first use *without* protection
# rules, so the approval gate the deploy workflow is built around can be absent
# while every log line still reads normally. That makes this the highest-
# consequence check in the deploy path, and a check that has never been observed
# failing is not a check (ADR-0004 §1, F0 spec §6). Here it is exercised against
# fixtures that violate it, in CI, on every run.
#
# Exits 0 when the environment is protected, 1 when it is not, 2 on unusable
# input — a distinction the caller needs, because "cannot tell" must never be
# treated as "fine".

set -euo pipefail

usage() {
  printf 'usage: %s <environment.json|->\n       %s --self-test\n' "$0" "$0" >&2
  exit 2
}

analyse() {
  # $1 — path to the environment JSON, or - for stdin. The assertions live in
  # environment_guard.py; this wrapper owns argument handling and the self-test.
  python3 scripts/ci/environment_guard.py "$1"
}

self_test() {
  # Each assertion is proven against a fixture that violates it. A guard verified
  # only against a passing input is unverified, and this project has already
  # shipped one gate that could not fail.
  local failures=0 fixture expectation output status

  while read -r fixture expectation; do
    [ -n "$fixture" ] || continue

    printf '\n--- %s (expect %s)\n' "$fixture" "$expectation"

    set +e
    output="$(analyse "scripts/ci/testdata/environments/${fixture}" 2>&1)"
    status=$?
    set -e

    printf '%s\n' "$output" | sed 's/^/    /'

    case "$expectation" in
      pass) [ "$status" -eq 0 ] || { printf '    SELF-TEST FAILED: protected environment rejected\n'; failures=$((failures + 1)); continue; } ;;
      fail) [ "$status" -eq 1 ] || { printf '    SELF-TEST FAILED: unprotected environment accepted (status %d)\n' "$status"; failures=$((failures + 1)); continue; } ;;
      unusable) [ "$status" -eq 2 ] || { printf '    SELF-TEST FAILED: unusable input not reported as unusable (status %d)\n' "$status"; failures=$((failures + 1)); continue; } ;;
    esac
    printf '    as expected\n'
  done <<'FIXTURES'
protected.json pass
no-branch-policy.json pass
no-protection-rules.json fail
wait-timer-only.json fail
reviewers-removed.json fail
not-json.txt unusable
FIXTURES

  printf '\n'
  if [ "$failures" -gt 0 ]; then
    printf '%d self-test(s) failed\n' "$failures"
    exit 1
  fi
  printf 'environment guard self-test passed\n'
}

[ "$#" -eq 1 ] || usage

cd "$(git rev-parse --show-toplevel)"

if [ "$1" = "--self-test" ]; then
  self_test
else
  analyse "$1"
fi
