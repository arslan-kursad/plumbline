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
