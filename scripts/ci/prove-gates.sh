#!/usr/bin/env bash
#
# Proves every invariant gate can fail (F0 spec §6, acceptance criterion 9).
#
#     scripts/ci/prove-gates.sh
#
# "A gate verified only against a clean tree is unverified." Each case below
# introduces one deliberate violation, runs the gates, and asserts that the
# expected gate — and no other — reports it. The violations live in a throwaway
# git worktree, so the repository being worked in is never modified.
#
# This is a repeatable prover rather than a one-time manual demonstration on
# purpose: a manual proof stops being evidence the moment the gate script
# changes, and the gate script will change.
#
# Two of the strings this script must produce are the very strings a whole-
# repository gate forbids. They are assembled at runtime from fragments so that
# this file cannot match them — the same self-non-matching rule the gates
# themselves follow (ADR-0004 §4).

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
gates="${repo_root}/scripts/ci/invariant-gates.sh"

worktree="$(mktemp -d "${TMPDIR:-/tmp}/plumbline-gate-proof.XXXXXX")/tree"

cleanup() {
  git -C "$repo_root" worktree remove --force "$worktree" >/dev/null 2>&1 || true
  rm -rf "$(dirname "$worktree")"
}
trap cleanup EXIT

git -C "$repo_root" worktree add --detach --quiet "$worktree" HEAD

# The gates under test are the working copy's, not HEAD's: a gate is proven in
# the state it is about to be merged in.
install -m 0755 "$gates" "${worktree}/scripts/ci/invariant-gates.sh"

failures=0
case_number=0

# expect_failure NAME EXPECTED_GATE — run the gates, require a non-zero exit
# and require EXPECTED_GATE to be the gate that reported.
expect_failure() {
  local name="$1" expected="$2" output status

  case_number=$((case_number + 1))
  printf '\n--- case %d: %s\n' "$case_number" "$name"

  set +e
  output="$(cd "$worktree" && ./scripts/ci/invariant-gates.sh 2>&1)"
  status=$?
  set -e

  printf '%s\n' "$output" | sed 's/^/    /'

  if [ "$status" -eq 0 ]; then
    printf '    PROOF FAILED: gates passed while the violation was present\n'
    failures=$((failures + 1))
  elif ! printf '%s\n' "$output" | grep -q "^FAIL  ${expected}"; then
    printf '    PROOF FAILED: expected %s to report, it did not\n' "$expected"
    failures=$((failures + 1))
  else
    printf '    proven: %s failed on the violation\n' "$expected"
  fi

  # Return the worktree to its clean state for the next case.
  git -C "$worktree" reset --quiet
  git -C "$worktree" clean -qfd
  git -C "$worktree" checkout --quiet -- .
  install -m 0755 "$gates" "${worktree}/scripts/ci/invariant-gates.sh"
}

# violate PATH CONTENT — write a tracked violating file.
violate() {
  local path="$1" content="$2"
  mkdir -p "$(dirname "${worktree}/${path}")"
  printf '%s\n' "$content" > "${worktree}/${path}"
  git -C "$worktree" add -N -- "$path"
}

printf 'gate failure proofs (F0 spec §6)\n'

# Baseline: the clean tree must pass, otherwise every proof below is meaningless.
printf '\n--- case 0: clean tree\n'
if (cd "$worktree" && ./scripts/ci/invariant-gates.sh 2>&1 | sed 's/^/    /'); then
  printf '    baseline: gates pass on a clean tree\n'
else
  printf '    PROOF FAILED: gates do not pass on a clean tree\n'
  failures=$((failures + 1))
fi

# Gate A — the forbidden package, as a real PackageReference.
violate "worker/Plumbline.Worker/Plumbline.Worker.csproj" \
'<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Google.Cloud.BigQuery.V2" Version="3.5.0" />
  </ItemGroup>
</Project>'
expect_failure "Gate A: legacy BigQuery client package in a csproj" "Gate A"

# Gate B — the symbol the .NET client actually exposes, which the retired
# insertAll grep could never have caught.
violate "worker/Plumbline.Worker/BadWrite.cs" \
'public static class BadWrite
{
    public static void Write(BigQueryClient client) => client.InsertRowsAsync(null, null, null);
}'
expect_failure "Gate B: streaming-insert symbol in worker source" "Gate B"

# Gate B coverage — source code in a directory nobody added to the scan list.
# The file is deliberately clean; the defect is that nothing would scan it.
violate "services/gateway/Program.cs" \
'public static class Program { public static void Main() { } }'
expect_failure "Gate B coverage: source outside the declared roots" "Gate B coverage"

# Gate C — both key markers, assembled so this script does not contain them.
violate "infra/terraform/leaked.json" \
"$(printf '{\n  "%s": "%s",\n  "%s": "-----BEGIN PRIVATE KEY-----"\n}' \
   'type' 'service_account' 'private_key')"
expect_failure "Gate C: exported service account key" "Gate C"

# Gate D — the fork-privileged trigger, in the only place GitHub reads it from.
violate ".github/workflows/danger.yml" \
'name: danger
on:
  pull_request_target:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo untrusted'
expect_failure "Gate D: pull_request_target in a workflow" "Gate D"

# Gate E — the retired project name, reintroduced the way it realistically would
# be: a document re-derived from a stale external snapshot.
violate "docs/stale-snapshot.md" \
"$(printf '# Stale snapshot\n\nBigQuery dataset: %s_dataset (pre-rename)\n' "$(printf 'agent%slens' '_')")"
expect_failure "Gate E: retired project name" "Gate E"

printf '\n'
if [ "$failures" -gt 0 ]; then
  printf '%d proof(s) failed\n' "$failures"
  exit 1
fi

printf 'all %d gate failure proofs passed\n' "$case_number"
