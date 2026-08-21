# ADR-0006 — PII redaction happens in the worker, after deserialization

**Status:** Proposed · **Date:** 2026-08-21 · **Work package:** F1 / W4
**Architecture:** §2.1, §2.3, §3.2, §3.4, §5, §6.3
**Supersedes:** — · **Superseded by:** —

> **Proposed, not accepted.** This ADR was authored by Claude Code under the F1
> autonomous governance mode, which explicitly excludes flipping an ADR to `Accepted`
> (F1 spec §7). The redaction stage it describes is implemented and tested, and it is
> implemented in isolation precisely so that a rejection at the F1 exit review is a
> small change rather than a rewrite. Issue #11 owns the question.

## Context

Claude Code's native OTel emission carries personal data by default. This was measured,
not assumed: `docs/evidence/claude-code-otel-capture.md` §4.4 records `user.id`,
`user.email`, `organization.id`, `user.account_uuid`, `user.account_id` and `session.id`
on **every span** of every capture, and §7.1 records that they sit on span attributes
rather than on the resource — so a resource-level denylist would remove none of them.
The documentation adds `workspace.host_paths` on events; no capture has produced an event
that carries it, and issue #11 requires it be treated as present until one shows
otherwise.

Three constraints meet here.

1. `CLAUDE.md` forbids personal data anywhere in this repository, fixtures and example
   payloads included, and the repository is public.
2. Architecture §2.1 forbids the collector from parsing span semantics, normalizing
   attributes, or applying dialect logic; ADR-0001 adds that the protobuf bytes are never
   re-modelled en route. Redaction is attribute manipulation on deserialized content, so
   it is excluded from the collector twice over.
3. The pipeline between the two is Pub/Sub, which means anything not redacted at the
   collector is redacted no earlier than the worker — and transits, and can persist.

The third point is the one that has not been decided anywhere. It would otherwise simply
happen.

## Decision

1. **Redaction runs in the worker**, after deserialization and normalization, before the
   write. `Plumbline.Normalization.Redaction.Redactor` is a stage of its own: it operates
   on finished rows, reads nothing but its rule files, and no other stage knows it exists.
2. **Rules are versioned data, not code:** `normalization/redaction/v1/<dialect>.yaml`,
   embedded at build time beside the mappings (ADR-0003). Every rule names the key it
   covers and **why**, and a test fails a rule with no reason — a rule nobody can justify
   is a rule nobody can safely remove.
3. **Values are replaced, keys are kept.** A redacted value becomes
   `[REDACTED:sha256:<first 8 hex of sha256(value)>]`. Deterministic, so counts and joins
   over redacted keys still work: the same `client_request_id` on a span and on its event
   still matches, and spans of one session still group without the session being nameable.
   The key, its position, and the fact that a value was there stay visible.
4. **Rules apply at every attribute level** — resource, scope, span, event, link —
   because the identity block was found on spans and events, and a rule scoped to where a
   key was last seen fails the next time the emitter moves it.
5. **Redaction is per dialect.** Only `claude-code` has rules today. A dialect without
   rules is untouched, and adding rules for a dialect is a pull request with fixtures.
6. **The transit and DLQ consequence is accepted explicitly**, with the mitigations under
   Consequences. Accepting it is the substance of this ADR; the implementation is the easy
   part.

## Alternatives considered

**A. Emitter-side suppression only.**
Turn off what the documented environment variables turn off, before anything is emitted.
Rejected as a complete answer, kept as a partial one: `user.id` and `user.email` are
documented as always included when available, and the two `OTEL_METRICS_INCLUDE_*` flags
are metrics-scoped while the capture found the attributes on spans. It also puts the
control on every operator of every agent rather than in the pipeline. The capture runbook
sets the flags anyway, because a partial reduction at the source is still a reduction.

**B. Redact in the collector.**
The only place that would keep personal data out of Pub/Sub entirely, and the reason it
is rejected is not squeamishness about a rule. Architecture §2.1 forbids the collector
from parsing span semantics, and ADR-0001 forbids re-modelling the bytes; redaction
requires both. Doing it there would not be a small exception — it would retire ADR-0001,
make the data plane dialect-aware, and turn every new emitter's PII surface into a
collector deployment on the hot path.

**C. Do not ingest Claude Code telemetry into the shared path.**
Capture it for fixtures only and drop it as a live source. This is the honest option that
changes a success criterion — SC-2's third real source — rather than a design detail, and
it is recorded because it is the only alternative that removes the transit exposure
instead of accepting it. Rejected because the exposure is bounded (see Consequences) and
the criterion is load-bearing for the project's dogfooding claim. If review disagrees,
this is the option to take, and the cost is one criterion, not a rewrite.

**D. Redact at query time, in the views.**
Store what arrives; filter on read. Rejected: the base table would hold personal data
indefinitely, `spans_deduped` and `spans_real` are conveniences rather than a security
boundary, and Looker Studio can read a table a view was meant to hide. It moves the
question without answering it.

## Consequences

**Positive**

- The collector stays semantics-free, so ADR-0001 and architecture §2.1 hold unamended.
- Rules are reviewable data with reasons attached, versioned next to the mappings, and
  golden tests show exactly what a redacted row looks like.
- Determinism keeps the analytical value: a redacted `session.id` still groups a session,
  which is what makes redaction acceptable to the eval engine rather than merely safe.
- Isolation makes this decision cheap to reverse. If the boundary moves, what moves is one
  class and its call site.

**Negative / accepted costs**

- **Unredacted personal data transits Pub/Sub** inside the gzipped payload, and sits in
  the subscription backlog for as long as delivery lags. Within-project, over Google
  transport, under the project's own IAM — but present, and not something the collector
  could have prevented.
- **The dead-letter topic holds it durably.** Architecture §3.4 gives `traces-dlq` a pull
  subscription with no consumer by default and manual replay, so a poison message carrying
  personal data sits there until a human drains it, with a depth alert as the only signal.
  This is the sharpest edge of the decision. Two obligations follow, and F2 owns both: the
  DLQ runbook states that a dead-lettered message may contain personal data and must be
  inspected on a workstation, not pasted into an issue; and DLQ retention is set
  deliberately rather than left at the default.
- **The marker is reversible for guessable values.** Eight hex characters of an unkeyed
  SHA-256 over an email address is recoverable by anyone willing to hash a candidate list.
  A keyed HMAC would fix it and needs a key, which is a secret this design does not have
  (architecture §6.3) and would be the first one. The marker defends against casual
  disclosure in a public dataset, not against a motivated attacker with the address book.
- **Redaction is forward-only.** Rows written before a rule existed are not corrected, and
  cannot be: ADR-0001 keeps no raw bytes to reprocess from. Adding a key to the rule set
  protects future rows, and past rows need a deletion, not a re-run.
- **A dialect with no rules is silently untouched.** That is correct for the two dialects
  whose emissions were constructed and carry nothing personal, and it is a trap for a
  fourth dialect added later. The mitigation is procedural rather than mechanical, and
  saying so is the point: a new dialect's pull request adds a mapping, fixtures, and an
  answer to "what does this emitter send about people".

## Enforcement

- **Golden-file tests** hold the redacted rows for the claude-code fixtures, so a change
  to the rules or the marker shows up as a field-level diff rather than as nothing.
- **A test requires every rule to state a reason**, which is what keeps the rule file a
  record of decisions instead of a list of keys.
- **A test asserts determinism** — the same value produces the same marker on a span and
  on its event — because that property is what the analytical claims rest on.
- **No automated control prevents an unredacted dialect from being added.** Naming that
  asymmetry rather than implying coverage: ADR-0004's taxonomy calls this a report-class
  gap with no report, and closing it needs a rule that knows which emitters carry personal
  data, which nothing in this repository does.

## References

- `docs/architecture.md` §2.1, §2.3, §3.2, §3.4, §5, §6.3.
- `docs/evidence/claude-code-otel-capture.md` §4.4, §5.2, §7.1 — what was measured.
- Issue #11 — the question this ADR answers; issue #10 — the capture procedure.
- ADR-0001 — wire-only scope, and why the collector cannot hold this stage.
- ADR-0003 — rules as versioned in-repo YAML embedded at build time.
- ADR-0004 — prevent-class versus report-class controls.
