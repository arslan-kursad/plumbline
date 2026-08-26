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

### W0.1 — Wave 0 applies from the maintainer's credentials; the CI path is Wave 1's
**Made:** 2026-08-21 · **Work item:** Wave 0 · **Reversibility:** one-way (the apply
itself); cheap (the sequencing)
**Decision:** Wave 0's two pending changes are applied by the maintainer in
`infra/terraform`, as #33 specifies. The gated CI apply path is built in Wave 1 and binds
absolutely from there.
**Why this is not a relaxation of D1:** F0 shipped one CI identity and made it provably
incapable of deploying. `infra/terraform/wif.tf` describes `ci-deploy` in a comment and
deliberately does not create it, so that F0's identity is *demonstrably* unable to mutate
anything. The first mutation of F2 therefore cannot be a CI apply under any governance
model: the identity does not exist, and creating it is itself a mutation requiring
credentials CI does not have. This is a fact about the bootstrap, not a preference about
process, and pretending otherwise would put a sentence in the spec that no wave could
satisfy.
**Alternatives:** create `ci-deploy` first in a wave of its own — it needs a human-run
apply too, so it relocates the bootstrapping step without removing it, and it delays G1
while the kill-switch is known inert; hand-create the identity with `gcloud` and import it
— hand-created resources are drift by architecture §8, and the import would be the
project's first.
**Rationale:** the kill-switch is inert *now*. The shortest correct path to G1 is the one
#33 already describes, and every day it is not taken is a day the last cost control does
not work. The governance model loses nothing: Wave 0's apply is two billing-account-scoped
changes, which is the scope Wave 1 argues the CI identity out of holding anyway.
**Exit review:** yes — it is a deviation from the directive's five-gated-waves shape, even
though the deviation was forced.

### W0.2 — The deploy identity's two scopes are separate questions
**Made:** 2026-08-21 · **Work item:** Wave 0 (recorded), Wave 1 (decided)
**Reversibility:** costly
**Decision:** recorded now, resolved in Wave 1 with its cost either way. *Project scope:*
growing the deploy identity's own grants per wave (D6) requires project IAM
administration, which makes that identity project-admin-equivalent; the honest consequence
is that the control is the environment gate and the plan guard, not the role list.
*Billing-account scope:* `wif.tf` already names the cleaner shape — billing-scoped
resources in their own state, so no CI identity crosses that boundary — and names F2 as
where the conversation happens.
**Rationale for recording it here rather than in Wave 1:** Wave 0's apply is exactly the
billing-account-scoped mutation the second question is about. Deciding it after that apply
would be deciding it after the only evidence arrives, which is the right order; writing it
down before is what stops the question from being answered by default when Wave 1 is busy.
**Exit review:** yes — ADR-0004 Amendment 2 had to withdraw a claim about what an identity
could not do. This is the same class of claim, made in advance.

### W1.1 — The approval is bound to the diff by a fingerprint, not by a saved plan
**Made:** 2026-08-21 · **Work item:** Wave 1 · **Reversibility:** cheap
**Decision:** `deploy.yml` runs `preflight → plan → [environment approval] → apply`. The
plan job prints the diff and publishes a fingerprint of it — sorted `address action`
pairs, hashed — as a job output. The apply job re-plans, recomputes the fingerprint, and
refuses unless it matches. No plan file is uploaded anywhere.
**Alternatives:** upload the plan as an artifact and `terraform apply plan.tfplan`, which
is the usual way to bind an approval to a diff — rejected because this repository is
public and workflow artifacts are not masked the way logs are, so the artifact would
publish every value the plan carries, including the billing account ID the repository
keeps as an Actions secret; re-plan and apply without comparing — rejected because then
the reviewer approves one diff and the runner applies whatever it finds, which is D1's
property in name only.
**Rationale:** the fingerprint carries addresses and action verbs and no attribute values,
so it is safe to print in a public log and still answers the only question the gate asks:
is this the change that was approved? Its blind spot is stated rather than papered over —
an attribute-level change that keeps the same address and action set would not move the
fingerprint. The plan guard runs in both jobs, and the same-run checkout pins the code, so
the remaining gap is a value edited in the cloud console between plan and apply, which is
drift, which is already a bug by architecture §8.
**Also decided here:** the preflight refuses unless it can see a required reviewer on the
`gcp-production` environment. Naming an environment that does not exist creates it on
first use without protection rules, so the gate the workflow is built around would
silently not be there — the same failure shape as the two W6.4 settings that returned
HTTP 200 and changed nothing. Refusing when the environment cannot be read at all is
deliberate: an unverified gate is not a gate.
**Verified how:** dispatched once on `main` before any of this was configured, and it
refused —
[run 32503826772](https://github.com/arslan-kursad/plumbline/actions/runs/32503826772):
`missing repository variables: GCP_DEPLOY_SERVICE_ACCOUNT`, with `plan` and `apply`
skipped. So the deploy path fails closed.

**What that run did not prove, which is the part that matters.** It refused at the
variables check, two steps before the environment check, so the highest-consequence
assertion in the workflow was never reached. Waiting for it to be exercised in anger would
mean trusting it first: once `gcp-production` exists and the variables are set, the check
passes forever and is never observed failing — the exact shape ADR-0004 §1 calls a comfort
object. It is therefore extracted into `scripts/ci/environment-guard.sh` and proven against
six fixtures — no protection rules, a wait timer instead of reviewers, a rule whose
reviewers were all removed, unparseable input, and two protected shapes — running in the
`invariant gates` job on every CI run rather than in a path-filtered one, because what it
protects is an apply.

**Three-valued exit, deliberately:** 0 protected, 1 unprotected, 2 unusable input. Folding
"cannot tell" into either of the other two is how a gate starts reporting on a question it
did not answer, and the workflow refuses on all of 1 and 2.
**Exit review:** no, unless the preflight's environment read turns out to need a token
permission the default one lacks, which changes the repository's Actions posture.

### W1.2 — D4's mechanism: views by extraction, the table schema by generation
**Made:** 2026-08-21 · **Work item:** Wave 1 · **Reversibility:** cheap
**Decision:** two different mechanisms, because the two artefacts are not the same problem.

*Views.* `bigquery.tf` reads `analytics/sql/002_*.sql` and `003_*.sql` with `file()` and
strips the DDL prologue with one `regex()`, then expands the `plumbline.` dataset
reference to a project-qualified one for the cloud copy. Nothing is duplicated and nothing
is generated: there is one authored definition and Terraform reads it. Verified offline
with `terraform console` — the extracted `spans_deduped` body is the `SELECT` with
`FROM \`plumbline-19458.plumbline.spans\``, and a `precondition` on each view fails the
plan if the extraction ever stops starting with `SELECT`.

*Table schema.* A BigQuery table resource wants a JSON schema, and no regex should be
asked to turn thirty-three column definitions into one. `scripts/ci/bq_schema.py` derives
it from `001_spans_table.sql`; the result is committed under `infra/terraform/generated/`
because Terraform reads it with `file()` and has no build step; and
`scripts/ci/bq-schema-guard.sh` fails CI when the two disagree.
**Alternatives:** hand-write the JSON schema in Terraform — thirty-three columns in a
second place, which is the divergence D4 exists to prevent, one level below the views D4
names; parse the DDL in HCL with `regexall` — it works and it is unreadable, and this
project has to be able to review its own controls; generate the DDL *from* the JSON — the
DDL is the file carrying F1's reasoning in comments, and making it an output would throw
that away.
**Rationale:** one authored source per artefact, and where a copy is unavoidable it is
generated and guarded rather than maintained. The parser refuses any column line it does
not fully understand instead of skipping it, because a parser that skips silently drops a
column and produces a schema that looks fine.
**Verified how:** the guard's self-test, on four fixtures — a matching pair, a stale JSON
missing a column and loosening a mode, a `DEFAULT` clause the parser will not guess at,
and an unknown type. Three-valued exit again: match, mismatch, unparseable.
**Path filter, which was the defect underneath:** `analytics/sql/` was not in the terraform
job's filter, so the schema guard would have stayed skipped on precisely the pull request
that changed the DDL. Added, with the reason next to it — the README already warns that a
filter must cover a job's *inputs*, not its own directory.
**Exit review:** no.

### W0.3 — Wave 0's apply is targeted, because Lane A merges ahead of the waves
**Made:** 2026-08-21 · **Work item:** Wave 0 · **Reversibility:** cheap
**Decision:** Wave 0 plans and applies with
`-target=google_billing_account_iam_member.killswitch_billing_admin`.
**What forced it:** Lane A authorizes merging Terraform source for later waves, on the
argument that merging mutates nothing and only `apply` does. That argument holds, and it
has a consequence nobody wrote down: `main` now describes more infrastructure than Wave 0
is allowed to create. Measured, not supposed — an unqualified plan on `main` today reports
`5 to add`: the four BigQuery resources from the Wave 1 branch plus Wave 0's grant. An
untargeted apply from a laptop would therefore create Wave 1 resources outside the gated
path, which is precisely what the phase forbids from Wave 1 on.
**Alternatives:** hold Wave 1's Terraform out of `main` until Wave 0 has applied — it
would idle the whole repository lane behind one human step, and it contradicts Lane A's
own reasoning; apply everything and call Wave 0 "Wave 0 and 1" — it would put the first
BigQuery objects into the project through an unreviewed local apply, on the day the
kill-switch is still known inert.
**Rationale:** `-target` is normally a smell because it produces a state that matches no
configuration. Here it is the opposite: it is how one deliberately chosen resource is
applied while the rest of the configuration waits for the gate that does not exist yet.
Terraform's `Resource targeting is in effect` warning is the wave's receipt.
**Exit review:** no, but it belongs in the completion note as a property of the governance
model rather than an incident: any phase that merges ahead of its applies inherits it.
### W1.3 — DLQ retention is seven days, and the default is chosen rather than inherited
**Made:** 2026-08-21 · **Work item:** Wave 1 · **Reversibility:** cheap
**Decision:** `traces-dlq-pull` sets `message_retention_duration = "604800s"` explicitly,
with `retain_acked_messages = false` and no expiration policy. The reasoning is in the
resource and in [`dead-letter.md`](../runbooks/dead-letter.md) §4, not only here.
**Alternatives:** 24 hours — smallest exposure window, and it would routinely expire
before anyone looked, since this project is maintained part-time; the alert would then
describe a message that no longer exists, which is exposure without evidence. 31 days, the
maximum — a month of unredacted personal data waiting for someone who was going to look in
the first week anyway.
**Rationale:** the window is simultaneously the exposure window and the evidence window,
and #44 requires the decision to name both. Seven days is the shortest that survives a
week of not looking.
**On choosing the API default:** the value equals Pub/Sub's default, and that is not an
argument against setting it. #44's obligation is that the value be *decided*: an inherited
default is a number nobody argued for, and a future change to it would have nothing to
argue against. Now it does.
**Also decided:** no expiration policy (`ttl = ""`). A subscription that deletes itself
after 31 idle days takes the dead-letter path with it, and nothing would notice until a
poison message had nowhere to go — the silent degradation §3.4 exists to prevent.
**Exit review:** surfaced at #44's closure, per §8.

### W1.4 — The alert destination is a variable, because the repository is public
**Made:** 2026-08-21 · **Work item:** Wave 1 · **Reversibility:** cheap
**Decision:** `var.alert_email` has no default and is validated as an address. CI supplies
it from a secret; the maintainer's `terraform.tfvars` is gitignored.
**Alternatives:** hard-code the address — world-readable personal data in a history that
is not erasable in practice, in a repository whose own rules forbid exactly that; make the
channel optional so the alert can be created without one — an alert policy with no
notification channel is a control that fires into nothing, which is worse than not having
it because the console shows it as configured.
**Rationale:** the only free notification channel type is email, and an email address is
personal data. The variable keeps the control mandatory and the address out of the repo.
**Exit review:** no.

### W1.5 — The deploy identity: project-admin-equivalent, and nothing on the billing account
**Made:** 2026-08-21 · **Work item:** Wave 1 · **Reversibility:** costly
**Decision:** `ci-deploy` exists, reachable only from `main`, holding project-scoped roles
that grow per wave — including `resourcemanager.projectIamAdmin`, which is what makes
per-wave growth possible and also makes the identity administrator-equivalent at project
scope. On the billing account it holds `roles/billing.viewer` and nothing else. W0.2's
second question is answered: **billing-account writes never belong to a CI identity.**
**What the honest version of this sounds like:** the control is not the role list. An
identity that can grant itself any project role has, in effect, every project role. What
actually bounds it: it is unreachable except from `main` (enforced by Google), every apply
pauses on a required reviewer (enforced by GitHub), every plan is checked against the §7.1
allowlist so a resource type nobody argued for is refused even with permission to create
it, and there is no key to steal. ADR-0004 Amendment 2 had to withdraw a claim that an
identity could not do something; this is written so there is nothing to withdraw.
**Alternatives:** keep the role set in the human-run bootstrap module — then D6's per-wave
growth costs a local apply per wave, and "one click per wave" becomes "one click and one
laptop"; grant `roles/owner` and stop pretending — it would be more honest about the
project scope and would also hand over the billing account, which is the boundary worth
keeping; billing-scoped resources in their own state, as `wif.tf` proposed in F0 — still
the cleanest shape, and it costs state surgery on the budget that *is* the kill-switch,
during the phase where the kill-switch is the entry gate. The viewer-only line gets most
of the benefit for none of that risk, and the split stays available later.
**Consequence, stated:** a plan needing a billing-account write fails in CI with a
permission error. That is intended. It is visible, it names the resource, and it routes
the change to the only path allowed to make it.
**Mechanism correction worth recording:** the branch restriction lives in the
principalSet (`attribute.ref/refs/heads/main`), not in an IAM condition on the binding. An
IAM condition evaluates request attributes and cannot see the OIDC assertion, so
`assertion.ref == '...'` written there would read a variable it has no access to — a
control that looks present and either grants nothing or refuses nothing. `attribute.ref`
was already mapped on the provider in F0; one attribute per principalSet, so the ref is
bound here and the repository stays in the provider's `attribute_condition`.
**Not yet proven:** that the binding issues credentials at all. It cannot be tested before
it is applied. The first deploy dispatch after W1a is the test, and its failure mode is
loud — `google-github-actions/auth` fails before Terraform runs.
**Exit review:** yes. This is the largest standing authority created in the phase.
### W0.4 — Attempt 2 failed; the phase is halted and the fix is one permission
**Made:** 2026-08-21 · **Work item:** Wave 0 · **Reversibility:** cheap
**What happened:** the second live-fire failed with the same 403 as the first, and the
Amendment 2 grant was live on the billing account at the time — verified against the
billing account's IAM policy rather than against Terraform state. Cause: the function's
first call is `Projects.GetBillingInfo`, which needs `resourcemanager.projects.get` on the
**project**, and the identity's entire project-level permission set was six permissions
that did not include it. Full analysis in ADR-0004 Amendment 3; transcript in
[`kill-switch.md`](../runbooks/kill-switch.md) §4.
**Stop rule, applied:** spec §2 halts the phase on a second live-fire failure. Wave
preparation stopped at the moment the logs were read. Wave 1's remaining Lane A items —
Firestore, Artifact Registry, `keyctl` — are **not** being built until a live-fire has
succeeded and been archived. What continues is this fix and its record, which the stop rule
exists to make room for.
**Decision:** a custom role carrying exactly `resourcemanager.projects.get`, rather than
`roles/browser` — the narrowest predefined role containing it, which also grants project
IAM policy reads, project listing, and folder and organization reads. This identity already
holds administrator rights over the billing account (Amendment 2); it is the last one in
the project that should collect incidental reads. Cost: `google_project_iam_custom_role`
added to the architecture §7.1 allowlist, which is what that list is for, and an
architecture version bump.
**Alternatives:** `roles/browser` — one line, five permissions this identity has no use
for, on the most powerful identity in the project; drop the read from the function and call
`UpdateBillingInfo` unconditionally — it removes the permission requirement and also
removes the `billing already detached; nothing to do` path that the runbook documents as
contract and that the redelivery test exercises, so a control would lose a behaviour to
avoid an IAM line.
**Diagnosis was not measured, and that is stated:** the claim that `GetBillingInfo`
requires `resourcemanager.projects.get` comes from Google's API reference, not from an
observation on this account. Data-access audit logging is off, so the denial names no
permission, and impersonating the function's identity to reproduce the call was itself
refused — the maintainer's Owner role does not carry
`iam.serviceAccounts.getAccessToken`. What *is* measured: the failing call, from the
function's source and its log line; and the identity's complete permission set, from the
project policy and the role definitions. The third live-fire is the test of the remaining
inference, and it is cheap to run.
**Exit review:** yes. Two live-fires, two permission defects, both invisible to
configuration review.

### W0.5 — G1 is satisfied; the halt is lifted
**Made:** 2026-08-21 · **Work item:** Wave 0 · **Reversibility:** one-way (the test
happened)
**Decision:** the third live-fire passed — notification, detach, API-confirmed
`billingEnabled: false`, an idempotent redelivery, and a clean re-attach. Evidence in
[`kill-switch.md`](../runbooks/kill-switch.md) §4, #33 closed. The stop rule invoked in
W0.4 is lifted and Wave 1's remaining Lane A work resumes.
**What the phase learned, kept because it is the reusable part:** two permission defects in
one identity, in a control whose configuration had been reviewed twice and read correct
both times. Neither was visible in Terraform, in the role names, or in the architecture's
identity table. Configuration review found nothing; firing it found both.
**And a second-order lesson:** after Attempt 1's fix the control was believed working for
an hour, on the strength of a correct diagnosis of a real defect. It was still inert. A
control is not tested by being fixed — which is exactly why the stop rule counts *failures
to fire*, not *unexplained failures*.
**Deliberate omission, logged rather than skipped:** no console screenshot is archived. §3
requires confirming the detach at the API rather than only in the logs, and the API output
is in the record; a screenshot is the same fact one layer further away. The requirement
was written before the API check was.
**Exit review:** yes — the three-attempt sequence is the phase's most transferable finding.

### W1.6 — `gcf-artifacts` is adopted, and its cleanup policy starts in dry run
**Made:** 2026-08-21 · **Work item:** Wave 1 · **Reversibility:** costly (the adoption),
cheap (the dry run)
**Decision:** Terraform adopts the `gcf-artifacts` repository through an `import` block
and gives it the same keep-last-2 policy as `plumbline` — with
`cleanup_policy_dry_run = true` until what it would delete has been observed (#57).
**Why adopt something this project did not create:** a Gen2 function is built by Cloud
Build into an auto-created repository that nothing owned, that accumulates an image per
deploy, and that already holds ~93 MB of a project-wide 0.5 GB free allowance from a
handful of kill-switch deploys. `docs/runbooks/kill-switch.md` §7 assigns bounding it to
F2. "Not ours" is not a size limit.
**Why dry run, which is the part worth arguing:** the images in there include the one the
kill-switch function runs. A Gen2 function scales to zero, so every invocation is a
potential cold start and a potential image pull; deleting a version a deployed function
still references breaks the last cost control in the project, at the moment it is needed,
and nothing reports it until then. keep-last-2 *should* never select a running image — the
current one is the most recent by construction. This phase has already watched that
control be inert twice on reasoning that read correctly, so the policy runs in dry run,
its decisions are read out of the logs, and it goes live in Wave 2.
**Verified before committing:** the import plans as `will be updated in-place`, not as a
replacement — an adoption that destroyed and recreated the repository would delete every
image in it, including the running one. `1 to import, 12 to add, 1 to change, 0 to
destroy`.
**Small thing, done on purpose:** the repository's existing description — Cloud Functions'
own words — is carried into the configuration rather than blanked. Adopting a resource is
not a licence to erase the metadata of the system that still writes to it, and a diff that
nulls a field nobody asked to change costs a reviewer attention for nothing.
**Exit review:** no, but #57 must not close silently.

### W1.7 — `keyctl` lives in the collector module, not in `tools/`
**Made:** 2026-08-21 · **Work item:** Wave 1 · **Reversibility:** cheap
**Decision:** the issuing tool is `collector/cmd/keyctl`, not `tools/keyctl` as D5
sketched. `internal/auth` is importable from there and from nowhere else, so the key the
tool issues and the key the collector accepts are defined by one piece of code — the
format, the prefix, the issuable environment markers and the hash. A tool in a separate
module would restate that contract, and a restated contract drifts silently until an agent
in production presents a key the data plane rejects.
**Consequence worth naming, because it looks like the tail wagging the dog:** the Gate B
source-root extension this phase predicted is no longer needed. That is a side effect, not
the reason. Had `tools/` been right on the merits, the gate roots would have grown and the
change would have been logged — widening a scan is the response ADR-0004 §3 asks for.
**Also added:** `auth.HasIssuableShape`, exported so the tool can assert that what it just
generated is something the collector would accept. Two places agreeing about a format by
inspection is how a tool ships keys that fail at an agent, in production, on someone else's
clock; one function called by both cannot drift from itself. Its doc comment says it
answers shape and not authentication, because a future caller will be tempted.
**Refusal that is deliberate:** `Create`, not `Set`. An `api_key_id` that already exists
belongs to a key some agent may still be presenting; overwriting the hash would revoke it
silently at the next collector start, with no error anywhere near the person who caused it.
**Exit review:** the maintainer runs this tool, so its UX is theirs to accept.

### W1.8 — Wave 1 applied; the post-apply drift check failed the wave, correctly
**Made:** 2026-08-22 · **Work item:** Wave 1 · **Reversibility:** cheap
**What happened:** the first gated apply succeeded —
`Apply complete! Resources: 1 imported, 11 added, 1 changed, 0 destroyed` — and then
`deploy.yml`'s post-apply step failed the run with *changes remain after apply; the wave is
not finished*. Three resources still proposed changes, all of the same class: **values the
API normalises and the configuration insists on rewriting.**

| Resource | The loop |
| --- | --- |
| `google_monitoring_notification_channel.alerts` | Monitoring lowercases the address; the secret was typed with capitals, so every plan proposed changing it back |
| both Artifact Registry repositories | `older_than = "0s"` is not stored, so every plan proposed re-adding a condition the API had dropped |

**Fixes:** `lower(var.alert_email)`, so the configuration is independent of how the secret
was typed; and `older_than = "86400s"`, the smallest value that both persists and buys
something — an image is never eligible for deletion on the day it is pushed, so a deploy
cannot prune the artefact it just created.

**The check earned its place on its first run, which is the part worth recording.** Without
it the wave would have reported success while leaving a diff that never converges — and the
next wave's plan would have carried three unexplained changes that someone would have
approved as noise, which is exactly how a plan-diff review stops being a review. Failing a
wave whose apply succeeded looks harsh and is the correct reading of "drift is a bug"
(architecture §8).

**Not a stop-rule event.** The spec halts the phase on a kill-switch live-fire failure and
on billed cost. A wave that applied cleanly and then reported an unconverged configuration
is neither; it is a wave that is not finished, and it finishes with a second apply.
**Exit review:** no, but the completion note should carry it — the first use of the gated
path found a real defect, and that is evidence about the gate rather than about the defect.

### W2.1 — The images were already distroless; what was missing was the assertion
**Made:** 2026-08-22 · **Work item:** Wave 2 · **Reversibility:** cheap
**Found rather than built:** Wave 2's first item asks for distroless Dockerfiles. F1 had
already written both — `gcr.io/distroless/static-debian12:nonroot` for the collector,
`aspnet:8.0-jammy-chiseled` for the worker. Rewriting them to satisfy a checklist would
have been work that changed nothing.
**What was actually missing:** anything that would notice if that stopped being true. A
base image swapped for a convenient one while debugging is exactly the change that merges
quietly and is discovered when someone asks why the image is 900 MB. The new job runs
`docker run --entrypoint sh` against both images and fails if either answers — the same
shape as the gate proofs: assert the property, do not trust the file that declares it.
**Push is main-only, and the `if` is documentation rather than the control.** `ci-deploy`
is bound to `attribute.ref/refs/heads/main`, so a pull request cannot obtain a token that
writes to Artifact Registry even if this job asked for one. The condition states the rule;
Google enforces it.
**No `latest` tag.** Images are tagged by commit alone. A moving tag makes "which image is
running" a question with no answer, and Cloud Run pins a digest regardless.
**Path filter covers inputs, not directories:** the worker image is built from the
repository root because it embeds the mapping YAML, so `normalization/` and `third_party/`
are its inputs and are in the filter. The same rule that `analytics/sql/` had to be added
under.
**Exit review:** no.

### W2.2 — OIDC push validation is real; the stub's capability survives only as guarded local configuration
**Made:** 2026-08-22 · **Work item:** Wave 2 · **Reversibility:** cheap
**Decision:** `OidcPushAuthenticator` validates the push subscription's bearer token with
`GoogleJsonWebSignature.ValidateAsync` — Google's signature, issuer and expiry checks —
then asserts the audience and that the issuer-verified email is the push service
account's. The email check is what makes this authentication rather than "a Google-signed
token exists": any principal with a Google identity can mint a token naming any audience.
`StubPushAuthenticator` and `UnimplementedOidcAuthenticator` are deleted; Gate G asserts
the absence of both names and the stub's marker string outside documentation, **and** the
presence of the real validator call — absence alone is a rename detector, which is not
the property DoD 7 asks for.
**The audience is a fixed string, not the service URL.** The subscription (Wave 3) mints
tokens for what the service (Wave 2) expects; a URL-shaped audience would make the
earlier apply depend on the later one's output. Pub/Sub's `oidc_token.audience` carries
any agreed value; `PLUMBLINE_PUSH_OIDC_AUDIENCE` and the subscription must state the same
one.
**What remains of the stub, stated rather than slipped past:** the local pipeline still
runs with push authentication off (`PLUMBLINE_PUSH_AUTH=none`), because the Pub/Sub
emulator cannot mint Google-signed tokens and F1's `make e2e` must keep passing. The
guard is unchanged — refusing outside a Development environment, named on `/healthz` and
in the startup log. What W5.2's announcement marked was a validator that did not exist;
that condition is gone, and the accept-all path is now deliberate, guarded configuration
for an environment that cannot do better rather than a placeholder waiting to ship.
**Alternatives:** validate OIDC locally against a fake issuer — a second issuer
configuration whose only production effect is widening what the cloud could be
misconfigured to trust; drop the local push path and test the worker only through unit
tests — it would retire the F1 e2e's strongest property, the poison path exercised
through a real push delivery.
**Interface consequence:** `IsAuthentic` became `IsAuthenticAsync` — certificate fetch is
IO. The validator seam is injectable and the tests fake only that seam; one test pins the
real seam refusing a malformed token as a refusal rather than a crash.
**Not yet proven:** acceptance of a genuine Google-signed token. No test can mint one.
Wave 3's first real push delivery is the test, and its failure mode is loud — every
delivery refused, the subscription's backlog alert fires.
**Exit review:** no.

### W-repo.1 — Verification A stays a human touchpoint
**Made:** 2026-08-21 · **Work item:** W-repo · **Reversibility:** cheap
**Decision:** the spec's §9 lists Verification A as touchpoint 4, adding it to the
directive's list of human touchpoints, which the directive itself called complete.
**Alternatives:** keep §9 identical to the directive and leave Verification A where it is
today — outstanding in [`kill-switch.md`](../runbooks/kill-switch.md) §1 and in #17 step 2,
owned by an F0 issue that closes when the billing period does. That is how an obligation
becomes nobody's: the phase that could have discharged it declines to name it, and the
issue that names it closes for an unrelated reason.
**Rationale:** ADR-0004 Amendment 1 changed the budget's spend basis on the premise that
Always Free is credit-implemented rather than an absence of charge. That premise has never
been observed on this account — the runbook says so in the place where the observation
should be. F2 is the first phase where the check is not vacuous, because F2 is the first
phase with usage to look at, and the check is one browser tab in a morning. Deferring it
again would leave a live control resting on documentation about how a different account
behaves.
**Cost, stated:** it obligates the maintainer for a step the directive did not budget.
That is why it is logged as a deviation rather than folded into §9 quietly.
**Exit review:** yes — it is the one place this spec asks for more than the directive did.

### W2.3 — The Firestore registry reads the whole collection once, at startup
**Made:** 2026-08-22 · **Work item:** Wave 2 · **Reversibility:** cheap
**Decision:** `FirestoreRegistry` reads every document of `api_keys` at startup under
the collector's own identity and resolves to the same in-memory keyset as the file
registry — one validation path (`buildKeyset`), one constant-time lookup, two loaders.
The collection name moves into `internal/auth` beside the key format, shared with
`cmd/keyctl` by the W1.7 argument: the data plane must read what the tool writes, and
two places agreeing about a name by inspection is drift waiting to be found in
production. Exactly one backend may be configured; a file path and a Firestore project
set together is a startup error rather than a precedence rule.
**Alternatives:** per-request Firestore reads — hot-path latency and an unbounded
failure mode for a registry that changes at human cadence; a status-filtered query —
one backend filtering in a query language the other never runs, so the two registries
would disagree about what "inactive" means the day the filter and `buildKeyset` drift;
precedence instead of refusal when both backends are set — whichever the guess picked,
the collector would look configured while authenticating against the other one's keys.
**Skew accepted, named:** a key issued after startup is invisible until the next cold
start or redeploy. That is the file registry's contract already (W1.7 makes rotation a
redeploy), and with `min_instances = 0` an idle collector re-reads on its next wake
anyway.
**Not proven here:** the read path against real Firestore under the collector's service
account — no emulator runs on this host, and the unit tests cover parsing and selection,
not the wire. Wave 4's cloud e2e with the provisioned `adjudicator-prod-2` key is that
test.
**Exit review:** no.

### W2.4 — Cloud Run serves the collector's OTLP/HTTP only; gRPC is unreachable in the cloud
**Made:** 2026-08-22 · **Work item:** Wave 2 · **Reversibility:** cheap (the setting);
**costly** (the fix, if F4 needs one)
**Found rather than chosen.** A Cloud Run service routes to exactly one container port.
The collector serves OTLP/HTTP on 4318 and OTLP/gRPC on 4317 from two listeners, and
architecture §2.1 and the §1 diagram both promise agents `OTLP/HTTP+gRPC`. Only HTTP is
reachable once deployed; the gRPC listener still starts and nothing routes to it.
**Decision:** expose HTTP on the container port, leave the gRPC listener running, and
record the gap here rather than deleting the listener or quietly editing the promise.
Deleting it would remove the local pipeline's gRPC coverage to make a cloud limitation
tidier; editing §2.1 would retire a capability on the strength of one platform
constraint nobody has yet tried to work around.
**Alternatives:** a second Cloud Run service for gRPC — a third service in a phase whose
spec says two, and a second public endpoint to defend; h2c multiplexing in the collector,
serving gRPC and HTTP on one port — the right fix and a collector code change with no
spec behind it, which §"no scope beyond the active spec" refuses.
**Consequence for the phase:** F2's DoD sends the constructed corpus over OTLP/HTTP, so
nothing in this phase is blocked. What is blocked is an agent that speaks gRPC only, and
F4's dogfooding is where that stops being hypothetical.
**Raised, not resolved:** proposed back as a spec change in #68, with the three options
and their costs, because the honest ones are a collector change or an architecture
amendment and neither belongs inside a wave that is already armed.
**Exit review:** yes — it is a documented capability that the deployment does not have.

### W2.5 — Firestore access is project-scoped, and §6.1 is corrected rather than reinterpreted
**Made:** 2026-08-22 · **Work item:** Wave 2 · **Reversibility:** cheap
**Decision:** the collector reads the key registry through `roles/datastore.viewer` at
**project** scope, and architecture §6.1's "table/collection-scoped least privilege" row
is split and corrected in the same change (v0.9). Table-scoped is real and is
implemented — the worker holds `roles/bigquery.dataEditor` on `spans` and not on the
dataset, so it cannot write the views. Collection-scoped is not a thing Firestore has:
IAM is granted at project scope (conditions can narrow it to a database, and this project
has one), and per-collection rules exist only for mobile and web clients, not for the
server client library the collector uses.
**Verified how:** Google's Firestore IAM documentation, read at wave time, against the
claim rather than in support of it.
**Alternatives:** leave §6.1 as written and implement the widest grant quietly — the
document would then describe a control nobody built, which is the failure mode this
project has already paid for twice in the kill-switch; add a database-scoped IAM
condition to look narrower — with exactly one database it narrows nothing, and a
condition that is decorative teaches a reader that conditions here are decorative.
**What actually bounds it:** the collector reads and cannot write, Firestore holds no
span data by §2.6, and the widest reachable secret is a set of SHA-256 hashes that are
useless without the plaintext (§6.3).
**Exit review:** yes — a documented boundary was wider in reality than the document said.

### W2.6 — The image tag lives in the repository, because the approval gate cannot see attributes
**Made:** 2026-08-22 · **Work item:** Wave 2 · **Reversibility:** cheap
**Decision:** `var.image_tag` is a full commit SHA with its value defaulted in
`variables.tf`, and bumping it is a pull request. Both services run
`<registry>/<component>:<tag>`; a moving tag is refused by a validation rule.
**Why not a dispatch input, which was the obvious shape:** W1.1 binds the reviewer's
approval to a fingerprint of sorted `address action` pairs and states its blind spot —
an attribute change that keeps the same addresses and actions does not move it. The
image a service runs is exactly such an attribute, and it is the one where the blind spot
matters most: the same commit could be dispatched twice and deploy different code, with
an identical fingerprint both times. Keeping the tag in git moves that decision into the
diff a reviewer has already read.
**Cost, accepted and stated:** the deployed image lags its own merge by one commit,
because a commit's images exist only after CI has built them. So arming a wave has an
ordering: merge the code, let CI push, bump the tag, then dispatch.
**Also added:** the plan job refuses tags with no images in Artifact Registry. Cloud Run
resolves a tag when it starts a revision, not when Terraform plans one, so without this
the failure lands *after* the approval — the reviewer having approved a plan that could
never apply.
**Exit review:** no.

### W2.7 — Three IAM types added to the allowlist, each to narrow a grant
**Made:** 2026-08-22 · **Work item:** Wave 2 · **Reversibility:** cheap
**Decision:** §7.1 gains `google_cloud_run_v2_service_iam_member`,
`google_pubsub_topic_iam_member` and `google_bigquery_table_iam_member` (architecture
v0.9), and the deploy identity gains `roles/run.admin` plus `roles/iam.serviceAccountUser`
granted **per runtime service account** rather than at project scope — D6's per-wave
growth, enumerated in #63.
**Worth naming:** the allowlist already carried `google_cloud_run_service_iam_member`, the
v1 type, which does not manage a v2 service's IAM policy. A row that looks like coverage
and is not is worse than an absent row, because the guard would have refused the correct
resource while the table said the case was handled.
**Why each earns its place:** all three exist to make a grant *smaller* than the
project-scoped alternative — publish on `traces` alone rather than every topic including
`billing-alerts`; write `spans` alone rather than the dataset holding the views; invoker
on one service rather than `roles/run.invoker` project-wide. The allowlist exists to catch
resource classes that end the zero-cost envelope, and these three end nothing.
**On `allUsers` as an invoker:** the collector is deliberately public (§6.1) and this is
the project's only unauthenticated endpoint. It is written in one resource, named
`collector_public`, so a reader looking for "what is exposed" finds it in one grep.
**Exit review:** no, unless the exit review wants to revisit the public collector itself.

### W2.8 — The cleanup policy goes live on evidence that it is inert, which is not the evidence W1.6 asked for
**Made:** 2026-08-22 · **Work item:** Wave 2 (#57) · **Reversibility:** cheap to reverse
the flag; **one-way** for anything it deletes
**What the dry run was asked:** whether keep-last-2 would ever select the image the
kill-switch function runs. W1.6 put the policy in dry run rather than trusting the
reasoning, because this phase had already watched that control be inert twice on
reasoning that read correctly.
**What it answered: nothing, because it had nothing to select.** Measured on 2026-08-22
against the project: `gcf-artifacts` holds two packages with exactly **one version each**
— the function image and its build cache — so keep-last-2 claims both and DELETE selects
nothing. There are no Artifact Registry cleanup entries in this project's logs at all.
W1.6's premise, that the repository accumulates an image per function deploy, is not what
the repository shows; 93 MB is one image plus one cache, not a handful of deploys' worth.
**Decision:** switch it live anyway, and say plainly what that rests on. The flag changes
nothing today — the policy is provably inert either way — so flipping it carries no
present risk, and leaving it in dry run indefinitely means the only bound on a 0.5 GB
allowance is a control that has been asked never to act.
**What actually carries the risk, stated because it is not observation:** the running
image is the most recent by construction, keep-last-2 spares the two most recent, and
`older_than = 86400s` adds a day. This is the same protection `plumbline` has run live
under since Wave 1 — and that repository holds the images Cloud Run pins, so the project
already depends on this argument for the services it is about to deploy.
**Alternatives:** hold dry run until a third kill-switch deploy makes a version eligible
— it is the observation W1.6 wanted, and it waits on an event that may not happen this
phase while the allowance stays unbounded; drop the policy on this repository — it
reverses W1.6's adoption argument, and "not ours" was never a size limit.
**The honest residual:** the first genuine exercise of this policy is the third
kill-switch deploy. If a deploy is ever followed by a function that cannot pull its
image, the runbook's §7 is where that trail starts.
**Exit review:** yes — #57 must not close silently, and this is the entry that says the
dry run answered a different question than the one it was set up for.

### W2.9 — The phase is halted: real spend was reported and the kill-switch fired
**Made:** 2026-08-22 · **Work item:** Wave 2 · **Reversibility:** one-way (the charge and
the detach happened); cheap (the halt)
**What happened:** at 2026-08-22 02:16:18 UTC a budget notification carrying a **real**
reported cost of 0.01 TRY — `interval_start=2026-08-01T07:00:00Z`, not one of Wave 0's
synthetic `LIVE-FIRE*` markers — caused the kill-switch to detach billing from
`plumbline-19458`. Confirmed at the API: `billingEnabled: false`. Full record in
[`f2-billing-incident-2026-08-22.md`](../evidence/f2-billing-incident-2026-08-22.md).
**Stop rule, applied:** spec §2 halts every further wave on any billed cost. Wave 2 was
Lane-A complete and ready to dispatch; it is **not** armed. `#66` and `#67` are held
unmerged — permitted under Lane A, but the wave's own ordering needs CI to push images,
which it cannot do with billing detached.
**Decision:** investigate read-only, record, and stop. **Billing is not re-attached.**
That is Lane C, and it is also the wrong first move: re-attaching before the cause is
known restores the conditions that produced the charge, and the next notification carries
the same interval's cost, so the switch fires again. The sequence on 2026-08-21 already
demonstrated that shape — detach, re-attach, detach.
**What cannot be decided from here:** whether 0.01 TRY is genuine spend beyond Always
Free or the credit lag ADR-0004 Amendment 1 predicted might exist. The budget measures
with `INCLUDE_SPECIFIED_CREDITS`/`FREE_TIER`, so the figure is net of Always Free *if* the
credit had been applied when the line was reported. Distinguishing needs Billing Reports —
gross versus credited, by service, by day — which is the maintainer's console.
**Worth more than the incident:** this is the first real observation of Amendment 1's
premise on this account. W-repo.1 records that the premise had never been observed, and
that F2 was the first phase where checking it would not be vacuous. It arrived
unannounced, three waves early, as a real sequence rather than a scheduled look.
**Follow-up this exposes, independent of the outcome:** nothing alerts on "the kill-switch
fired". A detached project cannot run the function that detached it, so a *working*
kill-switch is silent afterwards, and what surfaced this was an unrelated CI job failing
on an image push. The DLQ depth alert is the project's only notification channel today.
**Exit review:** yes. This is the phase's most consequential event and the first time a
cost control acted on something that was not a test.

### W2.10 — The halt is lifted: the cost was the kill-switch's own CPU, fully credited
**Made:** 2026-08-22 · **Work item:** Wave 2 · **Reversibility:** cheap
**Measured:** Billing Reports for `011680-E61D62-C3CAA2`, August 1–22, grouped by SKU. One
SKU carries a non-zero gross line — *Cloud Run functions CPU (Request-based billing) in
us-central1*, 30.82 seconds, ₺0.04 gross, -₺0.04 savings, **₺0.00 subtotal**. Every other
SKU reads zero gross. Total ₺0.00, no tax. The 0.01 TRY that fired the kill-switch was a
gross line reported before its `FREE_TIER` credit landed.
**Decision:** lift the halt. Spec §2 names two stop-rule triggers, and they disagree here:
a notification carrying `costAmount > 0.00` (fired — the *detector*) and *"Billing Reports
showing gross cost not fully credit-offset"* (not met — the *adjudicator*). The Reports are
the ground truth about billed cost, so the substantive condition never held. The incident
note the escape hatch requires was written and merged before this reading, not assembled
around it.
**What this settles, which outlives the incident:** ADR-0004 Amendment 1's premise — that
Always Free is credit-implemented rather than an absence of charge — is **confirmed on this
account**, for the first time (W-repo.1 records it had never been observed). What the
amendment did not anticipate is that the gross line and its credit do not land together,
and the budget publishes in the gap. Amendment 1 deferred the fix pending a real sequence;
this is that sequence, and it is now #71 with the three options re-read against data.
**Consequence for the phase, stated rather than deferred:** the trigger can fire again on
any new gross line, and Wave 2 deploys services that will produce them. A spurious detach
with services running is an outage — the difference from Wave 0, where the live-fire was
argued side-effect-free *because* nothing was deployed. #71 should be resolved before Wave
4's traffic and arguably before Wave 2's apply; that is the maintainer's call because it
amends an ADR.
**Not performed, and why:** re-attachment. The 24 stale notifications queued while the
function could not start must be dropped first — otherwise the function wakes, reads the
old 0.01, and detaches again. Both that `seek` and the re-attach were refused to the agent
by its own tooling, so the restart procedure is written out in the evidence note for the
maintainer to run instead of being executed.
**Exit review:** yes — a stop rule was invoked and lifted inside one day, and both halves
should be read together.

---

## A2-level — ADR-0004 Amendment 4 (#71)

Autonomous choices made executing
[`F2-directive-kill-switch-amendment-2.md`](F2-directive-kill-switch-amendment-2.md).
The decisions D1–D5 are the maintainer's; these are the calls the directive left to
the executor, plus three places where its literal text could not be followed.

### A2.1 — Filed as Amendment 4, because Amendment 2 is taken
**Made:** 2026-08-25 · **Reversibility:** cheap
**Decision:** the supplied text was authored as "Amendment 2". `ADR-0004` already has
an Amendment 2 — the 2026-08-21 entry on the detach permission model — and both
`killswitch.tf` and `wif.tf` cite it *by number* in load-bearing comments. Filed as
Amendment 4; every new reference in Terraform, function source, tests, the plan guard
and the gates written to match.
**Alternatives:** append verbatim as a second "Amendment 2" — the document would then
contain two amendments with one number, one about credit filters and one about IAM,
and every existing citation would become ambiguous; renumber the older one — it is
cited from configuration and from the runbook, so renumbering it rewrites history to
protect a draft.
**Rationale:** a decision record whose numbering collides is a record you cannot cite.
**Exit review:** no, but the maintainer should know their draft's number moved.

### A2.2 — The gross-cost budget has no `all_updates_rule`, and that is what emails
**Made:** 2026-08-25 · **Reversibility:** cheap
**Decision:** the directive's W2 asked for `all_updates_rule` carrying
`disable_default_iam_recipients = false` and no `pubsub_topic`. The provider refuses
exactly that shape: the block requires one of `pubsub_topic` or
`monitoring_notification_channels`, so it cannot be written without handing this
budget one of the two programmatic paths D3 forbids it. The block is omitted.
**Consequence, and it is an improvement rather than a compromise:** with no
`all_updates_rule`, the budget notifies on its threshold rules (50%, 100%) instead of
on every cost update. An alert that fired every thirty minutes would be muted by the
third day, and D3's purpose is to be noticed.
**Verified how:** `terraform validate` refuses the directive's shape with
`"all_updates_rule.0.pubsub_topic": one of ... must be specified`; it accepts the
omission.
**Exit review:** no.

### A2.3 — Gate H, so the superseded filter cannot come back quietly
**Made:** 2026-08-25 · **Reversibility:** cheap
**Decision:** the directive asked for a grep gate on `credit_types` and the enumerated
credit type under `infra/terraform/`. Implemented as Gate H in the existing gate
framework rather than as a standalone script, with patterns written so they cannot
match their own text — the convention that lets this repository's gates name the
strings they forbid without an exclusion list.
**Why it earns its place:** a regression here reads as a *tightening*. Someone
restoring an enumerated filter would believe they were narrowing the control, and the
control would then fire on ordinary usage. That is the same shape as the defect it
guards against, which is why detection is worth having on top of the ADR.
**Proven both ways:** a probe resource carrying the old filter fails Gate H; removing
it passes. Both runs are in the pull request.
**Exit review:** no.

### A2.4 — The plan-guard assertion reads the attribute, not the resource name
**Made:** 2026-08-25 · **Reversibility:** cheap
**Decision:** D3's "exactly one budget references `billing-alerts`" is asserted
against planned `all_updates_rule.pubsub_topic` values, and the guard reports which
budget holds the binding on clean runs as well as violating ones.
**Alternatives:** match on resource name — a rename would defeat it, and what matters
is where a budget publishes rather than what it is called.
**Fixtures:** `plan-amendment-2.json` (the intended shape, passes) and
`plan-two-budgets.json` (a second budget bound to the topic, fails). Both are in the
guard's self-test, which now runs eight fixtures.
**Exit review:** no.

### A2.5 — The decision is a pure function, and NaN is not spend
**Made:** 2026-08-25 · **Reversibility:** cheap
**Decision:** `shouldDetach(cost, threshold)` is isolated from the CloudEvent, the
billing client and the network. It refuses NaN, ±Inf and negative costs before
comparing, rather than relying on NaN comparisons happening to be false.
**Why explicit:** the accidental version is correct today and silently depends on IEEE
semantics that a future refactor to `!(cost < threshold)` would invert. A negative
cost is a refund or a correction, and neither is a reason to take a project offline.
**Startup guard:** `DETACH_THRESHOLD` has no default. Missing, unparseable, zero,
negative or non-finite are all startup failures — a threshold nobody chose is either
zero, which restores the behaviour this amendment removes, or a number invented at the
moment the control is needed.
**Exit review:** no.

### A2.6 — The runbook's §1 was rewritten, not just appended to
**Made:** 2026-08-25 · **Reversibility:** cheap
**Decision:** the directive asked for a new "credit lag and promotional period"
section. Adding only that would have left §1 and its "Spend basis" subsection still
stating the old trigger — that the function fires above zero, and that the budget
subtracts one named credit type. Both were rewritten to the new rule, with the old one
named and dated so the change is visible rather than erased.
**Also updated:** Verification A's record. It read "NOT YET DONE"; it has now been
attempted and is **inconclusive by construction** — the trial credit absorbs the usage,
so this account cannot show how it behaves on Always Free alone until 2026-10-05. That
is written where the verification lives, with the observed figures, rather than left as
an open checkbox that looks merely undone.
**Rationale:** a runbook that states the trigger twice, differently, is worse than one
that states it once and wrongly, because the reader cannot tell which sentence is
current.
**Exit review:** no.

### A2.7 — `deploy.yml` gains a targets input, because Lane A merges ahead of its applies
**Made:** 2026-08-25 · **Reversibility:** cheap
**What forced it:** the authenticated plan on this branch reports Wave 2's Cloud Run
services alongside the amendment's two budget changes — they merged to `main` on the
Lane A argument that merging mutates nothing. Applying Wave 1.5 untargeted would
therefore deploy Wave 2, which the directive's §2 puts out of scope and whose §6 step 6
forbids until the live-fire passes. This is W0.3's situation exactly, one wave later,
and W0.3 predicted it: *any phase that merges ahead of its applies inherits it.*
**Decision:** an optional `targets` dispatch input, applied to the plan, the re-plan
and the post-apply drift check. Empty means the whole configuration, so every previous
wave's behaviour is unchanged.
**The post-apply check has to share the scope, and that is the part worth stating.** An
untargeted convergence check after a targeted apply reports the resources the wave was
deliberately not allowed to create, and fails a wave that finished correctly. Scoping
it keeps the check meaningful — the targeted subset converged — rather than turning it
into noise a future operator learns to ignore.
**Injection seam closed while touching it:** the input reaches the script through the
environment rather than being interpolated into the script body. A dispatch input
pasted into shell source is a command-injection seam, and this is the workflow that
applies infrastructure.
**Alternatives:** hold Wave 2's Terraform out of `main` until this applies — it idles
the repository lane behind one human step and contradicts Lane A's own reasoning;
apply everything and call it Wave 1.5+2 — it deploys services under a control whose
replacement has not been live-fired, which is the one ordering the directive names.
**Exit review:** yes — it changes the gated apply path, which is D1's mechanism.

### A2.8 — The restart targets the budget alone, because the window is three minutes
**Made:** 2026-08-25 · **Reversibility:** cheap
**Measured, after getting it wrong once:** billing was re-attached at 10:51:10 UTC and
the first budget notification reached the function at 10:54:45 — three and a half
minutes. The procedure this log and the runbook both carried said "one notification
interval, roughly thirty minutes". It is not. The amendment's own apply was still
waiting at the approval gate when the old code detached billing again at 10:58:22.
**Decision:** the next restart applies `google_billing_budget.zero_spend` and nothing
else. The credit filter alone is sufficient — `INCLUDE_ALL_CREDITS` makes the published
figure net, net on this account is 0.00, and even the un-amended above-zero rule does
not fire on zero. One resource, one API call, seconds. The function's threshold and the
gross-cost budget follow in a second apply with no clock on it.
**Why the full amendment cannot go first:** updating the function replaces its source
archive and rebuilds the container. That is minutes by construction, so it loses a
three-minute race every time, and losing it mid-apply is worse than not starting.
**Alternatives:** update the budget by hand with `gcloud` — it would converge with the
merged configuration rather than drift from it, and it is still a mutation outside the
gated path, which spec §2 calls a process violation; raised for the maintainer rather
than taken, and only worth revisiting if the coordinated attempt fails twice.
**What this costs:** two approvals instead of one for this remediation. Cheap against
the alternative, which is a wave that half-applies while the control fires underneath it.
**Exit review:** yes — the phase's restart procedure was wrong in a way that only firing
it revealed, which is the same lesson the three live-fires taught, in a new place.

### A2.9 — The budget half of the amendment cannot go through the gated path, by design
**Made:** 2026-08-25 · **Reversibility:** cheap
**What happened:** the Wave 1.5 apply reached the gate, was approved, and failed:
`Error updating Budget "billingAccounts/***/budgets/02d42f8d-...": googleapi: Error 403:
The caller does not have permission`.
**Not a defect — W1.5's own boundary, meeting its first real case.** `ci-deploy` holds
`roles/billing.viewer` on the billing account and nothing else, because W1.5 decided
that *billing-account writes never belong to a CI identity*. A budget is a
billing-account resource. So the amendment's central change — the credit filter — can
never be applied by the gated path, and W1.5 predicted the shape exactly: *"a plan
needing a billing-account write fails in CI with a permission error. That is intended.
It is visible, it names the resource, and it routes the change to the only path allowed
to make it."*
**Decision:** Wave 1.5 splits by scope rather than by wave. The two budgets are applied
by the maintainer from their own credentials, targeted — the Wave 0 and W1a precedent,
which exists for exactly this class of resource. The function and its source object are
project-scoped and go through the gate as normal.
**What this says about the directive:** its §6 describes Wave 1.5 as a single armed
apply. That was not executable, and no amount of care in the plan would have revealed
it — the permission boundary only announces itself at apply time, which is the third
time in this project a control's real behaviour differed from its configuration review.
**Exit review:** yes — the directive's own verification sequence needs this correction
before anyone follows it again.

### A2.10 — A filter change needs its own seek, because in-flight messages carry the old figure
**Made:** 2026-08-25 · **Reversibility:** cheap
**What happened:** the credit filter was applied at ~11:51. At 11:53:03 a notification
arrived still reading `cost=0.04` and the function detached billing. That looked like
the fix failing.
**It was not.** A delivery attempt at 11:47:58 had aborted with *no available instance*,
and Pub/Sub retries with backoff — so the message delivered at 11:53 was published
**before** the filter changed and carried a figure computed under the old one. After a
second seek and re-attach, the first genuinely fresh notification, at **12:11:23**, read
`cost=0` and billing stayed attached.
**The rule this establishes:** changing what a budget *measures* does not change messages
already in flight. A seek belongs **after** the filter apply as well as before the
re-attach, or the first delivery after the fix re-creates the failure and reads as proof
that the fix did not work.
**Why it nearly cost more than a restart:** the false reading pointed at a much larger
conclusion — that `INCLUDE_ALL_CREDITS` does not subtract this account's credit either,
which would have left the epsilon as the only remedy and no window to deploy it in. One
observation was the difference between that and a two-minute retry.
**Exit review:** no, but the runbook carries it.

### A2.11 — The kill-switch's own resources are human-applied; the gate handles everything else
**Made:** 2026-08-26 · **Reversibility:** cheap
**What happened:** with the budget filter live and stable for 21 hours, the function's
threshold apply was approved and failed:
`Error deleting contents of object billing-killswitch-...zip: 403:
ci-deploy@... does not have storage.objects.delete access`.
Replacing the source archive is a delete plus a create, and `ci-deploy` has no grant on
that bucket at all. `wif.tf` says why, in words: *"State access scoped to the state
bucket, not project-wide: this identity must not reach the function-source bucket."*
**Decision:** keep the boundary and move the resource, rather than widen the boundary to
fit the resource. The kill-switch function and its source object are applied by the
maintainer from their own credentials, targeted — the same path the two budgets already
take. The rule that falls out is worth stating once: **the kill-switch's own resources
are human-applied; everything else goes through the gate.** The last cost control should
not be rewritable by the automation it exists to bound.
**Alternatives:** grant `ci-deploy` `roles/storage.objectAdmin` on the function-source
bucket — one line, and it dissolves the only stated separation between the deploy
identity and the code of the control that stops it; apply the whole amendment from Lane
C — already true for the budgets, and this makes it true for all four resources, which
is where it lands anyway.
**The uncomfortable half, stated so nobody mistakes the boundary for a control:**
`ci-deploy` holds `resourcemanager.projectIamAdmin`, so it can grant itself that bucket
access whenever it likes. The separation is a *convention this repository keeps*, not
something Google enforces — exactly the class of claim ADR-0004 Amendment 2 had to
withdraw once already. Keeping the convention still has value: it means a routine apply
cannot touch the kill-switch by accident, and reaching it would take a visible,
reviewable IAM change. Calling it a security boundary would not.
**Third time this phase a permission announced itself only at apply:** the kill-switch's
two live-fire failures, the budget 403, and now this. Configuration review has found none
of them.
**Exit review:** yes — it changes which resources the gated path owns.

### A2.12 — The live-fire passed; what it proves and what it cannot
**Made:** 2026-08-26 · **Work item:** Amendment 4 (#71) · **Reversibility:** one-way
(the test happened)
**Result:** all three steps passed. `4.99` produced `spend reported below detach
threshold; no action` with billing untouched — the case the pre-amendment rule got
wrong. `5.00` detached in two seconds, confirmed at the API. After re-attaching, two
consecutive real notification cycles read `cost=0` with no detach and no
below-threshold WARN. A read-only plan across all four kill-switch resources found no
differences.
**Both halves are separable in the logs, which was not guaranteed.** The real cycles
report a genuine zero rather than a small figure the epsilon is absorbing, so the credit
filter is doing its own work and the threshold is not quietly covering for it. Had the
figure come back as 0.04 with a WARN, the amendment would have been one fix wearing two
hats.
**What it does not establish, stated because the last time this was glossed the phase
lost three days:** the live-fire starts at the notification. It says nothing about how
the budget computes the figure it publishes — the exact segment where the original
defect lived. `kill-switch.md` §4 already carried that caveat before any of this, and it
was right. No synthetic message can reach that segment; only Verification A and B can,
and #74 says neither can answer before the promotional credit expires.
**The stronger evidence is not the test.** It is the 38 consecutive real notifications
reading `cost=0` between the filter going live and this check, against a control that
had not survived eighteen minutes attached. The live-fire proves the boundary; the 38
prove the premise.
**Exit review:** yes — with A2.9 through A2.11, this is the record of a control that was
wrong in production for four days and how it was corrected.

### A2.13 — The pinned image aged out while the wave was blocked
**Made:** 2026-08-26 · **Work item:** Wave 2 · **Reversibility:** cheap
**What happened:** the Wave 2 dispatch was refused at the plan job —
*no image tagged ac7b5af... in Artifact Registry for: collector worker*. That tag was
verified present on 2026-08-22. In between, the kill-switch incident held the wave for
four days while three newer commits pushed images, and the `plumbline` repository's
cleanup policy — keep the last two versions, delete anything older than a day — collected
it.
**Two decisions interacting, neither of which anticipated the other.** W2.6 put the image
tag in the repository so the approval gate could see which code deploys. W1.6 gave the
image repository a two-version retention to bound a 0.5 GB allowance. Both are right on
their own; together they mean **a pin has a shelf life**, and a wave that waits outlives it.
**Decision:** re-pin to current `main` and leave the retention alone. Widening retention
buys a longer shelf life with storage against a hard free-tier ceiling, for a problem
that only appears when a wave is blocked for days — and a wave blocked for days should be
re-examined before arming anyway, which is what re-pinning forces.
**The guard that caught it was built for something else.** The plan job's Artifact
Registry check exists because Cloud Run resolves a tag at revision start, so a missing
image would otherwise fail *after* the approval. It refused this before the reviewer was
asked. A check written for one failure mode caught a different one, which is the argument
for asserting the property rather than the scenario.
**Exit review:** no, but the completion note should carry it — any project pinning
artefacts in git against a retention policy inherits this.

### W2.11 — Wave 2's first apply found two more permission defects, both invisible before it
**Made:** 2026-08-26 · **Work item:** Wave 2 · **Reversibility:** cheap
**What happened:** the approved apply failed on two errors at once.

*One — a missing role.* `Error setting IAM policy for pubsub topic "traces": User not
authorized`. `ci-deploy` held `roles/pubsub.editor`, which creates topics and cannot
scope publish rights on them. Verified against the role definitions rather than
inferred: `gcloud iam roles describe` shows `pubsub.topics.setIamPolicy` in
`roles/pubsub.admin` and absent from `editor`. So the identity could build the transport
and could not apply the grant that keeps the collector off `billing-alerts` — the §6.1
boundary this wave exists to draw. Fixed by widening to `roles/pubsub.admin`.

*Two — an ordering race the configuration allowed.* `Permission
'iam.serviceaccounts.actAs' denied on service account collector@...`. The service
references its runtime identity's *email*, so Terraform ordered it after the service
account — but not after `ci_deploy_acts_as`, the grant that lets the deployer impersonate
that account, which is a separate resource with no data dependency between them. The two
raced and the service lost. Fixed with an explicit `depends_on`.
**Why `depends_on` and not a re-run:** a re-run would probably have worked, which is the
trap. The dependency is real and was simply unexpressed; leaving it to retry luck means
the same apply passes or fails depending on how the provider schedules two independent
resources. IAM *propagation* delay is a separate problem that ordering cannot fix
(kill-switch runbook §2), and if it bites, a re-run is the honest remedy — but it should
be the only thing left to chance.
**A custom Pub/Sub role was considered and rejected.** W0.4 set the precedent of one
permission in a custom role rather than a predefined role carrying five. That precedent
exists for the kill-switch identity, which is the last one in the project that should
collect incidental rights. `ci-deploy` already holds project IAM administration (W1.5),
so a custom role here would be ceremony rather than containment.
**The pattern, now at five:** the kill-switch's two live-fire failures, the budget 403,
the storage-object 403, and these two. **Every permission defect in this phase has
announced itself at apply time and none at review time.** That is not a run of bad luck;
it is what IAM is like, and it is the argument for the gated path — each of these failed
loudly against a reviewer's approval rather than quietly in production.
**Exit review:** yes — five for five is a finding about the method, not about the wave.

### W2.12 — The collector's 404 was the probe path, and `/healthz` is shadowed on the public URL
**Made:** 2026-08-26 · **Work item:** Wave 2 · **Reversibility:** cheap
**What it was not:** ingress (`INGRESS_TRAFFIC_ALL`, read back from the API), IAM (a
missing invoker returns 403, not 404, and `allUsers` holds `roles/run.invoker`), the
default URL being disabled (both URL forms are present in `urls`), an organisation policy
(`constraints/run.allowedIngress` is effectively `allValues: ALLOW`), or URL propagation.
Each was eliminated by a query rather than by waiting.
**What it was:** the probe path. Cloud Run's request log settles it in one query — and the
first attempt at that query was wrong, which cost most of the investigation: the log name
is URL-encoded (`run.googleapis.com%2Frequests`), and a regex against a decoded form
matches nothing and looks exactly like *no request arrived*.

With the query right, the split is unambiguous:

| Path | Response | Reached the container |
| --- | --- | --- |
| `/zzz`, `/health`, `/healthz/` | `404 page not found` (Go's mux) | yes |
| `/v1/traces` | `405 only POST is accepted` | yes |
| `/healthz` | Google's HTML 404 | **no** |

**So the service was healthy the entire time**, and `/v1/traces` — the only path that
matters — answers correctly from its own handler. What is genuinely broken is narrower
than it looked: **the exact path `/healthz` never reaches the container on the public
URL**, while `/health` and `/healthz/` do. The collector's health endpoint works locally
and is unreachable in the cloud.
**Recorded rather than worked around.** The obvious fix is to move the health path, and
that is the wrong instinct: it would make the local and cloud surfaces differ for no
reason the code expresses, and the next reader would find a health endpoint at an unusual
path with no explanation. The endpoint is not load-bearing — Cloud Run's startup probe is
a TCP check on the port, and it passed — so this is documented and left alone until
something needs it.
**Worth naming for anyone probing a Cloud Run service:** a Google HTML error page and the
application's own error body are different witnesses. `404 page not found` is Go; a styled
page with *"That's all we know"* never touched your code.
**Exit review:** no.

### W2.13 — Wave 2's ingress posture has no guard, and that is the reusable defect
**Made:** 2026-08-26 · **Work item:** Wave 2 · **Reversibility:** cheap
**Observation, from the 404 investigation rather than from design review:** the two
services have deliberately opposite ingress postures — the collector public, the worker
internal-only — and **nothing asserts either.** The plan guard checks scaling, region,
resource types and topic retention; ingress is not among them. A worker copied from the
collector's block, or a collector tightened by a careless edit, changes the project's
entire exposure surface and every existing control still reports green.
**Why it matters more than this incident:** the failure modes are asymmetric and both are
quiet. A worker set to `all` is an open ingestion endpoint whose only protection is the
OIDC check; a collector set to `internal` is a pipeline that silently accepts nothing from
the agents it exists to serve — which is precisely the shape the wave issue predicted for
guessing the worker's setting wrong, and it went unguarded on the other service.
**Decision:** the plan guard gains a per-service ingress assertion, expressed against the
planned attribute and keyed by service name, so the intended posture of each service is
stated in one place a control reads. Implemented separately from this record so it lands
with its own fixtures in both directions.
**Exit review:** no, but it is the answer to "what would have caught this class".

### W2.14 — The ingress guard refuses an undeclared service, not just a wrong one
**Made:** 2026-08-26 · **Work item:** Wave 2 · **Reversibility:** cheap
**Decision:** `plan_guard.py` gains `INGRESS_POSTURE`, a map from Cloud Run service name
to the ingress value that service is allowed to have, asserted against the planned
attribute. `collector` must be `INGRESS_TRAFFIC_ALL`; `ingestion-worker` must be
`INGRESS_TRAFFIC_INTERNAL_ONLY`.
**The part that does the work is the third case.** A service *absent* from the map is a
violation. Checking only the two known services would leave the next one — `analytics-api`
in F3 — to inherit whatever posture was copied from the block above it, which is the
mechanism W2.13 describes rather than a hypothetical. Refusing an undeclared service makes
adding one a deliberate line stating its exposure.
**Why a map in the guard rather than parsed from architecture §6.1:** the allowlist is
parsed from §7.1 because that section is a table of resource types and reads as data.
§6.1 is a prose table about boundaries, and a parser over it would be a second, weaker
statement of what the prose means. The map is small, it sits beside the assertion that
reads it, and the reasoning is in the comment above it.
**Proven in three directions:** the intended postures pass (`plan-wave2.json`), the worker
opened to the internet fails (`plan-ingress-inverted.json`), and an undeclared third
service fails (`plan-ingress-undeclared.json`). The self-test now runs ten fixtures.
**What this would have caught:** not the 404 — that was a probe path — but the class the
404 investigation exposed. Both services' exposure was correct by luck of authorship and
unasserted by anything.
**Exit review:** no.

### W3.1 — G2 is satisfied by a Wave 1 commit, and the ordering is a fact rather than a claim
**Made:** 2026-08-26 · **Work item:** Wave 3 (#44) · **Reversibility:** cheap
**Checked before anything was written, because the gate is on the apply and not on
the pull request:** both ADR-0006 obligations landed in `f7d6ca3`, Wave 1's transport
commit, two waves before the subscription that makes them binding exists.

*Obligation 1* — `docs/runbooks/dead-letter.md` §1 states, at the point it tells an
operator to inspect, that a dead-lettered message carries `user.id`, `user.email`,
`organization.id`, `session.id` and `workspace.host_paths`; that inspection happens
on a workstation and never in an issue, a pull request or a chat transcript; and
that replay is preferred because a replayed message passes through the redaction
stage. *Obligation 2* — `message_retention_duration = "604800s"` on
`traces-dlq-pull`, with both pressures named in the resource and, as #44's "Done
when" specifically requires, **in the commit message**: exposure window against
evidence window, a part-time maintainer, and why equalling the API default is not
an argument for inheriting it.
**Why this is worth an entry rather than a checkbox:** #44's own framing is that
the obligations are what make ADR-0006's acceptance defensible, and the defence is
worthless if it is written after the exposure. The ordering is checkable by anyone
with the repository — `git log --diff-filter=A -- docs/runbooks/dead-letter.md`
against the commit that adds `google_pubsub_subscription.traces_push` — which is
the property the spec asked for when it said *checkable rather than narrated*.
**Exit review:** yes — it is one of the two phase entry gates.

### W3.2 — The push path is stated once and read twice, so Wave 2's default stops being load-bearing
**Made:** 2026-08-26 · **Work item:** Wave 3 · **Reversibility:** cheap
**Found while writing the subscription:** the worker serves push on
`PLUMBLINE_PUSH_PATH`, defaulted to `/push` in `WorkerOptions`, and Wave 2 left the
variable unset. The subscription needs a path in its endpoint. Writing `/push`
there would have made two places state one route and agree by inspection — the
shape W2.3 refused for the Firestore collection name and W2.2 refused for the OIDC
audience.
**Decision:** a `push_path` local in `cloudrun.tf`, set as the worker's
`PLUMBLINE_PUSH_PATH` and interpolated into the subscription's `push_endpoint`.
**Why it matters more here than for the audience:** an audience mismatch fails
loudly and specifically — every delivery refused by the worker's own validator,
with a log line naming the audience. A path mismatch fails as a **404 from the
worker's mux**, which Pub/Sub counts as a failed delivery like any other, so five
of them dead-letter a message that nothing was ever wrong with. The DLQ then fills
with healthy payloads and the depth alert reports a poison-message incident. The
runbook now says so at the top, because that is where someone reads it at 2am.
**Cost, stated:** the worker takes a new revision in this wave for an environment
variable whose value it already had. The plan is therefore `4 to add, 1 to change`
rather than `4 to add`, and the changed resource is a service the reviewer already
approved once.
**Exit review:** no.

### W3.3 — Five delivery attempts is the floor, and the floor is correct; the retry policy is what needed choosing
**Made:** 2026-08-26 · **Work item:** Wave 3 · **Reversibility:** cheap
**Decision:** `max_delivery_attempts = 5`, which is simultaneously the spec's
figure, the API minimum and the API default — set explicitly on #44's reasoning
that a number nobody argued for is one a future change has nothing to argue
against.
**The argument for the floor:** the worker's failure modes divide cleanly. A
payload that fails to deserialize fails identically on the hundredth attempt, so
extra attempts buy no recovery — they buy latency to the DLQ, CPU on a message that
will not succeed, and more copies of unredacted personal data in flight, which
ADR-0006 counts as a cost. What the five *do* cover is the transient case: a cold
start, a redeploy, an instance evicted mid-request.
**What actually needed a decision was the retry policy, and leaving it unset would
have been the defect.** Pub/Sub's default is immediate redelivery, and immediate is
wrong against `min_instance_count = 0`: a cold start that refuses three deliveries
while the container boots would spend most of a five-attempt budget before the
worker had answered once, and dead-letter a healthy message for arriving early.
`minimum_backoff = 10s` is longer than a warm instance needs and shorter than a
cold one takes; `maximum_backoff = 600s` stops a genuine outage retrying tightly
for a week.
**Verified how:** Google's dead-letter documentation read at wave time — default 5,
minimum 5, maximum 100, and forwarding described as best-effort, so the number is
approximate by the platform's own account.
**Exit review:** no.

### W3.4 — No token-creator grant is written, because two already carry it and the wider one is Google's
**Made:** 2026-08-26 · **Work item:** Wave 3 · **Reversibility:** cheap
**The obvious resource, not written.** An OIDC push subscription needs its minting
principal — Google's Pub/Sub service agent — to hold `iam.serviceAccounts.getOpenIdToken`
on `pubsub-push@`, or `roles/iam.serviceAccountTokenCreator` on that account or an
ancestor. The obvious move is a `google_service_account_iam_member` saying so.
**Two grants already carry it, and one cannot be removed.** `gcloud iam roles
describe roles/pubsub.serviceAgent` lists `iam.serviceAccounts.getOpenIdToken`
among ten permissions; that role is Google's automatic grant to the agent and is a
precondition of Pub/Sub working at all. Separately, `killswitch.tf` grants
project-scoped `roles/iam.serviceAccountTokenCreator` to the same principal for
Eventarc's invocation of the kill-switch function.
**Decision:** write the fact where the dependency is — a comment at the
subscription — and not a third resource. A narrow grant here cannot make the
subscription work in any case where it does not already, because the widest of the
three is not ours to withdraw. It would look like the control without being it,
which is precisely the argument W2.5 used to decline a decorative Firestore IAM
condition: a grant that narrows nothing teaches the next reader that grants here
are decorative.
**Alternatives:** add it anyway for locality — defensible, and it would survive a
future narrowing of the kill-switch's grant; rejected because the surviving grant
would still be Google's, so the robustness is imaginary. A comment naming both
existing grants gives a reader the same locality without the false statement.
**Raised, not resolved:** `google_project_iam_member.pubsub_token_creator` in
`killswitch.tf` may itself be redundant for the same reason — `roles/pubsub.serviceAgent`
already carries the permission its comment says it grants. Narrowing or removing it
touches the kill-switch's own configuration, needs its own re-verification of
Eventarc, and is outside this spec. Filed rather than taken.
**Exit review:** no.

### W3.5 — Two dead-letter grants, both of which fail silently when absent
**Made:** 2026-08-26 · **Work item:** Wave 3 · **Reversibility:** cheap
**Decision:** the Pub/Sub service agent gets `roles/pubsub.publisher` on
`traces-dlq` and `roles/pubsub.subscriber` on `traces-push`, both at resource
scope. `google_pubsub_subscription_iam_member` is not in architecture §7.1, so it
arrives as a spec change with a changelog entry (architecture v0.11), per D6.
**Verified how, and why verification was not optional:** Google's dead-letter
documentation, read at wave time — the agent publishes the message to the
dead-letter topic and acknowledges the original on the subscription, and it holds
neither right by default. Confirmed against the project as well: `traces-dlq` had
an empty IAM policy, and `roles/pubsub.serviceAgent` — checked with `gcloud iam
roles describe` rather than assumed to be broad — carries neither
`pubsub.topics.publish` nor `pubsub.subscriptions.consume`. So unlike W3.4's grant,
these two are genuinely missing.
**The failure mode is what makes them worth a decision entry.** Omitting either
applies cleanly. The subscription is created, the plan is clean, the drift check
passes, and dead-lettering simply never happens: Pub/Sub retries the message past
its attempt limit and it stays in the backlog. The one path in this design that is
supposed to catch everything else would be the path that was never exercised, and
the DLQ depth alert — the project's only notification channel (W2.9) — would report
nothing, because nothing arrives.
**Ordered, not just present:** `depends_on` puts the publisher grant before the
subscription. Terraform has no data dependency between them, so without it the two
race, and losing the race produces exactly the silent state above rather than an
error. W2.11 is the precedent — a real dependency left unexpressed is decided by
provider scheduling.
**Exit review:** no.

### W3.6 — The public-invoker guard, and the fixture that made it look broken
**Made:** 2026-08-26 · **Work item:** Wave 3 · **Reversibility:** cheap
**Decision:** `plan_guard.py` gains `PUBLIC_INVOKER_ALLOWED = {"collector"}` and
refuses `allUsers` or `allAuthenticatedUsers` holding `roles/run.invoker` on any
other Cloud Run service. This is DoD 7's *"the push service account is the sole
invoker"* expressed as a control: that claim is false the moment anyone else holds
the role, whatever the push binding says, and Cloud Run has no separate
"unauthenticated" switch — the member **is** the setting. The worker's protection is
therefore an *absence*, which is the one thing a configuration review reads past,
because nothing is on the screen to notice.
**What the new check immediately reported: a violation in `plan-wave2.json`, a
fixture that is supposed to pass.** The temptation is to adjust the check until the
fixture is quiet. The question is whether Terraform populates `after.name` on an
invoker binding, and it is answerable in one command rather than by argument — a
real authenticated plan of this wave renders
`google_cloud_run_v2_service_iam_member.worker_push_invoker` with
`name = "ingestion-worker"`. So the fixture was wrong: hand-written, carrying only
the fields the checks of the day happened to read. It is now completed from real
plan output, along with the two other IAM members that were missing their `member`.
**The reusable half.** A fixture that omits what no current check reads is a trap
for the next check, and it fails in the direction that costs most — the new check
looks broken and the reflex is to weaken it. This is the same lesson as W2.8 in a
new place: evidence gathered for one question does not automatically answer the
next one.
**Third case, on W2.14's pattern:** an invoker binding whose service or member the
guard cannot read is a **violation**, not a skip. Both are known at plan time here,
so this costs nothing today; what it buys is that the guard can never report clean
over a binding it did not understand. Proven in three directions —
`plan-wave3.json` passes with the push identity on the worker and `allUsers` on the
collector, `plan-worker-public.json` fails with the worker opened up *while its
ingress stays internal and the ingress guard passes*, and
`plan-invoker-unresolved.json` fails on an unreadable binding. The self-test now
runs thirteen fixtures.
**Exit review:** no.

### W3.7 — §6.1's ingress row named a wider setting than the one deployed
**Made:** 2026-08-26 · **Work item:** Wave 3 · **Reversibility:** cheap
**Observation, from writing the row's other half rather than from review:** §6.1's
"Pub/Sub → Worker" row said the worker's ingress was the
`internal-and-cloud-load-balancing` equivalent. Wave 2 deployed
`INGRESS_TRAFFIC_INTERNAL_ONLY`, which is narrower, and the plan guard has asserted
that exact value since W2.14. The row was written before the worker existed and the
two had never been read against each other.
**Decision:** correct the document to what is built, on W2.5's rule. The direction
is the comfortable one this time — reality is *tighter* than the document, not
wider — and it is still worth correcting, because a reader checking the deployment
against §6.1 finds a different value and cannot tell which is authoritative. The
row now also names the load-balancer allowance as unnecessary: verified at wave
time, a push subscription in the same project targeting the default `run.app` URL
counts as internal traffic, so nothing needs the wider setting.
**Also folded in:** the row now names both checks rather than one. Wave 3 is where
the sole-invoker half stops being a plan, and the worker's own audience and
issuer-email validation (W2.2) is the second, independent one. Either alone would
be defensible; both is what makes a mistake in one a failed delivery rather than an
open write path to `spans`.
**Exit review:** yes — it is a boundary the document described differently from the
deployment for four days.

### W3.8 — Wave 3 applied first time, which is the first time this phase that a permission did not announce itself at apply
**Made:** 2026-08-26 · **Work item:** Wave 3 · **Reversibility:** one-way (the apply)
**Result:** [run 32969025343](https://github.com/arslan-kursad/plumbline/actions/runs/32969025343)
— `Apply complete! Resources: 4 added, 1 changed, 0 destroyed`, fingerprint matched
the approved plan, post-apply plan `No changes`. Verified at the API rather than
from the plan: the subscription carries the endpoint, audience, service account,
dead-letter topic, five attempts, 60s deadline, seven-day retention, no expiration
and the 10s/600s backoff it was configured with; the worker's **only** invoker is
`pubsub-push@`; the service agent holds publisher on `traces-dlq` and subscriber on
`traces-push`; the worker runs revision `00002-j29` with `PLUMBLINE_PUSH_PATH=/push`
and the audience and service-account pair matching the subscription exactly.
**One dispatch, no split by scope, no targeting** — the first wave since W0.3 for
which that was true. None of the kill-switch's four human-applied resources (A2.11)
appear in a Wave 3 plan, so the boundary that forced Wave 1.5 into two applies did
not touch this one.
**The streak ended, and the reason is not luck.** W2.11 counted five permission
defects in this phase, every one surfacing at apply and none at review. This wave
needed four new IAM operations and got none of them wrong, because the roles were
already in place from the waves that discovered they were needed: W2.7's per-service-account
`actAs` deliberately included `pubsub_push` for a subscription that did not exist
yet, and W2.11's widening to `roles/pubsub.admin` — made for a topic binding —
covers subscription creation and subscription IAM as well. **Least privilege granted
one wave early is what a clean apply looks like from the inside.** That is worth
recording precisely because five-for-five was starting to read as a law rather than
as a symptom of granting permissions at the moment they are first needed.
**Two claims this apply does not support, stated because the phase has already paid
for glossing one:**

*The OIDC path is wired, not proven.* W2.2 recorded that no test can mint a
genuine Google-signed token, and named Wave 3's first real push delivery as the
test. Nothing has published to `traces`, so no delivery has been attempted and the
worker's validator has still never seen a real token. The subscription existing is
not the evidence; a delivery is.

*No test message was published to close that gap, and the decision is deliberate.*
Publishing to `traces` would answer the question in one message — the worker's logs
separate an auth rejection from a deserialization failure cleanly, even though both
end in the DLQ after five attempts. It was not done for three reasons, in order of
weight: a published Pub/Sub message cannot be unpublished, which this log's
preamble names as one of the phase's few genuinely one-way acts; publishing outside
the gated path is the process violation spec §2 defines, and Lane A's authority
does not extend to cloud mutations; and a message landing in the DLQ now would
pre-empt Wave 4's triage rehearsal, which is specified against *its* poison fixture
and would otherwise begin by explaining an artefact from a previous wave.
**So the honest status of DoD 7 is split**, and the wave issue should say so rather
than tick it: the stub is mechanically gone and the sole-invoker binding is live and
verified, while "push authentication is real" is proven for the code path (W2.2's
tests, Gate G) and unproven end-to-end until Wave 4's first delivery.
**Exit review:** yes — a clean apply is worth as much attention as a failed one when
five preceding ones failed, and the reason it was clean is a finding about method.
