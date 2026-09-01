# DoD 1, 2, 5 and 12 — re-derived at closure

**Measured:** 2026-09-01 · **Directive:** Amendment 7 §3.1, Stage 5 step 17
**Rule:** spec §7.2 CN4 — carrying a status forward from a prior document is not
verification. Nothing below cites the decision log as its evidence; each item is measured
again from git, from the API, or from a CI run.

**CI run for the mechanical items:** [`33475352691`](https://github.com/arslan-kursad/plumbline/actions/runs/33475352691),
`main` — **all ten jobs succeeded and none was skipped.** No path-filter caveat applies to
this run.

## DoD 1 (G1) — the kill-switch gate held

G1's operative clause is *"No application service deploys before G1."* That is a claim
about ordering, and ordering is measurable now.

| Fact | Value | Source |
| --- | --- | --- |
| #33 closed | `2026-08-21T20:35:09Z` | issue API |
| `collector` created | `2026-08-26T10:42:16Z` | Cloud Run API |
| `ingestion-worker` created | `2026-08-26T10:35:13Z` | Cloud Run API |
| `billing-killswitch` created | `2026-08-21T10:24:22Z` | Cloud Run API |

Both application services were created **five days after** the gate closed.

**The kill-switch predates it, and that is the design rather than a breach.** Wave 0 *is*
the kill-switch's remediation and live-fire, so the function had to exist to be fired at;
the spec scopes the gate to the service footprint for exactly that reason. Recorded
explicitly because a table of timestamps read carelessly says the opposite.

## DoD 2 (G2) — both obligations landed, and the ordering is a fact

G2 says *"ordering is verifiable from merge and apply history."*

| Fact | Value |
| --- | --- |
| `f7d6ca3`, the commit carrying both obligations | committed `2026-08-21T19:37:18Z` |
| `traces-push`, the subscription that makes them binding | applied in Wave 3, `2026-08-26` |

Five days between the obligation and the thing it binds.

Both obligations verified in their current form, not inferred from the commit:

- **Personal data at the inspection point** — `dead-letter.md` names `user.id`,
  `user.email` and the unredacted-content risk where it tells an operator to inspect, and
  states that content is *"**never** pasted into an issue, a pull request, a commit"*
  because the repository and its tracker are public.
- **DLQ retention explicit in Terraform** — `message_retention_duration = "604800s"` in
  `pubsub.tf`, and the deployed subscription reads back `604800s` from the API.

**Incidentally measured:** `traces-dlq` carries no topic-level retention, which is one of
`CLAUDE.md`'s hard cost invariants and had not been read back before.

## DoD 5 — plan clean, and one resource that is not Terraform-declared

```
No changes. Your infrastructure matches the configuration.
plan guard: clean (29 resource types allowed by §7.1)
plan guard: nothing in this plan carries a checked attribute
```

**Every resource enumerated against the configuration**, discovered from the API rather
than assumed:

| Resource | Terraform-declared? |
| --- | --- |
| `plumbline` (Artifact Registry) | yes |
| `gcf-artifacts` (Artifact Registry) | yes — adopted, `google_artifact_registry_repository.gcf_artifacts` |
| `traces-push` | yes |
| `traces-dlq-pull` | yes |
| `eventarc-us-central1-billing-killswitch-…-sub-406` | **no** |

**The one exception is not an out-of-path creation.** It is the subscription Eventarc
creates as a child of a Terraform-declared trigger, named by Google and not addressable in
the configuration. Recorded as a fact about the footprint rather than filed as a violation
— but recorded, because "every resource is Terraform-owned" read without this line is
slightly untrue.

## DoD 12 — gates green, and nothing loosened

All nine gate assertions passed in run `33475352691`:

```
ok  Gate A — no legacy BigQuery client package
ok  Gate B — no streaming-insert symbols in source
ok  Gate B coverage — all source under the scanned roots
ok  Gate C — no exported service account keys
ok  Gate D — no pull_request_target in workflows
ok  Gate E — retired project name absent
ok  Gate F — no issued API key in the repository
ok  Gate G — push-auth stub gone, OIDC validator present
ok  Gate H — no enumerated credit filter in Terraform
```

**"Nothing loosened" measured on the two artefacts that could carry it:**

- `scripts/ci/invariant-gates.sh` — **unchanged** since before #82 merged (`git diff` over
  the window is empty).
- `.claude/settings.json` — **untouched for the entire phase** (`git log 490beac..HEAD` on
  that path returns nothing). This is the one Amendment 7 declined to widen, and declining
  is why DoD 12 needs no asterisk.

`ci.yml` did change: three self-test steps were **added** — the state readout's, the
seeder's and the cloud harness's. Additions are the opposite of loosening, and each runs a
check that can fail.
