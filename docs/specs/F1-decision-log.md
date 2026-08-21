# F1 — Decision log

**Status:** Live for the duration of F1 · **Opened:** 2026-08-21

F1 runs in autonomous mode ([`F1-local-first-core.md`](F1-local-first-core.md) §2): the
handoff directive is the single approval, and this log is what replaces propose → confirm.
An entry is written when the decision is made, not reconstructed at phase close — a log
assembled afterwards records what the author still remembers agreeing with.

## Entry format

```
### <id> — <one-line decision>
**Made:** YYYY-MM-DD · **Work item:** W<n> · **Reversibility:** cheap | costly | one-way
**Decision:** what was decided, in a form that can be checked against the repository.
**Alternatives:** what else was on the table, and what each would have cost.
**Rationale:** why this one.
**C2:** whether the maintainer sees it in the exit review batch, and why.
```

**Reversibility classes.** *Cheap* — undoing it is a contained change with no data or
external consequence. *Costly* — undoing it means rework across work items, or discarding
artefacts, but nothing outside the repository changes. *One-way* — undoing it is not
possible, or requires acting outside the repository.

**One-way decisions do not exist in F1 by design.** F1 creates no cloud resource, spends
nothing, and publishes nothing outside the repository, so there is no action here that
cannot be reverted by reverting a commit. If a decision in this phase turns out to be
one-way, that is a scope defect: stop and escalate rather than log it (directive §1.2).

---

## D-level — resolved on handoff

The directive pre-authorized these. They are logged with their reversibility class
because the Definition of Done requires every decision of consequence to carry one, and
because "someone else decided it" is not a rationale a reader can check.

### D1 — Freeze A is the F3 entry gate, not the F1 entry gate
**Made:** 2026-08-21 · **Work item:** W1 · **Reversibility:** cheap
**Decision:** the eval-plan Freeze A moves from the F1 entry gate to the F3 entry gate.
Freeze B stays at F3 before the first seeded-regression run. `docs/specs/F0-foundations.md`
and `docs/project-brief.md` carry dated amendment notes; `docs/eval-plan.md` is **not**
edited, and continues to say "F1 entry gate" until the human who performs Freeze A
reconciles it.
**Alternatives:** (a) hold F1 until Freeze A happens — blocks 25 h of work that has no
dependency on evaluation criteria, behind a question about Adjudicator ground truth that
F1 cannot answer; (b) freeze now with placeholder criteria — pre-registration whose
content was invented to unblock a schedule is worse than an unfrozen plan, and the F0
spec already rejects that reasoning for Freeze B constants.
**Rationale:** Freeze A protects the seeded-regression experiment, which starts in F3.
Nothing in the collector, the worker, or the mappings reads a criterion.
**C2:** yes — ratification issue #35, which states the eval-plan contradiction rather
than quietly carrying it.

### D2 — External-dialect fixtures are constructed, and labelled as such
**Made:** 2026-08-21 · **Work item:** W2 · **Reversibility:** cheap
**Decision:** `langgraph-python` and `dotnet-agent` fixtures are constructed from
documented emitter behaviour, tagged `provenance: constructed`, with the construction
basis recorded per fixture. An F4 re-validation issue is opened in W8.
**Alternatives:** capture from the real agents — out of handoff scope, they are
independent projects; or drop to one dialect — abandons the phase's exit condition and a
success criterion.
**Rationale:** the golden tests remain valid as normalization contract tests. What they
cannot prove — detection fidelity against a real emitter — is stated in the manifest.
**C2:** yes — constructed-fixture risk sign-off.

### D3 — The claude-code fixture is derived from measured evidence; C1 fires
**Made:** 2026-08-21 · **Work item:** W2 · **Reversibility:** cheap
**Decision:** the P11 evidence was inspected first, as directed. It does not meet the
promotion condition: `docs/evidence/claude-code-otel-capture.md` §5.1 records that the raw
capture was deliberately never committed, and §3 records that no `claude_code.tool` or
`claude_code.hook` span was ever observed. Both halves of the condition fail, so C1 fires:
a capture runbook is written for the maintainer, and until a real capture lands the F1
fixture is built from the measured marker inventory in §4 under its own provenance class.
**Alternatives:** block the claude-code dialect until C1 returns — C1 is explicitly
non-blocking; or tag the derived fixture `captured` because its content came from a real
measurement — that would overstate what the artefact is, which is the failure mode the
evidence file itself was written to avoid.
**Rationale:** the inventory is measured, complete for resource, scope, and two span
types, and cross-checked across two emitter builds. That is a defensible basis for a
fixture as long as the manifest says exactly which parts are measured and which are not.
**C2:** yes — with the capture status, since C1's outcome may still change the fixture.

### D4 — BigQuery stand-in: emulator preferred, sink abstraction authorized
**Made:** 2026-08-21 · **Work item:** W5 · **Reversibility:** cheap
**Decision:** prefer `goccy/bigquery-emulator` over gRPC, verified empirically before the
write path depends on it; fall back to an `ISpanSink` abstraction with the real Storage
Write API client behind it and a local sink for the end-to-end run.
**Alternatives:** none seriously — a real BigQuery dataset is a GCP mutation and out of
scope for the phase.
**Rationale:** either branch keeps the legacy streaming-insert surface unreachable, which
is what Gate A exists to guarantee.
**C2:** only if the fallback is activated (§7 of the spec).

### D5 — Local key registry is file-backed, not the Firestore emulator
**Made:** 2026-08-21 · **Work item:** W3 · **Reversibility:** cheap
**Decision:** a `KeyRegistry` interface with a file-backed local implementation reading
hashed keys from a mounted file. The Firestore adapter is F2.
**Alternatives:** the Firestore emulator — a second emulator in compose, plus a client
dependency in the collector, to exercise an adapter that F2 will write anyway.
**Rationale:** the interface is the part F1 needs to get right; which store sits behind it
locally is not evidence of anything.
**C2:** no.

### D6 — Redaction is an isolated worker stage; ADR-0006 is authored as `Proposed`
**Made:** 2026-08-21 · **Work item:** W4 · **Reversibility:** cheap by construction
**Decision:** redaction runs post-deserialize and pre-write as its own stage, driven by
`normalization/redaction/v1/claude-code.yaml`, replacing values with a deterministic
marker so joins and counts survive. ADR-0006 is written with status `Proposed` and is not
self-accepted.
**Alternatives:** the collector — excluded twice over by architecture §2.1 and ADR-0001,
and recorded in the ADR so the reader sees it was considered; emitter-side suppression
alone — partial by construction, since `user.id` and `user.email` are documented as always
included.
**Rationale:** isolation is what makes a C2 rejection cheap. The stage's boundary is the
decision under review, so the code must not spread it across the normalizer.
**C2:** yes — ADR-0006 accept or reject.

---

## W-level

### W1.1 — Vendored semconv lives at `normalization/semconv/v1.41/`
**Made:** 2026-08-21 · **Work item:** W1 · **Reversibility:** cheap
**Decision:** vendor the upstream gen-ai model YAMLs there rather than under
`third_party/`.
**Alternatives:** `third_party/opentelemetry-semantic-conventions/` — the conventional
home for vendored upstream source, and it keeps a single directory for everything
vendored.
**Rationale:** issue #8 and `docs/eval-plan.md` SC-1 row 1.4 both already name
`normalization/semconv/v1.41/`. Choosing the conventional path instead would mean the
first consumer of the artefact points somewhere it is not, and the eval plan cannot be
edited in this phase to correct it (§4). The pin also versions the directory the same way
ADR-0003 §4 versions the mappings, which puts the registry and the mappings that reference
it under the same versioning rule.
**C2:** no.

### W1.2 — Vendoring scope: six model files, plus the upstream license
**Made:** 2026-08-21 · **Work item:** W1 · **Reversibility:** cheap
**Decision:** vendor `registry.yaml`, `spans.yaml`, `metrics.yaml`, `events.yaml` and both
`deprecated/` files, with the upstream Apache-2.0 `LICENSE` alongside them. Not the
generated `docs/gen-ai/*.md`, and not the rest of the upstream `model/` tree.
**Alternatives:** gen-ai only, no `deprecated/` — smaller, and it was the shape issue #8
sketched; the whole `model/` tree — resolves the external references without an allowlist,
at the price of hundreds of unrelated namespaces.
**Rationale:** the deprecated files are load-bearing rather than decorative here: the
claude-code dialect emits `gen_ai.system`, which v1.41 deprecates in favour of
`gen_ai.provider.name`, and a mapping that rewrites a deprecated name must be able to show
the source name was a real deprecated attribute rather than a typo. Upstream ships no
`NOTICE` at this tag (verified: HTTP 404), so Apache-2.0 §4(d) adds nothing to carry, and
the vendored `LICENSE` plus the provenance README is the whole attribution obligation. The
F0 spec §0.3 statement that there are "no third-party attributions to carry" describes F0
and stops being true here; the license file records that, and no root `NOTICE` is created
for an obligation that does not exist.
**C2:** no.

### W1.3 — Issue #8 cannot be closed whole in F1; its eval-plan half is split out
**Made:** 2026-08-21 · **Work item:** W1 · **Reversibility:** cheap
**Decision:** deliver #8's three repository-side items — vendored model YAMLs with
checksums and a refresh procedure, the closed external-attribute allowlist, and the row-1.4
check implemented against both sources — and split its fourth item, "update eval plan row
1.4 wording ... as part of eval-plan v0.2", into issue #36, targeted at Freeze A.
**Alternatives:** close #8 anyway and let the wording drift — the artefact and the rule
that cites it would disagree, with nothing recording that anyone noticed; or edit
`docs/eval-plan.md` — prohibited outright for this phase (spec §4), and prohibited for
good reason, since the plan is a pre-registration document.
**Rationale:** the directive says W8 closes #8, and the standing prohibition says part of
#8 cannot be done. Both hold; what gives is the assumption that the issue is indivisible.
**C2:** yes, briefly — it is a scope-gap fix against the directive's own wording.
