# F2 DoD 8, 9 and 10 — gross or billed, and what a deliberate spend would falsify

**Read:** 2026-09-03 · **Lane:** A · **Task:** F3 Unblock dispatch U-04
**Source:** [`F2-minimal-gcp-footprint.md`](../specs/F2-minimal-gcp-footprint.md) §7, items 8–10 and 13

**This readout gates a pending human decision. It does not act on one, and it recommends nothing.**

---

## The answer is written into the spec, directly beneath the three items

> *Items 8–10 are evaluated against **billed cost** while a promotional trial credit is
> active. They establish that the period was **fully credit-offset**. They do **not**
> establish that gross cost is zero, and are not evidence for the project's zero-cost
> claim. That claim is carried by item 13.*

So the semantics question is not open. **Items 8–10 are billed-cost items** — net after
credit — and the spec says in terms that they carry no gross-cost claim.

## Per item

| # | Item | Asserted of | Would deliberately raising gross spend before 2026-09-30 falsify it? |
|---|---|---|---|
| 8 | Verification B — a real budget notification reading `costAmount = 0.00` | **billed / net** | **No**, while the credit absorbs the spend |
| 9 | The credit-lag procedure is live with at least one data point | **procedure liveness**, not a value | **No** — see below |
| 10 | Billing Reports for the period fully credit-offset at `$0.00` billed | **billed** | **No**, while the credit absorbs the spend |

**Item 8.** The budget publishes net cost after all credits — ADR-0004 Amendment 4 D1,
*"Trigger on net cost after all credits"*, and Gate H exists to keep any enumerated credit
filter out of Terraform so the figure stays all-credits-inclusive. Gross rising while the
credit absorbs it leaves `costAmount` at `0.00`, which is precisely what item 8 asks to
observe.

**Item 9** is the one that is not a value at all. It asks that the credit-lag *procedure be
live with at least one data point*. A period with non-zero gross and zero billed is a
**better** data point than a period with neither, because credit lag is only observable when
there is something to lag. Raising gross spend cannot falsify item 9; the failure mode for
item 9 is an idle account.

**Item 10** is the one with a sharp edge, and it is worth stating exactly where it is.
*"Fully credit-offset at `$0.00` billed"* holds only while the period's gross stays within
the credit remaining. The credit is recorded at ₺13,987.54 remaining
([`#74`](https://github.com/arslan-kursad/plumbline/issues/74); and see the caveat below).
A spend that exceeded it inside one period would produce a non-zero billed line and falsify
item 10 directly.

## The three answers do not generalise to the project's claim

The callout is explicit that items 8–10 are **not evidence for the zero-cost claim**. That
claim is item 13 — Verification C — and 13a reads *"net cost at or below the monthly ceiling
— 200 TRY"*, measured **after** the credit ends on 2026-10-05.

**So the two are not in tension and the window matters.** Spend before 2026-09-30 is
evaluated against billed cost by items 8–10, which the credit zeroes. The zero-cost claim is
evaluated after 2026-10-05 by item 13, which the credit cannot reach because it no longer
exists. **A deliberate spend inside the credit window does not touch the claim** — which is
the same conclusion ADR-0009 reaches from the other direction, and this readout is the
spec-side confirmation it was missing.

## Two caveats this read cannot remove

**The credit-remaining figure is not read here.** ₺13,987.54 is transcribed from a console
screenshot via `#74`. `gcloud billing accounts list` was refused at the permission layer
from Lane A on 2026-09-03, so item 10's headroom is stated from a secondary source, not
measured. ADR-0009 §3.1 makes that read a precondition for exactly this reason.

**`#74` and ADR-0009 §1.4 disagree about whether the credit is being consumed at all.** If
the trial credit is *not* the mechanism offsetting usage — the Free Tier discount is — then
item 10's headroom is not ₺13,987.54 and the boundary above sits somewhere else. That
question is settled by the same refused read.

**Neither caveat changes the semantics answer.** Items 8–10 are billed-cost items whichever
credit does the offsetting.
