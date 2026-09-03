# C-2 — the Apartment Triage agent, read for OTLP emission

**Read:** 2026-09-03 · **Lane:** A · **Source:** `github.com/arslan-kursad/apartment-triage`
**Pinned at commit `15c1d6ebdeef43d22c76bf32e7198966083c937f`**, committed
`2026-07-13T16:59:52Z`. Public repo, read-only. C#, 310 tree entries, 161 `.cs` files.
**Task:** F3 Unblock dispatch U-01. **Method:** the four-method shape of
[`c1-adjudicator-readout.md`](c1-adjudicator-readout.md).

**This is a read, not a run.** Nothing here executes the agent.

---

## The headline: **this agent emits nothing either**

The same answer as the Adjudicator, reached by the same four methods — and it means C7
contains **two** instrumentation projects, not one.

| Method | Probe | Result |
|---|---|---|
| 1 · dependency manifest | `PackageReference` across all five `.csproj` | **24 references, zero `OpenTelemetry.*`** |
| 2 · source-level import scan | `OpenTelemetry`, `ActivitySource`, `System.Diagnostics`, `StartActivity`, `TracerProvider` | **0 files each** |
| 3 · file inventory | any path named for telemetry / otel / tracing / instrument | **0 of 310 tree entries** |
| 4 · declared-but-unused | `Microsoft.Extensions.AI` — the framework the fixture manifest credits | **present in 4 files, all documentation, all negations** — see below |

Configuration probes, same result: `otlp` **0**, `OTEL_` **0**, `4317` **0**.

**Controls, so the zeros mean something.** A probe that only ever returns zero is measuring
its own spelling, not the repository. Run over the same tree: `Serilog` **15**,
`using System` **46**, `ILogger` **18**. The scan reaches the source; the instrumentation
is absent from it.

> **Method note.** GitHub code search was used first and rate-limited mid-run, returning
> empty for queries that had previously returned counts. Every number above is instead from
> a deterministic grep over the extracted tarball at the pinned SHA. The controls exist
> because the first broken invocation of that grep returned zero for *everything*,
> including Serilog — which is what caught it.

## Method 4 in full, because it inverts a claim in this repository

`Microsoft.Extensions.AI` appears four times, and every occurrence says the project does
**not** use it:

- `CLAUDE.md:22` and `AGENTS.md:22` — *"Custom `IAgent<TIn,TOut>` orchestrator (~500 LOC) —
  Semantic Kernel / AutoGen / Microsoft.Extensions.AI YOK"*
- `docs/decisions/ADR-0001-custom-orchestrator-over-semantic-kernel.md:83` — listed under
  *"Alternative C"*, i.e. the option that was rejected.

**plumbline's own fixture manifest credits that framework with the instrumentation.**
[`testdata/fixtures/dotnet-agent/manifest.yaml`](../../testdata/fixtures/dotnet-agent/manifest.yaml)
reads `emitter: .NET agent using Microsoft.Extensions.AI OpenTelemetry instrumentation`.
The agent's own decision record rejects that framework by name. The manifest is
`provenance: constructed`, so nothing was measured to produce that line — it describes an
emitter that was assumed and does not exist.

This is the same shape as the `langgraph-python` manifest, whose `constructed` provenance
the C-1 readout explained the same way: *"there was never a real emitter to capture from."*

---

## What this changes

### SC-1 is not "one hard capture and two easy ones"

Read together with [`c1-adjudicator-readout.md`](c1-adjudicator-readout.md) and the
manifests, every dialect is blocked, and only one of the three blocks is an access problem:

| Dialect | Agent | Emits today | Block |
|---|---|---|---|
| `langgraph-python` | Anomaly Adjudicator | **no** | needs instrumentation |
| `dotnet-agent` | Apartment Triage | **no** | needs instrumentation |
| `claude-code` | Claude Code | **yes**, natively | authentication (`#10`) |

**Two instrumentation projects and one authentication problem.** No dialect can be captured
by scheduling alone.

### Two documents in this repository are now wrong, both dated 2026-09-03

Both were written before this read and both say the .NET agent is capturable:

- [`ADR-0009`](../adr/ADR-0009-instrumental-credit-expenditure.md) §D3 — *"`dotnet-agent` is
  capturable and is the stretch-goal replication"*. The second half stands
  ([`eval-plan.md`](../eval-plan.md) §7.1); the first half does not.
- `#177` — its dialect table reads *"dotnet-agent | constructed | yes — first-party,
  instrumented"*. Wrong on the last word.

Both are corrected by this readout rather than silently, and the finding is filed as `#183`.

### C7's constraint grows

[`F2-completion-directive.md`](../specs/F2-completion-directive.md) F2C-19 requires
*"F3 exit + three emitters ingest-ready ≤ 2026-10-04"*. "Three emitters ingest-ready" was
already understood to include one instrumentation project. It includes two. Nothing about
this read moves the date.

## What this read does not claim

It does not claim the agent is untraceable or hard to instrument — 161 `.cs` files in a
conventional five-project ASP.NET layout with Serilog already wired is an ordinary
instrumentation target, and `Program.cs` has a single obvious composition root at
`builder.Host.UseSerilog(...)`. **Sizing that work is a design question and is not
attempted here.** It claims only that today, at this SHA, nothing is emitted.

It also does not settle whether the Triage agent *should* be instrumented. That is the same
class of decision as T2-01, it belongs to whoever owns C7's scope, and Lane A does not take
it.

---

# Addendum — U-03: the P11 discrepancy, and the report that was wrong

**Read:** 2026-09-03 · same session as the readout above.

**Two documents disagreed about P11** (*"Claude Code emitter scope markers
(architecture §10 OQ-4) — affects SC-1 fixtures"*, [`eval-plan.md`](../eval-plan.md)
Appendix A):

- The F3 status report of 2026-09-03 listed P11 as **absent** — *"P11 YOK"*.
- The dispatch's external context recorded the scope marker as **measured** at
  `mappings/v1.41/claude-code.yaml:20`.

**The status report is wrong, and it was mine.** Read at
[`normalization/mappings/v1.41/claude-code.yaml`](../../normalization/mappings/v1.41/claude-code.yaml):16-23:

```yaml
detection:
  # The answer to architecture §10 open question 4. Vendor-namespaced, identical across
  # two emitter builds, and versioned independently of the application — `service.version`
  # moved while the scope stayed at 1.0.0.
  scope_names:
    - com.anthropic.claude_code.tracing
```

The file states in its own comment that it *is* the answer to OQ-4, and gives the reasoning
for trusting it: vendor-namespaced, stable across two builds, versioned independently of
the application. [`architecture.md`](../architecture.md):465 agrees —
*"scope marker measured; tool/hook spans still unobserved"*.

## The distinction the correction has to keep

Flipping "absent" to "present" would overshoot. P11 has two halves and they are in
different states:

| P11's content | State | Where |
|---|---|---|
| Claude Code **scope marker** for dialect detection | **measured** | `claude-code.yaml`:19-20; `architecture.md`:465 |
| **tool/hook spans** | **still unobserved** | `architecture.md`:465; `#10` |
| P11 **as an Appendix A placeholder**, recorded in `eval-plan.md` v0.2 with its value | **unfilled** | Freeze A exit item 1 |

So the accurate statement is: **P11's measurement exists and its freeze record does not.**
The status report collapsed those three rows into one "absent", which is wrong about the
first row, right about the third, and silent about the second.

**Consequence for Freeze A.** P11 is the one Freeze A placeholder whose value can be
transcribed rather than decided — it is already measured and its source is cited. That
makes it the cheapest of the eight, and it is the only one of the eight not owned by
"Human" alone in Appendix A, which lists its owner as **F1 capture**.

**Correction recorded rather than quietly fixed.** The status report was a working document
sent outside the repository and is not repo-normative; this addendum is the durable record,
per the dispatch's instruction to record the correction in the readout. `project-context`
is not in this repository and was not used as a source for anything above — the mapping
file and `architecture.md` were read directly.
