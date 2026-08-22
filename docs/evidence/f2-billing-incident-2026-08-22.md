# Incident — real spend reported, kill-switch fired, phase halted

**Opened:** 2026-08-22 · **Status:** open, awaiting the maintainer's Billing Reports read
**Trigger:** F2 spec §2 stop rule — *"Any billed cost stops every further wave"* ·
architecture §7 escape hatch
**Wave in flight when it fired:** Wave 2 (#63), Lane A complete, not armed

---

## What happened

At **2026-08-22 02:16:18 UTC** the budget published a notification carrying a **real**
reported cost of **0.01 TRY**, and the kill-switch detached billing from
`plumbline-19458`. It did exactly what it was built to do.

```
2026-08-22T02:16:18.189005Z  INFO  budget notification received budget="plumbline zero-spend"
                                   cost=0.01 currency=TRY threshold_exceeded=0
                                   interval_start=2026-08-01T07:00:00Z
2026-08-22T02:16:18.447424Z  WARN  spend reported; detaching billing account
                                   project=plumbline-19458
                                   billing_account=billingAccounts/011680-E61D62-C3CAA2
                                   cost=0.01 currency=TRY
2026-08-22T02:16:19.362860Z  WARN  billing detached project=plumbline-19458
                                   previous_billing_account=billingAccounts/011680-E61D62-C3CAA2
```

**Billing was attached when this fired, and that is the question a later reader asks
first** — Wave 0's live-fire on 2026-08-21 deliberately produced `billingEnabled: false`,
so "is the current state just yesterday's test?" is the obvious reading. It is not, on two
independent pieces of evidence:

- The function **performed** the detach: `spend reported; detaching billing account`
  followed by `billing detached ... previous_billing_account=billingAccounts/011680-...`.
  When it finds billing already off it says so instead — `billing already detached;
  nothing to do`, which is exactly what it logged for the live-fire redelivery at
  2026-08-21 20:30:34.
- The function **ran at all**, repeatedly, in between. A detached project cannot start it.
  After the hand re-attach recorded in [`kill-switch.md`](../runbooks/kill-switch.md) §4,
  it processed six notifications reporting `cost=0` — 21:05, 21:48, 22:28, 23:10, 23:51
  and 00:31 — and Wave 1's gated apply (21:06–21:08) and the image push (21:18) both
  succeeded, neither of which is possible with billing off.

**So the cost line appeared between 00:31 and 02:16**, on an interval that had read `cost=0`
for the previous fourteen hours. Nothing of ours ran in that window; Wave 1's resources were
created at 21:06–21:18. A billing pipeline reporting those resources' first storage lines
overnight is the shape that fits, which is a concrete thing to look for in the Reports
rather than a hunch to argue about.

**This is not a live-fire.** The Wave 0 tests are distinguishable in the same log by
their synthetic `interval_start` markers — `LIVE-FIRE`, `LIVE-FIRE-2`,
`LIVE-FIRE-2-REDELIVERY`, `LIVE-FIRE-3`, `LIVE-FIRE-3-REDELIVERY`, all on 2026-08-21.
This one carries `interval_start=2026-08-01T07:00:00Z`, the real August billing interval,
and it arrived on the budget's own ~30-minute cadence.

Confirmed at the API, not only in the logs:

```
$ gcloud beta billing projects describe plumbline-19458
billingAccountName: ''
billingEnabled: false
```

## Current state of the project

Billing has been detached since 02:16 UTC. Everything in the project that needs an
enabled billing account is therefore failing:

- **The kill-switch itself cannot start.** Every budget notification since 02:16 has
  produced `The request failed because billing is disabled for this project.` — roughly
  every 30 minutes, ~25 failures observed. The last control in the chain is inert, and it
  is inert *because it worked*.
- **CI on `main` is failing** ([run 32582278023](https://github.com/arslan-kursad/plumbline/actions/runs/32582278023)):
  `images (distroless)` cannot push (`denied: This API method requires billing to be
  enabled`), and `terraform plan (wif)` cannot read state
  (`UserProjectAccountProblem: The billing account for the owning project is disabled in
  state absent`).
- No Cloud Run service exists yet, so nothing user-facing is affected. The live-fire
  window §6 describes — "with none deployed the test has no side effects" — is still
  open, which is the one piece of luck in the timeline.

## What the number means, and what it does not

The budget measures with `credit_types_treatment = "INCLUDE_SPECIFIED_CREDITS"` and
`credit_types = ["FREE_TIER"]` (`killswitch.tf`, ADR-0004 Amendment 1). So **0.01 TRY is
what remained after Always Free credits were applied** — on the premise that Always Free
is credit-implemented rather than an absence of charge.

Two readings fit the evidence, and this repository cannot tell them apart from the logs:

1. **Genuine spend beyond Always Free.** Something crossed a free-tier boundary. Total
   Artifact Registry usage is 151 MB of 500 MB, and the only workloads that ran are the
   kill-switch function and the Wave 1 resources, so if this is real the cause is small
   and identifiable by service.
2. **Credit lag.** The gross cost line was reported before its `FREE_TIER` credit was
   applied, and the net figure will settle at zero. ADR-0004 Amendment 1 deferred exactly
   this question — an epsilon threshold versus a two-update confirmation rule — because
   choosing before observing real sequences would substitute a guess for a measurement.

**This event is that measurement, and it is the first one this account has produced.**
W-repo.1 records that Amendment 1's premise had never been observed here; Verification A
(#17, #18) is the observation, and it needs the Billing Reports console — gross versus
credited, by service, by day — which is Lane C.

## What was done and what was deliberately not done

Done:

- Investigation, from the logs and the API, read-only.
- Wave 2 **not armed.** The stop rule halts every further wave, and the wave was ready to
  dispatch when this was found.
- `#66` and `#67` held unmerged. They mutate nothing, so merging them is permitted under
  Lane A — but the wave's own ordering (bump `image_tag` to a commit whose images exist)
  cannot complete while CI cannot push images, and merging a Terraform change during a
  billing incident buys nothing.

Not done, deliberately:

- **Billing has not been re-attached.** That is Lane C — the billing console, a human with
  billing permissions — and it is also the wrong first move: re-attaching before the cause
  is understood restores the conditions that produced the charge, and the kill-switch will
  fire again on the next notification carrying the same interval's cost. It did precisely
  that once already: detached at 2026-08-21 20:29 (live-fire 3), re-attached, then
  detached for real at 02:16.

## What the maintainer needs to do, in order

1. **Billing Reports, for billing account `011680-E61D62-C3CAA2`, August 2026:** gross
   cost and credited cost, grouped by service and by day. The question is which service
   produced a non-credit-offset line, and whether the credit arrives on a lag.
2. Decide on re-attachment with that in hand. If it is credit lag, the fix is a budget
   rule change (Amendment 1's deferred question, now with a data point). If it is genuine
   spend, the service that caused it is the thing to change before billing comes back.
3. Record the observation against #18 and #17 — this is Verification A arriving
   unannounced, and it is worth more than the scheduled version because it is a real
   sequence rather than a quiet month.

## Timeline

| When (UTC) | What |
| --- | --- |
| 2026-08-21 10:24 | Kill-switch function deployed (current revision) |
| 2026-08-21 11:05 | Live-fire 1 — synthetic, failed on a permission (ADR-0004 Amendment 3) |
| 2026-08-21 20:17–20:18 | Live-fire 2 and its redelivery — synthetic, failed |
| 2026-08-21 20:29–20:30 | Live-fire 3 and redelivery — synthetic, **passed**; detach, idempotent redelivery; billing re-attached afterwards (#33 closed, W0.5) |
| 2026-08-21 21:18 | Collector and worker images pushed to Artifact Registry (#62) |
| 2026-08-22 (Wave 1) | Wave 1 applied through the gated path (W1.8) |
| **2026-08-22 02:16** | **Real budget notification, cost=0.01 TRY; billing detached** |
| 2026-08-22 02:16 → now | Every subsequent notification fails: the function cannot start without billing |
| 2026-08-22 15:38 | Discovered — `main` CI failed on the image push and the Terraform state read |

## Reading this back later

The control chain worked. A real cost line appeared, the budget published, the function
detached billing inside a second, and the project stopped being able to spend money. The
cost of that success is that the same mechanism cannot report on itself afterwards — a
detached project cannot run the function that detached it — so the failure mode of a
*working* kill-switch is silence, and what surfaced it was a CI job failing on something
else entirely.

That is worth a follow-up independent of how the 0.01 TRY resolves: **nothing in this
project alerts on "the kill-switch fired".** The notification channel carries the DLQ
depth alert (Wave 1), not this. Discovering the last cost control has fired by noticing
that an unrelated build broke is not a monitoring story anyone would choose.
