# `detach_threshold` = 200 TRY — applied and verified

**Measured:** 2026-09-02 · **Lane:** A (read-only verification) · **Applied by:** maintainer
**Change:** ADR-0004 Amendment 5, D2 · **Merged as:** `#150` (`c5929dd`)
**Repo:** `main` @ `d080dda`

The apply is Lane C by [`kill-switch.md`](../runbooks/kill-switch.md) §4a — the kill-switch's
four resources are applied from the maintainer's own credentials, targeted, because
`ci-deploy` has no grant on the function-source bucket. *"The last cost control is not
rewritable by the automation it bounds."*

---

## Four readings, all after the apply

| Reading | Before | After |
|---|---|---|
| Live API — `serviceConfig.environmentVariables` | `DETACH_THRESHOLD=5` | **`200`** |
| Function `updateTime` | `2026-08-26T09:47:45Z` | **`2026-09-02T09:22:01Z`** |
| Revision (latest / serving) | `00002-hed` / `00002-hed` | **`00003-yoh` / `00003-yoh`** |
| Terraform state, serial | `5`, serial 29 | **`200`, serial 30** |

**Why four and not one.** The env var alone cannot distinguish an apply that reached the API
from a state file edited without one, and it cannot show whether the new revision is
actually serving. The serial increment and the revision pair are what make the reading a
statement about the deployed system rather than about one field.

The revision pair matters on its own: `latestReadyRevisionName` and the traffic target are
the same, so there is no half-completed migration with the old revision still serving.

## The first attempt did not apply, and that is recorded rather than tidied away

An earlier attempt on the same day left all four readings unchanged — API `5`, state `5` at
serial 29, state file last written 30 hours earlier, no lock object. `terraform plan`
against the same target then produced a clean `0 to add, 1 to change, 0 to destroy`, which
ruled out backend, credential and working-directory causes and left the apply itself as
the thing that had not completed.

Recorded because "the command was run" and "the change is live" are different claims, and
the four readings are what separates them. The second attempt used
`terraform plan -out=…` followed by `terraform apply <planfile>`, which applies the plan
that was reviewed and does not prompt.

## What this does not establish

**The ceiling is configured, not proven.** ADR-0004 Amendment 5's own Verification section
says so: Amendment 4's three-step threshold live-fire is the procedure, and re-running it
against `200.00` is required before the ceiling can be claimed as enforced. Until that run
is archived this describes a configuration.

**The detach path cannot fire on real traffic before 2026-10-05.** Net cost is zero by
construction while the promotional credit applies (`#74`), so the live-fire is either
synthetic now — the §3 procedure all three prior attempts used — or against a real figure
after the credit ends.

## The live-fire this owes is DoD 13b, and they are one event

Spec §7 item 13b requires *"the three-step kill-switch live fire has been re-run **after**
the account upgrade and passed. Every prior firing occurred behind the credit; this is the
first time the `INCLUDE_ALL_CREDITS` trigger arms against a real charge."*

Amendment 5 requires the same three-step procedure re-run against the new threshold.
**One run satisfies both**, and recording them separately would produce two obligations
where there is one event — the defect the completion note's §5 identifier rule describes.
Sequencing follows from that: the run has to happen after C1's account upgrade
(**2026-09-21**) and after the credit ends (**2026-10-05**) to satisfy 13b's "against a
real charge", so it is one dated item and not two.

## DoD 13a's premise was withdrawn and the item was not reconciled — raised, not answered

Spec §7 item 13a requires *"Billing Reports for a full period show **gross cost $0.00**,
not merely $0.00 billed after credit offset."*

Amendment 5 withdrew the sentence that requirement rests on — *"`$0.00` is a hard
constraint here, not a target"* — and replaced it with a 200 TRY **net** ceiling. Gross
cost is non-zero during entirely free operation (Amendment 1), which is why the hard-zero
claim was close to unachievable and is the reason the ceiling exists. So 13a now asks for
evidence of a claim the project has stopped making.

Two readings, and choosing between them is a judgement rather than a transcription:

1. **13a becomes the ceiling.** *"Billing Reports for a full period show net cost ≤ 200
   TRY."* Consistent with SC-4b's proposed wording and with the ADR. Retires the
   gross-zero claim entirely.
2. **13a survives as a separate, weaker claim.** Gross cost is recorded but not gated on,
   so the project can still report what it costs before credits without the number being
   a pass condition.

**Not drafted here.** It changes a Definition of Done item after the phase ran, which is a
spec amendment and belongs with the maintainer — the same treatment `eval-plan.md` row 4.6
was given for the same reason. `#74` and `#138` both touch it.
