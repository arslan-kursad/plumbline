#!/usr/bin/env bash
#
# Pre-flight for the Claude Code capture (F3E-03, #10, architecture §10 OQ-4).
#
#     scripts/capture/claude-code-preflight.sh
#     scripts/capture/claude-code-preflight.sh --self-test
#
# Every check below was a prose prerequisite in claude-code-capture.md §3 and §4.3 — a
# line a human confirmed by reading it. Reading them is how three capture attempts were
# spent and every one failed at authentication before reaching a tool call.
#
# The scarcest resource on the path to 2026-10-04 is a human attempt at this capture.
# Spending one to learn nothing is the failure this script exists to prevent, so it
# refuses to be optimistic: an unknown is reported as unknown and blocks, rather than
# passing quietly and letting the session discover it.
#
# Lane C runs this. Lane A cannot: check 7 needs a real authenticated Claude Code, and a
# nested one cannot authenticate.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
fail=0
warn=0

ok()    { printf '  ok      %s\n' "$1"; }
bad()   { printf '  BLOCKED %s\n      → %s\n' "$1" "$2"; fail=1; }
soft()  { printf '  warn    %s\n      → %s\n' "$1" "$2"; warn=1; }

# --- self-test ------------------------------------------------------------------
# Proves the script's own logic, not the environment: on this machine most checks are
# expected to fail, and that is the point — a pre-flight that passes everywhere is not
# checking anything. What is asserted is that it *reports* rather than crashes, and that
# a deliberately wrong environment is refused.
if [ "${1:-}" = "--self-test" ]; then
  echo "claude-code preflight self-test"
  echo
  out="$(CLAUDE_CODE_ENABLE_TELEMETRY=0 OTEL_EXPORTER_OTLP_PROTOCOL=http/json \
         PLUMBLINE_CAPTURE_DIR="$repo/inside-the-repo" \
         PLUMBLINE_SKIP_AUTH_PROBE=1 "$0" 2>&1)"
  rc=$?
  t=0
  expect() { if printf '%s' "$out" | grep -q -- "$1"; then echo "  ok    $2"; else echo "  FAIL  $2"; t=1; fi; }

  expect 'CLAUDE_CODE_ENABLE_TELEMETRY'      "refuses telemetry disabled"
  expect 'http/protobuf'                      "refuses the wrong exporter protocol"
  expect 'inside the repository'              "refuses a capture directory inside the repo"
  [ "$rc" -ne 0 ] && echo "  ok    non-zero exit on a bad environment" || { echo "  FAIL  exited 0 on a bad environment"; t=1; }

  # capture_report.py's terminal states. It ships with the pre-flight because they are
  # one deliverable: the pre-flight stops an attempt being wasted, the report stops one
  # ending without a name.
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

  # `set -o pipefail` is on, and capture_report.py exits non-zero for three of the four
  # terminal states by design. Piping it straight into grep would therefore report the
  # tool's verdict instead of grep's match — which the self-test caught, and which is the
  # same shape as every other finding here: the assertion looked right and measured
  # something else.
  states() {
    local dir="$1" want="$2" label="$3" out
    out="$(python3 "$here/capture_report.py" "$dir" 2>&1 || true)"
    if printf '%s' "$out" | grep -q -- "$want"; then echo "  ok    $label"
    else echo "  FAIL  $label"; t=1; fi
  }

  mkdir -p "$tmp/empty"
  states "$tmp/empty" 'NO-EXPORT' "report names NO-EXPORT on an empty directory"

  # The real corpus payload carries interaction and llm_request and no tool span, which
  # is the boundary every capture so far has hit. Using it rather than a synthetic file
  # anchors this assertion to the artefact the finding came from.
  mkdir -p "$tmp/model-only"
  cp "$repo/testdata/fixtures/claude-code/happy-path/request.pb" "$tmp/model-only/" 2>/dev/null
  states "$tmp/model-only" 'REACHED-MODEL-NOT-TOOLS' "report names REACHED-MODEL-NOT-TOOLS on the known boundary"

  # A span type no capture has produced. Synthetic on purpose: the artefact does not
  # exist yet, and the report must recognise it when it does.
  mkdir -p "$tmp/moved"; printf 'x\x00claude_code.tool\x00y' > "$tmp/moved/request.pb"
  states "$tmp/moved" 'BOUNDARY MOVED' "report names BOUNDARY MOVED when a new span type appears"

  mkdir -p "$tmp/alien"; printf 'not an otlp payload' > "$tmp/alien/request.pb"
  states "$tmp/alien" 'EXPORTED-BUT-UNRECOGNISED' "report names EXPORTED-BUT-UNRECOGNISED on foreign bytes"

  echo
  [ "$t" -eq 0 ] || { echo "preflight self-test FAILED"; exit 1; }
  echo "preflight self-test passed"
  exit 0
fi

echo "claude-code capture pre-flight"
echo

# 1 — the binary
if command -v claude >/dev/null 2>&1; then
  ok "claude on PATH ($(command -v claude))"
else
  bad "claude is not on PATH" "install Claude Code, then re-run"
fi

# 2 — python for the receiver
if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
  ok "python3 $(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])') (receiver needs 3.9+, stdlib only)"
else
  bad "python3 is missing or older than 3.9" "the receiver is standard library only but needs 3.9"
fi

# 3 — the beta gate. All three, and #10 §1 records that none is optional.
for pair in "CLAUDE_CODE_ENABLE_TELEMETRY=1" "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1" "OTEL_TRACES_EXPORTER=otlp"; do
  name="${pair%%=*}"; want="${pair#*=}"; got="${!name:-}"
  if [ "$got" = "$want" ]; then ok "$name=$want"
  else bad "$name is '${got:-unset}', needs '$want'" "spans are not exported without all three (#10 §1)"; fi
done

# 4 — protocol. The fixture is the bytes, so json is not interchangeable here.
for name in OTEL_EXPORTER_OTLP_PROTOCOL OTEL_EXPORTER_OTLP_TRACES_PROTOCOL; do
  got="${!name:-}"
  if [ "$got" = "http/protobuf" ]; then ok "$name=http/protobuf"
  else bad "$name is '${got:-unset}', needs 'http/protobuf'" "the P11 evidence used http/json; for a fixture the bytes are the artefact"; fi
done

# 5 — endpoint, and whether anything is listening on it
endpoint="${OTEL_EXPORTER_OTLP_ENDPOINT:-}"
if [ -z "$endpoint" ]; then
  bad "OTEL_EXPORTER_OTLP_ENDPOINT is unset" "export http://127.0.0.1:4318"
else
  ok "OTEL_EXPORTER_OTLP_ENDPOINT=$endpoint"
  host_port="${endpoint#*://}"; host="${host_port%%:*}"; port="${host_port##*:}"; port="${port%%/*}"
  if python3 - "$host" "$port" <<'PY' 2>/dev/null
import socket, sys
s = socket.socket(); s.settimeout(1.5)
raise SystemExit(0 if s.connect_ex((sys.argv[1], int(sys.argv[2]))) == 0 else 1)
PY
  then ok "something is listening on $host:$port"
  else soft "nothing is listening on $host:$port" "start the receiver first; this is a warning because the order is yours"; fi
fi

# 6 — the capture directory. Refusing one inside the tree is not a style rule: a raw
# capture carries user.id, user.email and organization.id, and this repository is public.
capdir="${PLUMBLINE_CAPTURE_DIR:-$HOME/plumbline-captures/$(date -u +%Y-%m-%d)}"
case "$(cd "$(dirname "$capdir")" 2>/dev/null && pwd || echo "$capdir")" in
  "$repo"|"$repo"/*) bad "capture directory is inside the repository: $capdir" "a raw capture carries personal data and this repository is public (CLAUDE.md)" ;;
  *) mkdir -p "$capdir" 2>/dev/null && ok "capture directory $capdir (outside the repository)" \
       || bad "cannot create $capdir" "choose a writable path outside the repository" ;;
esac

# 7 — the hook workspace, because claude_code.hook spans exist only if a hook runs
ws="${PLUMBLINE_CAPTURE_WORKSPACE:-$HOME/plumbline-capture-workspace}"
if [ -f "$ws/.claude/settings.json" ] && grep -q 'PostToolUse' "$ws/.claude/settings.json" 2>/dev/null; then
  ok "hook workspace $ws carries a PostToolUse hook"
else
  soft "no PostToolUse hook at $ws/.claude/settings.json" "claude_code.hook spans are emitted only when a hook runs — see the runbook §4.2"
fi

# 8 — authentication. The one that has failed every time, and the only check that costs
# a real round trip. Deliberately last: everything above is free.
if command -v claude >/dev/null 2>&1; then
  if [ "${PLUMBLINE_SKIP_AUTH_PROBE:-}" = "1" ]; then
    soft "authentication not probed (PLUMBLINE_SKIP_AUTH_PROBE=1)" "the capture will discover it instead, which is what this script exists to avoid"
  else
    probe="$(claude -p 'reply with the single word ok' 2>&1 </dev/null | head -c 400)"
    case "$probe" in
      *[Oo][Kk]*)              ok "claude answered a non-interactive prompt — authenticated" ;;
      *auth*|*Auth*|*login*|*Login*|*credential*|*401*|*403*)
                               bad "claude is not authenticated" "run 'claude' once interactively and complete login, then re-run. This is the failure every prior attempt hit" ;;
      "")                      bad "claude produced no output" "run 'claude -p ok' by hand and read the error" ;;
      *)                       soft "claude answered, but not recognisably" "output began: $(printf '%s' "$probe" | head -c 120)" ;;
    esac
  fi
fi

echo
if [ "$fail" -ne 0 ]; then
  echo "PRE-FLIGHT BLOCKED — fix the items above before spending a capture attempt."
  exit 1
fi
[ "$warn" -ne 0 ] && echo "pre-flight passed with warnings — read them; each is a way to spend an attempt and learn nothing."
echo "pre-flight passed. Start the receiver, then follow claude-code-capture.md §4.3."
exit 0
