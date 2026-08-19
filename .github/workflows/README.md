# .github/workflows

`ci.yml` — the only workflow. Path-filtered Go, .NET and Terraform jobs, plus the
invariant gates, aggregated into a single `ci complete` status check.

Posture (F0 spec §W6.1, §W6.3):

- Triggered by `pull_request`, never `pull_request_target`. Gate D fails the
  build if that trigger ever appears in this directory.
- Top-level permissions are `contents: read`. Only `terraform plan (wif)` raises
  `id-token: write`, and that job additionally refuses to run for a pull request
  from a fork.
- Third-party actions are pinned to commit SHAs with the tag in a comment. A
  moving tag is a supply-chain decision made by someone else.
- No exported service account key: GCP access is a short-lived token from
  Workload Identity Federation.
- `terraform plan (wif)` stays skipped until the GCP repository variables exist.
  A skipped job proves nothing, which is why F0 acceptance criterion 8 is tied to
  a specific authenticated run recorded in the completion note.

Branch protection requires `ci complete` only — see
`docs/runbooks/branch-protection.md` for why the aggregate exists and how to
recover if a broken workflow file deadlocks `main`.
