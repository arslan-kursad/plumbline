# ADR-0001 — Preserve OTLP wire format end-to-end; no invented canonical schema

**Status:** Accepted · **Date:** 2026-08-18 · **Work package:** F0 / W2
**Architecture:** §2.1, §2.3, §3.1, §4.1, §5, §9
**Supersedes:** — · **Superseded by:** —

## Context

plumbline ingests OTel GenAI telemetry from emitters it does not control: a
LangGraph/Python agent, a .NET agent, and Claude Code's native emission
(`architecture.md` §5). These disagree on attribute names and shapes even at a single
pinned semantic-convention version, and they will drift independently across releases.

The industry answer is a canonical internal span model: translate every dialect into a
vendor-owned schema at ingest, then store and query that schema. It is a sound answer
for a product with a support contract behind it. It is the wrong answer here, for one
specific reason: the project's stated positioning is an OTel-native reference
implementation. A canonical schema is by construction a second vocabulary with no
upstream owner, and adopting one would put the project's central claim in conflict with
its own data model — at the first place a technical reader would look.

The decision had to be made before any collector or worker code existed, because it
determines what the collector is permitted to do (§2.1) and what "normalization" means
at all (§5).

## Decision

1. The OTLP `ExportTraceServiceRequest` protobuf is the interchange format along the
   whole wire path: agent SDK → collector → Pub/Sub → worker deserialization. The bytes
   are transported (batched, gzipped, published) and never re-modeled, re-encoded, or
   partially parsed into another representation en route.
2. **"End-to-end" is scoped to the wire.** The at-rest representation in BigQuery is not
   raw bytes: it is a set of normalized columns whose names follow OTLP and semconv
   field names, plus a lossless `attributes` JSON column carrying everything unmapped
   (§4.1). Raw protobuf is not persisted.
3. Emitter variance is resolved in one direction only: dialects are mapped **to** GenAI
   semconv v1.41. No intermediate vocabulary is introduced between a dialect and the pin.
4. Fidelity of raw → normalized is a **tested** property, not a stored one: golden-file
   tests per dialect (§5; F1 Definition of Done).
5. Widening the scope — persisting raw bytes, or introducing a canonical model — is a
   scope change and requires an ADR that supersedes this one.

## Alternatives considered

**A. Canonical internal span schema, dialects translated at ingest.**
The mature-vendor pattern, and the reason it is the default is real: it decouples storage
from protocol churn. Rejected on three counts. It requires two mappings per dialect
(dialect → canonical, canonical → storage) instead of one, doubling the surface the
golden tests must cover. Every semconv release becomes a migration of a schema nobody
upstream maintains. And it contradicts the project's positioning at exactly the point a
reader would check first.

**B. Persist raw protobuf bytes alongside the normalized columns.**
Attractive as a fidelity guarantee: any mapping defect becomes repairable by
reprocessing. Rejected because the bytes are inert for every analytical query while
consuming the 10 GiB BigQuery storage free tier, which is the binding budget under the
zero-cost invariant (§7); and because it substitutes storage for the control that
actually catches mapping defects. Stored bytes catch nothing at write time — golden-file
tests do. This buys reprocessing capability at a certain cost to answer a need that has
not yet appeared. What it forecloses is stated under Consequences rather than left
implicit.

**C. Convert to OTLP/JSON at the collector.**
Human-readable payloads in Pub/Sub, easier incident inspection. Rejected: JSON inflates
payloads against the 10 MB push limit and the ≤ 4 MiB compressed working target (§3.2),
and it discards the protobuf schema contract in exchange for debuggability that a decode
step already provides.

**D. Normalize in the collector instead of the worker.**
Removes a hop and one deserialization. Rejected: it makes the data plane dialect-aware,
so every new emitter dialect becomes a collector deployment on the hot path, and the
Go/.NET split (§2.1 / §2.3) stops being a clean data-plane / control-plane boundary.
Normalization belongs where the mapping tables and their tests live.

## Consequences

**Positive**

- Any OTel SDK is a supported source with no plumbline-specific emitter code. Onboarding
  a fourth dialect is a mapping YAML plus a fixture, not a protocol change.
- The collector stays stateless and semantics-free (§2.1), which is what makes it small
  enough to meet the p95-overhead and RAM-ceiling success criteria.
- Moving the semconv pin touches mapping tables and column definitions; it never touches
  the transport contract.

**Negative / accepted costs**

- The collector cannot filter, sample, or route on span semantics, because it is not
  allowed to parse them. Any such capability lands downstream or requires a later ADR.
- Fidelity rests entirely on the golden-file corpus. A thin corpus produces silent
  mapping loss and nothing in the storage layer will reveal it. This is the largest
  correctness risk the decision creates; the F1 DoD (three dialects, golden tests per
  dialect) is its only mitigation.
- Exact wire payloads are unrecoverable after ingest. Re-running a corrected normalizer
  over historical traffic is not possible from BigQuery: historical rows can be repaired
  only forward, or the affected window re-ingested from the source if the source still
  holds it. Accepted knowingly as the price of Alternative B's rejection.
- The `attributes` JSON column grows with unmapped keys. It is lossless by design and is
  therefore not a place to economize; it is watched against the storage tier in F2.

## Enforcement

- **Golden-file tests per dialect (F1):** raw `ExportTraceServiceRequest` fixture →
  expected normalized rows. These are the enforcement mechanism for §3.1, not a
  stylistic preference.
- **`CLAUDE.md` boundary rules:** the collector never parses span semantics; the worker
  never mutates raw OTLP bytes before deserialization.
- **Component contracts** in architecture §2.1 and §2.3, checked at review.
- No automated gate exists for "did not invent a canonical schema": this invariant is
  review-enforced and reported, never prevented. Naming that asymmetry is deliberate —
  see ADR-0004 on which controls prevent and which only report.
- A pull request proposing a raw-bytes column or an intermediate model is rejected
  without a superseding ADR.

## References

- `docs/architecture.md` §2.1, §2.3, §3.1, §4.1, §5, §9.
- `docs/project-brief.md` — positioning; zero-cost invariants.
- OpenTelemetry GenAI semantic conventions v1.41 (the pin).
