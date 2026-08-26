# ADR-0008 — Single-port OTLP protocol multiplexing on Cloud Run

**Status:** Proposed · **Date:** 2026-08-26
**Related issues:** #68 (OTLP/gRPC unreachable in cloud)
**Affects:** architecture §2.1 (collector contract), §6.2 (known limitations), §8 (deployment)
**Number verified against `docs/adr/`:** 0001–0006 exist; 0007 is reserved for the
canonical-views decision (#61) and is not yet written, so this file leaves a deliberate
gap at 0007 rather than taking the next free integer. On the numbering that prompted the
check: ADR-0004's amendments run 1, 2, 3, 4 with no gap — this decision's draft was
authored as "Amendment 2", which was already taken by the 2026-08-21 entry on the detach
permission model, so it was filed as 4. The identifier moved; the audit trail did not.

---

## Context

Architecture §2.1 states the collector owns OTLP receive on HTTP `4318` and gRPC `4317`.
A Cloud Run service exposes exactly one port, so the deployed collector cannot bind two.
As deployed in Wave 2 it serves HTTP only; OTLP/gRPC is unreachable in the cloud while
remaining functional under docker-compose.

This is not F2-blocking — no F2 acceptance criterion depends on gRPC ingest — but it
becomes real in F4, when three heterogeneous emitters are instrumented against the
deployed collector.

Relevant platform behaviour:

- Cloud Run downgrades HTTP/2 to HTTP/1 before the container, **except** native gRPC
  traffic, which is forwarded as HTTP/2. Enabling end-to-end HTTP/2 (`--use-http2`,
  or a container port named `h2c`) is therefore not required for unary gRPC.
- Connection-layer multiplexers (cmux) are unsafe on Cloud Run when end-to-end HTTP/2
  is enabled: the fronting proxy can mix gRPC and h2c requests on one connection, while
  cmux pins a connection to a single protocol, producing upstream protocol resets.

OTLP export (`ExportTraceServiceRequest`) is a unary RPC. Streaming is not used and is
not planned.

## Decision

**D1 — Multiplex both OTLP transports on the collector's single Cloud Run port.**
The container serves one listener wrapped in `h2c.NewHandler`. Dispatch is **per
request**, not per connection:

- `r.ProtoMajor == 2` and `Content-Type` prefixed `application/grpc` → gRPC server's
  `ServeHTTP`.
- everything else → the existing OTLP/HTTP mux (`/v1/traces`).

**D2 — End-to-end HTTP/2 stays disabled.** No `use-http2`, no `h2c`-named container
port. Unary gRPC does not need it, and enabling it is precisely the configuration in
which connection-layer muxing fails.

**D3 — No connection-layer multiplexer.** cmux and equivalents are forbidden in the
collector. The rejection is recorded so a future contributor does not reintroduce it as
a "simplification".

**D4 — Local topology is unchanged.** Under docker-compose the collector keeps separate
`4317`/`4318` listeners. Cloud and local differ in *binding*, not in accepted protocols
or in normalization behaviour. Golden-file tests are transport-independent (they operate
on the deserialized `ExportTraceServiceRequest`) and remain the fidelity guarantee.

**D5 — Auth and rate limiting are transport-independent.** API-key extraction reads the
key from gRPC metadata and from the HTTP header, resolving to the same `api_key_id`.
The per-key token bucket is keyed by `api_key_id` and shared across both paths in one
process — never one bucket per listener. A test asserts that traffic split across the
two transports consumes a single bucket.

**D6 — Fallback is documented, not silent.** If D1 fails empirical verification (§
Verification), the cloud collector serves HTTP only, `OTEL_EXPORTER_OTLP_PROTOCOL=
http/protobuf` becomes a documented requirement for all three F4 emitters, and the
divergence is recorded in architecture §6.2 as a known limitation. Falling back without
recording it is a silent degradation and is not permitted.

## Alternatives rejected

- **Retire OTLP/gRPC ingest for v0.1.** Cheapest in code, but creates a local/cloud
  behavioural divergence that undermines the local-first principle (§8), and a
  reference implementation that refuses the ecosystem's default OTLP transport is
  materially less useful as a reference. The `.NET` OTel exporter defaults to gRPC;
  all three emitters are under our control, so the fix would be configuration — but
  the divergence is the objection, not the effort.
- **A second Cloud Run service dedicated to gRPC.** Stays within the zero-cost envelope
  (`min-instances=0`), but doubles collector surface: two revisions, two IAM bindings,
  two rate-limit populations (§6.2's 2× approximation becomes 4×), two deploy paths.
  Cost is in complexity, not currency.
- **Enable end-to-end HTTP/2 and use cmux.** The documented failure mode above. Buys
  streaming support that OTLP export does not use.
- **External load balancer with two backends.** Violates the no-paid-resources
  invariant (§7).

## Consequences

- **Collector:** the gRPC server is no longer started via `grpc.Server.Serve` on its own
  listener in the cloud path; it is invoked through `ServeHTTP`. This is grpc-go's HTTP
  handler transport, which is less optimised than the native server. Acceptable at this
  scale, but the collector p95 overhead figure (a Brief success criterion) must be
  measured over **both** transports, not HTTP only.
- **Graceful shutdown:** wrapping the gRPC server in `net/http.Server` loses grpc-go's
  `GracefulStop` semantics. Impact is bounded: an export lost at instance shutdown is
  retried by the OTel SDK exporter, and the downstream contract is already at-least-once
  (§3.3). Recorded in §6.2.
- **Architecture:** §2.1 gains a note that cloud deployment serves both transports on one
  port; §8 gains the port/protocol topology; §6.2 gains the two limitations above.
- **Testing:** a cloud integration check exercising both transports against the deployed
  collector is added to the F4 readiness list. It cannot run until the collector's public
  endpoint is reachable (open 404 investigation).

## Verification

Empirical, not assumed. Both must pass before #68 is closed:

1. **Local:** `curl -i --http2-prior-knowledge http://localhost:PORT` succeeds against the
   multiplexed handler, and an OTLP/HTTP POST to `/v1/traces` on the same port succeeds.
2. **Cloud:** with `use-http2` disabled, an OTLP/gRPC exporter and an OTLP/HTTP exporter
   both reach the deployed collector and both produce rows in `spans` with matching
   normalization. Specifically confirms that Cloud Run forwards native gRPC as HTTP/2
   without end-to-end HTTP/2 enabled — the one platform behaviour this decision depends on.

If (2) fails, D6 applies.

## Sequencing

Lane A. Not F2-blocking. Scheduled after F2 close and before F4 instrumentation, and
gated on the collector's public endpoint being reachable.
