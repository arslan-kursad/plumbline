#!/bin/sh
#
# Posts every fixture payload to the collector over OTLP/HTTP, with the seeded API key.
# Runs inside the `sender` container, on the compose network.
#
# Poison payloads are sent too, and deliberately: the point of the end-to-end run is that
# one unreadable message reaches the dead-letter topic while the good ones land, so the
# poison has to travel the same path as everything else rather than being injected
# downstream.

set -eu

collector="${COLLECTOR:-http://collector:4318}"
key="$(cat /e2e/api-key)"

status=0
sent=0

for payload in /testdata/fixtures/*/*/request.pb; do
  case "$payload" in
    */poison/request.pb) expect="accepted (unreadable downstream)" ;;
    *) expect="accepted" ;;
  esac

  code="$(curl -sS -o /dev/null -w '%{http_code}' \
    -X POST "${collector}/v1/traces" \
    -H 'Content-Type: application/x-protobuf' \
    -H "x-plumbline-api-key: ${key}" \
    --data-binary "@${payload}")"

  printf '  %-60s HTTP %s  (%s)\n' "${payload#/testdata/fixtures/}" "$code" "$expect"

  if [ "$code" != "200" ]; then
    status=1
  fi
  sent=$((sent + 1))
done

printf '\nsent %d payload(s)\n' "$sent"

if [ "$status" -ne 0 ]; then
  printf 'at least one payload was refused by the collector\n' >&2
fi

exit "$status"
