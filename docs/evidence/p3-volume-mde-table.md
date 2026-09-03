# P3 — measured case volume, and the MDE each category selection buys

**Derived:** 2026-09-03 · **Lane:** A · **Task:** F3 Unblock dispatch U-08
**Volume source:** `arslan-kursad/aiqs-agent`, `results/decisions.csv`, read at
`0779c04ff98a744285b8b1c93ce35f4efd4a89b2`
**Method source:** [`freeze-a-prep.md`](../specs/freeze-a-prep.md) §4.4;
[`eval-plan.md`](../eval-plan.md) §7.5

**This table is for selecting from. It recommends no row.**

---

## The measured volume

`decisions.csv` holds eight run records. They cover **three distinct categories**, not
eight — `visa-capsules` appears six times with identical counts, which is six runs of one
category rather than six categories.

| Category | Dataset | n | normal | defective | image AUROC | runs |
|---|---|---:|---:|---:|---:|---:|
| `mvtec-screw` | MVTec AD | **160** | 41 | 119 | 0.9758 | 1 |
| `mvtec-capsule` | MVTec AD | **132** | 23 | 109 | 0.9765 | 1 |
| `visa-capsules` | **VisA** | **160** | 60 | 100 | **0.7387** | 6 |

## The selections

`N per arm` is the pooled case count. MDE is recomputed with §7.5's stated parameters —
unpaired two-proportion, one-sided, α = 0.05, power = 0.80, `p_baseline = 0.90`.

**The method is validated against the plan's own two anchors before use:** δ = 0.10 gives
n = **156.6** (§7.5 states *"n ≈ 157"*; freeze-a-prep §4.4 recomputed 156.6), and n = 160
gives **9.9 pp** (§4.4's table row). Same formula, same figures.

| | Selection | N per arm | Achieved MDE | Meets δ = 0.10? | Dataset |
|---|---|---:|---:|---|---|
| **A** | `mvtec-screw` only | 160 | **9.9 pp** | met | MVTec |
| **B** | `mvtec-capsule` only | 132 | **11.0 pp** | **missed** | MVTec |
| **C** | `visa-capsules` only | 160 | **9.9 pp** | met | VisA |
| **D** | both MVTec | 292 | **7.0 pp** | met | MVTec |
| **E** | `mvtec-screw` + `visa-capsules` | 320 | **6.7 pp** | met | mixed |
| **F** | `mvtec-capsule` + `visa-capsules` | 292 | **7.0 pp** | met | mixed |
| **G** | all three | 452 | **5.5 pp** | met | mixed |

## Four things the table does not show, each load-bearing

**1 · Every figure is conservative by an unknown amount.** §7.5: the design is paired, so
the unpaired number is *"a conservative upper bound; the realized power depends on the
discordant-pair rate, which is unknown before calibration."* True MDE at any N is **better**
than its row. §5.2 still forbids silently keeping δ at an underpowered N, so B's miss is
recorded either way.

**2 · `p_baseline = 0.90` is an assumption, not a measurement**, and every row moves with
it. The measured baseline arrives with Freeze B's calibration (§7.3, `k = 5` runs of `B0`) —
*after* this selection. **P3 is fixed on an assumed baseline by construction.**

**3 · Rows C, E, F and G cross a dataset boundary.** `visa-capsules` is VisA, not MVTec AD.
[`c-1-dossier-filled-2026-09-02.md`](c-1-dossier-filled-2026-09-02.md) C2 establishes label
independence for **MVTec AD** specifically; VisA is named there only as a *"second labelled
source"* suggested by `configs/patchcore_visa.yaml`. Pooling across the two is exactly the
comparability question [`freeze-a-prep.md`](../specs/freeze-a-prep.md) §4.3 raises, and this
table does not answer it.

**4 · The detector is not equally good on all three.** AUROC 0.9758 / 0.9765 on MVTec
against **0.7387** on VisA. Pooling arms whose upstream detector performs that differently
changes what a single `p_baseline` means — the assumption in point 2 is applied per arm, and
a pooled arm is not one population. **This is the strongest argument against C, E, F and G,
and it is a statistical objection rather than a logistical one.**

## Pooling costs something else, named in the source

[`freeze-a-prep.md`](../specs/freeze-a-prep.md) §4.4 lists pooling as one of three responses
to short volume and states its price: it *"costs P6's per-agent stratification"*. Selections
D through G all pay it. `eval-plan.md` E2 stratification keys — category being the natural
one — become unavailable in the pooled arm.

## The shape of the choice, without a recommendation

- **A** is the only single-category selection that meets δ = 0.10 on MVTec, which is the
  dataset whose label independence is established.
- **B** alone misses, by 1.0 pp.
- **D** is the largest selection that stays inside one dataset and one detector-performance
  regime.
- **C, E, F, G** buy more N by crossing a dataset boundary that §4.3 has flagged and this
  read has not cleared.

Selecting a row is P3, it is Freeze A, and it is human. Nothing above is a recommendation.
