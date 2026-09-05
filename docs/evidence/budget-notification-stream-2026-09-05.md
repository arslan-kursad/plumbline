# The budget notification stream, read from the function's own logs

**Read:** 2026-09-05 · **Lane:** A · **Repo:** `main @ e1a1d8f`
**Source:** Cloud Logging, `resource.labels.service_name="billing-killswitch"`, project
`plumbline-19458`, retention window `2026-08-21` → `2026-09-05`
**Task:** [`completion-plan.md`](../specs/completion-plan.md) W0-5, W0-6 · **Closes:** DoD 8
(`#18`), DoD 9 · **Narrows:** `#74`

> **Why this source exists at all.** The `zero-spend` budget publishes to `billing-alerts`
> on every cost update, and the kill-switch function logs each notification it receives
> before deciding. So the function's log **is** the notification archive, and it has been
> accumulating since the function was deployed. Nothing had read it as a series.
>
> **What it is not.** Every figure below is **net of all credits** since 2026-08-25 ~11:51
> and net of `FREE_TIER` credits only before that. It is not gross cost, and §5 is careful
> about what it can and cannot conclude from that.

---

## 1. The series

**529 notifications retained**, every one `currency=TRY`.

| `cost` | Count | Kind |
|---|---:|---|
| `0` | **518** | real |
| `0.01` | 6 | 5 synthetic (live fire), 1 real |
| `0.04` | 3 | real |
| `4.99` | 1 | synthetic — Amendment 4 step 1 |
| `5` | 1 | synthetic — Amendment 4 step 2 |

Synthetic messages identify themselves: the live-fire procedure sets `interval_start` to a
label rather than a date (`LIVE-FIRE`, `AMENDMENT-4-AT-THRESHOLD`), so a test message and a
real one are separable by construction rather than by timing. **That is the identity rule
working in a place nobody wrote it down for.**

## 2. Every non-zero reading, with its timestamp

```
2026-08-21T11:05:13Z  cost=0.01  interval_start=LIVE-FIRE                     synthetic — Attempt 1
2026-08-21T20:17:49Z  cost=0.01  interval_start=LIVE-FIRE-2                   synthetic — Attempt 2
2026-08-21T20:18:33Z  cost=0.01  interval_start=LIVE-FIRE-2-REDELIVERY        synthetic
2026-08-21T20:29:10Z  cost=0.01  interval_start=LIVE-FIRE-3                   synthetic — Attempt 3, the pass
2026-08-21T20:30:34Z  cost=0.01  interval_start=LIVE-FIRE-3-REDELIVERY        synthetic — idempotence
2026-08-22T02:16:18Z  cost=0.01  interval_start=2026-08-01T07:00:00Z          REAL — first false positive
2026-08-22T17:11:17Z  cost=0.04  interval_start=2026-08-01T07:00:00Z          REAL — second false positive
2026-08-25T10:58:22Z  cost=0.04  interval_start=2026-08-01T07:00:00Z          REAL — third detach
2026-08-25T11:53:03Z  cost=0.04  interval_start=2026-08-01T07:00:00Z          REAL — the message published before the filter landed
2026-08-26T09:40:54Z  cost=4.99  interval_start=AMENDMENT-4-BELOW-THRESHOLD   synthetic — WARN, no detach
2026-08-26T09:45:03Z  cost=5     interval_start=AMENDMENT-4-AT-THRESHOLD      synthetic — detach
```

**The four real rows match [`f2-dod1-five-facts.md`](f2-dod1-five-facts.md) fact 4's table
one for one**, which reconstructed them from `kill-switch.md` §4 and §4a. Two documents
derived from prose now have the machine's own record behind them, and it agrees.

**From `2026-08-25T11:53:03Z` to `2026-09-05T11:06:31Z` — eleven days — every real
notification reads `cost=0`.**

## 3. DoD 8 / `#18` — a real notification reading `costAmount = 0.00`

`#18` asks for a **real** budget notification, captured with the Cloud Run services
deployed and serving traffic, asserting `costAmount == 0.00`.

```
2026-09-01T05:44:42Z  budget="plumbline zero-spend" cost=0 currency=TRY
                      threshold=5 threshold_exceeded=0 interval_start=2026-08-01T07:00:00Z
```

**Sixteen minutes after the DoD 7b first delivery** (`2026-09-01T05:28:55Z`, from
`.e2e-cloud/result.json`) and **nineteen minutes after the poison drill dead-lettered**
(`2026-09-01T05:25:02Z`, [`f2-dod4-drill.md`](f2-dod4-drill.md)). Its
`interval_start=2026-08-01T07:00:00Z` is the August billing period, which contains Wave 4's
apply, both cloud deliveries and the drill.

**So the period this figure reports on is one in which the services ran and served**, which
is the substance of `#18`'s "while services serve traffic". Two later notifications in the
same period — `06:19:31Z` and `07:00:36Z` — read the same.

**The billing period boundary is 07:00 UTC, not midnight.** `interval_start` reads
`2026-09-01T07:00:00Z`, which is midnight Pacific. Recorded because a reader checking
whether the first delivery falls inside the August period will otherwise put it in
September by six hours and reach the opposite conclusion.

## 4. DoD 9 — the credit-lag procedure, live, with data points

DoD 9 asks that the credit-lag procedure be live with **at least one data point**. It has
four, and they are the reason the procedure exists:

| When | Reported | What it was |
|---|---|---|
| 2026-08-22T02:16Z | 0.01 TRY | a gross line arriving before the credit that cancelled it; billing detached, nothing was ever billed |
| 2026-08-22T17:11Z | 0.04 TRY | the same, 18 minutes after a re-attach |
| 2026-08-25T10:58Z | 0.04 TRY | the first delivery to find a warm instance |
| 2026-08-25T11:53Z | 0.04 TRY | a message published at ~11:47, before the new filter landed at ~11:51, carrying the old figure |

`kill-switch.md` §4a is the procedure and it is deployed. **The data point is not a
hypothetical: the lag was observed four times and cost four detachments.**

## 5. What this says about `#74`, and what it does not

`#74` and [`ADR-0009`](../adr/ADR-0009-instrumental-credit-expenditure.md) §1.4 disagree
about which credit absorbs this project's usage. `#74`'s argument rests on a premise it
asserted from the Billing Report:

> The budget — which filters on `FREE_TIER` credits only — reports the gross figure
> unchanged.

**That premise is now measured rather than asserted.** Amendment 1's enumerated
`FREE_TIER`-only filter was live until 2026-08-25 ~11:51 (`kill-switch.md` §4a). Under it
the budget reported **0.04 TRY** — and `#74` records the August Billing Report as gross
`0.04`, savings `0.04`, subtotal `0.00`.

Reported = gross − `FREE_TIER` credits. Reported equals gross. **Therefore the `FREE_TIER`
credits applied to that line were zero, and the 0.04 of savings came from something that is
not of type `FREE_TIER`.**

**What that settles.** `#74`'s premise holds. Always Free was not what covered this
project's only non-zero cost line in August.

**What it does not settle, stated plainly.** It does not establish that the *promotional
trial credit* was the thing that covered it. GCP's "savings" column carries credits **and**
discounts, and this reading cannot tell a promotional credit from a discount of another
kind. ADR-0009 §1.4's counter-observation — that the credit's remaining balance still equals
its promo value exactly, when 0.04 is representable at the displayed precision — is
untouched by anything here and remains a real objection.

**So the dispute narrows from two candidates to two different ones**, and the read that
closes it is unchanged: cost broken down **by credit type**, which needs the Cloud Billing
console (see [`billing-readout-2026-09-05.md`](billing-readout-2026-09-05.md) §4 for why no
command returns it).

## 6. Two corroborations that were not being looked for

**The live-fire timezone question is closed.**
[`f2-dod1-five-facts.md`](f2-dod1-five-facts.md) fact 2 flagged that `kill-switch.md` §4
does not label its log timezone, and that Attempt 3's ordering relative to `#33`'s closure
holds under either reading but is unlabelled. Cloud Logging stamps UTC explicitly:
Attempt 3 fired at **`2026-08-21T20:29:10Z`**, `#33` closed at **`2026-08-21T20:35:09Z`**.
**Six minutes, UTC, fire before closure.** The ambiguity was real and the answer is the
first of the two readings that file offered.

**Amendment 4's three-step live fire is in the machine record**, not only in the runbook:
`4.99` produced no detach, `5` produced one, four minutes apart on 2026-08-26. That is
steps 1 and 2 of the procedure ADR-0004 Amendment 5's Verification section requires be
re-run against `200.00`.

## 7. Provenance and its limit

Read 2026-09-05 with `gcloud logging read` against `plumbline-19458`, filtered to the
kill-switch service, `--freshness=40d`, 529 entries returned and all of them scanned for a
non-zero `cost` field rather than sampled.

**The window is the retention window, and it is not the project's history.** The `_Default`
log bucket keeps 30 days, so the earliest entry here is 2026-08-21 and anything before it is
gone. A claim about the whole of August cannot be made from this file; a claim about
2026-08-21 onward can.
