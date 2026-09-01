#!/usr/bin/env bash
#
# The cloud end-to-end harness (F2 completion directive v1.7, F2C-04.2, Decisions 6-13).
#
#     make e2e-cloud       PLUMBLINE_E2E_TARGET=cloud E2E_RUN_ID=<id>
#     make e2e-cloud-drill PLUMBLINE_E2E_TARGET=cloud E2E_RUN_ID=<id>
#
# READ THIS BEFORE RUNNING IT AGAINST THE CLOUD.
#
# The first cloud execution of this harness *is* the DoD 7b exam (F2C-11), and the exam is
# taken once. Amendment 6 forbids running it against the cloud before then. That is why the
# default target is the emulator and why cloud needs an explicit variable and an explicit
# run id: a forbidden action guarded only by a remembered rule is this project's named
# anti-pattern, so it is a mechanism instead.
#
# Two entry points, one tool (Decision 9). The happy path and the drill are separate exams:
# the drill needs the DLQ drained to zero and a recorded separation from F2C-08.2's channel
# test, and neither holds at first delivery. One entry point would fire DoD 7b and DoD 4
# together and make both weaker.
#
# Stages are the branches of the fault tree in docs/runbooks/wave4-first-delivery.md, and
# the result JSON names the stage reached, so triage of a failed exam starts at the right
# section of the runbook instead of being improvised.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

drill=0
[ "${1:-}" = "--drill" ] && drill=1

state=".e2e-cloud"
run_id="${E2E_RUN_ID:-}"
harness=(python3 scripts/e2e/cloud.py --run-id "$run_id")

step() { printf '\n=== %s\n' "$1"; }
fail() { printf '\ne2e-cloud: FAILED at stage %s\n' "$1" >&2; exit 1; }

# Arming, first and always. Delegated to the harness so the rule lives in one place and
# is unit-tested there rather than restated here in shell.
"${harness[@]}" --emit corpus --corpus-out "${state}/corpus" || exit $?

if [ "${PLUMBLINE_E2E_TARGET:-emulator}" != "cloud" ]; then
  # The harness already said so and exited 0; stop before any cloud call.
  exit 0
fi

mkdir -p "$state"

# ---------------------------------------------------------------------------
# Stage 0 — view provenance. Before anything is sent.
#
# A stale view fails the golden diff with a normalization-shaped error that is really a
# deployment-shaped one, and this phase has already spent four days on one misread failure.
# ---------------------------------------------------------------------------
step "stage view_provenance"
"${harness[@]}" --emit provenance || fail view_provenance

if [ "$drill" = "1" ]; then
  # -------------------------------------------------------------------------
  # The drill (F2C-13/14, DoD 4). Preconditions first: a drill that starts from a
  # non-empty DLQ cannot attribute what it finds there to itself.
  # -------------------------------------------------------------------------
  step "drill precondition: dead-letter queue drained"
  depth="$("${harness[@]}" --emit depth)" || fail publish
  printf '  traces-dlq-pull depth: %s\n' "$depth"
  if [ "$depth" != "0" ]; then
    printf '  the drill needs a drained queue; %s message(s) are already there\n' "$depth" >&2
    fail publish
  fi

  printf '\n  The remaining drill steps publish a poison payload and wait for the alert.\n'
  printf '  That alert reaches an inbox outside the project, so it is send-shaped and needs\n'
  printf '  a per-instance go-ahead (directive §4). It is also separated from the F2C-08.2\n'
  printf '  channel test by at least 30 minutes or by a marker (Decision 14).\n'
  printf '\n  Not automated past this point on purpose: this script must not be the thing\n'
  printf '  that fires it.\n'
  exit 0
fi

# ---------------------------------------------------------------------------
# The happy path.
# ---------------------------------------------------------------------------
step "normalizing the same corpus locally"
: "${PLUMBLINE_E2E_API_KEY_ID:?set PLUMBLINE_E2E_API_KEY_ID to the key id the cloud run uses}"
dotnet run --project worker/Plumbline.Fixtures -- \
  --normalize "${state}/corpus" --out "${state}/local-rows.ndjson" \
  --api-key-id "$PLUMBLINE_E2E_API_KEY_ID" || fail normalize

step "stage publish"
: "${PLUMBLINE_E2E_API_KEY:?set PLUMBLINE_E2E_API_KEY; key plaintext is Lane C custody and is never stored here}"
collector="$(gcloud run services describe collector --region us-central1 \
  --project plumbline-19458 --format='value(status.url)')"
printf '  collector: %s\n' "$collector"

for payload in "${state}"/corpus/*.otlp.json; do
  binary="${payload%.otlp.json}.pb"
  dotnet run --project worker/Plumbline.Fixtures -- --encode "$payload" "$binary" || fail publish
  code="$(curl -sS -o /dev/null -w '%{http_code}' -X POST "${collector}/v1/traces" \
    -H 'Content-Type: application/x-protobuf' \
    -H "x-plumbline-api-key: ${PLUMBLINE_E2E_API_KEY}" \
    --data-binary "@${binary}")"
  printf '  %-44s HTTP %s\n' "$(basename "$payload")" "$code"
  [ "$code" = "200" ] || fail publish
done

# push_auth, normalize and write are the worker's stages. The harness observes them by
# their effect -- rows appearing -- because it has no other honest view of them.
step "stage push_auth / normalize / write — waiting for rows"
for attempt in $(seq 1 60); do
  if "${harness[@]}" --emit diff --local-rows "${state}/local-rows.ndjson" >/dev/null 2>&1; then
    break
  fi
  [ "$attempt" = "60" ] && printf '  no matching rows after 60s\n'
  sleep 2
done

step "stage query — the golden diff"
"${harness[@]}" --emit diff --local-rows "${state}/local-rows.ndjson" || fail query

step "stage query — DoD 3's walling proof"
"${harness[@]}" --emit queries

printf '\ne2e-cloud: PASS (stage complete)\n'
