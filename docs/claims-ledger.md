# Claims ledger

**Derived:** 2026-09-03 · **Lane:** A · **Task:** F3 Unblock dispatch U-06

> **Perishable and stamped.** Every row below was re-derived from the repository on the
> date shown, not carried forward from any prior document. A row is evidence only for the
> date it names. Re-derive before citing; a stale ledger row is the defect class this
> project has now recorded five times.

The four claims are [`project-brief.md`](project-brief.md) §Differentiators, items 1–4.

---

## 1 · Polyglot by necessity — Go owns the data plane, .NET the control plane

**State: HOLDS.** The only claim of the four that is fully evidenced today.

| Evidence | Read 2026-09-03 |
|---|---|
| Go data plane | `collector/` — 21 `.go` files; kill-switch function — 2 `.go` files |
| .NET control plane | `worker/` + `analytics/` — 33 `.cs` files (excluding build output) |
| Both build in CI | `collector (go)`, `worker and analytics (.net)` jobs in `ci.yml` |

**Caveat, so the claim is not read wider than it is:** this evidences that both languages
are present and building. The *"where the industry defaults to it"* half of the claim is a
design argument, not a measurement, and nothing in the repository tests it.

## 2 · Dogfooding on 3 heterogeneous real sources

**State: NOT MET. Zero of three sources emit into the pipeline today.**

| Source | Emits today | Block | Read |
|---|---|---|---|
| Anomaly Adjudicator (LangGraph/Python) | **no** | no instrumentation at all | [`c1-adjudicator-readout.md`](evidence/c1-adjudicator-readout.md), 2026-09-02 |
| Apartment Triage (.NET) | **no** | no instrumentation at all | [`c2-triage-readout.md`](evidence/c2-triage-readout.md), 2026-09-03 |
| Claude Code | **yes**, natively | not access — **redaction** (`#10` finding 3) | [`claude-code-export-vs-capture.md`](evidence/claude-code-export-vs-capture.md), 2026-09-03 |

Corroborating, and independent of the readouts: no fixture manifest in
`testdata/fixtures/*/manifest.yaml` reads `provenance: captured`. Count read 2026-09-03:
**0 of 4**.

**Two of the three blocks are instrumentation projects.** This was believed to be one until
2026-09-03.

## 3 · Pre-registered evaluation criteria and a seeded-regression experiment

**State: PARTIALLY MET — the pre-registration exists and is not frozen; the experiment has
not run.**

| Half of the claim | State | Read |
|---|---|---|
| Criteria are written down in advance | **yes** — `docs/eval-plan.md` exists, 400+ lines, SC-1…SC-4 and §7's experiment design | this repo |
| Criteria are **frozen** | **no** — the file's own header reads `Status: DRAFT — NOT FROZEN`, version 0.1, dated 2026-08-19 | `eval-plan.md`:3 |
| The experiment has run | **no** — F3 has no spec and none of T1–T6 exists | `F3-entry-directive.md` §2 |
| The gate could score it if it ran | **no** — E1's four conjuncts are all trace-computed and the subject emits nothing | [`#177`](https://github.com/arslan-kursad/plumbline/issues/177), [`e1-predicate-readout.md`](evidence/e1-predicate-readout.md) |

**The strongest honest form of this claim today** is that the criteria were written before
the results existed, which is the substance of pre-registration and is verifiable from git
history. The freeze — the part that makes them un-revisable — is Freeze A and has not
happened.

## 4 · Enforced monthly cost ceiling of 200 TRY net on GCP

**State: PARTIALLY MET — configured and applied, not yet proven against a real charge.**

| Component | State | Read |
|---|---|---|
| Ceiling defined and pre-registered | **yes**, 200 TRY net | `eval-plan.md`:191 row 4.5; ADR-0004 Amendment 5 |
| `detach_threshold` applied at 200.00 | **yes**, verified live | [`f2-detach-threshold-200-applied.md`](evidence/f2-detach-threshold-200-applied.md) |
| Kill-switch **mechanism** proven | **yes** — live-fired | F2 decision log A2.12 |
| Kill-switch **at 200.00** proven | **no** — A2.12 fired against 5.00 | ADR-0004:690, *"describes a configuration, not a control"* |
| Ceiling observed against real (post-credit) cost | **no** — window opens 2026-10-05 | F2 DoD 13 / Verification C |

**The claim changed on 2026-09-02** and the brief records it: this read *"$0.00 on GCP
Always Free"* until ADR-0004 Amendment 5 withdrew the hard zero. Any external material
predating that is describing a claim the project no longer makes.

**One unresolved question sits underneath this row.** Whether the zero-cost envelope
currently rests on the trial credit or on Always Free is disputed between
[`#74`](https://github.com/arslan-kursad/plumbline/issues/74)'s mechanism argument and
ADR-0009 §1.4's arithmetic observation. It is settled by one read of the cost export by
credit type, which was refused to Lane A at the permission layer on 2026-09-03.

---

## Summary

| Claim | State on 2026-09-03 |
|---|---|
| 1 · Polyglot | **holds** |
| 2 · Three real sources | **not met** — 0 of 3 emitting |
| 3 · Pre-registered + seeded regression | **partial** — written, not frozen, not run |
| 4 · 200 TRY net ceiling | **partial** — configured, not proven against a real charge |

**Nothing here is a closing-note entry.** Three of the four rows depend on work that is
scheduled after this date, and the fourth is the only one whose evidence is complete.
