#!/usr/bin/env bash
#
# Fixture provenance gate (F2 directive W3C.2).
#
#     scripts/ci/fixture-provenance-guard.sh
#     scripts/ci/fixture-provenance-guard.sh --self-test
#
# Holds the rule in scripts/ci/testdata/README.md: guard fixtures are derived
# from real plan output, never authored. A fixture added or modified in a change
# must be `captured` and must be declared in the same change.
#
# The consistency half — every fixture declared, every declaration real — runs
# with no git history at all. The "changed in this commit" half needs a range, so
# it is computed here and passed in rather than discovered by the Python, which
# keeps that logic a pure function the self-test can drive.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

TESTDATA="scripts/ci/testdata"

analyse() {
  # $1 — testdata dir, $2 — 1 if the manifest changed, rest — changed paths.
  python3 scripts/ci/fixture_provenance.py "$@"
}

self_test() {
  # Every assertion is driven against a tree that violates it. The gate's real
  # subject is a git range, which cannot be conjured in a unit test, so the range
  # is an argument and the fixtures below are directories built on the fly.
  local failures=0 workdir

  workdir="$(mktemp -d)"
  trap 'rm -rf "$workdir"' RETURN

  build() {
    # $1 — case name, $2 — provenance for probe.json, $3 — 1 to also write extra.json
    local dir="$workdir/$1"
    mkdir -p "$dir"
    printf '{"format_version":"1.2","resource_changes":[]}\n' > "$dir/probe.json"
    if [ "$3" = "1" ]; then
      printf '{"format_version":"1.2","resource_changes":[]}\n' > "$dir/extra.json"
    fi
    cat > "$dir/fixtures.manifest.json" <<EOF
{
  "fixtures": {
    "probe.json": { "provenance": "$2", "source": "self-test", "capture_date": "2026-08-26" }
  }
}
EOF
    printf '%s' "$dir"
  }

  run_case() {
    # $1 — description, $2 — expect pass|fail, rest — args to analyse
    local description="$1" expectation="$2"
    shift 2

    printf '\n--- %s (expect %s)\n' "$description" "$expectation"

    set +e
    output="$(analyse "$@" 2>&1)"
    status=$?
    set -e

    printf '%s\n' "$output" | sed 's/^/    /'

    if [ "$expectation" = "pass" ] && [ "$status" -ne 0 ]; then
      printf '    SELF-TEST FAILED: a compliant tree was rejected\n'
      failures=$((failures + 1))
    elif [ "$expectation" = "fail" ] && [ "$status" -eq 0 ]; then
      printf '    SELF-TEST FAILED: a violating tree was accepted\n'
      failures=$((failures + 1))
    else
      printf '    as expected\n'
    fi
  }

  local dir

  dir="$(build consistent captured 0)"
  run_case "nothing changed, manifest consistent" pass "$dir" 0

  dir="$(build captured-change captured 0)"
  run_case "captured fixture changed, manifest updated" pass "$dir" 1 "$dir/probe.json"

  dir="$(build captured-no-manifest captured 0)"
  run_case "captured fixture changed, manifest NOT updated" fail "$dir" 0 "$dir/probe.json"

  dir="$(build legacy-touched hand-authored-legacy 0)"
  run_case "legacy fixture touched must upgrade to captured" fail "$dir" 1 "$dir/probe.json"

  dir="$(build legacy-untouched hand-authored-legacy 0)"
  run_case "legacy fixture left alone is grandfathered" pass "$dir" 0

  dir="$(build undeclared captured 1)"
  run_case "fixture on disk with no manifest entry" fail "$dir" 0

  dir="$(build orphan captured 0)"
  rm -f "$dir/probe.json"
  run_case "manifest entry with no file" fail "$dir" 0

  dir="$(build bad-provenance invented 0)"
  run_case "provenance outside the two permitted values" fail "$dir" 0

  printf '\n'
  if [ "$failures" -gt 0 ]; then
    printf '%d self-test(s) failed\n' "$failures"
    exit 1
  fi
  printf 'fixture provenance self-test passed\n'
}

if [ "${1:-}" = "--self-test" ]; then
  self_test
  exit 0
fi

# On a pull request the range is the merge base with the target branch; on main
# there is nothing to diff against a base, so only the consistency half runs.
# Erring toward "nothing changed" here is safe: the gate that matters for a new
# fixture runs on the pull request, which is where the file is introduced.
range=""
if [ "${GITHUB_EVENT_NAME:-}" = "pull_request" ] && [ -n "${GITHUB_BASE_REF:-}" ]; then
  git fetch --quiet origin "$GITHUB_BASE_REF"
  range="origin/${GITHUB_BASE_REF}...HEAD"
fi

changed=""
manifest_changed=0
if [ -n "$range" ]; then
  changed="$(git diff --name-only --diff-filter=ACMR "$range" -- "$TESTDATA" | grep '\.json$' || true)"
  if printf '%s\n' "$changed" | grep -q "fixtures.manifest.json"; then
    manifest_changed=1
  fi
fi

# shellcheck disable=SC2086 -- word splitting is how the paths become arguments
analyse "$TESTDATA" "$manifest_changed" $changed
