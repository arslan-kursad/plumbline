# Incident — real spend reported, kill-switch fired, phase halted

**Opened:** 2026-08-22 · **Status:** cause identified 2026-08-22 — **no billed cost**; halt lifted on the evidence below
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

## Resolved: the cost was the kill-switch's own CPU, and it is fully credited

Billing Reports, account `011680-E61D62-C3CAA2`, August 1–22 2026, grouped by SKU. Exactly
one SKU carries a non-zero gross line, and it is the kill-switch function itself:

| SKU | Service | Usage | Usage cost | Other savings | Subtotal |
| --- | --- | --- | --- | --- | --- |
| Cloud Run functions CPU (Request-based billing) in us-central1 | Cloud Run Functions | 30.82 second | ₺0.04 | -₺0.04 | **₺0.00** |

Every other SKU reads ₺0.00 gross — Cloud Storage class A and B operations, Firestore
reads and writes, Cloud Build minutes, Cloud Run functions memory and invocations, Pub/Sub
inter-region delivery, Artifact Registry egress. **Subtotal ₺0.00, tax none, total ₺0.00.**

So the answer is reading (2) below: **credit lag.** The 0.01 TRY in the 02:16 notification
was a gross line that had not yet had its `FREE_TIER` credit applied. The credit has since
landed and the interval has settled at zero, where it had been for the fourteen hours
before.

**There is no billed cost, and the stop rule's substantive condition is not met.** Spec §2
names two triggers: a budget notification carrying `costAmount > 0.00`, which fired and is
the *detector*; and *"Billing Reports showing gross cost not fully credit-offset"*, which is
the *adjudicator* — and it says the gross **is** fully offset. The halt is lifted on that
reading, and this note is the escape hatch's incident record, written before the lifting
rather than assembled after it.

**The irony is load-bearing rather than decorative.** The only thing in this project that
has produced a gross cost line is the control that exists to stop gross cost lines. Those
30.82 CPU-seconds are three live-fire attempts plus a day of ~30-minute budget
notifications. A pipeline carrying no traffic still pays its watchman.

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
W-repo.1 records that Amendment 1's premise had never been observed here. It is now
observed, and it holds: Always Free **is** credit-implemented on this account — a gross
line appears and a `FREE_TIER` credit of equal size cancels it. Amendment 1's premise was
right; what it did not anticipate is that the two do not land at the same instant, and the
budget publishes in between.

**The observed lag: between 00:31 and 02:16 UTC the reported figure read 0.01 with no
credit; by 15:50 the same interval read 0.00 with a -₺0.04 credit against a ₺0.04 gross.**
That is one data point for the series the credit-lag procedure is meant to accumulate, and
it is the first.

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

- **Billing has not been re-attached.** It was the wrong move before the cause was known —
  re-attaching restores the conditions that produced the charge — and after the cause was
  known it became blocked on the step above it: the 24-message backlog has to be dropped
  first, and that command was refused to the agent by its own tooling. The restart
  procedure below is therefore written for the maintainer to run rather than performed.

## Restart procedure, and why the order is not negotiable

**The stale backlog must be dropped before billing is re-attached.** While the function
could not start, its Eventarc subscription accumulated **24 undelivered notifications**,
each carrying the stale `costAmount: 0.01` snapshot. Re-attaching first means the function
starts, receives one of them, and detaches billing again within two seconds — the control
flapping on a figure that stopped being true hours earlier.

```
gcloud pubsub subscriptions seek eventarc-us-central1-billing-killswitch-041365-sub-406 \
  --project plumbline-19458 --time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

gcloud beta billing projects link plumbline-19458 \
  --billing-account 011680-E61D62-C3CAA2

gcloud beta billing projects describe plumbline-19458    # expect billingEnabled: true
```

Then watch one notification arrive (~30 minutes) and confirm it reads `cost=0`:

```
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="billing-killswitch"' \
  --project plumbline-19458 --freshness=1h --limit=10 --format='value(timestamp,textPayload)'
```

If it reads `cost=0.01` again, the credit has not landed for the next gross line either and
the trigger rule — not the billing state — is what needs changing (#71).

## Then, to resume Wave 2

1. Re-run the failed `images` job on
   [run 32582278023](https://github.com/arslan-kursad/plumbline/actions/runs/32582278023)
   so both images exist for `ac7b5af132d17bcd8177a805a7dbf743aabf625a`, the commit carrying
   the OIDC validator and the Firestore registry.
2. `image_tag` is already bumped to that commit on the Wave 2 branch; the plan job verifies
   the images exist before the reviewer is asked.
3. Merge #66 and #67, dispatch `deploy.yml` for wave 2, approve at `gcp-production`.

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
