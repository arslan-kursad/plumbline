# F2C-08 claim 2 — the channel test

**Sent:** 2026-09-01, between `04:48:36Z` and `04:48:39Z` · **Channel:**
`17645137777150770481`, type `email`, `enabled: true`, displayName *plumbline alerts*
**Result:** `HTTP 200`, body `{}` · **Go-ahead:** given per §4, this being one of F2's three
send-shaped actions

## What was sent, and why this call

Cloud Monitoring's v3 API offers no test-notification endpoint, and `gcloud beta monitoring
channels` exposes only `create`, `delete`, `describe` and `list`. The one API-driven real
send available to Lane A is:

```
POST https://monitoring.googleapis.com/v3/projects/plumbline-19458/notificationChannels/17645137777150770481:sendVerificationCode
```

## The limit, stated rather than glossed

**This is a verification email, not an alert notification.** It proves the address receives
mail from Cloud Monitoring. It does not prove the alert path, and the directive already
scopes that away: claim 3 says the policy firing end-to-end is proven only by F2C-14.

The console's *Send test notification* would be closer in shape, and it is not reachable
from an API. If a stronger artefact is wanted, that button is the way to it — recorded here
so the choice is visible rather than absent.

## The send is proven; arrival is not, by me

A `200` with an empty body means the API accepted the request. **It does not mean an email
arrived**, and that distinction is exactly the one this task exists to enforce — claim 2 is
titled *delivery, proven not read* because a configuration read had been standing in for it.

Arrival is confirmed by the person holding the inbox. Until that confirmation is recorded
here, this document proves a send was accepted and nothing more.

## Decision 14 — attribution is by timestamp, not by marker

Measured before sending: **the channel test admits no distinguishing marker.** The channel
resource carries only `displayName`, `labels`, `enabled`, `type` and its mutation records —
no `description`, no `userLabels` — and the email body is Google's fixed template, so
nothing of ours can be carried in it.

So attribution between this notification and the drill's alert rests on **recorded
timestamps and a gap**, which is the fallback Decision 14 names. Of its two options, this is
the second, and recording which applied is part of the decision.

| | |
| --- | --- |
| channel test sent | `2026-09-01T04:48:36Z` … `04:48:39Z` |
| earliest permissible drill | **`2026-09-01T05:18:39Z`** |
| drill's own marker | `plumbline_drill=f2-dod4` — the drill *does* carry one |

The asymmetry is worth naming: the drill's alert is identifiable on its own content, so the
gap protects the reverse direction — it stops this verification email being mistaken for the
drill's alert, not the other way round.

## Timestamp provenance

Decision 14 asks for the send timestamp "from the command's own output". The response body
is empty and the call does not appear in the audit log, so there is no timestamp in the
output to take. The record is therefore the bracket around the call, taken from the same
shell that issued it — narrower than three seconds, and honest about being a bracket rather
than a reported instant.
