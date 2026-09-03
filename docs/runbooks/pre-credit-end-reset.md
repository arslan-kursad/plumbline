# Pre-credit-end reset — what must be returned to steady state before 2026-10-05

**Status:** **Proposed** · **Drafted:** 2026-09-03 · **Lane:** A
**Task:** F3 Unblock dispatch U-12 · **Related:** ADR-0009, `#74`, F2 DoD 13

> **This is a draft checklist and nothing here has been executed.** It exists because the
> distinction it names is currently written nowhere: **compute during the credit window is
> free; storage created during it is billed after it.**

---

## The rule this checklist exists for

Until 2026-10-05 the trial credit absorbs usage, so a resource's cost is **deferred, not
avoided**. Compute stops costing when it stops running. **Storage does not** — bytes
created under the credit are still there on 2026-10-06, and from that morning they are
billed against the payment method with no credit behind them.

Anything raised, created or accumulated during the credit window and not returned to steady
state becomes a standing charge at exactly the moment the project's headline cost claim
starts being measured (F2 DoD 13 / Verification C).

---

## The checklist

Values read from `infra/terraform/` on 2026-09-03. **Re-read at execution time** — this file
pins nothing.

### 1 · BigQuery stored bytes — against the 10 GB free tier

| | |
|---|---|
| Steady-state target | total stored bytes comfortably under **10 GB** |
| Current value | **not read** — requires a billing/BQ API read refused to Lane A on 2026-09-03 |
| Latest safe return date | **2026-10-01** (ADR-0009 D6, not 10-04) |
| Mechanism | delete synthetic partitions; `spans` is partitioned on `start_time` (daily) so a campaign's days are individually droppable |

**This is the highest-risk row on the list.** It is the only one where the cost survives
the campaign by default rather than by mistake, and the only one whose current value nobody
has read. ADR-0009 §3.4 makes a pre-campaign headroom reading a precondition precisely so
this row has a number to return to.

**Note on what "delete" must mean here:** dropping partitions removes the rows; it does not
by itself prove the bytes went. The post-teardown reading is the proof, per ADR-0009 D5 —
identity against the pre-campaign snapshot, not the absence of an error.

### 2 · Artifact Registry — against the 0.5 GB free tier

| | |
|---|---|
| Steady-state target | under **0.5 GB** stored |
| Current value | **not read** |
| Latest safe return date | 2026-10-01 |
| Mechanism | the `plumbline` repository already has a cleanup policy — *keep the last two versions, delete anything older than a day* |

**A caution recorded from experience rather than theory.** That cleanup policy has already
caused an incident: F2 decision log A2.13 records a pinned image ageing out mid-wave while
the wave was blocked, breaking a dispatch. **Do not tighten this policy to save bytes
during the campaign** — the existing one is already aggressive enough to have caused a
failure, and 0.5 GB against two-version retention of two small distroless images is not the
binding constraint.

### 3 · Cloud Run min-instances

| Service | Steady state | Read 2026-09-03 | Action needed |
|---|---|---|---|
| collector | `min_instance_count = 0` | **0** (`cloudrun.tf:91`) | none, if unchanged |
| worker | `min_instance_count = 0` | **0** (`cloudrun.tf:214`) | none, if unchanged |
| kill-switch function | `min_instance_count = 0` | **0** (`killswitch.tf:213`) | none, if unchanged |

`min_instances = 0` is a standing cost invariant (`CLAUDE.md`; `architecture.md` §7), and
raising it is already prohibited by ADR-0009 §5 and by the dispatch's own stop conditions.
**This row is a verification, not a reset** — the check is that all three still read 0, and
the plan guard should catch any drift before apply.

### 4 · Cloud Run max-instances

| Service | Steady state | Read 2026-09-03 |
|---|---|---|
| collector | `≤ 2` | **2** (`cloudrun.tf:92`) |
| worker | `≤ 2` | **2** (`cloudrun.tf:215`) |
| kill-switch function | — | **1** (`killswitch.tf:214`) |

Same status as row 3: an invariant to verify, not a value to restore. Both services are
already at the ceiling, so any campaign that wanted more throughput would have to breach
the invariant, which is why ADR-0009 §5 forbids it in terms.

### 5 · Cloud Scheduler frequency

| | |
|---|---|
| Steady state | **no Scheduler resource exists today** |
| Read 2026-09-03 | no `google_cloud_scheduler_job` in `infra/terraform/` |
| Action | if F3's nightly batch introduces one, its frequency belongs on this list |

**Recorded as a forward-looking row.** The nightly batch is an F3 deliverable
(`project-brief.md`:59) and does not exist. When it lands, a schedule set generously during
the credit window and left generous afterwards is exactly the shape this checklist is for.

### 6 · Raised quotas

| | |
|---|---|
| Steady state | the declared preference in Terraform |
| Read 2026-09-03 | one `google_cloud_quotas_quota_preference`, `bigquery_query_usage_per_day` |
| Action | verify the value at teardown equals the value at snapshot |

Raising a quota is prohibited by the dispatch's stop conditions, so this row should be a
no-op. It is listed because a quota raised temporarily and forgotten is invisible in
day-to-day operation and shows up only on an invoice.

### 7 · Pub/Sub retention

| | |
|---|---|
| Steady state | **no topic-level retention** — a hard cost invariant (`CLAUDE.md`) |
| Read 2026-09-03 | two topics, `traces` and `billing_alerts` |
| Action | verify no `message_retention_duration` was added at topic level |

Listed because it is storage rather than compute and therefore falls under this file's rule,
and because it is one of the four hard invariants in `CLAUDE.md`.

---

## Sequencing

| Date | What |
|---|---|
| before campaign | ADR-0009 §3.2 snapshot and ADR-0009 §3.4 headroom reading — **the identity term this checklist returns to** |
| 2026-10-01 | every row above verified; ADR-0009 D6's proof deadline |
| 2026-10-05 | credit ends; Verification C's window opens |

**2026-10-01 rather than 10-04 is deliberate.** A failed teardown needs repair time before
the credit expires, and 10-04 is already C7's own constraint, which is blocked on Freeze A
(`F2C-19`).

## What this draft cannot do

Rows 1 and 2 have no current values, because reading them needs API access refused to Lane A
on 2026-09-03. **A checklist whose targets are unmeasured is a form, not a control** — the
same distinction this project applies to a ready form versus a filled one. It becomes a
control when ADR-0009 §3.1 and ADR-0009 §3.4's readings fill those two cells.
