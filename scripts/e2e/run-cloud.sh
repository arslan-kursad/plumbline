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

# Decision 11. Every exit writes the stage it reached, including the ones that leave
# before any cloud call -- a run that stopped on a missing variable and a run that
# stopped on a rejected token are different facts, and reconstructing which from the
# files left on disk is the improvisation the fault tree exists to prevent.
record() { "${harness[@]}" --emit result --stage "$1" --failure "${2:-}" >/dev/null 2>&1 || true; }
fail() {
  record "$1" "${2:-stopped at ${1}}"
  printf '\ne2e-cloud: FAILED at stage %s\n' "$1" >&2
  printf 'result: .e2e-cloud/result.json\n' >&2
  printf 'triage: docs/runbooks/wave4-first-delivery.md section 2\n' >&2
  exit 1
}

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

  # Both gates are mechanisms, not reminders: PLUMBLINE_E2E_DRILL_ARMED=yes on top of the
  # cloud target, and Decision 14's 30-minute separation from the channel test enforced
  # against a recorded timestamp. The script may fire the alert; it may not do so by
  # accident, and it may not do so early.
  step "drill precondition: armed, separated, queue drained"
  "${harness[@]}" --emit drill-check || fail publish

  step "stage publish — the poison fixture, straight to traces"
  "${harness[@]}" --emit drill-publish --result "${state}/drill-publish.json" \
    | tee "${state}/drill-publish.json" || fail publish

  step "stage write — waiting for the dead-letter"
  for attempt in $(seq 1 40); do
    depth="$("${harness[@]}" --emit depth 2>/dev/null || echo 0)"
    [ "$depth" != "0" ] && { printf '  depth reached %s after ~%ss\n' "$depth" "$((attempt * 15))"; break; }
    [ "$attempt" = "40" ] && { printf '  depth still 0 after ~600s\n' >&2; fail write; }
    sleep 15
  done

  printf '\n  The alert fires from this depth and reaches an inbox this script cannot read.\n'
  printf '  Arrival is confirmed by the person holding it; depth and the published marker\n'
  printf '  are what is measurable here.\n'
  record complete
  printf '\ne2e-cloud-drill: poison published and dead-lettered (stage complete)\n'
  exit 0
fi

# ---------------------------------------------------------------------------
# The happy path.
# ---------------------------------------------------------------------------
step "normalizing the same corpus locally"
if [ -z "${PLUMBLINE_E2E_API_KEY_ID:-}" ]; then
  printf '  PLUMBLINE_E2E_API_KEY_ID is unset. It is the key id the cloud run uses.\n' >&2
  fail normalize "PLUMBLINE_E2E_API_KEY_ID unset"
fi
dotnet run --project worker/Plumbline.Fixtures -- \
  --normalize "${state}/corpus" --out "${state}/local-rows.ndjson" \
  --api-key-id "$PLUMBLINE_E2E_API_KEY_ID" || fail normalize

step "stage publish"
if [ -z "${PLUMBLINE_E2E_API_KEY:-}" ]; then
  printf '  PLUMBLINE_E2E_API_KEY is unset or empty.\n' >&2
  printf '  Key plaintext is Lane C custody and is never stored here (directive section 4).\n' >&2
  printf '  If it came from a file, check the file is not empty: keyctl runs inside the\n' >&2
  printf '  collector module, so it needs -C collector or a cd.\n' >&2
  fail publish "PLUMBLINE_E2E_API_KEY unset or empty"
fi
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

record complete
printf '\ne2e-cloud: PASS (stage complete)\n'
