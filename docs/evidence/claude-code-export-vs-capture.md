# Claude Code — what is actually blocked, and what is not

**Read:** 2026-09-03 · **Lane:** A · **Task:** F3 Unblock dispatch U-05
**Sources:** [`#10`](https://github.com/arslan-kursad/plumbline/issues/10);
[`claude-code-capture.md`](../runbooks/claude-code-capture.md); `scripts/capture/`

**No capture run was attempted.** This is a read of the issue and the harness.

---

## The premise needed correcting before the question could be answered

This dialect is routinely described in project documents — including one I wrote on
2026-09-03 — as *"blocked at authentication"*. Read against `#10` and the runbook, that is
not what blocks it, and the difference decides how expensive it is to close.

## (a) What exactly is authentication-blocked

**Not capture. Not export. The *nested, non-interactive invocation* is.**

[`claude-code-capture.md`](../runbooks/claude-code-capture.md):13 —

> A nested, non-interactive `claude -p` session cannot authenticate: the credential is
> […] an authenticated session is the only way to reach them, and that is a terminal only
> the [human] has.

The runbook records three attempts, all of which *"failed at authentication before reaching
a tool call"* (:43). Every one of those was **Lane A trying to run Claude Code from inside
Claude Code**. The authentication failure is a property of the caller, not of the capture
path or the exporter.

**So the accurate statement is:** Lane A cannot *perform* the capture. Nothing about
authentication prevents the capture from working when a human performs it.

## What `#10` actually lists as blocking

`#10` names three findings and marks **one** of them blocking, and it is not authentication:

| `#10` finding | Nature | Blocking? |
|---|---|---|
| 1 · Span export is behind a beta flag | configuration — `CLAUDE_CODE_ENABLE_TELEMETRY=1`, `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`, `OTEL_TRACES_EXPORTER=otlp`, default off | no — settable |
| 2 · The dialect does not speak `gen_ai.*` | mapping work; also OQ-4's question | no |
| 3 · **The emission carries personal data into a public repository** | `user.id`, `user.email`, `organization.id`, `user.account_uuid`, `session.id`, `terminal.type`, and `workspace.host_paths` on events | **yes** |

**The blocking item is redaction, not access.** That is a materially different problem: it
is about what may be *committed*, not about whether spans can be produced.

## (b) Is ordinary human terminal use blocked by the same cause?

**No.** The cause in (a) is that a nested non-interactive session holds no credential. A
human's own terminal is interactively authenticated by definition — the runbook's own
prerequisite list asks for exactly that (*"Claude Code installed and **interactively
authenticated**"*, :47).

So continuous OTLP export during ordinary human use requires setting three environment
variables in a terminal that already authenticates. The runbook documents them at :95 and
records at :106 that *"all three of the first environment variables are required for spans;
the beta gate is"* the third.

**Nothing in the authentication finding stands in the way of that.**

## What this changes

Of the three SC-1 dialects, `claude-code` is the only one whose emitter **already exists and
already emits** — the other two need instrumentation projects
([`c2-triage-readout.md`](c2-triage-readout.md), [`c1-adjudicator-readout.md`](c1-adjudicator-readout.md)).
And its block is not access but redaction, for which this repository already built the
machinery: `scripts/capture/redact.py`, `manifest_validate.py` covering `redacted_fields`,
and a redaction gate asserted in CI, all delivered under `#153`.

**That makes it plausibly the cheapest of the three to close**, and it is currently
described in a way that implies the opposite. Whether it is worth closing first is a
scheduling decision and is not taken here — `eval-plan.md` §7.1 excludes Claude Code from
the seeded-regression experiment, so its value is to SC-1 and SC-2, not to the gate.

## What this readout does not do

It does not attempt a capture, does not set any environment variable, and does not assess
whether the redaction rules are sufficient for the documented attribute set. The last of
those is a real open question — `#10`'s finding 3 lists attributes the redaction config
would have to cover, and checking that coverage is a separate task.
