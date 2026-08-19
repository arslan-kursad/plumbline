# ADR-0005 — Static JSON export as the v0.1 SPA data path

**Status:** Accepted · **Date:** 2026-08-18 · **Work package:** F0 / W2
**Architecture:** §2.5, §2.7, §3.5, §4.1, §6.1
**Supersedes:** — · **Superseded by:** —

## Context

F4 requires a working public demo link: a trace-waterfall SPA on GitHub Pages, backed by
real ingested data. The default design is for the SPA to call the Analytics/Eval API,
which means a publicly reachable Cloud Run service, running with `min-instances=0`, whose
queries reach BigQuery.

That default carries three costs the project cannot absorb: a cold start on the first
request from every new visitor, an unauthenticated and uncapped query-cost surface against
the 2 TiB/month scan tier, and an attack surface on a service holding credentials to the
data store — added at F4, months before the threat model that would evaluate it is written
(F5).

## Decision

1. A **nightly job** in the Analytics/Eval API exports curated JSON — recent traces, eval
   summaries, synthetic runs flagged separately — and pushes it to the GitHub Pages branch.
2. **The Analytics/Eval API is not publicly exposed in v0.1.** It has no unauthenticated
   ingress.
3. The export is **world-readable by construction** (the repository is public per F0 spec
   §0.2). It therefore carries curated trace and eval summaries only, and never API keys,
   customer data, or internal hostnames.
4. **Synthetic data is carried but flagged**, never merged into real-source figures. The
   export reads the `spans_real` / `spans_deduped` views rather than filtering at export
   time, so the wall is a property of the data model, not of the exporter.
5. A **live read-only API** (CORS, rate limiting, cost caps) remains an explicit,
   separate F4 decision. It is not assumed by anything in v0.1.

## Alternatives considered

**A. Live read-only public API on the Analytics service.**
Rejected for v0.1 on three independent grounds, any one of which is sufficient. *Cold
start:* with `min-instances=0`, the first visitor arriving from a blog post meets a blank
screen for seconds — the demo's worst moment placed exactly where its audience is largest,
and `min-instances=1` is not available inside the cost envelope. *Cost surface:* an
unauthenticated endpoint over BigQuery is unbounded scan volume against the free tier, and
limiting it correctly requires shared rate-limiter state, which the zero-cost invariant
forbids — §6.2 already documents the collector's limiter as approximate for exactly this
reason, and the failure mode there is throttling, while here it is spend. *Sequencing:* it
adds a public attack surface at F4 to a system whose threat model is an F5 deliverable.

**B. SPA queries BigQuery directly using an embedded credential.**
Rejected outright. No credential belongs in a public static site, and BigQuery offers no
per-caller cost cap that would contain the consequences.

**C. Pre-rendered static HTML instead of JSON plus SPA.**
Cheaper and simpler. Rejected: the interactive waterfall *is* the artifact being
demonstrated. A rendered picture of a trace demonstrates that a screenshot can be taken.

**D. Export to a public-read GCS bucket instead of the Pages branch.**
Rejected: GCS egress is billable beyond the free allowance, which would place the demo
link's traffic — the one component whose usage the project actively wants to grow — on the
wrong side of the billing kill-switch. GitHub Pages bandwidth is free and the repository
is public already.

## Consequences

**Positive**

- Zero marginal cost, no cold-start dependency on the public path, and no unauthenticated
  service in the v0.1 topology.
- The demo is decoupled from GCP availability: if the kill-switch fires, or a Cloud Run
  revision is broken, the public link still works and still shows the last good export.
- Each export is a commit, so a regression in the exported data is visible as a diff
  rather than as an unexplained change in a dashboard.

**Negative / accepted costs**

- Data is up to 24 hours stale. Acceptable for a demonstration, but it means the SPA is
  lagging evidence for the "14 days of continuous ingest" criterion, not live proof.
  Freshness must therefore be shown explicitly as a generated-at timestamp in the export
  and rendered by the SPA — never implied.
- Repository size grows with every nightly commit. v0.1 overwrites a fixed set of files
  over a rolling window rather than appending dated ones, but git history still
  accumulates and needs a measured size budget before F4 ships. Architecture open question
  3 (export cadence and payload budget) stays open and is owned by F4.
- Pushing to the Pages branch from a Cloud Run job requires a credential with write access
  to the repository — a new secret in a system otherwise designed to be secret-free by
  construction (§6.3). Scoping it (fine-grained token, single repository, minimum
  permissions, rotation procedure) is F4 work and must not be improvised at implementation
  time. This is the single largest thing this decision adds to the threat model, and it is
  named here rather than discovered during F4.
- The SPA cannot support ad-hoc queries or drill-down beyond what the export contains.
  The export shape therefore becomes a product decision, made once per change, rather than
  a flexible surface — a real constraint on how convincing the demo can be.

## Enforcement

- **Architecture §2.5:** the Analytics/Eval API must not expose a public unauthenticated
  live API in v0.1. Review-enforced; no automated gate.
- **Export content rule** (no keys, no customer data, no internal hostnames) is the
  public-repository rule already in `CLAUDE.md`. Gate C (no exported service account keys,
  whole repository) backstops the credential class of leak but does not cover the others.
- **Synthetic separation** is guaranteed by reading `spans_real`, a view-level property
  (§4.1), rather than by exporter logic that could regress silently.
- **Changing the data path** — introducing a live API, or widening the export beyond
  curated summaries — requires a superseding ADR, not an F4 implementation choice.

## References

- `docs/architecture.md` §2.5, §2.7, §3.5, §4.1, §6.1, §6.3, §9, §10 (open question 3).
- `docs/specs/F0-foundations.md` §0.2 — public repository; GitHub Pages on Free.
- ADR-0004 — cost guardrails and the billing kill-switch this path is independent of.
