# DoD 3 and DoD 7b — measured after Wave 4's first deliveries

**Measured:** 2026-09-01 · **Directive items:** F2C-11 (7b), F2C-12 (3), F2C-09 (walling)
**Runs:** `w4-second-delivery`, `w4-third-delivery` · **Key:** `wave4-e2e-3`
**Every figure below is an API read.** None is taken from the harness's own report, for a
reason recorded in §4.

## 1. DoD 7b — push transport exercised

The worker's log, after Wave 4's `custom_audiences` fix applied:

```
POST http://ingestion-worker-.../push - 204
ingested message 21643570449831296: 1 row(s), api_key_id=wave4-e2e-3, redacted=0
```

A real Google-signed token was accepted **twice over**: by Cloud Run's own authentication,
which had refused the first attempt (branch A, `f2-dod7b-first-delivery.md`), and then by
the worker's validator reading `PUSH_OIDC_AUDIENCE`. 7a proved the transport existed; this
is the first evidence it carries a message.

## 2. DoD 3 — constructed OTLP lands through the views, every row flagged

Queried against `spans_deduped` under the corpus's own partition window
(`2026-08-18` … `2026-08-20`), scoped by run id:

| Run | `rows_seen` | `distinct_spans` | `unflagged` |
| --- | --- | --- | --- |
| `w4-second-delivery` | 13 | 13 | 0 |
| `w4-third-delivery` | 13 | 13 | 0 |

Both halves of the claim:

- **Every span landed once.** `rows_seen` equals `distinct_spans`, so no
  `(trace_id, span_id)` appears twice through the view.
- **Every landed row is flagged.** `unflagged` is 0 — no row of either run has `synthetic`
  anything but true.

13 rows is what the local normalization produced from the same corpus (`normalized 7
payload(s) into 13 row(s)`), so the count is not merely plausible, it is the expected one.

## 3. F2C-09 — the walling holds

```
SELECT COUNT(*) AS leaked FROM `…plumbline.spans_real`
WHERE DATE(start_time) BETWEEN '2026-08-18' AND '2026-08-20' → 0
```

Zero across **both** runs. This is the first live test of the walled-off-synthetic
invariant, and it is the claim F4 depends on: `spans_real` is the only view its 14-day
window reads, so a leak here would contaminate a measurement F4 has no cheap way to clean.

## 4. Why these are API reads and not the harness's report

The harness printed `PASS` for `w4-second-delivery`, and that PASS is **not citable**: the
partition-window fix was written while the run was in its polling loop, and each poll
re-invokes the module, so the run consumed the fix mid-flight (W3.18). `w4-third-delivery`
is the clean run — no code changed during it, `result.json` reads
`stage=complete, passed=true` — and even for that one the figures here were re-read from
the API rather than lifted from the tool.

## 5. What is measured here and what is not

| Claim | State |
| --- | --- |
| DoD 7b — push transport exercised | **satisfied**, §1 |
| DoD 3 — rows through the views, all flagged | **satisfied**, §2 |
| F2C-09 — `spans_real` excludes the runs | **satisfied**, §3 |
| Idempotence — "run it twice, counts stay stable" | **not tested.** §6 |
| DoD 4 — poison → DLQ → alert → triage | **blocked.** §6 |

## 6. Two things this does not close

**Idempotence is untested, and the reason is a design consequence worth naming.** The spec
asks Wave 4 to run the harness twice and show counts stable through the views — a dedup
test. Two runs here produced `base = 26, deduped = 26`: no duplicate was ever presented,
because Decision 6 derives span identity from the run id (#102) and two run ids are two
identities. The dedup test is therefore **re-running the same run id**, which produces the
same derived identity and the same `start_time` and so must collapse to 13. Cheap, and not
yet done.

**DoD 4 is blocked on a queue this phase filled itself.** `traces-dlq-pull` holds five real
messages from the failed first delivery. They are branch A's evidence and the drill needs a
drained queue with unambiguous attribution, so they are drained after this document exists,
not before.
