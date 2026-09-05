# Lane A deny-list — rewrite from enumeration to principle, prepared not applied

**Prepared:** 2026-09-05 · **Lane:** A · **Task:** F3 Unblock Directive v1.0 U-13
**Target:** `.claude/settings.json` · **Class 3 — Lane C applies. Nothing here is applied.**
**Records:** decision **D5** — *a task's lane is determined by the strongest permission its
execution requires, not by the layer that authors it.*

---

## The defect, stated as the repository already states it

[`F2-completion-note.md`](../specs/F2-completion-note.md) records it under a heading that is
itself the diagnosis — *"The Lane A deny-list is enumerated, not principled"*:

> What it denies is `Bash(gcloud alpha:*)`, an entire command surface regardless of whether a
> call reads or writes, and F2C-08.1 was blocked because the command reached for was
> `gcloud alpha monitoring policies list`. Measured 2026-08-31 from Lane A, the GA surface is
> permitted and returns the same reading […] **The shape defect is real and is this — denial
> by command surface rather than by effect.**

The same note records why it was not fixed in F2: doing so means editing
`.claude/settings.json` while DoD 12 asserts nothing was loosened across F2. D5 is the
authorised moment.

## Current state, read 2026-09-05

`.claude/settings.json` carries a 14-entry `deny` list and no `allow` list.
`.claude/settings.local.json` adds one `allow` entry, `Bash(git checkout *)`.

| # | Entry | Denies by | Would D5 keep it? |
|---|---|---|---|
| 1 | `Bash(gcloud billing:*)` | **surface** | narrow — see below |
| 2 | `Bash(gcloud projects delete:*)` | effect | **yes**, unchanged |
| 3 | `Bash(gcloud alpha:*)` | **surface** | narrow — see below |
| 4 | `Bash(terraform apply:*)` | effect | **yes**, unchanged |
| 5 | `Bash(terraform destroy:*)` | effect | **yes**, unchanged |
| 6 | `Bash(terraform import:*)` | effect | **yes**, unchanged |
| 7 | `Bash(bq insert:*)` | effect | **yes**, unchanged |
| 8 | `Bash(bq rm:*)` | effect | **yes**, unchanged |
| 9 | `Bash(git push --force:*)` | effect | **yes**, unchanged |
| 10 | `Bash(git push -f:*)` | effect | **yes**, unchanged |
| 11–14 | `Write(.env*)`, `Write(**/*.tfstate)`, `Write(**/*service-account*.json)`, `Write(**/*credentials*.json)` | effect | **yes**, unchanged |

**Twelve of fourteen entries already deny by effect and are untouched by this proposal.**
The defect is two entries, not the list.

## The proposed change — two entries narrowed, twelve unchanged

```diff
   "deny": [
-    "Bash(gcloud billing:*)",
+    "Bash(gcloud billing accounts update:*)",
+    "Bash(gcloud billing accounts create:*)",
+    "Bash(gcloud billing projects link:*)",
+    "Bash(gcloud billing projects unlink:*)",
+    "Bash(gcloud billing budgets create:*)",
+    "Bash(gcloud billing budgets update:*)",
+    "Bash(gcloud billing budgets delete:*)",
     "Bash(gcloud projects delete:*)",
-    "Bash(gcloud alpha:*)",
+    "Bash(gcloud alpha * create:*)",
+    "Bash(gcloud alpha * update:*)",
+    "Bash(gcloud alpha * delete:*)",
     "Bash(terraform apply:*)",
```

Everything below that line is unchanged.

## Per refused operation the principle would permit

The directive asks for the reason each is a read and not a mutation.

### 1 · Billing reads — `gcloud billing accounts list`, `... describe`, `... projects describe`

**A read.** These verbs return account and linkage state and change nothing. The mutating
verbs on the same surface are `accounts update`, `projects link`/`unlink`, and the `budgets`
create/update/delete family — all of which the proposal denies explicitly.

**Refused twice, measured.** `gcloud billing accounts list` was refused at the permission
layer from Lane A on 2026-09-03 and again on 2026-09-05.

**What it blocks today:** ADR-0009 §3.1's cost baseline, which is a precondition of the whole
credit-expenditure regime; ADR-0009 §1.4's open question — whether August's ₺0.04 was
absorbed by the trial credit or by Always Free; and `#74`'s own wording, which turns on the
same read. **Three documents wait on one `list` call.**

### 2 · Monitoring reads — `gcloud alpha monitoring policies list`

**A read.** It enumerates alert policies. The defect is documented above and was *already
worked around* rather than fixed: the GA surface `gcloud monitoring policies list` is
permitted and was measured on 2026-08-31 to return the same reading.

**So the current rule denies nothing an operator cannot get another way** — which is the
clearest possible demonstration that it denies by surface rather than by effect. A rule that
blocks one spelling of a read and permits another is not a security boundary; it is a
spelling test.

### 3 · Cloud Run reads — **and here the directive's premise does not hold**

The directive lists Cloud Run reads among *"currently-refused operations that the principle
would permit"*.

**Read 2026-09-05: neither `.claude/settings.json` nor `.claude/settings.local.json` contains
any Cloud Run or `gcloud run` entry.** Searched both files for `run` and `monitoring`; the
only `monitoring` relevance is via the `gcloud alpha` surface above.

**So Cloud Run reads are not denied by this file.** If they are being refused, the refusal
comes from somewhere else — the interactive permission layer, which is situational rather
than configured. **This proposal cannot fix that, and editing `settings.json` would not
change it.** Recorded rather than silently dropped, because a proposal that claimed to fix a
denial it does not control would be worse than one item short.

## What this proposal deliberately does not do

**It does not add an `allow` list.** The deny-list is the mechanism DoD 12 asserts about, and
introducing a parallel allow mechanism in the same change would make "nothing was loosened"
harder to check, not easier.

**It does not touch the twelve effect-based entries**, including every `Write` rule. The
principle endorses them as they stand.

**It does not widen `gcloud alpha` beyond read verbs.** The three narrowed patterns deny
`create`, `update` and `delete` across every alpha service, so a new alpha mutation surface is
denied by default rather than by enumeration — which is the direction D5 asks for.

## Residual uncertainty

**Pattern matching is not effect analysis.** `Bash(gcloud alpha * create:*)` is still a string
pattern, and a mutating verb that is not `create`/`update`/`delete` — `set-iam-policy`,
`add-iam-policy-binding`, `enable` — would pass it. **This proposal narrows the defect; it
does not convert the mechanism into one that understands effects**, because the permission
system matches patterns and nothing else is available.

The honest description of the result: **denial by effect where the verb names the effect, and
by surface where it does not.** That is better than the current state and is not the principle
fully realised. Stating it here so a later reader does not assume more than was built.

## Verification for whoever applies it

1. `python3 -c "import json; json.load(open('.claude/settings.json'))"` parses.
2. `gcloud billing accounts list` succeeds from Lane A.
3. `gcloud monitoring policies list` still succeeds; `gcloud alpha monitoring policies list`
   also succeeds.
4. `gcloud billing projects link` is still refused.
5. `terraform apply`, `bq insert`, `bq rm` and `git push --force` are still refused.
6. DoD 12's assertion is restated for F3 against the new list, not inherited from F2's.
