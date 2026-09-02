#!/usr/bin/env bash
#
# One-command capture path for a first-party emitter (F3E-02).
#
#     scripts/capture/capture.sh langgraph-python
#     scripts/capture/capture.sh dotnet-agent
#     scripts/capture/capture.sh --self-test
#
# Lane C runs this. Lane A built it and cannot run it: a capture needs a real agent
# driven by a human, and the output lands outside the repository by design.
#
# It does three things and refuses rather than guessing at any of them: starts the file
# receiver, prints the exporter environment the agent needs, and — once the capture
# exists — runs redaction and manifest validation over it. The raw capture is never
# written into the repository (ADR-0006; CLAUDE.md's public-repository rule).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../.." && pwd)"

if [ "${1:-}" = "--self-test" ]; then
  echo "capture self-test"
  echo
  fail=0
  check() { if eval "$2" >/dev/null 2>&1; then echo "  ok    $1"; else echo "  FAIL  $1"; fail=1; fi; }
  ncheck() { if eval "$2" >/dev/null 2>&1; then echo "  FAIL  $1"; fail=1; else echo "  ok    $1"; fi; }

  # The validator discriminates. All three cases, because "rejects everything" and
  # "accepts everything" are both untested validators.
  check  "accepts a complete captured manifest" \
         "python3 '$here/manifest_validate.py' '$here/testdata/admissible/manifest.yaml'"
  ncheck "rejects a captured manifest missing one row-1.2 field" \
         "python3 '$here/manifest_validate.py' '$here/testdata/missing-field/manifest.yaml'"
  ncheck "rejects the existing hand-authored corpus" \
         "python3 '$here/manifest_validate.py' $repo/testdata/fixtures/*/manifest.yaml"

  # Redaction refuses when nothing accounts for what it found, and only then.
  ncheck "refuses a payload with identity keys and no rule file" \
         "python3 '$here/redact.py' '$repo/testdata/fixtures/claude-code/happy-path/request.otlp.json'"
  check  "redacts the same payload when the rule file accounts for it" \
         "python3 '$here/redact.py' '$repo/testdata/fixtures/claude-code/happy-path/request.otlp.json' \
            --rules '$repo/normalization/redaction/v1/claude-code.yaml' --allow user_prompt_length"

  echo
  [ "$fail" -eq 0 ] || { echo "capture self-test FAILED"; exit 1; }
  echo "capture self-test passed"
  exit 0
fi

dialect="${1:-}"
case "$dialect" in
  langgraph-python|dotnet-agent) ;;
  *)
    echo "usage: capture.sh <langgraph-python|dotnet-agent> | --self-test" >&2
    echo >&2
    echo "claude-code is deliberately not offered here: its capture is blocked on #10" >&2
    echo "(beta gate, and every attempt so far failed at authentication before reaching" >&2
    echo "a tool call). F3E-03 owns that path." >&2
    exit 2 ;;
esac

out="${PLUMBLINE_CAPTURE_DIR:-$HOME/plumbline-captures/$(date -u +%Y-%m-%d)-$dialect}"
mkdir -p "$out"

cat <<TXT
capture — $dialect
output: $out   (outside the repository, and it stays there)

1. In another terminal, point the agent at the receiver:

     OTEL_TRACES_EXPORTER=otlp
     OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
     OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318

   Do not set OTEL_SEMCONV_STABILITY_OPT_IN. Its value is recorded in the manifest as
   emitted, and exporting it here would record this run's setting rather than the
   emitter's default (SC-1 row 1.2).

2. Drive one real interaction. One is enough; the corpus needs a real shape, not volume.

3. Stop the receiver, then:

     python3 scripts/capture/redact.py "$out/<file>.otlp.json" \\
       --rules normalization/redaction/v1/$dialect.yaml \\
       --out testdata/fixtures/$dialect/happy-path/request.otlp.json

   There is no rule file for $dialect yet, and that is expected: redact.py will refuse
   and name every key it found. Writing the rule file from that list is the first thing
   this capture produces.

4. Fill the manifest, then:

     python3 scripts/capture/manifest_validate.py testdata/fixtures/$dialect/manifest.yaml

TXT

exec python3 "$here/otlp-file-receiver.py" --out "$out"
