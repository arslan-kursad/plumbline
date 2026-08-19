#!/usr/bin/env bash
#
# Cost- and security-invariant gates (F0 spec §W6.2, ADR-0004 §1, §3, §4).
#
# Runnable locally and in CI, no arguments:
#
#     scripts/ci/invariant-gates.sh
#
# Exit code 0 if every gate passes, 1 otherwise, with offending `path:line`
# printed for each failure. Every gate runs even after one fails: a run that
# stops at the first failure hides the others.
#
# Two conventions hold throughout.
#
#   Scan set. Gates scan every file git would consider part of the repository:
#   tracked files plus untracked ones that are not ignored. Ignored paths (build
#   output, provider caches) are out by construction, so no gate needs an
#   exclusion list. Untracked files are in deliberately — scanning only tracked
#   files passes a violation locally until someone runs `git add`, and then fails
#   it in CI, which is the worst possible ordering.
#
#   Pattern notation. Forbidden-string patterns are written so they cannot match
#   their own text; a character class around a single literal character is
#   enough (`private[_]key`). Consequence: this script can name the strings it
#   forbids, no gate needs an exclusion list, and none can be defeated by adding
#   a path to one.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# Directories that contain source code. Declared once, here. The coverage check
# in Gate B fails if a source file appears outside this list, so extending the
# repository's source layout is an explicit decision rather than a silent
# reduction in what the symbol scan covers (issue #5).
SOURCE_ROOTS=(collector worker analytics infra/functions)

failed_gates=()

fail() {
  failed_gates+=("$1")
  printf 'FAIL  %s\n' "$1"
}

pass() {
  printf 'ok    %s\n' "$1"
}

# repo_files [pathspec...] — every non-ignored file in the repository,
# NUL-separated, tracked or not.
repo_files() {
  if [ "$#" -eq 0 ]; then
    git ls-files -z --cached --others --exclude-standard
  else
    git ls-files -z --cached --others --exclude-standard -- "$@"
  fi
}

# scan NAME PATTERN [pathspec...] — report tracked files matching PATTERN.
# Returns 0 when nothing matches.
scan() {
  local name="$1" pattern="$2"
  shift 2

  local matches
  matches="$(repo_files "$@" | xargs -0 -r grep -nE -- "$pattern" 2>/dev/null || true)"

  if [ -n "$matches" ]; then
    printf '      %s: %s\n' "$name" "$pattern"
    printf '%s\n' "$matches" | sed 's/^/        /'
    return 1
  fi
  return 0
}

# ---------------------------------------------------------------------------
# Gate A — forbidden dependency (load-bearing, prevent-class).
#
# The permitted BigQuery write path is the Storage Write API
# (Google.Cloud.BigQuery.Storage.V1). If the legacy client package is absent,
# the streaming-insert surface cannot be reached whatever its symbols are
# called — which is why this gate, not the symbol scan, is the real control.
# ---------------------------------------------------------------------------
gate_a() {
  local ok=0
  scan "forbidden package" 'Google[.]Cloud[.]BigQuery[.]V2' \
    '*.csproj' 'Directory.Packages.props' || ok=1

  if [ "$ok" -eq 0 ]; then
    pass "Gate A — no legacy BigQuery client package"
  else
    fail "Gate A — legacy BigQuery client package referenced"
  fi
}

# ---------------------------------------------------------------------------
# Gate B — path-scoped symbol scan (secondary, report-class) plus a coverage
# check on its own scope.
#
# Scoped by a path allowlist, not a file denylist: documentation will keep
# naming these symbols and must never need an exclusion entry.
# ---------------------------------------------------------------------------
gate_b() {
  local ok=0 pattern
  local -a code_paths=()

  for root in "${SOURCE_ROOTS[@]}"; do
    code_paths+=("${root}/**/*.go" "${root}/**/*.cs" "${root}/*.go" "${root}/*.cs")
  done

  for pattern in \
    'insert[A]ll' \
    'tabledata[.]insert[A]ll' \
    'InsertRow[(]' \
    'InsertRows[(]' \
    'InsertRowsAsync[(]' \
    '[.]Inserter[(]'
  do
    scan "streaming-insert symbol" "$pattern" "${code_paths[@]}" || ok=1
  done

  if [ "$ok" -eq 0 ]; then
    pass "Gate B — no streaming-insert symbols in source"
  else
    fail "Gate B — streaming-insert symbol in source"
  fi

  # Coverage: every source file must sit under a declared root. Stricter than
  # "no new top-level source directory", and immune to the same defect — a
  # source tree nested one level deeper would satisfy the top-level reading
  # while being scanned by nothing.
  local uncovered="" file
  while IFS= read -r -d '' file; do
    local covered=0
    for root in "${SOURCE_ROOTS[@]}"; do
      case "$file" in
        "$root"/*) covered=1; break ;;
      esac
    done
    [ "$covered" -eq 1 ] || uncovered+="        ${file}"$'\n'
  done < <(repo_files '*.go' '*.cs' '*.csproj' '*.sln')

  if [ -n "$uncovered" ]; then
    printf '      source files outside the declared scan roots (%s):\n' "${SOURCE_ROOTS[*]}"
    printf '%s' "$uncovered"
    fail "Gate B coverage — source outside the scanned roots"
  else
    pass "Gate B coverage — all source under the scanned roots"
  fi
}

# ---------------------------------------------------------------------------
# Gate C — no exported service account keys. Whole repository, no exclusions: a
# leaked key can land in any path, so narrowing this gate would be a regression.
# Detection backstop behind GitHub push protection (F0 spec §W6.4), which is the
# control that acts before the secret reaches history.
# ---------------------------------------------------------------------------
gate_c() {
  local ok=0
  scan "service account key field" '"private[_]key"' || ok=1
  scan "service account key type" '"type"[[:space:]]*:[[:space:]]*"service[_]account"' || ok=1

  if [ "$ok" -eq 0 ]; then
    pass "Gate C — no exported service account keys"
  else
    fail "Gate C — exported service account key material"
  fi
}

# ---------------------------------------------------------------------------
# Gate D — no pull_request_target. Scoped to workflow files under
# .github/workflows/, the only place and the only extensions GitHub reads
# workflows from, so the scoping is complete rather than a compromise (F0 spec
# §W6.1, issue #4).
#
# The extensions matter: the first draft scanned the whole directory and failed
# on .github/workflows/README.md, which documents the trigger it must not use.
# The invariant is a property of workflow files — a document naming the string is
# not a defect, and the fix is to say which files are workflow files rather than
# to start an exclusion list.
# ---------------------------------------------------------------------------
gate_d() {
  if scan "fork-privileged trigger" 'pull_request[_]target' \
    '.github/workflows/*.yml' '.github/workflows/*.yaml'; then
    pass "Gate D — no pull_request_target in workflows"
  else
    fail "Gate D — pull_request_target in a workflow"
  fi
}

# ---------------------------------------------------------------------------
# Gate E — retired project name, whole repository, case-insensitive. Hygiene
# rather than correctness: a stale dataset name would fail loudly at query time.
# The live reintroduction vector is documents re-derived from external snapshots
# that predate the rename.
# ---------------------------------------------------------------------------
gate_e() {
  local matches
  matches="$(repo_files | xargs -0 -r grep -nEi -- 'agent[-_. ]?lens' 2>/dev/null || true)"

  if [ -n "$matches" ]; then
    printf '      retired project name:\n'
    printf '%s\n' "$matches" | sed 's/^/        /'
    fail "Gate E — retired project name present"
  else
    pass "Gate E — retired project name absent"
  fi
}

printf 'invariant gates (F0 spec §W6.2)\n\n'

gate_a
gate_b
gate_c
gate_d
gate_e

printf '\n'
if [ "${#failed_gates[@]}" -gt 0 ]; then
  printf '%d gate(s) failed:\n' "${#failed_gates[@]}"
  printf '  - %s\n' "${failed_gates[@]}"
  exit 1
fi

printf 'all gates passed\n'
