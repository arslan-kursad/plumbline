#!/usr/bin/env bash
#
# The local end-to-end run (F1 W6, DoD item 2). One command:
#
#     make e2e
#
# Fixtures in through the collector, out through the BigQuery views, compared against the
# same golden files the unit tests use, with the poison payloads provably in the
# dead-letter topic. Deterministic and CI-runnable: flakiness here is a defect, not an
# environment excuse.
#
# Nothing in this path holds a GCP credential. That absence is the assertion that F1
# cannot touch the cloud — see the credentials check at the end.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

state=".e2e"
compose=(docker compose)
keep_up="${E2E_KEEP_UP:-0}"

step() { printf '\n=== %s\n' "$1"; }

cleanup() {
  local status=$?
  if [ "$keep_up" != "1" ]; then
    step "tearing down"
    "${compose[@]}" --profile tools down --volumes --remove-orphans >/dev/null 2>&1 || true
  else
    printf '\nstack left running (E2E_KEEP_UP=1); tear down with: docker compose --profile tools down -v\n'
  fi
  exit "$status"
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# 0. A fresh API key, generated per run.
#
# The plaintext key is never committed: it is generated here, hashed into the registry
# the collector reads, and left in a gitignored directory. Gate F would fail the build on
# a real key in the repository, and the way to keep that gate meaningful is to have no
# key to commit rather than an exception for the one that is.
# ---------------------------------------------------------------------------
step "generating a run key"
mkdir -p "$state"
api_key="plb_local_$(head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n')"
if command -v sha256sum >/dev/null 2>&1; then
  key_hash="$(printf '%s' "$api_key" | sha256sum | cut -d' ' -f1)"
else
  key_hash="$(printf '%s' "$api_key" | shasum -a 256 | cut -d' ' -f1)"
fi
printf '%s' "$api_key" > "${state}/api-key"
cat > "${state}/keys.json" <<JSON
{
  "keys": [
    {
      "api_key_id": "local-test",
      "key_sha256": "${key_hash}",
      "source_dialect": "claude-code",
      "rate_limit_per_second": 100,
      "burst": 200,
      "status": "active"
    }
  ]
}
JSON
printf '  api_key_id=local-test (plaintext key in %s/api-key, gitignored)\n' "$state"

# ---------------------------------------------------------------------------
# 1. Bring up the stand-ins and the two services.
# ---------------------------------------------------------------------------
step "starting the stack"
"${compose[@]}" up -d --build pubsub bigquery collector worker

step "waiting for the services"
for attempt in $(seq 1 60); do
  collector_ok=$(curl -sf -o /dev/null -w '%{http_code}' http://localhost:4318/healthz || true)
  worker_ok=$(curl -sf -o /dev/null -w '%{http_code}' http://localhost:8080/healthz || true)
  if [ "$collector_ok" = "200" ] && [ "$worker_ok" = "200" ]; then
    printf '  collector and worker are healthy (after %ss)\n' "$attempt"
    break
  fi
  if [ "$attempt" = "60" ]; then
    printf '  collector=%s worker=%s after 60s\n' "$collector_ok" "$worker_ok" >&2
    "${compose[@]}" logs --tail 40 collector worker >&2
    exit 1
  fi
  sleep 1
done

curl -sf http://localhost:8080/healthz | sed 's/^/  worker health: /'

# ---------------------------------------------------------------------------
# 2. Seed the topology and the schema.
# ---------------------------------------------------------------------------
step "seeding"
python3 scripts/e2e/seed.py

# ---------------------------------------------------------------------------
# 3. Send every fixture, poison included.
# ---------------------------------------------------------------------------
step "sending fixtures"
"${compose[@]}" --profile tools run --rm --no-deps sender

# ---------------------------------------------------------------------------
# 4. Wait for the rows, rather than sleeping and hoping.
# ---------------------------------------------------------------------------
step "waiting for rows"
expected_rows="$(python3 - <<'PY'
import json, pathlib
total = 0
for path in pathlib.Path("testdata/fixtures").rglob("expected-rows.json"):
    total += len(json.loads(path.read_text()))
print(total)
PY
)"
printf '  expecting %s row(s) across the corpus\n' "$expected_rows"

for attempt in $(seq 1 90); do
  actual="$(python3 scripts/e2e/query-rows.py --view spans_deduped --out /dev/null --count-only 2>/dev/null || echo 0)"
  if [ "$actual" -ge "$expected_rows" ]; then
    printf '  %s row(s) after %ss\n' "$actual" "$attempt"
    break
  fi
  if [ "$attempt" = "90" ]; then
    printf '  only %s of %s rows after 90s\n' "$actual" "$expected_rows" >&2
    "${compose[@]}" logs --tail 60 worker >&2
    exit 1
  fi
  sleep 1
done

# ---------------------------------------------------------------------------
# 5. Compare what the pipeline produced with the golden files.
# ---------------------------------------------------------------------------
step "querying the views"
python3 scripts/e2e/query-rows.py --view spans_deduped --out "${state}/spans_deduped.ndjson"
python3 scripts/e2e/query-rows.py --view spans_real --out "${state}/spans_real.ndjson"

step "comparing against the golden files"
dotnet run --project worker/Plumbline.Fixtures -- --verify "${state}/spans_deduped.ndjson"

# ---------------------------------------------------------------------------
# 6. The poison payloads have to be in the dead-letter topic.
#
# One per dialect with a poison case. This is the no-silent-degradation property: an
# unreadable message is retained where an operator can find it, not dropped.
# ---------------------------------------------------------------------------
step "checking the dead-letter topic"
poison_count="$(find testdata/fixtures -path '*/poison/request.pb' | wc -l | tr -d ' ')"
python3 scripts/e2e/dlq-depth.py --expect "$poison_count"

# ---------------------------------------------------------------------------
# 7. No credential took part in any of this.
# ---------------------------------------------------------------------------
step "asserting the run touched no cloud"
if "${compose[@]}" config | grep -qiE 'GOOGLE_APPLICATION_CREDENTIALS|service[_]account|/\.config/gcloud'; then
  printf 'a GCP credential is referenced by the compose stack; F1 must not reach the cloud\n' >&2
  exit 1
fi
printf '  no GCP credential is mounted or referenced by the stack\n'

printf '\nend-to-end: PASS\n'
