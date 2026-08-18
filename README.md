# plumbline

Agent-observability pipeline: OTLP collector (Go), ingestion worker and analytics
API (.NET 8) on GCP, built under a zero-cost envelope.

Stub (F0). See `docs/specs/F0-foundations.md` for the current work package and
`CLAUDE.md` for the project contract.

## Layout

| Path | Contents |
| --- | --- |
| `collector/` | Go OTLP collector (module `github.com/arslan-kursad/plumbline/collector`) |
| `worker/` | `Plumbline.Worker` — .NET 8 ingestion worker |
| `analytics/` | `Plumbline.Analytics` — .NET 8 analytics API |
| `normalization/mappings/` | Versioned normalization mapping YAML (F1) |
| `infra/terraform/` | Terraform (F0: state backend, kill-switch, quotas) |
| `docs/` | Architecture, ADRs, specs, runbooks, eval plan — single source of truth |
