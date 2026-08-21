# F2 — Decision log

**Status:** Open with the phase · **Opened:** 2026-08-21
**Spec:** [`F2-minimal-gcp-footprint.md`](F2-minimal-gcp-footprint.md)

F2 runs in graduated mode ([spec §2](F2-minimal-gcp-footprint.md#2-governance-mode-graduated-delta-from-f1)):
Lane A decides alone and this log is what replaces propose → confirm there, while every
cloud mutation waits for a maintainer-armed environment approval. An entry is written
when the decision is made, not reconstructed at phase close — a log assembled afterwards
records what the author still remembers agreeing with.

## Entry format

```
### <id> — <one-line decision>
**Made:** YYYY-MM-DD · **Work item:** <handoff | Wave n | W-repo> · **Reversibility:** cheap | costly | one-way
**Decision:** what was decided, in a form that can be checked against the repository.
**Alternatives:** what else was on the table, and what each would have cost.
**Rationale:** why this one.
**Exit review:** whether the maintainer sees it in the closing review batch, and why.
```

**Reversibility classes.** *Cheap* — undoing it is a contained change with no data or
external consequence. *Costly* — undoing it means rework across work items, or discarding
artefacts, but nothing outside the repository changes. *One-way* — undoing it is not
possible, or requires acting outside the repository.

**One-way decisions exist in this phase, and that is the whole reason the governance mode
changed.** F1 could state that it had none: it created no cloud resource and published
nothing, so every decision was a revertible commit. Here an apply is not a commit. A
detached billing account needs a human with billing permissions to restore, a published
Pub/Sub message cannot be unpublished, a row written to BigQuery cannot be unwritten, and
a plaintext key that has been displayed cannot be un-displayed — it can only be revoked.
Where a decision below carries that property, it is labelled rather than rounded down to
the class that reads more comfortably.

---

## D-level — resolved on handoff

The directive pre-authorized these. They are logged with their reversibility class
because the Definition of Done requires it, and because "someone else decided it" is not
a rationale a later reader can check.

### D1 — Apply gating is a GitHub Environment protection rule
**Made:** 2026-08-21 · **Work item:** handoff · **Reversibility:** cheap
**Decision:** every `terraform apply` runs in CI against the `gcp-production`
environment, which carries a required-reviewer rule naming the maintainer. Five waves,
one approval each. No apply from any other path.
**Alternatives:** per-decision confirmation in chat — kills velocity and reintroduces the
failure mode the F1 governance model was built to remove; auto-apply on merge — makes
self-merge a cloud mutation, which is exactly the property Lane A depends on not having.
**Rationale:** the confirmation moves from a conversation to an enforcement point, so it
produces an artefact: an auditable, timestamped, in-platform review rather than a
sentence in a transcript nobody can grep six weeks later.
**Exit review:** yes — whether one click per wave was the right granularity is a
judgement only the person doing the clicking can make.

### D2 — Cloud verification traffic is constructed fixtures, `synthetic=true`
**Made:** 2026-08-21 · **Work item:** handoff · **Reversibility:** cheap to hold,
**one-way to break**
**Decision:** every payload sent to the cloud collector in F2 comes from the F1
constructed corpus and carries resource attribute `synthetic=true`. No real capture
reaches the cloud in this phase.
**Alternatives:** send the captured claude-code fixture, which would test real-source
fidelity a phase earlier — at the cost of shipping the maintainer's real `user.email` and
host paths through cloud Pub/Sub, where the DLQ can hold them durably (ADR-0006, #44),
before F4's dogfooding governance exists.
**Rationale:** the walled-off `synthetic` flag already gives a clean mechanism, so the
exposure buys nothing that waiting does not also buy. The class is asymmetric on purpose:
holding the decision costs nothing, and breaking it is unrecoverable — a message that has
transited Pub/Sub cannot be recalled.
**Consequence:** F2 proves the pipe, not real-source fidelity. That sentence belongs in
the completion note, not only here; #42 carries the other half.
**Exit review:** yes — it is one of the phase's stated limits.

### D3 — No Secret Manager; the collector stays secret-free
**Made:** 2026-08-21 · **Work item:** handoff · **Reversibility:** cheap
**Decision:** architecture Open Question 2 resolves toward the hashed-registry design.
The collector holds no secret: it reads hashed keys from Firestore under its own service
account, and the worker and CI authenticate through service accounts and WIF. If
implementation surfaces a genuine secret with no identity-based alternative, it is
recorded prominently here and Secret Manager is proposed scoped to that one item at the
next wave boundary — never added inside a wave already armed.
**Alternatives:** adopt Secret Manager pre-emptively — a free-tier dependency and an
extra resource type for a secret that may not exist; leave the question open — the F2
spec's own §5 context list names it as due here, and an open question that survives the
phase that was supposed to close it becomes permanent.
**Rationale:** the identity-based design already covers every boundary in architecture
§6.1. A secret store with nothing to store is a resource type in the allowlist earning
its place by being anticipated rather than needed.
**Exit review:** only if the fallback fires.

### D4 — One definition of the view logic, shared by local and cloud
**Made:** 2026-08-21 · **Work item:** handoff · **Reversibility:** cheap
**Decision:** the cloud views are Terraform-owned, and Terraform reads the same
`analytics/sql/` files the local stand-in uses. Exactly one place states the dedup rule.
**Alternatives:** an HCL copy of the query — the drift is invisible until a dedup
difference shows up as a row-count discrepancy nobody can attribute; a test asserting the
two copies match — a test that exists because the design chose duplication.
**Rationale:** structural prevention beats detection when structure is available. Golden
tests exist for divergence that cannot be designed out; this one can.
**Open at handoff, closed in Wave 1:** the files are executable DDL and the Terraform view
resource takes a query body, so `file()` alone does not carry it. The mechanism is a Wave
1 decision; the invariant is not negotiable — a mechanism that requires editing two files
has failed this decision rather than varied it.
**Exit review:** no, unless the mechanism forces a visible compromise.

### D5 — API keys through `tools/keyctl`, plaintext in human custody
**Made:** 2026-08-21 · **Work item:** handoff · **Reversibility:** cheap for the tool;
issuing a key is **one-way**
**Decision:** a small Go CLI generates a key, prints the plaintext once, and writes only
the hash and metadata to Firestore `api_keys`. The maintainer runs it (Lane C). The
plaintext never enters the repository, CI logs, chat, or the issue tracker. The tool
emits the format the collector already enforces — `plb_<environment>_<32 lowercase hex>`,
with `live` as the cloud marker — and its tests assert that shape rather than describe it.
**Alternatives:** seed keys in Terraform — state would then hold material derived from a
show-once workflow, and Terraform cannot model "display once"; generate by hand with
`openssl` — reproducible only as a runbook paragraph, and the hash format would be
restated in prose instead of shared with the code that validates it.
**Rationale:** the show-once property is the security property. A tool can hold it; a
declarative resource cannot.
**One-way note:** a displayed key cannot be un-displayed. Recovery from a leak is
revocation and reissue, which is why Gate F exists as detection behind it (#19).
**Exit review:** yes — the maintainer runs it, so the UX is theirs to accept.

### D6 — Permissions and the allowlist grow per wave
**Made:** 2026-08-21 · **Work item:** handoff · **Reversibility:** cheap
**Decision:** the CI service account gains only the roles each wave needs, added in that
wave's Terraform and enumerated in that wave's issue. The plan-diff guard passes at every
wave boundary and is never loosened wholesale.
**Alternatives:** one broad up-front grant — convenient exactly once, and thereafter the
project cannot say what its CI identity can do without reading IAM.
**Rationale:** least privilege is checkable per wave and unfalsifiable in aggregate.
**Reading against architecture §7.1 as it stands:** the allowlist already carries every
F2 resource type, authored ahead of this phase. Stripping those rows to re-add them wave
by wave would be churn; what D6 binds in practice is IAM grants, which do grow per wave,
and any type not already listed, which arrives as a spec change with a changelog entry.
Two rows describe more than F2 builds — `google_cloud_run_v2_service` names
`analytics-api` and `google_bigquery_table` names `eval_results`, both F3's. The type
check cannot catch F2 creating them, so it is written down here where a reader can.
**Exit review:** no, unless a wave needed a role that surprised us.

---

## W-level — decisions made during the phase

*No entries yet. The first arrives with Wave 0.*
