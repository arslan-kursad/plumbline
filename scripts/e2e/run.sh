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

# No fixture carries `synthetic=true`, so spans_real must hold exactly what
# spans_deduped holds. Checking it makes the second view a tested object rather than a
# file that was applied successfully.
deduped_rows="$(wc -l < "${state}/spans_deduped.ndjson" | tr -d ' ')"
real_rows="$(wc -l < "${state}/spans_real.ndjson" | tr -d ' ')"
if [ "$deduped_rows" != "$real_rows" ]; then
  printf '  spans_deduped has %s row(s) and spans_real has %s; no fixture is synthetic, so they must agree\n' \
    "$deduped_rows" "$real_rows" >&2
  exit 1
fi
printf '  spans_real agrees with spans_deduped (%s rows, none synthetic)\n' "$real_rows"

step "comparing against the golden files"
dotnet run --project worker/Plumbline.Fixtures -- --verify "${state}/spans_deduped.ndjson"

# ---------------------------------------------------------------------------
# 6. Present the dedup view a duplicate it actually has to collapse.
#
# The local sink writes through an explicit COMMITTED stream, so the stack produces no
# at-least-once duplicates of its own (f3e-01a S2). Every assertion above therefore holds
# identically whether dedup works or whether there was simply nothing to dedup -- a
# working view and an absent duplicate are the same output, which is the empty-result
# blindness this phase keeps finding.
#
# Replaying one payload through the real path -- collector, Pub/Sub, worker, Storage
# Write API -- is what redelivery looks like, and the worker deliberately carries no
# deduplication (IngestionEndpoint.cs). Nothing is written directly: insertAll is a
# forbidden cost invariant, and a row inserted beside the pipeline would not exercise the
# path the claim is about.
#
# Poison is excluded from the replay because the dead-letter check below asserts an exact
# depth, and re-sending it would double the count.
# ---------------------------------------------------------------------------
replay_fixture="claude-code/happy-path"
replay_rows="$(python3 -c "import json;print(len(json.load(open('testdata/fixtures/${replay_fixture}/expected-rows.json'))))")"

step "replaying ${replay_fixture} to produce a duplicate"
"${compose[@]}" --profile tools run --rm --no-deps \
  -e PLUMBLINE_ONLY="${replay_fixture}" sender

step "waiting for the replayed rows to land"
want_base=$((expected_rows + replay_rows))
printf '  base table should reach %s row(s): %s + %s replayed\n' \
  "$want_base" "$expected_rows" "$replay_rows"

for attempt in $(seq 1 90); do
  base_now="$(python3 scripts/e2e/query-rows.py --view spans --out /dev/null --count-only 2>/dev/null || echo 0)"
  if [ "$base_now" -ge "$want_base" ]; then
    printf '  %s row(s) in the base table after %ss\n' "$base_now" "$attempt"
    break
  fi
  if [ "$attempt" = "90" ]; then
    printf '  only %s of %s base rows after 90s; the replay did not land\n' \
      "$base_now" "$want_base" >&2
    "${compose[@]}" logs --tail 60 worker >&2
    exit 1
  fi
  sleep 1
done

step "asserting the dedup view returns the later row, not just one row"
python3 scripts/e2e/dedup-probe.py || {
  printf '  spans_deduped did not collapse the duplicate correctly\n' >&2
  exit 1
}

# ---------------------------------------------------------------------------
# 7. The poison payloads have to be in the dead-letter topic.
#
# One per dialect with a poison case. This is the no-silent-degradation property: an
# unreadable message is retained where an operator can find it, not dropped.
# ---------------------------------------------------------------------------
step "checking the dead-letter topic"
poison_count="$(find testdata/fixtures -path '*/poison/request.pb' | wc -l | tr -d ' ')"
printf '  expecting %s dead-lettered message(s)\n' "$poison_count"

# One call, which polls internally. Dead-lettering is not immediate — the subscription
# redelivers up to max_delivery_attempts, each attempt waiting out an ack deadline — and
# a pulled-but-unacked message is leased, so a second check moments later would see an
# empty subscription and disagree with the first.
python3 scripts/e2e/dlq-depth.py --expect "$poison_count" --timeout 120 || {
  printf '  the poison payloads did not reach traces-dlq\n' >&2
  "${compose[@]}" logs --tail 60 worker >&2
  exit 1
}

# ---------------------------------------------------------------------------
# 8. No credential took part in any of this.
# ---------------------------------------------------------------------------
step "asserting the run touched no cloud"
if "${compose[@]}" config | grep -qiE 'GOOGLE_APPLICATION_CREDENTIALS|service[_]account|/\.config/gcloud'; then
  printf 'a GCP credential is referenced by the compose stack; F1 must not reach the cloud\n' >&2
  exit 1
fi
printf '  no GCP credential is mounted or referenced by the stack\n'

printf '\nend-to-end: PASS\n'
