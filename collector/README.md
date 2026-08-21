# collector

Go OTLP collector: the data plane. It receives trace exports, authenticates them, rate
limits per key, splits oversized ones, compresses, and publishes to Pub/Sub.

What it does **not** do is the more useful half of the description. It does not parse
span semantics, normalize attributes, or apply dialect logic (architecture §2.1), and it
never re-models the protobuf bytes on their way through (ADR-0001). Adding a fourth
dialect changes nothing here.

## The boundary, and how it is held

Three mechanisms, in decreasing order of how much they would survive a determined
contributor:

1. **No OTLP message types are imported.** The gRPC server runs a codec whose only
   message type is `[]byte` (`internal/receiver/grpc.go`), so a handler has nothing to
   deserialize into. `boundary_test.go` parses every source file and fails on an import
   of `go.opentelemetry.io/proto`, `…/otel/semconv` or `…/collector`, and a companion
   test proves that check can fail.
2. **Byte identity is asserted.** `TestPayloadBytesInEqualPayloadBytesOut` sends every
   fixture through both transports and compares what the publisher received, after
   gunzip, with what the receiver was handed. This is F1 DoD item 3, and it is the
   mechanical form of "the bytes are never mutated".
3. **Splitting is envelope-only.** `internal/otlpwire` knows the protobuf wire format
   and six field numbers — the repeated members of `ExportTraceServiceRequest`,
   `ResourceSpans` and `ScopeSpans`, and their context fields. It regroups spans and
   copies everything else through verbatim. A span is moved, never read.

## Splitting, and why it can refuse

The compressed payload budget is 4 MiB (§3.2, against a 10 MB push limit). An export
over budget is split at the resource level, then the scope level, then span by span;
every part carries the resource and scope of the spans in it, so no span is left
unattributable.

When a single span with its context still does not fit, the export is **refused** —
`413` on HTTP, `InvalidArgument` on gRPC — because the alternative is truncation, and
§3.2 says oversized batches are split, never truncated. A refusal the client can see
beats a silent partial write.

## Configuration

Environment only; no config file in the image.

| Variable | Default | Meaning |
| --- | --- | --- |
| `PLUMBLINE_KEY_REGISTRY` | — (required) | Path to the hashed key registry |
| `PLUMBLINE_PUBSUB_PROJECT` | — (required) | Pub/Sub project id |
| `PLUMBLINE_PUBSUB_TOPIC` | — (required) | Topic to publish to |
| `PLUMBLINE_HTTP_ADDR` | `:4318` | OTLP/HTTP listener |
| `PLUMBLINE_GRPC_ADDR` | `:4317` | OTLP/gRPC listener |
| `PLUMBLINE_MAX_COMPRESSED_BYTES` | `4194304` | Per-message budget, compressed |
| `PLUMBLINE_SHUTDOWN_TIMEOUT` | `15s` | Graceful shutdown deadline |
| `PUBSUB_EMULATOR_HOST` | — | Read by the client library; the collector has no branch for it |

A missing required variable fails at startup rather than at the first request: a
collector that boots healthy and rejects everything is worse, because the health check
says it is fine.

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `POST /v1/traces` (HTTP `:4318`) | OTLP/HTTP, `application/x-protobuf`, optional gzip request body |
| `opentelemetry.proto.collector.trace.v1.TraceService/Export` (gRPC `:4317`) | OTLP/gRPC |
| `GET /healthz` (HTTP) | Liveness |

OTLP/JSON is refused with `415`. Accepting it would put a payload on the topic that the
worker's protobuf deserializer cannot read — a poison message manufactured by the
collector rather than sent by a client.

Health is HTTP-only: the gRPC server runs the raw-bytes codec, which the standard gRPC
health service, being a protobuf service, cannot share.

## API keys

Format `plb_<environment>_<32 lowercase hex>`. Issued environments are `local` and
`live`; **`test` is reserved and never issued**, which is what lets tests and
documentation carry realistic key-shaped strings while Gate F still matches every real
one (issue #19).

The collector never holds a plaintext key. The registry is hashes:

```json
{
  "keys": [
    {
      "api_key_id": "local-claude-code",
      "key_sha256": "<sha256 of the plaintext key, hex>",
      "source_dialect": "claude-code",
      "rate_limit_per_second": 50,
      "burst": 100,
      "status": "active"
    }
  ]
}
```

`source_dialect` travels to the worker as a **hint only**; the worker's detection is
authoritative and overrides it on mismatch (§5). Locally the registry is this file (F1
directive D5); in the cloud it is Firestore behind the same interface (F2).

The registry is read once, at startup. Rotating a key is a redeploy, which at
`min-instances=0` costs nothing and no downtime — cheaper than a hot-reload path on the
data plane and its failure modes.

## Known limitation — rate limiting

The token bucket is in-memory per instance. At `max-instances = 2` the effective limit
is up to twice the nominal one (architecture §6.2). A shared limiter is the fix and it
violates the zero-cost invariant, so the approximation is the design rather than a
defect to file.

## Tests

```bash
go test -race ./...
```

Unit tests per component, an envelope contract test on the published attributes, the
byte-identity test, and the import-boundary check. The wire splitter is tested against
the real fixture corpus in `testdata/fixtures/`, so its limits are measured rather than
assumed.
