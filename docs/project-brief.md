# plumbline — Project Brief (v0.1, 2026-08)

## Vision
OTel-native observability & evaluation platform for AI agents. Ingests OpenTelemetry GenAI
telemetry (semconv pinned at v1.41) from heterogeneous agent sources, normalizes emitter
dialects, stores traces in BigQuery, and runs a two-tier evaluation engine (deterministic
rules + tiered LLM-as-judge) with pre-registered regression gates usable as CI gates.

**Positioning:** not a product competing with mature vendors — an OTel-native reference
implementation + live case study, dogfooded on the author's own agents.

## Differentiators
1. Polyglot by necessity: Go owns the data plane (collector/ingestion), .NET owns the
   control plane (analytics, eval engine) — each language where the industry defaults to it.
2. Dogfooding on 3 heterogeneous real sources: a LangGraph/Python agent (Anomaly Adjudicator),
   a .NET agent (Apartment Triage), and Claude Code's native OTel emission.
3. Pre-registered evaluation criteria and a seeded-regression controlled experiment
   (baseline agent vs deliberately degraded version; the gate must catch it).
4. Runs at $0.00 on GCP Always Free, with enforced guardrails — itself a publishable result.

## Architecture (summary — full detail in docs/architecture.md)
Agents (OTel SDK) -> Go Collector on Cloud Run (OTLP HTTP+gRPC, API-key auth, per-key rate
limit, batch+gzip) -> Pub/Sub -> OIDC push subscription -> .NET Ingestion Worker on Cloud Run
(deserialize OTLP protobuf, apply v1.41 normalizer mapping table) -> BigQuery via Storage
Write API (date-partitioned, trace_id-clustered, require_partition_filter=true) ->
.NET Analytics/Eval API on Cloud Run -> Looker Studio dashboard + trace-waterfall SPA on
GitHub Pages (public repository — see zero-cost invariants). Metadata (eval definitions,
datasets, run states, API keys) in Firestore. BigQuery dataset: `plumbline`.
OTLP protobuf is preserved end-to-end (ADR-0001); no invented canonical schema.

## Zero-cost invariants
- BigQuery: Storage Write API only (2 TiB/mo free); insertAll forbidden. Custom query
  quota set project-level; partition filter required on all tables.
- Cloud Run: min-instances=0, max-instances<=2, us-central1, smallest viable instance.
- Pub/Sub: batched+gzipped messages; topic retention OFF.
- LLM: Google AI Studio free tier (Flash class) with client-side rate limiter + nightly
  batch; bulk judging on local Ollama; judge tiers mirror cost-tiered routing.
- Billing kill-switch: budget alert -> Pub/Sub -> function detaching billing account. Tested.
- Artifact Registry under 0.5 GB: distroless images, cleanup policy (keep last 2 tags).
- No Cloud SQL, no custom domain, no paid SaaS anywhere in the loop.
- Repository is public from F0 (`arslan-kursad/plumbline`, Apache-2.0). GitHub Pages and
  unmetered Actions minutes are Free-tier only on public repositories; a private
  repository would push the SPA data path onto a paid plan. Consequence: every commit is
  world-readable, so no secrets, customer data, or internal hostnames — ever, including
  in test fixtures.

## Phases (part-time, ~6 weeks, ~90–100 h)
- **F0 Foundations (~8h):** repo scaffold, ADR-0001..0005, pre-registered eval-plan.md,
  GCP project + kill-switch + quotas, Terraform skeleton, GitHub Actions via Workload
  Identity Federation. DoD: kill-switch fired in a test; empty pipeline green.
- **F1 Local-first core (~25h):** Go collector + golden-file tests for 3 emitter dialects;
  .NET worker + normalizer mapping table; docker-compose end-to-end. DoD: 3 dialects
  normalized and queryable locally.
- **F2 Minimal GCP footprint (~15h):** Terraform for Pub/Sub, BQ, Firestore, 2 Cloud Run
  services; CI build->distroless->Artifact Registry->deploy. DoD: local OTLP lands in cloud
  BQ; bill = 0.00.
- **F3 Eval engine (~20h):** deterministic checks; frozen golden datasets; Ollama+Gemini
  tiered judge (quota-aware); regression gate with pre-registered thresholds; nightly batch
  (Cloud Scheduler); GitHub Action CI gate. DoD: seeded regression caught by the gate.
- **F4 Dogfooding + demo (~18h):** instrument both real agents + Claude Code source;
  synthetic load generator (tagged synthetic=true); Looker Studio + trace viewer SPA.
  DoD: 14 days continuous ingest from 3 sources; public demo link works.
- **F5 Hardening + visibility (~12h):** README with architecture/threat/cost model; blog
  series (semconv pinning; $0 on GCP with billing screenshots; local-vs-Gemini judge
  agreement); TR+EN LinkedIn posts. DoD: published; bill still 0.00.

## Success criteria (draft — frozen in docs/eval-plan.md at the F3 entry gate)
- >=3 heterogeneous dialects normalized with golden tests.
- 14-day uninterrupted live ingest from 3 real sources.
- Seeded-regression experiment caught by the gate at pre-registered thresholds.
- Collector p95 overhead and RAM ceiling documented; two consecutive months at $0.00.

## Working model
claude.ai Project = design/ADR/spec/review layer (no implementation).
Claude Code = implementation layer, governed by CLAUDE.md (advisory) +
.claude/settings.json (enforced). docs/ in the repo is the single source of truth;
Project Knowledge holds snapshots and loses ties to the repo.

## Amendment note (2026-08-21, F1 directive D1)

The success-criteria heading above read "to be frozen in docs/eval-plan.md before F1
code". Freeze A now happens at the **F3 entry gate**: F1's code reads no evaluation
criterion, and what the freeze protects is the seeded-regression experiment in F3.
Freeze B is unchanged. `docs/specs/F0-foundations.md` v0.8 carries the same amendment
with its reasoning, `docs/specs/F1-decision-log.md` records the decision, and the
maintainer ratified it at the F1 exit review on 2026-08-21. `docs/eval-plan.md` was not
edited during F1 — so it still says "F1 entry gate" and is stale on that line until the
human performing Freeze A reconciles it (issue #36).

## Import note (2026-08-18, F0 spec W1.1)

Imported into the repository as the source of truth. Aligned at import: BigQuery dataset
named `plumbline` (F0 spec §0.1); repository visibility and license recorded under
zero-cost invariants (§0.2, §0.3). Content is otherwise the v0.1 text unchanged. Where
this Brief and `docs/architecture.md` disagree, the architecture document is the more
specific authority; the disagreement is raised, not resolved silently.
