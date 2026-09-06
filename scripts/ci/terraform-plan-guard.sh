#!/usr/bin/env bash
#
# Plan-diff guard (F0 spec §W5, architecture §7.1).
#
#     scripts/ci/terraform-plan-guard.sh <plan.tfplan|plan.json>
#     scripts/ci/terraform-plan-guard.sh --self-test
#
# The plan path may be relative to your own working directory or to the
# repository root. Both are tried, yours first. It used to be root-relative only,
# which is not discoverable from anywhere: this script cds to the root before
# resolving anything, so a plan named from the directory it sits in was reported
# as missing. That skipped the guard on a real apply on 2026-09-05 --
# docs/evidence/f2-killswitch-grpc-1831-redeploy-2026-09-05.md.
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

# Captured before the cd below discards it. The root is where the allowlist and
# the fixtures are addressed from; the plan file is the caller's, and the two are
# not the same directory unless the caller happened to be standing at the root.
invocation_dir="$PWD"

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

resolve_plan() {
  # Prints the resolved path and returns 0, or returns 1 having printed nothing.
  #
  # Both relative forms are real usage in this repository and neither is a
  # mistake: .github/workflows/deploy.yml runs from the root and names
  # infra/terraform/plan.tfplan, while the block in infra/terraform/README.md is
  # run from infra/terraform and names plan.tfplan. The caller's directory wins,
  # because that is the one they can see.
  local arg="$1" candidate
  local -a candidates

  case "$arg" in
    /*) candidates=("$arg") ;;
    *)  candidates=("${invocation_dir}/${arg}" "${PWD}/${arg}") ;;
  esac

  for candidate in "${candidates[@]}"; do
    if [ -f "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

self_test_paths() {
  # Resolution is this script's behaviour, not plan_guard.py's, so the fixture
  # loop cannot reach it -- that loop calls analyse() directly. Proven here on
  # the same reasoning the fixtures are: against the case that used to fail.
  local failures=0 dir got saved

  dir="$(mktemp -d "${TMPDIR:-/tmp}/plan-guard-paths.XXXXXX")"
  cp scripts/ci/testdata/plan-clean.json "${dir}/probe.json"

  printf '\n--- path resolution\n'

  # Relative to the caller's directory: the form that was reported as missing.
  saved="$invocation_dir"
  invocation_dir="$dir"
  if got="$(resolve_plan probe.json)" && [ "$got" = "${dir}/probe.json" ]; then
    printf '    caller-relative resolves: as expected\n'
  else
    printf '    SELF-TEST FAILED: caller-relative path did not resolve\n'
    failures=$((failures + 1))
  fi
  invocation_dir="$saved"

  # Relative to the repository root: the form the workflows use, unchanged.
  if got="$(resolve_plan scripts/ci/testdata/plan-clean.json)" \
     && [ "$got" = "${PWD}/scripts/ci/testdata/plan-clean.json" ]; then
    printf '    root-relative resolves: as expected\n'
  else
    printf '    SELF-TEST FAILED: root-relative path did not resolve\n'
    failures=$((failures + 1))
  fi

  # A name that is neither still has to be refused. Widening resolution must not
  # turn a wrong invocation into a silent one -- that is the defect, not the fix.
  if resolve_plan no-such-plan-file.json >/dev/null 2>&1; then
    printf '    SELF-TEST FAILED: a missing plan file resolved\n'
    failures=$((failures + 1))
  else
    printf '    missing file refused: as expected\n'
  fi

  rm -rf "$dir"
  return "$failures"
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
plan-wave3.json pass
plan-worker-public.json fail
plan-invoker-unresolved.json fail
FIXTURES

  local path_failures=0
  self_test_paths || path_failures=$?
  failures=$((failures + path_failures))

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

if ! plan_path="$(resolve_plan "$1")"; then
  printf 'no such plan file: %s\n' "$1" >&2
  case "$1" in
    /*) ;;
    *)  printf 'looked in %s (where you ran this) and %s (the repository root)\n' \
          "$invocation_dir" "$PWD" >&2 ;;
  esac
  exit 2
fi

convert_plan "$plan_path"
analyse "$plan_json"
