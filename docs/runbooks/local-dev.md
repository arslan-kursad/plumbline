# Runbook — local development

The whole pipeline runs on a laptop, with no GCP project and no credential:

```bash
make e2e
```

Fixtures go in through the collector and come out through the BigQuery views, compared
against the same golden files the unit tests use, with the poison payloads provably in
the dead-letter topic. That is F1's Definition of Done item 2, and it is a command rather
than a procedure so that it can also be a CI job.

## Prerequisites

| Tool | Why |
| --- | --- |
| Docker with Compose v2 | The two emulators and the two services |
| .NET 8 SDK | Builds the worker, and runs the fixture verifier at the end of the run |
| Go 1.26 | Collector tests (the image builds Go itself) |
| Python 3.9+ | Seeding and the query steps; standard library only |

`make test` needs only the two SDKs — the container runtime is for the end-to-end path.

A full run takes about two minutes on a cold GitHub-hosted runner — two emulator images
pulled, both service images built, the pipeline exercised end to end, torn down.

**A host that cannot run containers can still do most of the work.** `make test` covers
the collector, the normalization core, the worker endpoint and every golden file; what it
does not cover is the compose wiring, the Pub/Sub topology and the write path against the
stand-in. Those are what `make e2e` is for, and the CI job runs it on every pull request
that touches them (see the F1 decision log, W6.4).

## Targets

```
make help          list the targets
make test          collector (-race) + normalization + worker + golden files
make gates         the invariant gates, and the proof that each can fail
make fixtures      regenerate the binary fixtures from their OTLP/JSON twins
make e2e           the full local pipeline
make e2e-up        the same, leaving the stack running afterwards
make e2e-down      tear it down
```

## What `make e2e` does

1. **Generates an API key** into `.e2e/` (gitignored) and writes the hashed registry the
   collector reads. The plaintext key is never committed — Gate F fails the build on a
   real key in the repository, and the way to keep that gate honest is to have no key to
   commit rather than an exception for the one that is.
2. **Starts** the Pub/Sub emulator, the BigQuery stand-in, the collector and the worker.
3. **Seeds** the topology — `traces`, `traces-dlq`, a push subscription to the worker
   with `max_delivery_attempts = 5`, and a pull subscription on the dead-letter topic —
   then applies `analytics/sql/*.sql`.
4. **Sends every fixture**, poison included, through the collector's OTLP/HTTP endpoint.
5. **Waits for the rows** rather than sleeping: it polls until the expected count arrives
   or fails with the worker's logs.
6. **Queries the views** and compares the result against `expected-rows.json`, ignoring
   `ingest_time` because it is a clock.
7. **Pulls the dead-letter subscription** and requires exactly one message per poison
   fixture.
8. **Asserts no credential took part**, by refusing a stack that references one.

The collector runs with a 700-byte compressed message budget so the corpus actually
exercises the splitter. An end-to-end run where nothing was split would prove less than
it appears to.

## Poking at a running stack

```bash
make e2e-up                                   # run, then leave it up

curl -s localhost:8080/healthz | python3 -m json.tool
curl -s localhost:4318/healthz

# send one fixture by hand
curl -X POST localhost:4318/v1/traces \
  -H 'Content-Type: application/x-protobuf' \
  -H "x-plumbline-api-key: $(cat .e2e/api-key)" \
  --data-binary @testdata/fixtures/claude-code/happy-path/request.pb

python3 scripts/e2e/query-rows.py --view spans_real --out /tmp/rows.ndjson
python3 scripts/e2e/dlq-depth.py

make e2e-down
```

## Troubleshooting

**The worker's health endpoint says `push_authentication: none (...)`.** Correct locally
— the Pub/Sub emulator cannot mint Google-signed OIDC tokens — and it is printed so that
it cannot be true anywhere else without someone seeing it. The worker refuses to start
with authentication off outside a Development environment (architecture §6.1); the cloud
runs real OIDC validation (F2).

**A payload gets `413` from the collector.** A single span plus its resource and scope
exceeds the compressed budget. The collector refuses rather than truncating (§3.2). Raise
`PLUMBLINE_MAX_COMPRESSED_BYTES` in `docker-compose.yml` — the local value is deliberately
small.

**Rows never arrive.** Look at the worker first: `docker compose logs worker`. A 400 there
is the deserialize step refusing a payload, which is the poison path working. A 503 is the
sink failing, and the message will be redelivered.

**The dead-letter check finds nothing.** The push subscription's dead-letter policy is
applied at seeding time; re-run `python3 scripts/e2e/seed.py` and check its output. A
subscription created without the policy will retry a poison message forever and never
dead-letter it.

**`make e2e` leaves a stack behind after a failure.** `make e2e-down`. The run tears down
on exit unless `E2E_KEEP_UP=1`.

## What this stack is not

Every service here is a local stand-in. The Pub/Sub emulator is the official one; the
BigQuery stand-in is `goccy/bigquery-emulator` (F1 directive D4), which speaks the same
Storage Write API over gRPC that the cloud path uses — a different endpoint, not a
different code path. The key registry is a mounted file rather than Firestore (D5), and
push authentication is off rather than OIDC, because the emulator cannot mint
Google-signed tokens.

None of that makes the end-to-end run evidence about the cloud. It is evidence about the
normalization contract, the message contract, and the poison path. F2 is where the same
pipeline meets real services, and the F2 entry gate still requires the kill-switch
live-fire (#33) before anything is deployed.
