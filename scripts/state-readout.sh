#!/usr/bin/env bash
#
# One read-only artefact of live GCP state (F2 completion directive v1.7,
# Decision 5).
#
#     scripts/state-readout.sh [--window-lower YYYY-MM-DD] [--window-upper YYYY-MM-DD]
#     scripts/state-readout.sh --self-test
#
# Collects every reading the directive's remaining verification steps need --
# Cloud Run configs, project IAM policy, deployed BigQuery view DDL, Pub/Sub
# subscription config with its dead-letter policy, DLQ depth, Artifact Registry
# tags, and row counts by `synthetic` and run id over an explicit partition
# window -- so that no F2 verification depends on a human pasting command output.
#
# Each reading carries the command that produced it. A failed reading is recorded
# as failed rather than dropped: a missing reading and a zero reading must not
# look alike.
#
# Reads it cannot perform are listed under "blocked" with the rule that stops
# each one, named rather than worked around. Today that is gross period cost:
# `Bash(gcloud billing:*)` is denied and that denial is correct.
#
# Nothing here mutates, and `--self-test` proves the guard that enforces it.
# Exits non-zero if any reading failed.
#
# The output is an evidence artefact. Archive it under docs/evidence/ with the
# date it was taken; do not summarise it into one.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

for tool in gcloud bq curl python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf 'state-readout: %s is not on PATH\n' "$tool" >&2
    exit 2
  fi
done

exec python3 scripts/state_readout.py "$@"
