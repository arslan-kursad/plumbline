# plumbline

OTel-native observability and evaluation platform for AI agents: a Go OTLP collector,
a .NET ingestion worker, and a .NET analytics/eval API on GCP, running inside a
zero-cost envelope with enforced guardrails.

Stub (F0). See [`docs/specs/F0-foundations.md`](docs/specs/F0-foundations.md) for the
active work package and [`CLAUDE.md`](CLAUDE.md) for the project contract.

## Documentation precedence

`docs/` in this repository is the **single source of truth**. Any external snapshot —
Project Knowledge, chat attachments, exported copies — that disagrees with `docs/` is
stale by definition, and `docs/` wins without discussion. Snapshots are refreshed from
the repository, never the reverse. Contradictions *within* `docs/` are raised, not
resolved unilaterally.

Start here:

- [`docs/project-brief.md`](docs/project-brief.md) — vision, phases, zero-cost invariants.
- [`docs/architecture.md`](docs/architecture.md) — component contracts, data model,
  enforcement points.
- [`docs/adr/`](docs/adr/) — decision rationale.
- [`docs/specs/`](docs/specs/) — work package specs.
- [`docs/runbooks/`](docs/runbooks/) — operational procedures.

## Layout

| Path | Contents |
| --- | --- |
| `collector/` | Go OTLP collector (module `github.com/arslan-kursad/plumbline/collector`) |
| `worker/` | `Plumbline.Worker` — .NET 8 ingestion worker |
| `analytics/` | `Plumbline.Analytics` — .NET 8 analytics and eval API |
| `normalization/mappings/` | Versioned normalization mapping YAML (F1) |
| `infra/terraform/` | Terraform (F0: state backend, kill-switch, quotas) |
| `infra/functions/` | Cloud Function sources deployed by Terraform |
| `scripts/ci/` | Invariant gate scripts (W6) |
| `docs/` | Source of truth — see above |

## Repository posture

Public from F0 onward (F0 spec §0.2): GitHub Pages and unmetered Actions minutes are
Free-tier only on public repositories, and the Trace Waterfall SPA depends on Pages.
Every commit is world-readable, so no secrets, customer data, or internal hostnames
enter the repository — including in test fixtures.

## License

[Apache-2.0](LICENSE). The target ecosystem (OpenTelemetry / CNCF) standardizes on it,
and the explicit patent grant removes friction for corporate readers of a reference
implementation.
