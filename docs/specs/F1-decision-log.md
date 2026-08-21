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

### W2.1 — The human-readable twin is OTLP/JSON, not textproto
**Made:** 2026-08-21 · **Work item:** W2 · **Reversibility:** cheap
**Decision:** each fixture's readable form is `request.otlp.json` in OTLP/JSON — the
protobuf JSON mapping with trace and span ids in lowercase hex — rather than the
protobuf text format the directive named.
**Alternatives:** textproto, as written. It would mean either adding a Go tool that
imports the OTLP protos purely to render fixtures — the one import the collector is
forbidden to have, in a repository where that boundary is the point — or hand-writing
text format with no parser in the .NET toolchain to check it. `Google.Protobuf` ships a
JSON formatter and parser and no text-format parser.
**Rationale:** OTLP/JSON is a specified OTLP encoding rather than a convenience format,
so the twin is exactly what an OTLP/HTTP JSON exporter would send. Ids are re-encoded
hex → base64 by the generator so the authored file stays readable without giving up
canonical parsing.
**C2:** yes — it is a deviation from the directive's wording, however small.

### W2.2 — The twin is the source of truth; the binary is generated and verified
**Made:** 2026-08-21 · **Work item:** W2 · **Reversibility:** cheap
**Decision:** `request.pb` is produced from `request.otlp.json` by
`worker/Plumbline.Fixtures`, and a test fails if a committed binary no longer matches
its twin. Poison payloads are the first 96 bytes of the dialect's happy-path binary.
**Alternatives:** commit the binary as the authored artefact with the JSON as a rendered
view — inverts which file a reviewer can actually read; or generate the binary at test
time and not commit it — the Go collector tests and the end-to-end sender both need the
bytes on disk, and a fixture that only exists inside one language's test run is not a
corpus.
**Rationale:** a diff on `request.pb` tells a reviewer nothing. The generated-and-checked
ordering is what makes review possible without making the binary optional.
**C2:** no.

### W2.3 — The `attributes` JSON column carries all three attribute levels
**Made:** 2026-08-21 · **Work item:** W2 · **Reversibility:** costly
**Decision:** the lossless column is shaped
`{"resource": {...}, "scope": {"name","version","attributes"}, "span": {...}}`.
**Alternatives:** one flat bag of span attributes — loses every resource attribute that
has no typed column (`os.version`, `deployment.environment.name`, the whole telemetry.sdk
block) and lets a resource key silently collide with a span key of the same name; a flat
bag with prefixed keys — same information, but the prefix becomes part of every query.
**Rationale:** architecture §4.1 names the column "lossless remainder" and does not fix
its shape. Losslessness is the requirement; keeping the level a key came from is the only
way to meet it for a payload that carries the same key at two levels. Costly rather than
cheap because rows written under one shape are not rewritten — ADR-0001 keeps no bytes to
reprocess from.
**C2:** yes — it fills a gap in architecture §4.1 rather than following it.

### W2.4 — Typed `gen_ai_*` columns are the fifteen scalars; arrays stay lossless
**Made:** 2026-08-21 · **Work item:** W2 · **Reversibility:** costly
**Decision:** provider name, operation name, request/response model, response id,
conversation id, agent name, tool name, tool call id, input/output tokens, max tokens,
temperature, top_p, output type. Array-valued GenAI attributes —
`gen_ai.response.finish_reasons` is the only one this project's dialects emit — stay in
the `attributes` JSON.
**Alternatives:** a repeated column for finish reasons. It buys grouping the JSON column
already supports, and costs a schema shape the local BigQuery stand-in must also agree
with, in a phase whose stand-in is not yet chosen.
**Rationale:** architecture §4.1 delegates the exact list to the mapping table and names
"system, operation, model, token counts, …". Every column here is a v1.41 registry
attribute; nothing is invented.
**C2:** no — but the list is quoted in the completion note, since it is the table's shape.

### W2.5 — Timestamps truncate to microseconds, and a fixture proves it
**Made:** 2026-08-21 · **Work item:** W2 · **Reversibility:** cheap
**Decision:** OTLP nanosecond timestamps are floored to BigQuery `TIMESTAMP`
microseconds. The nanosecond remainder is not preserved anywhere.
**Alternatives:** round rather than floor — an end time that rounds up can land after a
parent's, which is worse than being three digits short; keep the remainder in the
attributes JSON — invents a column-shaped attribute nobody queries.
**Rationale:** the loss is forced by the column type. What is decided here is that it is
*stated* — in the row model, in the mapping README — and made falsifiable: the
langgraph-python tool span ends at `…612345678` ns so the truncation appears in a golden
file rather than only in prose.
**C2:** no.

### W2.6 — `schema_url` resolves scope first, then resource
**Made:** 2026-08-21 · **Work item:** W2 · **Reversibility:** cheap
**Decision:** the column takes the `ScopeSpans.schema_url` when present, else the
`ResourceSpans.schema_url`, else null.
**Alternatives:** resource-first. OTLP allows both levels and the scope-level value is
the narrower claim — it describes the conventions the instrumentation emitted, which is
what the column audits.
**Rationale:** architecture §4.1 says "from OTLP resource" without addressing the scope
level, which the dotnet-agent dialect actually uses.
**C2:** yes, briefly — same class as W2.3.

### W2.7 — Redaction markers are `[REDACTED:sha256:<8 hex>]`
**Made:** 2026-08-21 · **Work item:** W2 · **Reversibility:** costly
**Decision:** a redacted value is replaced by the first eight hex characters of the
SHA-256 of the original, inside a marker that names the algorithm.
**Alternatives:** a constant marker — collapses every user into one value, so counts and
joins over redacted keys become meaningless; the full digest — 64 characters per
occurrence for no additional property at this cardinality; a keyed HMAC — better against
a dictionary attack on a known small domain, and it needs a key, which is a secret this
design does not have (architecture §6.3).
**Rationale:** D6 requires joins and counts to survive redaction, which needs
determinism, and the fixtures demonstrate it: the same `client_request_id` produces the
same marker on the span and on its event. The residual weakness — an eight-hex prefix of
an unkeyed digest is reversible for a guessable value such as an email address — is
stated in ADR-0006 rather than papered over.
**C2:** yes — inside the ADR-0006 decision.

### W2.8 — The unknown path fills typed columns from v1.41 names
**Made:** 2026-08-21 · **Work item:** W2 · **Reversibility:** cheap
**Decision:** an unrecognised dialect is normalized generically: OTLP structural fields
plus any attribute already carrying its exact v1.41 registry name populate the typed
columns; everything else stays in the lossless attributes; `source_dialect='unknown'`.
**Alternatives:** leave every typed column null for unknown payloads. Simpler, and it
throws away information the payload states in the project's own pinned vocabulary.
**Rationale:** architecture §5 says "normalized columns filled where OTLP fields map
directly". An attribute named exactly as the pin names it maps directly by any reading.
**C2:** no.

### W2.9 — OTLP protobuf definitions are vendored, not taken from a package
**Made:** 2026-08-21 · **Work item:** W2 · **Reversibility:** cheap
**Decision:** `third_party/opentelemetry-proto/v1.11.0/` holds the four `.proto` files
the worker needs plus the upstream Apache-2.0 license; C# types are generated at build
by `Grpc.Tools` with `GrpcServices="None"`.
**Alternatives:** a NuGet package carrying pre-generated OTLP types — one fewer build
step, and it makes the wire contract a transitive dependency of someone else's release
cadence in a project whose entire premise is pinning that contract.
**Rationale:** same reasoning as the semconv registry: the thing being pinned is
vendored with its checksums. `GrpcServices="None"` because the worker is a Pub/Sub push
endpoint and never serves the OTLP gRPC service.
**C2:** no.

### W2.10 — The golden harness lands in two halves
**Made:** 2026-08-21 · **Work item:** W2 · **Reversibility:** cheap
**Decision:** W2 delivers the fixture corpus, the expected rows, the row model, the
field-level diff engine with its own tests, and the corpus integrity tests. The golden
assertions that run a normalizer against the corpus land in W4, with the normalizer.
**Alternatives:** hold the whole harness for W4 — leaves the expected rows uncommitted
while the code that must satisfy them is written, which is the ordering that turns golden
files into a transcript of whatever the code did.
**Rationale:** the expectations are the contract and are written first, on purpose. What
cannot be written before the normalizer exists is only the call into it.
**C2:** no.

### W2.11 — Fixture manifests carry no checksums
**Made:** 2026-08-21 · **Work item:** W2 · **Reversibility:** cheap
**Decision:** manifests record provenance, emitter, semconv version emitted, opt-in
value and redacted fields — not digests of the fixture files.
**Alternatives:** a digest per file, as the vendored semconv registry carries. There the
checksum pins an artefact fetched from elsewhere; here both files are in the same commit
and the binary is already checked against the twin by a test, so a digest would be a
third copy of a fact two artefacts already state, and one more thing to forget to update.
**C2:** no.

### W2.12 — `dotnet test` joins CI now rather than in W7
**Made:** 2026-08-21 · **Work item:** W2 · **Reversibility:** cheap
**Decision:** the existing `.NET` CI job runs `dotnet test` on the worker solution from
this work item, ahead of the W7 CI extension.
**Rationale:** W2 is the first work item to add tests, and a test suite CI does not run
is not a control. Deferring it to W7 would mean the corpus integrity checks are advisory
for the length of three work items — exactly the "skipped and green" failure the CI job
design already argues against.
**C2:** no.

### W3.1 — The gRPC receiver runs a raw-bytes codec
**Made:** 2026-08-21 · **Work item:** W3 · **Reversibility:** cheap
**Decision:** the OTLP gRPC service is registered by hand with a codec whose only
message type is `[]byte`, so the handler receives wire bytes and the collector has no
OTLP message type to deserialize into.
**Alternatives:** import the generated `ExportTraceServiceRequest` and use the standard
proto codec, as every OTLP receiver does. It is less code and it puts the OTLP semantic
types inside the component that architecture §2.1 defines by their absence — and it
means the bytes are decoded and re-encoded on the way to Pub/Sub, so ADR-0001's "never
mutated" would rest on the round trip being faithful rather than on nothing having
happened.
**Rationale:** the boundary becomes structural instead of aspirational. A contributor
cannot read a span here because there is no type to read it into.
**C2:** no.

### W3.2 — Splitting is envelope-only, and refuses rather than truncates
**Made:** 2026-08-21 · **Work item:** W3 · **Reversibility:** cheap
**Decision:** `internal/otlpwire` knows the protobuf wire format and six field numbers:
the repeated member and the context fields of `ExportTraceServiceRequest`,
`ResourceSpans` and `ScopeSpans`. It regroups spans across three levels and copies
everything else verbatim. When one span plus its context still exceeds the budget, the
export is refused (HTTP 413, gRPC `InvalidArgument`).
**Alternatives:** parse with the OTLP types and re-serialize — see W3.1; or publish the
oversized message anyway — it would be rejected by Pub/Sub, converting a refusal the
client can act on into a 200 followed by a failure nobody sees.
**Rationale:** §3.2 says oversized batches are split, never truncated. "Never truncated"
has to include the case where splitting runs out of room, and the only honest answer
there is a refusal.
**C2:** no.

### W3.3 — OTLP/JSON is refused at the collector
**Made:** 2026-08-21 · **Work item:** W3 · **Reversibility:** cheap
**Decision:** `POST /v1/traces` accepts `application/x-protobuf` only; a JSON body is
`415`.
**Alternatives:** accept it and forward the bytes. The collector cannot tell the
difference — it does not read payloads — so the JSON would reach the topic and fail in
the worker's deserializer, landing in the DLQ. That is a poison message manufactured by
the collector rather than sent by a client.
**Rationale:** ADR-0001 makes protobuf the interchange format along the whole wire path.
The one Content-Type check is where that becomes enforcement rather than intent, and it
is a header check, not a payload parse.
**C2:** no.

### W3.4 — The API key format is fixed now, and Gate F enforces it (issue #19)
**Made:** 2026-08-21 · **Work item:** W3 · **Reversibility:** one-way *after* keys are
issued; cheap today, which is the entire argument for doing it now
**Decision:** keys are `plb_<environment>_<32 lowercase hex>`. Issued environments are
`local` and `live`; `test` is reserved and never issued. `scripts/ci/invariant-gates.sh`
gains **Gate F**, matching `plb_(local|live)_<32 hex>` over the whole repository, with a
failure proof in `prove-gates.sh` alongside the other six.
**Alternatives:** leave #19 for a later phase — the issue's own argument is that
retrofitting a prefix after keys are issued is a migration, and W3 is where the format
is born; or ship the prefix without the gate — a detection scheme with no detector.
**Rationale on the reserved marker:** tests and documentation need realistic key-shaped
strings. The alternative to reserving `test` is a gate with an exclusion list for the
test files, which is the shape this repository refuses on principle.
**Scope note:** the F1 directive's W3 does not mention #19, and W7 says Gates A–E stay
untouched. This adds a gate rather than changing one, and it is done here because the
key format is decided here and nowhere else.
**C2:** yes — it is scope the directive did not name.

### W3.5 — Authentication precedes rate limiting
**Made:** 2026-08-21 · **Work item:** W3 · **Reversibility:** cheap
**Decision:** the pipeline authenticates, then rate limits, then splits.
**Rationale:** a bucket is a per-key resource, and the limiter's map is keyed by strings
the caller influences. Limiting before authenticating would let an anonymous caller grow
that map at will — a memory-exhaustion path opened by a control meant to prevent
exhaustion. A test asserts no bucket exists after fifty unauthenticated requests.
Splitting comes last because it is the expensive step, and an over-quota caller should
not be able to buy CPU with a large payload.
**C2:** no.

### W4.1 — Mappings are embedded as resources, not generated into C#
**Made:** 2026-08-21 · **Work item:** W4 · **Reversibility:** cheap
**Decision:** the mapping and redaction YAML are `EmbeddedResource` items with fixed
logical names, parsed at first use.
**Alternatives:** a source generator turning the YAML into C# at build time — faster to
load and typed at compile time, and it puts a translation step between the reviewable
artefact and what runs. ADR-0003's Consequences want `normalization/mappings/v1.41/`
publishable on its own; a generator makes the YAML an input to code rather than the thing
itself.
**Rationale:** the load happens once per process and the file is a few kilobytes. There is
no problem to optimise.
**C2:** no.

### W4.2 — The unknown-dialect mapping is generated from the column set
**Made:** 2026-08-21 · **Work item:** W4 · **Reversibility:** cheap
**Decision:** no `unknown.yaml`. `MappingCatalog.Generic` is built in code from
`GenAiColumns`, one rule per column reading the v1.41 attribute that column stands for.
**Alternatives:** a fourth YAML file. It would be readable in the same place as the
others, and it would be a second list of the typed columns that can fall out of step with
the first — the drift being invisible exactly when a column is added.
**Rationale:** the generic path is *defined* as "the columns, filled from their own
names". Writing that out by hand is a copy, not a decision.
**C2:** no.

### W4.3 — Detection runs per scope, not per payload
**Made:** 2026-08-21 · **Work item:** W4 · **Reversibility:** cheap
**Decision:** the dialect is decided for each `ScopeSpans`, not once per export request.
**Rationale:** one export can carry two instrumentations, and `source_dialect` is a column
on a row. Deciding once per payload would label every span in a mixed export with whatever
the first scope happened to be.
**C2:** no.

### W4.4 — The collector hint breaks ties and introduces nothing
**Made:** 2026-08-21 · **Work item:** W4 · **Reversibility:** cheap
**Decision:** detection is scope name first, then resource markers, and the hint is
consulted **only** when resource markers match more than one dialect. A hint never
supplies a dialect the payload gave no evidence for; a mismatch is reported and the
detected value wins.
**Alternatives:** fall back to the hint when nothing matches. It reads as helpful and
makes detection a function of key registration — the label would then say what the
operator claimed at issuance rather than what the emitter sent, which is the failure
`docs/evidence/claude-code-otel-capture.md` §6 ranks the hint last to avoid.
**Rationale:** architecture §5 calls the hint a tiebreaker. A tie is the only situation
where one is needed.
**C2:** no.

### W4.5 — A value outside a rule's map yields null, not a pass-through
**Made:** 2026-08-21 · **Work item:** W4 · **Reversibility:** cheap
**Decision:** when a rule translates values and the emitter's value is not in the map, the
column stays null and a note is raised.
**Alternatives:** pass the raw value through. It fills the column, and it fills it with a
string that is not a v1.41 enum member while looking like one — which the eval engine and
every dashboard would read as conformant.
**Rationale:** a null column is a visible absence; a wrong value is an invisible one. ADR-0003's
Context is exactly this: a wrong mapping produces rows that are well-formed, queryable,
and quietly incorrect.
**C2:** no.

### W4.6 — ADR-0006 authored as Proposed, with the DLQ consequence stated
**Made:** 2026-08-21 · **Work item:** W4 · **Reversibility:** cheap by construction
**Decision:** `docs/adr/ADR-0006-pii-redaction-boundary.md` at status `Proposed`, and
architecture §10's index gains the row so the status is discoverable without reading the
stage. The ADR accepts, in writing, that unredacted personal data transits Pub/Sub and
persists in `traces-dlq` until a human drains it, and names two F2 obligations that follow.
**Alternatives considered inside the ADR:** emitter-side suppression only (partial by
construction), the collector (retires ADR-0001), not ingesting claude-code at all (changes
a success criterion, and is the option to take if review rejects the boundary), redaction
at query time (moves the question).
**Rationale:** the transit exposure was going to happen by default. The point of the ADR
is that it is now a decision someone signed rather than a consequence nobody noticed.
**C2:** yes — accept or reject.

### W5.1 — The status code is the only acknowledgement the worker gives
**Made:** 2026-08-21 · **Work item:** W5 · **Reversibility:** cheap
**Decision:** 204 for a stored message, 400 for one that can never be read, 503 for a
write that failed, 401 for an unauthenticated request. Nothing else.
**Alternatives:** ACK a poison message and record it somewhere of our own — a private
dead-letter table, a log line with the payload. Every version of that ends with
`traces-dlq` empty, the depth alert silent, and the operator's only evidence in a log
nobody reads.
**Rationale:** Pub/Sub ACKs on 2xx and NACKs on anything else, and the subscription's
`max_delivery_attempts` is what routes to the DLQ (§3.4). The worker's job is to answer
honestly; the routing is not its decision to make.
**C2:** no.

### W5.2 — The OIDC stub fails closed and announces itself
**Made:** 2026-08-21 · **Work item:** W5 · **Reversibility:** cheap
**Decision:** three implementations behind `IPushAuthenticator`. The stub accepts
everything and is **refused at startup outside a Development environment**; the OIDC
implementation does not exist yet and therefore refuses everything; the default is OIDC.
The chosen mechanism is named in the startup log and on `/healthz`.
**Alternatives:** a boolean flag and a comment — the F1 directive asks for the stub to be
"visible in code, so it cannot ship to cloud silently", and a comment is visible only to
someone already reading the file; or make the stub the default for convenience — that is
precisely the configuration that ships.
**Rationale:** Cloud Run sets no `ASPNETCORE_ENVIRONMENT`, so the guard bites by default
rather than by remembering to configure it. An incomplete deployment is visibly broken
instead of quietly open.
**C2:** no.

### W5.3 — `BigQueryStorageWriteSink` throws rather than pretending
**Made:** 2026-08-21 · **Work item:** W5 · **Reversibility:** cheap
**Decision:** the cloud sink carries its destination and the shape of the call, and
throws `NotSupportedException` if selected in F1.
**Alternatives:** implement it against the emulator now — F1 must not depend on a cloud
client library working against a stand-in that may not implement the API, and D4 makes
that a W6 question; or make it a no-op — a sink that silently drops rows looks exactly
like a working pipeline with no traffic, which is the worst of the available failures.
**Rationale:** D4 asks for the real client behind the interface as "wiring only". The
`insertAll` prohibition stays structurally true in both branches: Gate A refuses the
package that exposes it, so the legacy surface is unreachable rather than unused.
**C2:** only if the D4 fallback is activated in W6.

### W5.4 — `spans_deduped` uses ROW_NUMBER in a subquery, not QUALIFY
**Made:** 2026-08-21 · **Work item:** W5 · **Reversibility:** cheap
**Decision:** the view is written with a `ROW_NUMBER` subquery. Architecture §4.1
describes it as `QUALIFY ROW_NUMBER`; the semantics are identical.
**Alternatives:** QUALIFY, as written. It is shorter, it is the idiom a BigQuery reader
expects, and it is a BigQuery extension the local stand-in may not parse — which would
mean two definitions of the dedup rule, one per environment, and the local one untested
against the real one.
**Rationale:** one definition that runs in both places is worth more than the shorter
spelling. This is a deviation from architecture wording and is recorded as one.
**C2:** yes, briefly.

### W5.5 — No dedup in the worker
**Made:** 2026-08-21 · **Work item:** W5 · **Reversibility:** cheap
**Decision:** the worker writes what it receives, duplicates included.
**Rationale:** architecture §3.3 puts dedup downstream, in the views, on
`(trace_id, span_id)`. A worker-side cache would be a second implementation of the same
rule that is correct only while one instance's memory outlives the redelivery window —
and with `min-instances = 0` that window is routinely longer than the instance.
**C2:** no.

### W6.1 — The BigQuery stand-in is the emulator, on the real write path
**Made:** 2026-08-21 · **Work item:** W6 · **Reversibility:** cheap
**Decision:** D4's preferred option, verified empirically rather than assumed:
`goccy/bigquery-emulator` speaks the Storage Write API over gRPC, and the worker's
`BigQueryStorageWriteSink` writes to it through the same client and the same default
stream it will use in the cloud. The only difference is the endpoint and plaintext
credentials, and that difference is one `if` in the sink's constructor rather than a
second implementation.
**Alternatives:** the authorized fallback — a local sink for the end-to-end run with the
BigQuery client wired but unexercised. It was implemented first, is still present as
`LocalJsonSink`, and is what the worker's own tests use; what it cannot do is prove the
write path works, which is the half of the pipeline that carries the cost invariant.
**Rationale:** an end-to-end run that exercises a sink the cloud will never use tests the
plumbing and not the contract.
**C2:** yes, briefly — D4 asked for the empirical result either way.

### W6.2 — The local table is created from the SQL, through the API the stand-in supports
**Made:** 2026-08-21 · **Work item:** W6 · **Reversibility:** cheap
**Decision:** the stand-in refuses `CREATE TABLE ... PARTITION BY` (measured: HTTP 400,
"CREATE TABLE with PARTITION BY is unsupported"). Rather than keeping a second table
definition for local use, `scripts/e2e/seed.py` parses the column list out of
`analytics/sql/001_spans_table.sql` and creates the table through the REST API with
partitioning, clustering and `requirePartitionFilter` attached — retrying without them,
and saying so, if the stand-in refuses those too.
**Alternatives:** a local-only DDL file — two definitions of one table, drifting from the
first column added; or dropping `PARTITION BY` from the canonical file — that clause is a
cost invariant (§7), and removing it from the source of truth to satisfy a stand-in
inverts which one is authoritative.
**Rationale:** the SQL file stays the single definition and the local table is a
mechanical transformation of it. A test already compares that file against the proto twin
the write path uses, so all three now derive from one place.
**C2:** no.

### W6.3 — The end-to-end run generates its own API key
**Made:** 2026-08-21 · **Work item:** W6 · **Reversibility:** cheap
**Decision:** `scripts/e2e/run.sh` mints a fresh `plb_local_…` key per run, hashes it into
the registry the collector mounts, and leaves the plaintext in a gitignored directory.
**Alternatives:** commit a fixed development key. It would be a real, matching key in a
public repository, and Gate F would either fail on it or need an exclusion — which is how
a gate stops covering the file that matters.
**Rationale:** the gate stays meaningful because there is no key to commit, not because
the one that exists is excused. It also makes the seeding step real rather than a
formality.
**C2:** no.

### W6.4 — The end-to-end job runs on every pull request, path-filtered
**Made:** 2026-08-21 · **Work item:** W6/W7 · **Reversibility:** cheap
**Decision:** the `local end-to-end` job runs on any pull request touching the collector,
the worker, the mappings, the fixtures, the analytical SQL, the compose stack or the
end-to-end scripts. Not `main`-only.
**Alternatives:** `main`-only, which the directive allows. It halves the CI minutes on
documentation-heavy branches and reports a pipeline regression after the merge, to
somebody who no longer has the change in front of them.
**Rationale:** two things decide it. Actions minutes are unmetered on public repositories
(F0 spec §0.2), so the usual argument for `main`-only does not apply here. And this job is
the *only* place the compose path is exercised at all: F1's development host cannot run
containers (macOS 12, no supported container runtime), so every claim about the local
pipeline in this phase rests on this job. A check that runs after the merge would make
those claims unverifiable at the moment they are made.
**C2:** no — but the runtime is quoted in the completion note, because "either is
acceptable, silence about the choice is not".

### W6.5 — The compose collector runs a deliberately small message budget
**Made:** 2026-08-21 · **Work item:** W6 · **Reversibility:** cheap
**Decision:** `PLUMBLINE_MAX_COMPRESSED_BYTES=700` in `docker-compose.yml`, against a
4 MiB default.
**Rationale:** the fixture corpus is small enough that a realistic budget would pass every
payload through whole, and an end-to-end run in which nothing was split proves less than
it appears to. At 700 bytes the splitter runs, the parts are published separately, and the
assertion that every span survives is about something that happened.
**C2:** no.

### W6.6 — The end-to-end run asserts the absence of a credential
**Made:** 2026-08-21 · **Work item:** W6 · **Reversibility:** cheap
**Decision:** the last step of `scripts/e2e/run.sh` fails if the compose stack references
`GOOGLE_APPLICATION_CREDENTIALS`, a service-account file, or a mounted gcloud config.
**Alternatives:** rely on the phase's scope statement. F1 DoD item 7 asks for zero GCP
mutations "asserted by the absence of credentials in the e2e path" — an assertion is a
check, and a scope statement is a promise.
**Rationale:** it is the cheapest possible control for the invariant that matters most in
this phase, and it fails loudly on the change that would break it: someone mounting their
own credentials to "just try it against the real project".
**C2:** no.
