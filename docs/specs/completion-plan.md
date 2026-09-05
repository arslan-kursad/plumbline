# Completion plan — from the 2026-09-05 surface to F5

**Version:** 0.1 · **Status:** Proposed · **Date:** 2026-09-05 · **Lane:** A, under delegation
**Repo:** `main @ b7b3cf9` · **Live reads:** project `plumbline-19458`, GitHub API, both agent
repositories at their pinned commits (§8)
**Companions:** [`freeze-a-decision-package.md`](../proposals/freeze-a-decision-package.md)
(proposed values for every Freeze A placeholder, not applied) and
[`emitter-instrumentation-contract.md`](emitter-instrumentation-contract.md) (what each of
the three emitters must put on the wire)

> **Delegation, recorded.** On 2026-09-05 the maintainer asked for a full re-read of every
> phase, a task list with solutions down to the finest point that can block, and delegated
> the decisions to Lane A, asking only that anything genuinely requiring the maintainer be
> noted. Every decision below (§5) therefore carries its alternative and its residual
> uncertainty, and §6 is the list of things only the maintainer can do. Two boundaries are
> not delegable and are not crossed here: `docs/eval-plan.md` is edited by a human only, and
> `.claude/settings.json` is edited by a human only. For both, diffs are prepared and not
> applied.

> **Nothing in this plan is a measurement.** Every status claim names where and when it was
> read (F2 spec §7.2 CN4). A row copied from here into a closing note is the defect this
> project has now recorded five times. Re-read before citing.

---

## 1. State on 2026-09-05, re-derived

### 1.1 Per phase

| Phase | Record says | Measured 2026-09-05 | Open |
|---|---|---|---|
| **F0** | complete; criterion 11 (the period bill) deferred to `#17` | milestone `#2`: 1 open (`#17`); Verification A *inconclusive by construction* (`#74`) | `#17` waits on a Billing Reports read for a closed period |
| **F1** | complete, 2026-08-21 | milestone `#1`: 1 open (`#10`); the capture *procedure* is delivered, the capture is not | `#10` — one interactive session by the maintainer |
| **F2** | closure note is a *draft skeleton*; 9 DoD items satisfied, DoD 1 at 3/5, DoD 8–10 placeholders, DoD 13 open by design | milestone `#3`: 2 open (`#109`, `#18`). Cloud: three Cloud Run services (`collector`, `ingestion-worker`, `billing-killswitch`), `min 0 / max 2`, `us-central1`; `plumbline.spans` 52 rows, 52 synthetic, 0 real, last ingest `2026-09-01T04:19:43Z`, 29,745 bytes; both views three-column; `require_partition_filter` true; DLQ alert policy enabled; images tagged at `b7b3cf9` | DoD 8, 9, 10 (billing period); DoD 1 facts 4–5 (one billing read); the note's placeholders; `#109`, `#18` |
| **F3** | no spec, no build; entry work done (10 tasks, 9 delivered); prerequisite work done; unblock dispatch 12/12 delivered by `#185`–`#187` | milestone `#4`: 7 open. `eval-plan.md` is v0.1, `DRAFT — NOT FROZEN`, and still says *"F1 entry gate"*; rows 4.5–4.7 edited 2026-09-02. **Freeze A is not recorded as concluded or as deferred.** 0 of 3 emitters emit into the pipeline; 0 of 4 manifests read `captured`. `#177` disposition **(a) + (c)** recorded 2026-09-05. ADR-0009 and ADR-0010 `Proposed` | everything in §3 |
| **F4** | not started | `analytics/Plumbline.Analytics/Program.cs` is the .NET web template (a weather-forecast endpoint); no Scheduler job, no SPA, no Looker, no load generator; milestone `#5`: 1 open (`#42`) | all of it |
| **F5** | not started | `README.md` says *"Next is F2"*; `#7` (delivered early as F3E-04) and `#9` open; milestone `#6`: 1 open | all of it |

### 1.2 What runs, read locally on this host

| Check | Result |
|---|---|
| `scripts/ci/invariant-gates.sh` | nine assertions, all pass |
| `scripts/ci/xref-check.sh` | 13 findings under `docs/` — the recorded baseline, unchanged |
| `scripts/ci/partition-filter-check.sh` | 11 query sites, every one constrains `start_time`, is a view, or declares its absence |
| `go vet` + `go test -race ./...` in `collector/` | all packages ok |
| `dotnet test worker/Plumbline.Worker.sln` | 76 + 38 passed, 0 failed |
| CI on `main` | last eight runs green; latest `33958010711` at `b7b3cf9` |

The local host cannot run containers (prerequisite directive R-F, re-verified: `docker`
binary, no daemon), so `make e2e` is CI-only, as before.

### 1.3 The two agent repositories, read at their pinned commits

Both are checked out on this host, at exactly the commits the dossiers pinned:

| Agent | Local path | HEAD | OTel instrumentation |
|---|---|---|---|
| Anomaly Adjudicator (`aiqs-agent`) | `~/Anomally Adjudication` | `0779c04` (the C-1 pin) | none — `langfuse` pulls OpenTelemetry transitively and nothing imports it |
| Apartment Triage (`apartment-triage`) | `~/Apartman Triage AI/dev/apartment-triage` | `15c1d6e` (the C-2 pin) | none |

Both READMEs matter for sizing: the Adjudicator runs on *"a 2-core, CUDA-free, MPS-free
Intel Mac"*, which is also this host, and that fact reaches P7 (§5 CP-11). The Triage
agent *"runs in production for a small real building, processing live resident messages"*
on Fly.io, which means real traffic exists for SC-2 and that its messages are personal data
the trace must never carry unredacted (§5 CP-5).

---

## 2. The calendar, fixed dates only

| Date | Event | Source |
|---|---|---|
| 2026-09-05 | this plan; **29 days to C7** | machine clock |
| 2026-09-12 | ADR-0010 D6-1 trigger: is the Adjudicator emitting E1's inputs? | ADR-0010 §2 |
| 2026-09-21 (Mon) | C1 — account upgrade | F2 directive Decision 3, W3.28 |
| 2026-10-01 | ADR-0009 D6 — campaign teardown proven | ADR-0009 §2 |
| 2026-10-04 | **C7** — F3 exit + three emitters ingest-ready | F2 directive F2C-19 |
| 2026-10-05 | trial credit ends; Verification C window opens; `#138`'s ADR must be Accepted before this date | `#74`, `#138` |
| 2026-10-19 | earliest window close (14 days) | F2 spec §7.1 C3 |
| 2026-11-01 → 2026-12-31 | SC-4b: two consecutive full calendar months after the credit | `eval-plan.md` row 4.5 |
| 2027-01 | earliest date the cost claim is publishable | follows from the row above |

**One consequence stated once.** SC-4b needs two *full* calendar months after 2026-10-05, so
the earliest pair is November and December. The cost blog post cannot be written before
January 2027 whatever else happens. F5 is therefore split in §4: everything that does not
depend on SC-4b ships in October–November; the cost post waits.

---

## 3. Blockers, to the finest point that stops work

Each row names the *single* fact that, if it changed, would unblock the item — not the
category of the problem.

| # | Blocker | The finest point | Unblocked by |
|---|---|---|---|
| B1 | **Freeze A has not concluded**, and the record cannot say whether it was deferred (prerequisite directive §6) | Nobody has written P1's value into `eval-plan.md`. Every input now exists: C-1 and C-2 dossiers filled, P3 table, P5 inputs, items 2–6 diffs, P11 measured | the decision package + one dated session (W1-1); §5 CP-1 |
| B2 | **Both agents emit nothing**, and E1's four conjuncts are trace-computed | Neither repository declares an OpenTelemetry dependency; and even once spans exist, no attribute key carries the agent's output (`e1-predicate-readout.md`) | the instrumentation contract (§5 CP-2–CP-4); W1-3, W1-4 |
| B3 | Claude Code emits but is not captured | Personal data in a public repository is the block; the redaction machinery exists; the missing act is a ten-minute interactive session | W1-6 |
| B4 | Lane A cannot read billing | `Bash(gcloud billing:*)` denies `accounts list`; four documents wait on one `list` call | W0-2 (apply the U-13 rewrite) |
| B5 | The 200 TRY ceiling is configured, not proven | No three-step live-fire has run against `200.00` (ADR-0004 Amendment 5 Verification) | W1-8 |
| B6 | ADR-0008 undecided since 2026-08-26 | Its status; both emitters' exporter protocol setting depends on it | §5 CP-6; W0-7 |
| B7 | F3's budget is wrong and no corrected number exists | `project-brief.md`:59 says ~20 h against a scope that now includes two instrumentation projects and three captures | §4.7 carries an estimate; ADR-0010 D6-2 is the cut line |
| B8 | F2 cannot close | DoD 10 needs the August Billing Report read by a human; DoD 8 and 9 are closeable today from Cloud Logging and `kill-switch.md` §4a | W0-3, W0-5, W0-6 |
| B9 | `#175` — nothing asserts the table is partitioned | `bq_schema.py` compares columns only | W0-8 |
| B10 | The F3 Unblock Directive v1.0 is not in the repository | D2, D3 and D4 of that directive are unknown to the record; D1, D5, D6 are recorded elsewhere | §6 item 14 |
| B11 | The eval engine has no permitted way to read BigQuery yet | Gate A forbids `Google.Cloud.BigQuery.V2`; the Storage Read API cannot read views | §5 CP-8 |
| B12 | T1's host does not exist | Ollama is not installed on this host and the host has two cores | §5 CP-11; package P7 |
| B13 | The experiment's baseline configuration would never call the VLM | At the Adjudicator's default `target_prevalence = 0.02`, all 160 measured items are `pass` (C-1 dossier A4): no escalation, no VLM call, so D2 — which ablates the VLM prompt — would change nothing | package P1 fixes B0's run configuration |
| B14 | The gate's data-plane cost has no place to be measured | The collector exposes no latency histogram; SC-4 row 4.1 names one | W3-7 uses Cloud Monitoring's request-latency and memory metrics instead, and says so |

---

## 4. Task list, by wave

Lanes: **A** Lane A (this executor, self-merge after green CI) · **B** armed apply via
`deploy.yml` with the `gcp-production` approval · **C** human-only · **X** outside this
repository (a Claude Code session opened by the maintainer in the agent's repository; the
lane is decided by the strongest permission the work needs, D5).

Estimates are hours of work, not calendar days, and are the first numbers anyone has
written for this scope; they are recorded so they can be wrong in public.

### 4.1 Wave 0 — 2026-09-05 → 2026-09-08 · land the plan, unblock the reads

| ID | Task | Lane | Precondition | Done when | h |
|---|---|---|---|---|---|
| W0-1 | Land this plan, the decision package and the instrumentation contract | A | — | merged; xref baseline re-derived, not carried | 1 |
| W0-2 | Apply the deny-list rewrite ([`lane-a-denylist-rewrite.md`](../proposals/lane-a-denylist-rewrite.md)) | **C** | — | its six verification steps pass, including `gcloud billing accounts list` succeeding from Lane A | 0.2 |
| W0-3 | One billing console session: (a) cost by `project_id` **and** credit type (ADR-0009 §3.1); (b) August Billing Reports, credit filters cleared (DoD 10, `#17`); (c) billing attached and the `zero_spend` budget's `creditTypesTreatment` (DoD 1 facts 4–5) | **C** | — | raw output and exact command lines archived as `docs/evidence/billing-readout-2026-09.md`; `#74` §1.4's two readings settled by it | 0.5 |
| W0-4 | Schedule Freeze A session 2 — recommended **Mon 2026-09-08, 3 h** | **C** | — | date on the calendar and in `#36` | 0.1 |
| W0-5 | DoD 8: archive a post-first-delivery budget notification's raw fields (`costAmount`, currency, timestamp) from the kill-switch function's Cloud Logging entries | A | — | `docs/evidence/f2-dod8-notification.md`; a notification dated after `2026-09-01T05:28Z` (the drill) reading `0.00` | 0.5 |
| W0-6 | DoD 9: the credit-lag procedure's data points (2026-08-22 false positives, 2026-08-25 re-attach) cited from `kill-switch.md` §4a into the completion note row | A | — | row filled with dates, no new measurement claimed | 0.3 |
| W0-7 | ADR-0008 Amendment 1 drafted: HTTP-only cloud ingest through F4, D1 verification deferred to F5 (§5 CP-6); `architecture.md` §2.1 gains the one-line note `#68` asked for | A drafts · **C** accepts | — | amendment merged as `Proposed`; the flip is the maintainer's | 1 |
| W0-8 | `#175`: extend `scripts/ci/bq_schema.py` to compare partitioning field, clustering fields and `require_partition_filter` between `001_spans_table.sql` and `bigquery.tf` | A | — | the T1-02 experiment (DDL stripped of its three clauses) now fails the schema guard; the self-test carries that case and a passing one | 2 |
| W0-9 | Milestone due dates: F2 `2026-10-01`, F3 `2026-10-04`, F4 `2026-10-31`, F5 `2027-01-15` | A | W0-1 | set through the API and read back | 0.1 |

### 4.2 Wave 1 — 2026-09-08 → 2026-09-12 · Freeze A, instrumentation, the D6-1 date

| ID | Task | Lane | Precondition | Done when | h |
|---|---|---|---|---|---|
| W1-1 | **Freeze A session 2.** Transcribe the decision package into `eval-plan.md` v0.2; fill the eight rubric anchors; apply items 2–6; tag `eval-plan-freeze-a`; record the §5 choice | **C** | W0-4 | tag exists; header reads v0.2 and the freeze date; no `(P5 — unfilled)` marker remains | 3 |
| W1-2 | Write `docs/specs/F3-eval-engine.md` from the freeze and §4.3–4.4 here, the same day the tag exists | A | W1-1 | spec merged; every task in it cites a frozen value or an issue | 3 |
| W1-3 | Instrument the Adjudicator per the contract §2 | **X** (`aiqs-agent`) | contract merged | contract §5 acceptance (a)–(d) pass locally against `scripts/capture/capture.sh langgraph-python` | 6 |
| W1-4 | Instrument the Triage agent per the contract §3 | **X** (`apartment-triage`) | contract merged | same, for `dotnet-agent` | 6 |
| W1-5 | Issue three API keys (`api-keys.md` §2): `adjudicator`, `triage`, `claude-code` | **C** | — | three `api_keys` documents, plaintext held by the maintainer only | 0.3 |
| W1-6 | **Claude Code capture** (`claude-code-capture.md`, ~10 min); then A promotes it: redact, fixture, manifest `captured`, `#10` closed | **C** then A | — | `capture_report.py` names a terminal state; manifest validator admits the fixture | 1.5 |
| W1-7 | **D6-1 evaluation, 2026-09-12**, written down either way: is the Adjudicator emitting the E1 inputs (contract §2.4 attribute set) through the deployed collector? | A | W1-3, W1-5 | `docs/evidence/d6-1-evaluation-2026-09-12.md`; if no, ADR-0010 D6-2 is F3's exit criterion from this date | 0.5 |
| W1-8 | **Kill-switch three-step synthetic live-fire at `200.00`** (`kill-switch.md` §4a procedure: 199.99 → WARN, 200.00 → detach, re-attach, two clean cycles) | **C** | W0-3(c) | archived in `kill-switch.md` §4a with logs and API reads; ADR-0009 §3.3 satisfied; ADR-0004 Amendment 5 Verification satisfied for the mechanism | 1 |

### 4.3 Wave 2 — 2026-09-15 → 2026-09-19 · captures, mapping rework, the engine core

| ID | Task | Lane | Precondition | Done when | h |
|---|---|---|---|---|---|
| W2-1 | Two agent captures (`agent-capture.md`): one real interaction each, receiver outside the repo | **C** drives · A promotes | W1-3, W1-4 | two manifests read `provenance: captured`; with W1-6, SC-1 row 1.2 is **3 of 3** | 1.5 |
| W2-2 | Mapping rework from real bytes (`#42`): `langgraph-python.yaml` detection carries the three scope names the contract emits; `dotnet-agent.yaml` detection carries `ApartmentTriage.Agents`; fixtures regenerated from the captures; every golden diff recorded as a finding, not a merge conflict | A | W2-1 | golden tests green on captured fixtures; `SemconvRegistryTests` green; the diff table in `docs/evidence/f4-42-fixture-revalidation.md` | 4 |
| W2-3 | Redaction rule files `normalization/redaction/v1/langgraph-python.yaml` and `dotnet-agent.yaml`, written from `redact.py`'s refusal list on the first capture | A | W2-1 | `redact.py` accepts both captures; each key carries its `why` | 1.5 |
| W2-4 | `eval_results`: DDL `analytics/sql/004_eval_results.sql` with the 18 fields `eval-plan.md` §9 requires, partitioned on `run_ts`, `require_partition_filter`; Terraform; schema guard extended to a second table; **Wave F3-1 apply** | A + **B** | W1-2 | table exists in the cloud, read from the API; plan clean afterwards | 3 |
| W2-5 | Eval engine core in `analytics/`: the BigQuery read helper (§5 CP-8), R1–R4 and the frozen R5 set, E1 and E3, McNemar exact, Holm correction, the `gate` CLI with `--mode pr` (no LLM, `dev` split) and `--mode experiment`; results written through the Storage Write API to `eval_results` | A | W1-2, W2-4 | every check ships with one case it must fail and one it must pass, both in the test suite; a CI job runs `--mode pr` against a fixture-backed corpus | 16 |
| W2-6 | Replay harness `scripts/e2e/replay.py`: takes a capture directory, stamps `synthetic=true`, `plumbline.e2e_run_id`, `plumbline.variant_id`, `plumbline.dataset_id` as resource attributes at send time, posts to the deployed collector under the arming rule of `cloud.py` | A | W2-1 | a replayed capture lands in `spans_deduped` scoped to its run id; the arming guard refuses without both variables | 4 |
| W2-7 | **F3E-01c (`#184`)** as a read: after the first cloud replay of a captured fixture, read `attributes` back and compare to the fixture's expected JSON (S4); compare column-name matching against the emulator run (S5) | A | W2-6 | `docs/evidence/f3e-01c-round-trip.md`, each surface with direction or with the artefacts | 1 |
| W2-8 | Judges: T1 (Ollama) and T2 (Gemini) runners behind one interface; three repeats; fixed presentation template from the rubric; `judge_incomplete` set when T2's assigned set cannot complete; E2 with Wilcoxon | A | W1-1 | quota exhaustion produces `judge_incomplete=true` and E2 `UNKNOWN` in a test; never a silent pass | 6 |

### 4.4 Wave 3 — 2026-09-22 → 2026-09-30 · upgrade, campaign, Freeze B, the experiment

| ID | Task | Lane | Precondition | Done when | h |
|---|---|---|---|---|---|
| W3-1 | **C1 — account upgrade, 2026-09-21.** Refuse any credit extension or replacement (ADR-0009 §7.4) | **C** | W1-8 | upgrade recorded with date; credit remaining unchanged | 0.3 |
| W3-2 | ADR-0009 preconditions: ADR-0009 §3.2 resource snapshot (`scripts/state-readout.sh`, archived); ADR-0009 §3.4 storage headroom (`bq show` bytes; 29,745 today); ADR-0009 §3.1 and ADR-0009 §3.3 from W0-3 and W1-8 | A | W0-3, W1-8 | four readings archived and dated before any campaign traffic | 1 |
| W3-3 | **Calibration:** `k = 5` runs of B0 over the `gate` split (P3: 292 items) with content capture on, captured to files, replayed to the cloud with run ids `cal-1`…`cal-5` | **C** runs the agent · A replays and reads | W2-6, package P1's B0 configuration | five run ids present in `spans_deduped`, each `292 × (spans per item)` rows, `unflagged = 0` | 4 |
| W3-4 | **Freeze B:** `tools/calibrate.py` → `σ0`, `μ0`, `δ_min`, `ε_min`; `tools/mde.py` → achieved MDE; `docs/eval-plan.constants.yaml`; tag `eval-plan-freeze-b` **before any variant run** | A | W3-3 | tag exists; constants file is generated, not edited; `plan_sha256` recorded | 4 |
| W3-5 | Variant runs, captured and replayed: B0′ × 5 (negative control), D6 × 5 (positive control), D2 × 1 minimum (primary; × 5 if the maintainer's model spend allows) | **C** runs · A replays | W3-4 | every run carries `plan_sha256`, `variant_id`, `agent_commit`; the D2 branch is a one-file diff on `prompt.py` | 4 |
| W3-6 | **Experiment-mode gate runs:** SC-3 rows 3.1–3.4; both a firing and a non-firing observed and recorded (ADR-0010 §6.3) | A | W3-5 | `docs/evidence/f3-sc3-experiment.md`; verdicts in `eval_results`; a negative finding is published on the same terms as a positive one (`eval-plan.md` §11) | 3 |
| W3-7 | **SC-4a load run (L1):** replay the calibration corpus at a fixed rate for ten minutes; read p95/p99 from Cloud Monitoring's Cloud Run request-latency metric and container memory p99; count 429/5xx | A | W3-2 | rows 4.1–4.3 filled from API reads, with the metric names and the window; L1's parameters written into the constants file (P10) | 4 |
| W3-8 | F2 completion note: sixteen placeholders filled by measurement; `#109` closed by Amendment 8 to the directive naming the invocation split; `#18` closed with W0-5; **F2 milestone closed** | A | W0-3, W0-5, W0-6 | tally reads 12 of 13 with 13 open by design; CN5 full run dispatched against a tagged SHA and recorded | 3 |
| W3-9 | `#138` ADR drafted: SC-2's definition ratified as row 2.1 plus the staffing sentence; SC-4b's basis recorded as already applied by `#162` | A drafts · **C** accepts before 2026-10-05 | W1-1 | ADR Accepted; index row in `architecture.md` §10 | 2 |

### 4.5 Wave 4 — 2026-10-01 → 2026-10-04 · teardown proof, F3 exit, C7

| ID | Task | Lane | Precondition | Done when | h |
|---|---|---|---|---|---|
| W4-1 | Teardown: delete the L1 load run's rows by run id (a partition-filtered DML statement); keep the calibration and variant corpus rows (§5 CP-13) | A | W3-7 | rows gone by query; storage re-read | 0.5 |
| W4-2 | Residue-zero by identity (ADR-0009 D5): post-campaign `state-readout.sh` equals the §3.2 snapshot plus the declared additions (`eval_results`, the corpus rows) | A | W4-1 | diff is exactly the declared set, archived | 1 |
| W4-3 | **F3 exit review:** DoD per the experiment if W3-6 fired on D2, else per ADR-0010 D6-2; F3 completion note; C7 asserted per §5 CP-10 with the three captured fixtures named; `README.md` phase line updated | A · **C** reviews | W3-6 | note merged; milestone F3 closed on or before 2026-10-04 | 3 |
| W4-4 | [`pre-credit-end-reset.md`](../runbooks/pre-credit-end-reset.md) executed with values | A reads · **C** for any mutation | W4-2 | every row carries a value read on the day | 0.5 |

### 4.6 The window — 2026-10-05 → 2026-10-19 · Verification C, F4 ingest, F4 build

| ID | Task | Lane | Done when | h |
|---|---|---|---|---|
| V-1 | **DoD 13b:** three-step live-fire after the upgrade and after the credit ended — the first firing against a real charge | **C** | archived in `kill-switch.md` §4a with the API reads | 1 |
| V-2 | Daily: burn-line check (`architecture.md` §7), `state-readout.sh`, and **SC-2 staffing** — ≥ 1 real span per source per UTC day: an Adjudicator run, a Triage message, a Claude Code session with export on | **C** + A | fourteen daily readouts archived; row 2.1's table filled | 7 |
| V-3 | F4 build: `analytics-api` on Cloud Run (its first plan is red by design — `architecture.md` §7.1; declare ingress and invoker posture in the same change), Cloud Scheduler nightly, static JSON export + SPA on Pages (OQ-5 credential decided first), Looker Studio on the views, the uptime-check path decision | A + **B** + **C** | demo link works; nightly job runs on the schedule | 20 |
| V-4 | Human reference labels: 50-item stratified subset (package P6), labelled blind before any judge output; second pass ≥ 7 days later (A4) | **C** | two label files, dated | 3 |
| V-5 | Judge-tier agreement study A1–A4; routing decision applied per `eval-plan.md` §8.4 | A | numbers in `docs/evidence/`, the routing rule's outcome stated | 3 |

### 4.7 After the window

| ID | Task | Lane | h |
|---|---|---|---|
| P-1 | F4 exit: SC-2 verdict with 2.2–2.4 recorded; SC-4a documented; F4 completion note | A · **C** | 3 |
| P-2 | F5 part 1 (November): README with architecture, threat and cost model; blog 1 (semconv pinning) and blog 3 (judge agreement) drafts; `#9` | A · **C** publishes | 8 |
| P-3 | F5 part 2 (January 2027): SC-4b two-month reading; the cost post; the TR/EN posts | **C** | 4 |

**Total through F3 exit (Waves 0–4): ≈ 95 h, of which ≈ 12 h are maintainer hours.**
Against 29 calendar days, part-time, that is the whole risk of this plan and it is stated
rather than smoothed: if the engine core (W2-5) slips, the cut line is ADR-0010 D6-2 —
the gate mechanism proven against the replay corpus, the subject experiment dated to F4 —
and nothing else in Waves 0–2 is cut before that.

---

## 5. Decisions of record

Each carries the alternative not taken and the residual uncertainty. Class 3 items are
proposed, not applied, and say so.

**CP-1 — Freeze A completes in one dated second session from a transcription package.**
The §5 choice of [`freeze-a-prep.md`](freeze-a-prep.md) is recorded now as **(a)**, with the
date proposed in W0-4. The package exists so the session transcribes rather than derives.
*Alternative:* (b), a split-freeze ADR now. Rejected because every gate-critical placeholder
has a proposed value and the split would cost an ADR to buy time the session does not need.
*Residual:* if P5's anchors are not accepted in the session, (b) becomes necessary and the
session records it at T+150 as the brief requires.

**CP-2 — Instrumentation starts before Freeze A concludes.** The entry directive's §2
excluded F3 components before the freeze; this plan authors the contract now, against the
C-1 and C-2 dossiers' measured field lists. Under the delegation of 2026-09-05 this is a
recorded departure, not a covert start: the contract's attribute set is the dossiers'
field set, which is also what P1 and P2 freeze.
*Alternative:* wait for the tag. Rejected because D6-1 falls on 2026-09-12 and waiting makes
it fire by inaction.
*Residual:* if the session changes P1's field set, the contract's attribute list changes
with it — a mapping edit, not a redesign.

**CP-3 — Adjudicator instrumentation uses the OpenInference instrumentors plus one
project-owned span.** `openinference-instrumentation-langchain` covers the LangGraph graph
and emits the `openinference.instrumentation.langchain` scope the existing mapping already
keys on; `openinference-instrumentation-anthropic` covers the VLM call; one explicit span
from an `aiqs.adjudicator` tracer wraps the request and carries the output attributes
(contract §2).
*Alternative:* a hand-rolled tracer only. Rejected: it would abandon the mapping the
constructed fixture was written against and lose the LLM span's token counts for free.
*Residual:* whether LangGraph 1.2 under this instrumentor emits the scope name and the
`openinference.span.kind` values the mapping expects is measured at the first capture; a
mismatch is `#42`'s finding and is recorded, not hidden.

**CP-4 — Triage instrumentation is a project-owned `ActivitySource` named
`ApartmentTriage.Agents`, emitting v1.41 `gen_ai.*` names directly.** The constructed
fixture's premise — `Experimental.Microsoft.Extensions.AI` — describes a framework the agent
rejects by name (C-2 method 4). The mapping's detection scope changes to match the emitter.
*Alternative:* name the source after the framework so the fixture stays valid. Rejected as a
fake provenance.
*Residual:* token counts must be read from the Anthropic response inside
`AnthropicClient`, one seam the contract names.

**CP-5 — Content attributes are gated off by default and on only for eval replay from the
eval corpora.** `PLUMBLINE_CAPTURE_CONTENT=1` (and OpenInference's own hide-inputs and
hide-outputs switches) turn on message text, rationale and image paths. Production traffic
never exports them; the eval corpora contain no real residents.
*Alternative:* always export and rely on ADR-0006's redaction stage. Rejected because that
stage runs after deserialization, so the bytes would still transit Pub/Sub and rest in the
DLQ for seven days.
*Residual:* a Triage `rationale` may quote the message; a redaction rule covers the key.

**CP-6 — Cloud ingest stays OTLP/HTTP through F3 and F4; ADR-0008 D1's verification is
deferred to F5.** Both emitters configure `http/protobuf`; ADR-0008 D6's fallback wording is
adopted as an amendment, and the status flip stays the maintainer's.
*Alternative:* build the h2c multiplexer now. Rejected: a data-plane change plus a deploy
plus a verification pass inside 29 days, for a transport neither emitter needs.
*Residual:* the reference implementation ships without a verified cloud gRPC path until F5.

**CP-7 — F3's gate is a CLI in the analytics project, invoked by GitHub Actions
(`workflow_dispatch` and cron); `analytics-api` on Cloud Run and Cloud Scheduler move to
F4.** Actions minutes are free on a public repository; a third Cloud Run service adds a
red-by-design first plan, a Scheduler API, and two teardown rows to the credit window.
*Alternative:* ship the service in F3 as the brief lists. Rejected on the calendar.
*Residual:* `eval-plan.md` §9's mode table names Cloud Scheduler as the nightly trigger —
package item E-1 proposes the wording that covers both.

**CP-8 — Eval reads go through the BigQuery REST `jobs.query` surface
(`Google.Apis.Bigquery.v2`), never the Storage Read API and never the base table.** Every
query passes through one helper that requires a `start_time` or `run_ts` window and sets
`maximumBytesBilled` (F2 directive Decision 7's shape). Gate A forbids
`Google.Cloud.BigQuery.V2`; the REST package is a different package and the
streaming-insert method it exposes is caught by Gate B's symbol scan, whose roots already
include `analytics/`.
*Alternative:* the Storage Read API, already permitted. Rejected because it cannot read
views and `eval-plan.md` §5.1 reads views only.
*Residual:* package-level denial is stronger than symbol-level; a proposal to extend Gate A
to the REST package's `Tabledata` resource is Class 3 and is listed in §7, not applied.

**CP-9 — The credit campaign is scoped to three deliverables:** (1) three captured fixtures;
(2) the calibration and variant corpus replayed through the cloud pipeline; (3) one bounded
L1 load run for SC-4 rows 4.1–4.3, which also discharges the fidelity-under-load carry.
ADR-0009 D2 activates on `#177`'s recorded disposition (a) + (c).
*Alternative:* ADR-0009 A1, spend nothing. Rejected for the reason ADR-0009 gives.
*Residual:* ADR-0009 §3.1's baseline read still needs W0-2 or W0-3.

**CP-10 — The D6-1 / C7 gap closes by reading "three emitters ingest-ready" as: each
emitter has produced at least one captured, admissible fixture that has been ingested
through the deployed collector by 2026-10-04.** Ingest proven, not traffic sustained;
sustained traffic is SC-2's window and starts on 2026-10-05. ADR-0010 §3 named this as Lane
C's; it is taken here under the delegation and is the maintainer's to re-read.
*Alternative:* ADR-0010 A3, Adjudicator only. Rejected there and here.
*Residual:* none the plan can resolve; the reading is written so it can be disputed.

**CP-11 — P7's judge tiers, as proposed in the package:** T1 is Ollama on the maintainer's
machine with a small instruct model recorded by digest at install; T2 is a **stable,
non-preview** Gemini Flash model read from the models page on the session day, with the
free-tier daily cap `Q` recorded as a dated observation rather than frozen. This host has
two cores and no Ollama, so T1 is sized to what runs overnight, not to what is best.
*Alternative:* drop T1. Rejected because the tier design is frozen text and
`eval-plan.md` §8.4's routing rule already handles a weak T1 by demoting it.
*Residual:* the model ids are chosen in the session; the package names candidates only.

**CP-12 — The deny-list rewrite is recommended for application now.** It is prepared,
Class 3, and it unblocks four reads. The DoD 12 assertion is restated for F3 against the
new list, as the proposal's step 6 requires.
*Alternative:* keep routing billing reads through the maintainer. Rejected: a spelling test
is not a security boundary, and the reads are on the critical path.
*Residual:* pattern matching is not effect analysis; the proposal records that limit.

**CP-13 — The replay corpus rows stay in `plumbline.spans`; only the load run's rows are
deleted at teardown.** The corpus is the experiment's evidence and `eval_results` cites it;
its size is bounded (sixteen runs × 292 items × a handful of spans, well under 0.1 GB
against a 10 GB free tier).
*Alternative:* delete every synthetic partition (ADR-0009 §4.3 as written). Rejected because
it would destroy the rows the gate's verdicts reference.
*Residual:* ADR-0009 §4.3 says "synthetic partitions are deleted"; this narrows it and the
narrowing is written into W4-1 rather than applied silently.

**CP-14 — F3E-01c runs as a read, not a write.** The row it needs is produced by the
pipeline when a captured fixture is replayed (W2-6); Lane A reads it back. No `bq insert`.
*Alternative:* a human `bq insert`. Rejected as unnecessary once the pipeline writes.
*Residual:* the replay trigger needs the API key, which is the `#109` split and is
recorded as such.

**CP-15 — DoD 8 and 9 close from existing evidence; DoD 10 waits for one human read.**
The budget publishes on every cost update and the function logs each decision, so a
notification dated after the first delivery is one Cloud Logging read away (W0-5).
*Alternative:* wait for the September period. Rejected: the August period is closed and
readable now.
*Residual:* if no logged notification after 2026-09-01 carries `costAmount`, W0-5 records
that and DoD 8 waits for the next cycle rather than being argued.

**CP-16 — Milestone due dates are set from §2.** F2 `2026-10-01`, F3 `2026-10-04`, F4
`2026-10-31`, F5 `2027-01-15`.
*Alternative:* none needed; a milestone without a date is a list.
*Residual:* dates are the plan's, and the plan is Proposed.

---

## 6. What only the maintainer can do

Listed once, in calendar order, with the reason the lane is C and a time estimate. Nothing
here is delegable to Lane A, and the plan does not route around any of it.

| # | When | What | Why C | min |
|---|---|---|---|---|
| 1 | now | Apply the deny-list rewrite to `.claude/settings.json` (W0-2) | Class 3 by the F2 directive §4 | 10 |
| 2 | now | One billing console session (W0-3): cost by credit type; August Billing Reports; budget filter and billing attached | `gcloud billing` reads are denied until item 1; Billing Reports are console-only | 30 |
| 3 | now | Put Freeze A session 2 on the calendar (W0-4) | the session is human-only | 5 |
| 4 | 2026-09-08 | **Freeze A session 2** (W1-1): transcribe the package into `eval-plan.md` v0.2, write or accept the eight rubric anchors, tag `eval-plan-freeze-a` | pre-registration is human-only, Class 3 | 180 |
| 5 | 2026-09-08 | Accept or amend ADR-0008 Amendment 1 (W0-7) | a status flip is a review output | 15 |
| 6 | 2026-09-08 → 09-12 | Open a Claude Code session in each agent repository and implement the contract (W1-3, W1-4), or do it by hand | a write to another repository is outside every plumbline lane (D5) | 2 × 360 |
| 7 | 2026-09-09 | Issue three API keys (W1-5) | key plaintext custody | 20 |
| 8 | 2026-09-09 | Run the Claude Code capture (W1-6) | a nested session cannot authenticate | 10 |
| 9 | before 2026-09-12 | Kill-switch three-step synthetic live-fire at `200.00` (W1-8) | billing detach and re-attach are human-only | 60 |
| 10 | 2026-09-15 | Drive one real interaction per agent into the capture receiver (W2-1) | a capture needs a human at the agent | 30 |
| 11 | W2-4 and V-3 | Approve the `gcp-production` environment for the F3 and F4 applies | Lane B cannot be delegated | 3 × 5 |
| 12 | 2026-09-21 | Account upgrade (W3-1); refuse any credit extension | billing account is human-only | 20 |
| 13 | 2026-09-22 → 09-26 | Run the Adjudicator for the calibration and variant runs (W3-3, W3-5): 16 runs × 292 items, VLM called on the escalation bucket only — an Anthropic spend outside GCP, estimated at a few thousand Sonnet vision calls; record the invoice | the agent runs on the maintainer's key and machine | 4 × 60 |
| 14 | 2026-09-22 | Land the F3 Unblock Directive v1.0 in `docs/specs/`, or record in `#177` that this plan supersedes it — D2, D3 and D4 of that directive are unknown to the repository | the directive is Lane C's document | 30 |
| 15 | before 2026-10-05 | Accept the `#138` ADR (W3-9) and decide ADR-0009's and ADR-0010's status | review outputs | 30 |
| 16 | 2026-10-05 → 10-19 | SC-2 staffing: one real span per source per UTC day for fourteen days (V-2); DoD 13b live-fire on day one (V-1) | real traffic is human-initiated on all three sources | 14 × 20 |
| 17 | October | Label the 50-item reference subset, twice, ≥ 7 days apart (V-4) | the human anchor of `eval-plan.md` §8.4 | 2 × 90 |
| 18 | F4 | Decide the GitHub Pages push credential (architecture OQ-5) and the uptime-check path | the first secret in a secret-free design; a collector change | 30 |

---

## 7. Blocked register, and what this plan does not do

| Item | Blocked on | Not done here because |
|---|---|---|
| `docs/specs/F3-eval-engine.md` | the `eval-plan-freeze-a` tag | writing it first is the covert start the entry directive §2 forbids; §4.3–4.4 are its outline |
| `docs/eval-plan.md` v0.2 | the session | Class 3; the package is the diff |
| `.claude/settings.json` | the maintainer | Class 3; the rewrite is the diff |
| ADR-0008, ADR-0009, ADR-0010, `#138` status | review | status flips are review outputs |
| Extending Gate A to `Google.Apis.Bigquery.v2`'s `Tabledata` resource | Class 3 | changes what a gate asserts; proposed in CP-8's residual, not applied |
| The F3 Unblock Directive's D2, D3, D4 | its landing | not in the repository; not invented here |
| h2c multiplexing (ADR-0008 D1) | F5 | CP-6 |
| A second owner, an organization parent | Decision 18 | unchanged |

---

## 8. Provenance

Read on 2026-09-05 at `main @ b7b3cf9`, through the filesystem, `git`, the GitHub issues,
milestones, pull-requests and Actions APIs, and read-only `gcloud` and `bq` calls against
`plumbline-19458` (`run services list` and `describe`, `pubsub topics list` and
`subscriptions list`, `functions list`, `monitoring policies list`, `artifacts docker images
list`, `bq ls`, `bq show`, one partition-filtered `COUNT` query over `plumbline.spans`).
Local test runs are §1.2. The two agent repositories were read on this host at the commits
in §1.3. The Gemini models page and rate-limits page were read on 2026-09-05 for the
package's P7. No line here is admissible as evidence in a closing note; re-read from the
repository.

## 9. Changelog

**v0.1 — 2026-09-05.** Initial. Every phase re-derived; fourteen blockers named to the fact
that unblocks each; five waves and a window; sixteen decisions; eighteen maintainer items.
