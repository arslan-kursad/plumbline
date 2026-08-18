# ADR-0003 — Normalization mappings as versioned in-repo YAML embedded at build time

**Status:** Proposed · **Date:** 2026-08-18 · **Work package:** F0 / W2
**Architecture:** §2.3, §2.6, §4.2, §5
**Supersedes:** — · **Superseded by:** —

## Context

Three emitter dialects at v0.1 (`langgraph-python`, `dotnet-agent`, `claude-code`), more
later. Each needs a mapping from what the emitter actually produces to the GenAI semconv
v1.41 columns the platform stores.

The mapping is simultaneously the most volatile component and the one whose defects are
least visible. A broken collector fails loudly; a wrong mapping produces rows that are
well-formed, queryable, and quietly incorrect. Every downstream number — eval verdicts,
regression-gate thresholds, published measurements — inherits that error without any
signal that it happened.

The tempting design is to keep mappings in a config store. Firestore already exists in the
architecture for metadata, so the marginal cost looks like zero and the benefit is
obvious: fix a mapping without a deploy.

## Decision

1. Mappings are **versioned YAML in the repository** at
   `normalization/mappings/v1.41/<dialect>.yaml`, **embedded into the worker binary at
   build time**.
2. **No runtime configuration store for mappings.** Firestore holds the API key registry,
   eval definitions, dataset references, and eval run states — the collection list in
   §4.2 is exhaustive, and mappings are not on it.
3. **A mapping change is a code change:** branch, pull request, review, and golden-file
   tests in the same commit.
4. The directory is versioned by the **semconv pin**. Moving the pin creates a new
   directory rather than editing in place, so the mappings that produced historical rows
   stay readable next to those rows.
5. **Dialect detection is worker-side and deterministic**, based on resource and
   instrumentation-scope attributes. The collector's `source_dialect` message attribute is
   a hint used only as a tiebreaker; on mismatch the detected value wins and the mismatch
   is logged.
6. **An unknown dialect is normalized generically, never dropped:** OTLP fields that map
   directly are filled, everything else is preserved in the `attributes` JSON,
   `source_dialect='unknown'`, and a counter metric is incremented.

## Alternatives considered

**A. Mappings in Firestore, editable at runtime.**
Rejected. It is config-as-hidden-state: the binary and the store version independently, so
"which mapping produced this row" stops being answerable from a commit hash. For a project
whose success criteria are pre-registered and whose deliverable is a published case study,
losing reproducibility of the data-production path is disqualifying. It also removes the
attachment point for golden-file tests — there is no commit for a test to accompany. The
benefit it buys, hot-fixing a mapping without a deploy, is worth less than what it costs,
and the situations where that speed matters are exactly the situations where an unreviewed
mapping edit is most dangerous.

**B. YAML read at startup from GCS or a mounted file.**
The apparent middle ground: still versioned in a bucket, no rebuild. Rejected. It creates
a second source of truth for identical content, introduces an availability dependency on a
bucket during cold start of the write path, and turns "which mapping is this instance
running" from a build fact into an operational question answerable only by inspecting a
running revision.

**C. Mappings as hand-written C#, no YAML at all.**
Rejected. It fuses mapping data with traversal logic, so the diff of a one-attribute change
becomes unreadable as a mapping change. It also forecloses the F5 objective of publishing
the mapping tables as a standalone artifact useful to anyone else pinning semconv v1.41 —
that artifact has value precisely because it is not plumbline code.

**D. No dialect layer: require emitters to be semconv-compliant.**
Rejected, and recorded because a reader will ask. If emitters agreed at the attribute
level there would be no normalization problem and no project; the premise under test is
that they do not. Assuming compliance would replace a measured claim with an unmeasured
one.

## Consequences

**Positive**

- Every stored row is attributable to a commit: image tag → binary → embedded mapping
  version → expected rows. Reproducibility is a build property, not a convention.
- Golden-file tests can be a merge gate, because mapping and fixture arrive in the same
  pull request. This is what makes ADR-0001's fidelity claim enforceable at all.
- `normalization/mappings/v1.41/` is a readable, publishable artifact independent of the
  runtime — a stated F5 deliverable rather than an accident.

**Negative / accepted costs**

- Fixing a mapping requires a rebuild and a new Cloud Run revision: image build, Artifact
  Registry push, deploy. With `min-instances=0` the cost is minutes of wall clock and no
  money. Accepted.
- Rows produced by an earlier mapping are **not** retroactively corrected, and cannot be:
  ADR-0001 does not persist the raw bytes to reprocess. Corrections are forward-only. The
  two decisions compound here, and the compounding is stated rather than discovered later.
- The YAML *schema* is itself unversioned in v0.1 — the directory carries the semconv
  version, not the mapping-file format version. A breaking change to the file shape has no
  migration path today. Acceptable while the worker is the only consumer; if the mappings
  ship as a standalone artifact (F5), the format needs its own version field, and that is
  a spec change.
- Adding a dialect requires a worker deployment. This makes onboarding an emitter a
  release event rather than a configuration event — intentional, and the direct cost of
  refusing Alternative A.

## Enforcement

- **Golden-file tests accompany every normalization change** — a `CLAUDE.md` process rule
  and an F1 Definition-of-Done item. This is the load-bearing control.
- **`CLAUDE.md` boundary rule:** mappings live only under `normalization/mappings/`, never
  in Firestore, never in environment configuration.
- **Architecture §4.2 collection list is exhaustive.** A pull request adding a mappings
  collection to Firestore is a boundary violation; detection is review-only, with no
  automated gate (see ADR-0004 on prevent vs. report).
- **Unknown-dialect counter and detection-mismatch logging** are the reporting controls
  that make a missing or wrong mapping visible instead of invisible. They report; they do
  not prevent.

## References

- `docs/architecture.md` §2.3, §2.6, §4.2, §5, §9.
- ADR-0001 — normalized-at-rest representation; no raw bytes to reprocess against.
- ADR-0004 — control taxonomy: which invariants are prevented and which only reported.
