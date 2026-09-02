# plumbline — Architecture

**Version:** 0.14 · **Status:** Draft for F0 sign-off · **Date:** 2026-09-02
**Semantic conventions:** OTel GenAI semconv pinned at **v1.41** (see §5)
**Scope:** Current-state architecture, component contracts, data flow, data model, and
enforcement points for cost/security invariants. Decision *rationale* lives in ADRs (§10);
this document states the decisions and their operational consequences.

---

## 1. System Overview

```mermaid
flowchart LR
    subgraph sources [Agent Sources]
        A1[LangGraph / Python<br/>Anomaly Adjudicator]
        A2[.NET Agent<br/>Apartment Triage]
        A3[Claude Code<br/>native OTel]
    end

    subgraph gcp [GCP — us-central1, zero-cost envelope]
        C[Go Collector<br/>Cloud Run]
        PS[(Pub/Sub<br/>traces topic)]
        DLQ[(Pub/Sub<br/>dead-letter topic)]
        W[.NET Ingestion Worker<br/>Cloud Run]
        BQ[(BigQuery<br/>plumbline.spans)]
        FS[(Firestore<br/>metadata)]
        API[.NET Analytics / Eval API<br/>Cloud Run]
        SCH[Cloud Scheduler<br/>nightly batch]
    end

    subgraph frontends [Frontends]
        LS[Looker Studio]
        SPA[Trace Waterfall SPA<br/>GitHub Pages]
    end

    A1 -- OTLP/HTTP+gRPC --> C
    A2 -- OTLP/HTTP+gRPC --> C
    A3 -- OTLP/HTTP --> C
    C -- gzipped OTLP protobuf --> PS
    PS -- OIDC push --> W
    PS -. max delivery attempts .-> DLQ
    W -- Storage Write API --> BQ
    W <--> FS
    API <--> BQ
    API <--> FS
    SCH --> API
    LS --> BQ
    API -- nightly static JSON export --> SPA
```

External LLM judges (Google AI Studio Flash tier, local Ollama) are invoked by the Eval
engine inside the Analytics/Eval API and are covered in `docs/eval-plan.md`, not here.

---

## 2. Component Responsibilities

Each component has an explicit contract: what it owns, and what it must **not** do.
Boundary violations are treated as design regressions.

### 2.1 Go Collector (data plane)
- **Owns:** OTLP receive (HTTP `4318` + gRPC `4317`), API-key authentication, per-key
  rate limiting, batching, gzip compression, publish to Pub/Sub.
- **Contract in:** standard OTLP `ExportTraceServiceRequest` from any OTel SDK.
- **Contract out:** Pub/Sub message per §3.2. Raw protobuf bytes are never mutated
  (ADR-0001, wire-only — see §3.1).
- **Must not:** parse span semantics, normalize attributes, or apply dialect logic.
  The collector is dialect-agnostic by design; it may attach a `source_dialect` *hint*
  derived from the API key's registration, nothing more.
- **State:** stateless except in-memory rate-limit buckets (see §6.2 limitation).

### 2.2 Pub/Sub (transport)
- **Owns:** decoupling data plane from control plane; backpressure absorption;
  dead-lettering of poison messages.
- **Topology:** one topic `traces`, one OIDC push subscription to the worker, one
  dead-letter topic `traces-dlq` with a pull subscription.
- **Must not:** hold data as a store. Topic-level message retention is **disabled on all
  topics** (paid feature). The DLQ relies solely on subscription-level unacked message
  retention (default 7 days, free). These are two different mechanisms; Terraform must
  not generalize one onto the other.

### 2.3 .NET Ingestion Worker (control plane, write path)
- **Owns:** OIDC push endpoint; gunzip + OTLP protobuf deserialization; dialect
  detection; v1.41 normalization via the embedded mapping table (§5); writes to BigQuery
  via **Storage Write API** (default stream).
- **Contract in:** Pub/Sub push envelope per §3.2.
- **Contract out:** rows in `spans` per §4.1.
- **Must not:** write to BigQuery through the legacy streaming insert path — the
  `tabledata.insertAll` REST method and every client-library surface over it
  (`BigQueryClient.InsertRow` / `InsertRows` / `InsertRowsAsync`, Go `Table.Inserter`).
  The Storage Write API is the only permitted write path (cost invariant, §7).
- **Must not:** drop unmapped attributes (they are preserved in `attributes` JSON), or
  silently swallow poison messages (NACK → retry → DLQ, per §3.4).

### 2.4 BigQuery (analytical store)
- **Owns:** span storage and all analytical queries.
- **Constraints:** date-partitioned, `trace_id`-clustered, `require_partition_filter=true`
  on every table; project-level custom query quota. Details in §4.1.

### 2.5 .NET Analytics / Eval API (control plane, read path)
- **Owns:** query endpoints over BigQuery; eval engine (deterministic rules + tiered
  LLM judge); regression gate; nightly batch entrypoint (Cloud Scheduler); nightly
  static JSON export for the SPA.
- **Must not:** expose a public unauthenticated live API in v0.1 (see §3.5).

### 2.6 Firestore (metadata store)
- **Owns:** API key registry (hashed), eval definitions, frozen dataset references,
  eval run states.
- **Must not:** hold normalization mapping tables (rejected: config-as-hidden-state
  drift risk; mappings are versioned in-repo, §5) or span data.

### 2.7 Frontends
- **Looker Studio:** reads BigQuery directly (partition-filtered views only).
- **Trace Waterfall SPA:** static site on GitHub Pages; consumes nightly static JSON
  export. No live backend dependency in v0.1. Pages on GitHub Free requires a **public**
  repository (F0 spec §0.2); a private repository would make this data path a paid
  feature and break the zero-cost invariant.

---

## 3. Data Flow & Message Contracts

### 3.1 OTLP preservation — scope of ADR-0001 (wire-only)
"OTLP preserved end-to-end" is defined as **wire-level** preservation: from agent SDK
through collector to worker deserialization, the `ExportTraceServiceRequest` protobuf
bytes are never re-modeled into an invented canonical schema.

The **at-rest representation** in BigQuery is *not* raw bytes. It is a set of normalized
columns faithful to OTLP field names plus a lossless `attributes` JSON column. A raw
protobuf bytes column is deliberately **not** stored (would erode the 10 GB storage free
tier for zero analytical value). Fidelity of raw → normalized mapping is guaranteed by
golden-file tests per dialect (F1 DoD), not by storing the wire format.

Any future proposal to persist raw bytes is a scope change and requires an ADR.

### 3.2 Pub/Sub message contract
- **Payload:** exactly **one** gzipped, binary OTLP `ExportTraceServiceRequest` per
  message. No JSON encoding, no re-batching across export requests.
- **Attributes:**
  | Attribute | Source | Purpose |
  |---|---|---|
  | `api_key_id` | Collector auth | Provenance; joins to Firestore key registry |
  | `source_dialect` | API key registration | *Hint only*; worker detection is authoritative |
  | `content_encoding` | Collector | Always `gzip` in v0.1; explicit for forward compat |
  | `schema_url` | OTLP resource | Semconv version audit trail |
- **Size budget:** collector enforces batch sizing so the compressed payload stays well
  under the 10 MB push limit; working target ≤ 4 MiB compressed. Oversized batches are
  split at the collector, never truncated.

### 3.3 Delivery semantics
- **At-least-once.** Exactly-once subscriptions are not used (complexity + regional
  constraints, no zero-cost benefit).
- **Dedup is downstream:** duplicates land in BigQuery and are eliminated at query time
  and gate time on `(trace_id, span_id, start_time)`. That third column is not a
  refinement of the key but the reason the views can be queried under
  `require_partition_filter`, and it rests on duplicates carrying identical timestamps —
  an invariant with an enforcement point, not an assumption (ADR-0007 D7). Canonical
  views (§4.1) encapsulate the dedup so dashboards and the eval engine never see
  duplicates.
- **Write path:** Storage Write API **default stream** (at-least-once, matches the
  above; no exactly-once committed-stream complexity in v0.1).

### 3.4 Dead-letter path
- Main subscription: max delivery attempts = 5, then routed to `traces-dlq`.
- DLQ has a **pull** subscription (no consumer by default) + an alert on
  `num_undelivered_messages > 0`.
- Rationale: a poison message disappearing silently violates *no silent degradation*.
  Cost of the DLQ path is ~0 (no topic retention; subscription retention is free).
- Replay is manual in v0.1 (documented runbook step, not automation).

### 3.5 SPA data path (v0.1)
Nightly job in the Analytics/Eval API exports curated JSON (recent traces, eval
summaries, `synthetic` flagged separately) committed/pushed to the GitHub Pages branch.
Zero cost, zero attack surface, no cold-start dependency for the public demo.
A live read-only API (CORS + rate limit) is a separate F4 decision, not assumed here.

This path assumes a public repository (F0 spec §0.2). The exported JSON is therefore
world-readable by construction: it carries curated trace and eval summaries only, and
never API keys, customer data, or internal hostnames.

---

## 4. Data Model

### 4.1 BigQuery

**Dataset:** `plumbline` (us-central1).

**Table `spans`** (written only via Storage Write API):

| Column | Type | Notes |
|---|---|---|
| `start_time` | TIMESTAMP | **Partition column** (daily granularity) |
| `end_time` | TIMESTAMP | |
| `trace_id` | STRING | **Clustering key #1** |
| `span_id` | STRING | Clustering key #2 |
| `parent_span_id` | STRING | Nullable |
| `name` | STRING | |
| `kind` | STRING | OTLP enum name |
| `status_code`, `status_message` | STRING | |
| `service_name` | STRING | From resource attributes |
| `source_dialect` | STRING | Worker-detected (authoritative), see §5 |
| `api_key_id` | STRING | Provenance |
| `schema_url` | STRING | Semconv audit |
| `synthetic` | BOOL | From resource attr `synthetic=true`; **walled-off** flag |
| `gen_ai_*` | (typed) | Normalized v1.41 GenAI columns (system, operation, model, token counts, …) — exact list owned by the mapping table (§5) |
| `attributes` | JSON | Lossless remainder: all attributes incl. unmapped/original keys |
| `events`, `links` | JSON | OTLP events/links, unflattened |
| `ingest_time` | TIMESTAMP | Worker write time |

- **Options:** time partitioning on `start_time` (daily); clustering
  `(trace_id, span_id)`; `require_partition_filter = true`.
- **Views:** `spans_deduped` (ROW_NUMBER over `(trace_id, span_id, start_time)` keeping
  latest `ingest_time`) and `spans_real` (`synthetic = false`). All consumers (Looker,
  eval engine, SPA export) read views, never the base table.
- **The window includes `start_time`, and that is what makes the views queryable at all**
  (ADR-0007, #61). A predicate may only be pushed below a window function when it
  references the window's `PARTITION BY` columns, so the earlier two-column window left
  the inner scan without a partition predicate and `require_partition_filter` refused
  every query against the views. The effective dedup key is therefore
  `(trace_id, span_id, start_time)`; duplicates arise from redelivery of identical OTLP
  bytes and already share a `start_time`, so under that premise it is the same dedup.
  Where the premise breaks, this shape retains both rows rather than dropping one —
  visible rather than silent.
- **Consumers supply their own `start_time` predicate.** The views carry no embedded time
  bound. Hiding the cost guardrail behind a convenience filter inside the view is what
  ADR-0007 rejects, so a query with no partition filter fails loudly at query time.
- **`eval_results` table:** required for dashboarding but its schema is owned by the F3
  eval-engine spec; intentionally not fixed here (see §10 Open Questions).

### 4.2 Firestore collections

| Collection | Contents | Notes |
|---|---|---|
| `api_keys` | key hash, `api_key_id`, registered dialect hint, rate-limit tier, status | Plaintext keys never stored |
| `eval_definitions` | deterministic rules + judge configs, versioned | Frozen per `eval-plan.md` |
| `datasets` | frozen golden dataset references (GCS/BQ pointers + checksums) | Immutable after freeze |
| `eval_runs` | run state machine, thresholds used, verdicts | Gate audit trail |

---

## 5. Normalization Layer

- **Pin:** GenAI semconv **v1.41**. The pin is a contract: emitter drift is mapped *to*
  v1.41, never the reverse.
- **Dialects (v0.1):** `langgraph-python`, `dotnet-agent`, `claude-code`.
- **Detection:** worker-side, deterministic, based on resource/scope attributes
  (instrumentation scope name/version, resource markers). The collector's
  `source_dialect` attribute is a hint used only as a tiebreaker; on mismatch the
  detected value wins and the mismatch is logged.
- **Mapping tables:** versioned YAML under `normalization/mappings/v1.41/<dialect>.yaml`,
  **embedded into the worker binary at build time**. No runtime config store
  (Firestore rejected: hidden-state drift). A mapping change is a code change: PR,
  review, golden-file tests.
- **Unknown dialect:** processed as generic OTLP — normalized columns filled where OTLP
  fields map directly, everything else preserved in `attributes` JSON,
  `source_dialect='unknown'`, counter metric incremented. Never dropped.
- **Golden-file tests:** per dialect, raw `ExportTraceServiceRequest` fixture →
  expected normalized rows. These tests are the enforcement mechanism of §3.1.

---

## 6. Security Model

### 6.1 Identity & auth boundaries
| Boundary | Mechanism |
|---|---|
| Agent → Collector | API key (header), validated against hashed registry in Firestore; per-key rate limit |
| Collector → Pub/Sub | Collector service account, `roles/pubsub.publisher` on `traces` only |
| Pub/Sub → Worker | **OIDC push**, two independent checks: the push SA is the sole `roles/run.invoker` on the worker, and the worker itself validates the token's audience and issuer-verified email (F2 decision log W2.2). Worker ingress is `INGRESS_TRAFFIC_INTERNAL_ONLY` — the *narrower* of the two internal settings, not the `internal-and-cloud-load-balancing` this row named before the worker was deployed; a push subscription in the same project targeting the default `run.app` URL counts as internal, so nothing needs the load-balancer allowance. `ingress=all` avoided; unauthenticated invocations disabled |
| Worker → BigQuery | Dedicated SA, **table-scoped** grant on `spans` (`roles/bigquery.dataEditor` on the table, not the dataset) |
| Collector → Firestore | Dedicated SA, `roles/datastore.viewer` at **project scope** — Firestore grants IAM at project (conditionally, database) scope only; per-collection access exists solely through Security Rules, which govern mobile/web clients rather than server client libraries. The narrowest grant that reads `api_keys` therefore reads all Firestore data in the project. Stated because it is wider than least privilege would like, and no configuration can narrow it (F2 decision log W2.5) |
| GitHub Actions → GCP | **Workload Identity Federation**; no exported SA keys anywhere in the project |
| Analytics API → public | Not exposed in v0.1 (static export path, §3.5) |

### 6.2 Known limitation — rate limiting
Per-key rate limiting is an in-memory token bucket per collector instance. With
`max-instances ≤ 2`, the effective limit is approximate (up to 2× nominal). Accepted:
a shared limiter (Redis/Memorystore) violates the zero-cost invariant. Documented,
not hidden.

### 6.3 Secrets
API keys are generated once, shown once, stored hashed. No secrets in env-committed
files; runtime secrets via Cloud Run env from Terraform-managed Secret Manager only if
free-tier limits allow — otherwise hashed-registry design keeps the collector
secret-free by construction.

---

## 7. Cost Guardrails — invariant → enforcement point

| Invariant | Enforcement point(s) |
|---|---|
| Storage Write API only; the legacy streaming insert API and its client package are forbidden | **Gate A (load-bearing):** no `Google.Cloud.BigQuery.V2` reference in any `*.csproj` or `Directory.Packages.props` — if the package is absent the forbidden API surface cannot be reached, whatever the symbol is called. **Gate B (secondary):** path-scoped symbol scan over the declared source roots — `collector/`, `worker/`, `analytics/`, `infra/functions/` — for `insertAll`, `tabledata.insertAll`, `InsertRow(`, `InsertRows(`, `InsertRowsAsync(`, `.Inserter(`. Code review is **not** an enforcement point |
| `require_partition_filter=true`, custom query quota | Terraform (`google_bigquery_table`, project quota) |
| Cloud Run `min=0`, `max≤2`, smallest instance, us-central1 | Terraform; CI check on plan diff |
| Pub/Sub: no topic retention; batched+gzipped | Terraform (topics); collector code + golden tests (batching) |
| LLM: free-tier Gemini + client-side limiter; bulk on Ollama | Eval engine code; quota config in `eval_definitions` |
| Billing kill-switch | Budget alert (net of all credits) → Pub/Sub → billing-detach function, detaching at `detach_threshold` — the **monthly ceiling, 200 TRY net**, month-to-date; **fire-tested in F0 (DoD)**, trigger semantics per ADR-0004 Amendment 4, ceiling per Amendment 5 |
| Early warning below the ceiling | `gross-cost-alert` budget, notification-only (Terraform), emails at 50% and 100% of 100 TRY — two warnings before the 200 TRY detach. No Pub/Sub binding: the plan guard asserts exactly one budget publishes to `billing-alerts` (ADR-0004 Amendment 4 D3, role restated in Amendment 5 D3) |
| Artifact Registry < 0.5 GB | Distroless images; cleanup policy keep-last-2 (Terraform) |
| No Cloud SQL / custom domain / paid SaaS | Architecture review; Terraform allowlist of resource types |
| Public repository (Pages + unmetered Actions on Free) | F0 spec §0.2; `main` branch protection; Gate C (no exported SA keys) and Gate D (no `pull_request_target`) |

Escape hatch: net spend on a trajectory to exceed the monthly ceiling — in practice, two
consecutive days above `ceiling / days_in_month` — triggers an incident note in `docs/`,
before the kill-switch makes the question moot. The old form of this rule read *"any spend
> $0.00 for two consecutive days"*, which under a ceiling fires on ordinary operation
(ADR-0004 Amendment 5).

### 7.1 Terraform resource-type allowlist

`CLAUDE.md` forbids creating Terraform resources outside "the resource-type
allowlist (architecture §7)", and §7 named that allowlist without containing one.
The list is below, and it is the normative one: `scripts/ci/terraform-plan-guard.sh`
parses **this section** rather than keeping a second copy, so the document and the
control cannot drift apart.

A type absent from this table is not merely unreviewed, it is refused by the guard.
Adding one is a spec change with an entry in this changelog — which is the point:
the resource classes that end the zero-cost envelope (a managed database, a load
balancer, a reserved IP, a VM) all arrive as a resource type nobody argued about.

| Resource type | Introduced | Role |
| --- | --- | --- |
| `google_project_service` | F0 | Enabling the APIs the footprint uses |
| `google_storage_bucket` | F0 | Terraform state; Cloud Function source; both inside the 5 GB free tier |
| `google_storage_bucket_object` | F0 | Function source archive |
| `google_storage_bucket_iam_member` | F0 | State-bucket access for the CI identity |
| `google_service_account` | F0 | Per-component identities |
| `google_service_account_iam_member` | F0 | Workload Identity Federation binding to a service account |
| `google_project_iam_member` | F0 | Project-scoped role grants |
| `google_project_iam_custom_role` | F2 | One-permission roles where a predefined role would grant more than the caller needs (ADR-0004 Amendment 3) |
| `google_billing_account_iam_member` | F0 | Billing-account read for the CI identity, so `terraform plan` can refresh the budget |
| `google_cloud_run_service_iam_member` | F0 | Invoker grants scoped to one service |
| `google_pubsub_topic` | F0 | `billing-alerts`; F2 adds `traces` and `traces-dlq` |
| `google_cloudfunctions2_function` | F0 | Billing kill-switch only |
| `google_billing_budget` | F0 | Budget feeding the kill-switch |
| `google_cloud_quotas_quota_preference` | F0 | Project-level BigQuery query quota |
| `google_iam_workload_identity_pool` | F0 | CI identity federation (§6.1) |
| `google_iam_workload_identity_pool_provider` | F0 | GitHub OIDC provider with attribute conditions |
| `google_pubsub_subscription` | F2 | OIDC push subscription and the DLQ pull subscription (§3.2, §3.4) |
| `google_bigquery_dataset` | F2 | Dataset `plumbline` |
| `google_bigquery_table` | F2 | `spans`, views, `eval_results` (§4.1) |
| `google_firestore_database` | F2 | Metadata store (§4.2) |
| `google_cloud_run_v2_service` | F2 | `collector`, `ingestion-worker`, `analytics-api` |
| `google_cloud_run_v2_service_iam_member` | F2 | Invoker grants on v2 services: `allUsers` on the public collector, the push identity as sole invoker on the worker (§6.1) |
| `google_pubsub_topic_iam_member` | F2 | Publish scoped to `traces` alone, so no data-plane identity can reach `billing-alerts` |
| `google_pubsub_subscription_iam_member` | F2 | The Pub/Sub service agent's acknowledge right on the push subscription alone, which is what lets a failed delivery reach `traces-dlq` (§3.4) |
| `google_bigquery_table_iam_member` | F2 | Worker write scoped to the `spans` table rather than the dataset (§6.1) |
| `google_artifact_registry_repository` | F2 | Distroless images, keep-last-2 cleanup policy (§8) |
| `google_cloud_scheduler_job` | F3 | Nightly eval batch (§2.5) |
| `google_monitoring_alert_policy` | F2 | DLQ depth alert (§3.4) |
| `google_monitoring_notification_channel` | F2 | Destination for the above |

Named and refused, because each has been reached for by someone solving a problem
this design solves differently: `google_sql_*` (no Cloud SQL — §9),
`google_redis_*` (a shared rate limiter is the rejected fix for §6.2),
`google_compute_*` (no VMs, no load balancers, no reserved addresses),
`google_container_*` (no GKE), `google_cloud_run_domain_mapping` (no custom
domain), and `google_service_account_key` — an exported key is what §6.1 exists to
avoid, and Gate C only detects one after it has been written.

Five further plan-time assertions ride along with the type check, because each
enforces an invariant that otherwise had no mechanical control: Cloud Run and
Cloud Functions scaling stays `min = 0` and `max <= 2`; every resource carrying a
region or location is `us-central1`; no Pub/Sub topic declares
`message_retention_duration`, which is the paid retention feature §2.2 forbids;
each Cloud Run service carries the ingress posture §6.1 gives it; and no service
but the deliberately public `collector` may have `allUsers` as an invoker, which
is what "unauthenticated invocations disabled" actually means — Cloud Run has no
separate switch, so the worker's protection is the *absence* of that member and an
absence is what configuration review reads past.

**The last two deny a service they have not been told about, and F3 will meet
that.** Both are keyed by service name, and a Cloud Run service absent from either
map is a violation rather than a skip: defaulting a new service into whatever was
copied from the block above it is the mechanism both assertions exist to stop
(F2 decision log W2.14, W3.6). So **`analytics-api`'s first pull request will be
red**, and that is the guards working rather than a broken gate — the fix is to
declare its ingress and invoker posture as an F3 design decision, in the same
change that introduces it. **Loosening either guard to turn a pull request green
is a governance regression, not a fix**, and it is the specific move the fixture
provenance rule (`scripts/ci/testdata/README.md`) was written to make harder,
because it is always the cheapest thing available under schedule pressure.

---

## 8. Deployment Topology

- **Region:** `us-central1` (all services, dataset, topics).
- **Cloud Run services:** `collector` (Go), `ingestion-worker` (.NET), `analytics-api`
  (.NET). All: `min-instances=0`, `max-instances=2`, smallest viable CPU/mem,
  concurrency tuned per service in F2.
- **Images:** distroless, built in GitHub Actions, pushed to Artifact Registry via WIF,
  deployed by Terraform-driven pipeline. Cleanup policy: keep last 2 tags.
- **Terraform ownership:** all GCP resources (Pub/Sub, BQ, Firestore, Cloud Run,
  Scheduler, budget/kill-switch, quotas, IAM). Nothing hand-created; drift = bug.
- **Local-first:** full pipeline runs under docker-compose (F1) with emulators/local
  stand-ins; GCP is a deployment target, not a development dependency.

---

## 9. Non-goals (v0.1)

- Competing feature-for-feature with mature observability vendors.
- Metrics/logs pipelines (traces only; OTLP metrics/logs out of scope).
- Multi-region, autoscaling beyond 2 instances, or any paid-tier capacity.
- Exactly-once delivery semantics.
- Live public API for the SPA (static export instead; revisit in F4).
- Runtime-configurable normalization (mappings are code).
- Storing raw OTLP bytes at rest.

---

## 10. ADR Index & Open Questions

### ADR index
| ADR | Title | Status |
|---|---|---|
| ADR-0001 | Preserve OTLP wire format end-to-end; no invented canonical schema (wire-only scope per §3.1) | Accepted |
| ADR-0002 | Pub/Sub message contract & at-least-once delivery with downstream dedup | Accepted |
| ADR-0003 | Normalization mappings as versioned in-repo YAML embedded at build time | Accepted |
| ADR-0004 | Zero-cost guardrails & billing kill-switch design | Accepted |
| ADR-0005 | Static JSON export as v0.1 SPA data path | Accepted |
| ADR-0006 | PII redaction happens in the worker, after deserialization | Accepted |
| ADR-0007 | Canonical dedup views under `require_partition_filter` | Proposed |
| ADR-0008 | Single-port OTLP protocol multiplexing on Cloud Run (#68) | Proposed |

Rationale, alternatives, and consequences live in `docs/adr/`; this index carries titles
and status only. Where this document and an ADR disagree, the ADR is the decision record
and this document is the summary — the contradiction is a bug in one of them, and is
raised rather than resolved silently.

### Open questions
1. `eval_results` BigQuery schema — owned by F3 eval-engine spec.
2. Secret Manager vs. secret-free collector (hashed registry only) — confirm in F2
   against free-tier limits.
3. SPA export cadence & payload size budget for GitHub Pages — confirm in F4.
4. Claude Code emitter: confirm actual resource/scope markers for dialect detection
   against a captured sample before freezing its mapping YAML (F1).
   Capture evidence: `docs/evidence/claude-code-otel-capture.md` (scope marker measured;
   tool/hook spans still unobserved).
5. GitHub Pages push credential for the nightly export (ADR-0005): scope, storage, and
   rotation. The export job needs repository write access, which is the first secret in
   an otherwise secret-free design (§6.3). Decide in F4, before the exporter is written.

---

## 11. Changelog

**v0.14 — 2026-09-02** — the zero-cost constraint becomes a ceiling (ADR-0004 Amendment 5).

1. §7's kill-switch row names `detach_threshold` as the **monthly ceiling, 200 TRY net,
   month-to-date**, rather than an epsilon above zero.
2. §7's second budget row is retitled: its job was runaway detection while net cost was
   zero by construction under the promotional credit. After 2026-10-05 net is meaningful
   again, so it becomes the early-warning tier — two emails at 50 and 100 TRY before the
   200 TRY detach. The resource is unchanged; only what it is for.
3. §7's escape hatch is re-derived. It read "any spend > $0.00 for two consecutive days",
   which under a ceiling fires on ordinary operation.

**v0.13 — 2026-08-30** — ADR-0007, the canonical views (#61).

1. §4.1's view definition gains `start_time` in the dedup window, with the reason: the
   two-column window made the views unqueryable under `require_partition_filter`, not
   merely awkward. Two sentences record the effective dedup key and that consumers supply
   their own partition filter.
2. §3.3's "dedup is downstream" bullet names the three-column key and points at the
   invariant it now rests on.
3. §10 index: ADR-0007 moves from *reserved* to **Proposed**.

**v0.12 — 2026-08-26** — F2 directive W3C (post-Wave-3 consolidation).

1. §7's plan-time assertion paragraph said "three" and listed three; there have been
   five since W2.14 and W3.6 added per-service ingress and public-invoker checks. A
   register that undercounts its own controls is the failure mode §7 exists to prevent,
   so the paragraph now names all five.
2. §7 gains the F3 entry note. Both per-service assertions deny a service absent from
   their map, so `analytics-api`'s first pull request will be red by design. Written
   down because an undocumented red gate under schedule pressure invites the one fix
   that must not be taken — loosening the guard.

**v0.11 — 2026-08-26** — F2 Wave 3.

1. §7.1 gains `google_pubsub_subscription_iam_member`, per D6. Dead-lettering is carried
   out by Google's Pub/Sub service agent, which holds nothing on this project's
   subscriptions by default: it needs `roles/pubsub.subscriber` on the subscription
   carrying the dead-letter policy in order to acknowledge the message it has forwarded.
   The alternative is the same role at project scope, which would also hand the agent
   every future subscription — so this row exists to make a grant smaller, which is the
   test v0.9 applied to the previous three. Both halves of the requirement were read off
   Google's dead-letter documentation at wave time rather than inferred; the omission's
   failure mode is silent, which is why it is a row and not a comment.

2. §6.1's "Pub/Sub → Worker" row is corrected to the ingress value that was actually
   deployed. It named `internal-and-cloud-load-balancing`; Wave 2 deployed
   `INGRESS_TRAFFIC_INTERNAL_ONLY`, which is narrower, and the plan guard has asserted
   that value since W2.14. The row was written before the worker existed and the two had
   never been read against each other. Corrected in the direction W2.5 established — the
   document states what is built — and the row now also names the second check, since
   Wave 3 is where the sole-invoker half stops being a plan.

**v0.10 — 2026-08-26** — F2 Wave 2 close-out and the record gaps.

1. §10 ADR index gains ADR-0008 (single-port OTLP multiplexing, #68) at **Proposed**, and
   reserves ADR-0007 for the canonical-views decision (#61) so the number is held rather
   than taken by whatever is written next. ADR-0004's Amendment 4 moves to **Accepted** —
   it had been running in production against a record that still called it a proposal.
2. §7 kill-switch rows already carried Amendment 4 from v0.9; no change needed there.

**v0.9 — 2026-08-22** — F2 Wave 2.

1. §7.1 gains three IAM types the two services need, per D6:
   `google_cloud_run_v2_service_iam_member` (the v2 name; the list carried only the v1
   `google_cloud_run_service_iam_member`, which does not manage a v2 service's policy),
   `google_pubsub_topic_iam_member` and `google_bigquery_table_iam_member`. All three
   exist to *narrow* a grant the project would otherwise have to make at project scope.
2. §6.1 splits the "Worker → BigQuery/Firestore" row and corrects it. The row promised
   "table/collection-scoped least privilege"; table-scoped is achievable and is now
   implemented, collection-scoped is not a thing Firestore has. The corrected row says
   what the platform allows and names the residual width, rather than describing a
   control nobody can build (F2 decision log W2.5).

**v0.8 — 2026-08-21** — F2 Wave 0. §7.1 gains `google_project_iam_custom_role`: the
second kill-switch live-fire found the function unable to *read* the billing state it was
about to change, and the narrowest fix is a role carrying one permission rather than a
predefined role carrying six (ADR-0004 Amendment 3).

**v0.7 — 2026-08-21** — F1 exit review.

1. §10 ADR index: ADR-0006 moves from `Proposed` to `Accepted`. The maintainer accepted
   it at the F1 C2 checkpoint, which is what the status records — an ADR implemented under
   autonomous governance could not flip its own status, and the index carried `Proposed`
   for exactly as long as that was true. Accepting it makes two F2 obligations binding:
   the DLQ runbook must state that a dead-lettered message may carry personal data, and
   DLQ retention must be set deliberately (issue #44).

**v0.6 — 2026-08-21** — F1 W4.

1. §10 ADR index gains ADR-0006 (PII redaction boundary) at status **Proposed**. The
   index carries status, and an ADR that exists and is implemented but not accepted is a
   state the index has to be able to express — otherwise the only way to learn that the
   redaction stage rests on an unaccepted decision is to read the stage.

**v0.5 — 2026-08-21** — F0 W6, CI plan scope.

1. §7.1 allowlist gains `google_billing_account_iam_member`. `terraform plan`
   refreshes every resource in state, the budget is a billing-account resource,
   and neither project Owner nor project Viewer reaches it — so the read-only CI
   identity needs a grant at that scope or acceptance criterion 8 is unreachable.
   Adding a type to the allowlist is a change to this document by construction:
   the plan guard refuses anything absent from it, which is the mechanism working
   rather than an obstacle to route around.

**v0.4 — 2026-08-19** — F0 spec W4/W5, W6.

1. **§7.1 added — the Terraform resource-type allowlist now exists.** `CLAUDE.md`
   and F0 spec W5 both instruct that no resource may be created outside "the
   allowlist (architecture §7)", and §7 referred to a list this document never
   contained. Every consumer of that rule — the plan-diff guard above all — was
   therefore unimplementable as specified. The allowlist is enumerated here, and
   `scripts/ci/terraform-plan-guard.sh` parses this section directly rather than
   holding a copy, so there is one source of truth and no drift to detect.
2. §7.1 also records the three plan-time assertions that accompany the type check
   (Cloud Run scaling bounds, region, Pub/Sub topic retention). Each was a hard
   invariant in `CLAUDE.md` with no enforcement point named in §7; naming them
   here keeps the §7 register's promise that every invariant states what holds it.
3. §7 Gate B row now names the declared source roots rather than three fixed globs.
   W4 added Go source under `infra/functions/`, and Gate B's coverage check refuses
   to let source live outside the scanned roots — so the root list changed, in the
   explicit way issue #5 required. The executable list is `SOURCE_ROOTS` in
   `scripts/ci/invariant-gates.sh`; this row, the F0 spec and ADR-0004 describe it.

**v0.3 — 2026-08-18** — F0 spec W2.

1. **§2.3 write-path prohibition restated in terms of the API surface an implementer
   actually encounters.** The v0.2 wording forbade `insertAll`, a string the .NET client
   never surfaces; someone writing `BigQueryClient.InsertRowsAsync` would read the
   prohibition, never meet it, and believe they had complied. The v0.2 §7 correction
   addressed the control only; this is the same defect in the contract.
2. **§10 ADR index updated:** ADR-0001..0005 now exist as files under `docs/adr/`, and
   0002–0005 are Accepted. The note that they still needed a rationale write-up is
   removed, and precedence between this document and an ADR is stated.
3. **Open question 5 added:** the GitHub Pages push credential implied by §3.5 and named
   in ADR-0005 — the first secret in a design described as secret-free by construction.

**v0.2 — 2026-08-18** — imported into the repository (F0 spec W1.1). Three changes
applied at import time; the ADR index (§10) and the open questions carry over from
v0.1 unchanged.

1. **BigQuery dataset renamed** to `plumbline` per F0 spec §0.1: §4.1 dataset line and
   the §1 diagram, where the BigQuery node is now qualified as `plumbline.spans`. The
   pre-decision working name appears nowhere in the repository.
2. **§7 BigQuery write-path guardrail row rewritten.** v0.1 named "Code review + CI grep
   gate" as the enforcement point. That control cannot detect the violation it targets:
   the .NET client exposes the streaming insert path as
   `BigQueryClient.InsertRow`/`InsertRows`/`InsertRowsAsync` and never surfaces the
   literal REST method name, so a real violation in `worker/` would pass the grep. The
   row now names Gate A (forbidden `Google.Cloud.BigQuery.V2` dependency, load-bearing)
   and Gate B (path-scoped symbol scan), per F0 spec §W6.2. Code review is explicitly
   demoted from enforcement point to review practice.
3. **Repository visibility and license recorded** where this document assumed them:
   §2.7 and §3.5 now state that the GitHub Pages data path requires a public repository
   under GitHub Free, and §7 carries a public-repository row. The project is licensed
   Apache-2.0 (F0 spec §0.3).

**v0.1 — 2026-08-18** — initial draft for F0 sign-off (external snapshot, never in the
repository).
