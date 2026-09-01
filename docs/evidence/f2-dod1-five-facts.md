# DoD 1 — §7 item 1's five facts, read one at a time

**Measured:** 2026-09-01 · **Lane:** A · **Repo:** `main` @ `6a739c6`
**Rule:** spec §7.2 CN4 — carrying a status forward is not verification. Nothing below
cites [`f2-dod-1-2-5-12-rederived.md`](f2-dod-1-2-5-12-rederived.md), the decision log, or the closure note as evidence.

**The item under measurement**, verbatim from
[`F2-minimal-gcp-footprint.md`](../specs/F2-minimal-gcp-footprint.md) §7 item 1:

> 1. **G1**: #33 closed — post-fix live-fire succeeded, evidence archived, billing
>    re-attached, the corrected credit filter live.

Authored `2026-08-21 19:19:43 +0300` in `17acc4a`, the commit that created the spec. It
has never been edited. That timestamp matters for facts 4 and 5.

---

## Result

| # | Fact | Verdict | Measured from |
|---|---|---|---|
| 1 | #33 closed | **holds** | issue API |
| 2 | post-fix live-fire succeeded | **holds** | `kill-switch.md` §4 Attempt 3, API-confirmed |
| 3 | evidence archived | **holds, one omission reasoned** | `kill-switch.md` §4 |
| 4 | billing re-attached | **held on 2026-08-21; went false five times afterwards** | `kill-switch.md` §4, §4a |
| 5 | the corrected credit filter live | **referent moved; the authored reading is now a CI failure** | ADR-0004, `killswitch.tf`, `kill-switch.md` §4a |

Four of five are Lane A. Fact 4's *current* state is Lane C. Fact 5's repository half is
Lane A and is measured below; its live half could not be read from this session (see §5).

---

## 1. #33 closed — holds

`#33` — *"F2 entry gate: live-fire the kill-switch before any service is deployed"* ·
**CLOSED** `2026-08-21T20:35:09Z`.

## 2. Post-fix live-fire succeeded — holds

[`kill-switch.md`](../runbooks/kill-switch.md) §4, **Attempt 3 — 2026-08-21 — PASSED**. Operator:
maintainer. Three things were measured, not one:

- Detach, at the API rather than in the logs: `billingEnabled: false`,
  `billingAccountName: ''`.
- Idempotence under redelivery, published while detached:
  `billing already detached; nothing to do`.
- Drift after detach: `terraform plan` → `0 to change, 0 to destroy`.

Attempts 1 and 2 are archived as FAILED with their causes (ADR-0004 Amendments 2 and 3).
The pass is the third attempt, and the record says so.

**Ordering, since the DoD anchors on #33's closure.** Attempt 3's log lines read
`20:29:10`–`20:29:12`; the issue closed `20:35:09Z`. The runbook does not label the log
timezone. Under a UTC reading the sequence is fire → re-attach → close within six
minutes, which is coherent. Under a `+03:00` reading the pass precedes closure by three
and a half hours, also coherent. The ordering holds either way; the zone is unlabelled
and is worth stamping if this evidence is ever cited for a timing claim.

## 3. Evidence archived — holds, with one deliberate omission

§4 carries all three attempts with logs, `describe` output before and after, operator and
date. `#33` step 6 additionally asked for "a cropped billing screenshot". It is **not**
archived, and §4 records that as a decision rather than a gap: the API check is the
stronger claim and a console screenshot is a picture of the same fact one layer further
from it.

That is a defensible call. It is also a divergence between what the issue asked for and
what the archive contains, and it is only visible by reading both.

## 4. Billing re-attached — held on 2026-08-21, then went false five times

This is the fact that does not survive being read as written. **"Billing re-attached" is
a claim about a state, written in the grammar of an event.** The event happened. The
state did not stay.

Reconstructed from `kill-switch.md` §4 and §4a, in order:

| When | What | Source |
|---|---|---|
| 2026-08-21 ~20:31 | re-attached after the Attempt 3 live-fire — `billingEnabled: true` | §4 Attempt 3 |
| 2026-08-22 02:16 | **detached**, false positive, 0.01 TRY never billed | §4a |
| 2026-08-22 17:11 | **detached**, false positive, 0.04 TRY, 18 min after a re-attach | §4a |
| 2026-08-25 10:51:10 UTC | re-attached | §4a |
| 2026-08-25 10:58:22 | **detached** again — first delivery to find a warm instance | §4a |
| 2026-08-25 ~11:53 | **detached** again — a message published at ~11:47, before the filter landed at ~11:51, carried the old figure | §4a |
| 2026-08-25 12:11:23 | first fresh notification reads `cost=0`; billing stays attached | §4a |

So the last unbroken re-attach is **2026-08-25 ~12:11**, four days after the item was
recorded as satisfied. Between those dates the project's billing was detached on five
separate occasions, two of them against real money that was never owed.

None of this makes the 2026-08-21 re-attach untrue. It makes the *item* untrue as a
present-tense claim, and DoD items are read in the present tense at closure.

**Current state is unread.** The billing API is not reachable from this session — see §5.

## 5. The corrected credit filter live — the referent moved

The phrase was written `2026-08-21 19:19:43 +0300`. On that date, "the corrected credit
filter" had exactly one possible referent: **ADR-0004 Amendment 1 (2026-08-19)**, which
corrected the budget's spend basis from `EXCLUDE_ALL_CREDITS` to an enumerated filter
subtracting the `FREE_TIER` credit type and nothing else.

That filter was falsified in production on **2026-08-22**. It matched nothing on this
account — the usage was absorbed by a promotional credit with no matching credit line —
so the budget published gross cost and the kill-switch detached a healthy project twice.
**ADR-0004 Amendment 4** (2026-08-25, **Accepted** 2026-08-26) replaced it with
`INCLUDE_ALL_CREDITS` plus a threshold, on the reasoning that subtracting all credit
types "is the one reading that cannot be wrong about a category it has not met".

The consequence for this DoD item is sharp:

> **Read with its authoring referent, fact 5 asserts as a completion condition the exact
> configuration that CI Gate H now fails the build for containing.**

Gate H's failure string is `Gate H — Amendment 1's credit filter is back in Terraform`
(`scripts/ci/invariant-gates.sh:311`). The item and the gate point at the same object and
disagree about whether it should be there, because the phrase kept pointing while the
object underneath it was replaced.

**Read with today's referent — Amendment 4's filter — the fact is evidenced:**

- Repository: `infra/terraform/killswitch.tf:284` — `credit_types_treatment =
  "INCLUDE_ALL_CREDITS"` on `zero_spend`, no enumerated `credit_types` list. The second
  budget, `gross_cost_alert` (`:334`), carries `EXCLUDE_ALL_CREDITS` deliberately and has
  no Pub/Sub binding.
- Gate H passed in run [`33475352691`](https://github.com/arslan-kursad/plumbline/actions/runs/33475352691) on `main`.
- Live at the time: `kill-switch.md` §4a records "the budget filter went live 2026-08-25
  ~11:51 and the function's threshold 2026-08-26 09:34:53. Both confirmed at the API
  rather than from state", with the three-step threshold live-fire archived beneath it.

**What is not measured: whether the deployed budget still carries that filter today.**
The read is one API call, and Lane A cannot make it — `.claude/settings.json` denies
`Bash(gcloud billing:*)`:

```
gcloud billing budgets list --billing-account=<id> --format='value(displayName,budgetFilter.creditTypesTreatment,budgetFilter.creditTypes)'
```

Recorded as unread rather than assumed, per §4a's own standard: "confirmed at the API
rather than from state".

**This is the deny-list shape defect again, and it should be counted.** The closure note
§5 records that the Lane A deny-list denies by command surface rather than by effect,
with `Bash(gcloud alpha:*)` as its example. `Bash(gcloud billing:*)` is the second
instance: `budgets list` is a read, and it is refused for sharing a prefix with the
commands that detach billing. The note's example is not the only one.

---

## A fourth wording, found while writing this up

DoD 1 has four texts in three documents, each shorter than the last, and the status
`satisfied` has travelled across all four:

| Where | What it says | Facts named |
|---|---|---|
| spec §7 item 1 | `#33 closed - post-fix live-fire succeeded, evidence archived, billing re-attached, the corrected credit filter live` | 5 |
| spec §3, gate row G1 | Wave 0's conditions, ending `No application service deploys before G1.` | ordering + 5 |
| [`f2-dod-1-2-5-12-rederived.md`](f2-dod-1-2-5-12-rederived.md) §"DoD 1 (G1)" | quotes §3's ordering clause as "G1's operative clause" | 1 |
| [`F2-completion-note.md`](../specs/F2-completion-note.md) §1, row 1 | `G1 - #33 closed, post-fix live-fire` | 2 |

The closure note's own table is the shortest of the four. Read against §7 item 1 it drops
three facts silently; read against §3 it drops the ordering clause the evidence it cites
was actually measuring.

**The same shape, one row down.** §1 row 12 reads `Gates A-H green` in its item column
and `nine gate assertions green` in its evidence column. Eight lettered gates, nine
assertions - the ninth is `Gate B coverage`, which has no letter. Here the evidence column
happens to carry the correcting number, so nothing is lost. It is the same defect with a
better outcome, which is worth noticing precisely because the outcome was luck.

## What this changes for the closure note

The re-derivation closed DoD 1 against §3's ordering clause — *"No application service
deploys before G1"* — which is real, verbatim, and at
[`F2-minimal-gcp-footprint.md`](../specs/F2-minimal-gcp-footprint.md) §3. It is simply
not in §7 item 1. Of item 1's five facts it re-measured one (#33's closure timestamp).

Measured here, the item does not close cleanly:

- Facts 1, 2, 3 hold.
- Fact 4 holds as an event and fails as a present-tense claim; its current value is Lane C's to read.
- Fact 5 is ambiguous by construction and one of its two readings is CI-forbidden.

**Recommendation.** Do not carry "DoD 1 — met" into the closure note on the existing
evidence. Either re-word §7 item 1 so its five facts are individually checkable and
name their referents by version (`ADR-0004 Amendment 4's credit filter`, not "the
corrected credit filter"), or state in the closure note which of the five were measured
at closure and which were inherited. The `10/13` figure rests on this item.
