# CLAUDE.md — advisory contract for Claude Code

This file states the project rules Claude Code must follow. `.claude/settings.json`
enforces the mechanical subset (file-path deny rules, command deny-list); everything
here binds regardless of enforcement.

## Language

English only in every repo artifact, no exceptions: code, comments, identifiers,
commits, branches, PRs, docs, logs, test names.

The working conversation with the maintainer is held in Turkish. This does not
relax the rule above: the moment text is destined for the repository or for
GitHub it is written in English, including commit messages and pull request
descriptions drafted during a Turkish conversation.

## Cost invariants (hard)

- Never write an `insertAll` code path. The BigQuery Storage Write API is the only
  BigQuery write path.
- Never create Terraform resources outside the resource-type allowlist
  (architecture.md §7).
- Cloud Run services are always `min_instances = 0`, `max_instances <= 2`,
  region `us-central1`.
- No topic-level Pub/Sub retention.

## Boundaries

- The collector never parses span semantics.
- The worker never mutates raw OTLP bytes before deserialization.
- Mappings live only in `normalization/mappings/` — never in Firestore, never in
  environment config.

## Process

- One spec = one branch = one PR.
- Conventional Commits.
- Golden-file tests accompany any normalization change.
- No scope beyond the active spec — discovered work is proposed back as a spec
  change, not silently implemented.

## Docs

`docs/` is the single source of truth. Contradictions between docs are raised,
not resolved unilaterally.
