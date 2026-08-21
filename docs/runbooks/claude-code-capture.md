# Runbook — capturing a real Claude Code OTLP emission

**Audience:** the maintainer, on their own terminal · **Time:** ~10 minutes
**Produces:** raw `ExportTraceServiceRequest` protobuf files, outside the repository
**Consumes:** nothing from the repository except this runbook and the receiver script

This is checkpoint **C1** of F1 (`docs/specs/F1-local-first-core.md` §8). It exists
because Claude Code cannot run it for itself, and it closes the procedure half of issue
#10.

## 1. Why a human runs this

A nested, non-interactive `claude -p` session cannot authenticate: the credential is
held by the host application and does not resolve in a child process. Every capture
attempted that way failed at the first LLM request and the agent loop never reached a
tool call, which is exactly why `docs/evidence/claude-code-otel-capture.md` §3 records
`claude_code.tool` and `claude_code.hook` spans as unobserved. An interactively
authenticated session is the only way to reach them, and that is a terminal only the
maintainer has.

## 2. What the capture is for

The F1 claude-code fixture is currently `provenance: derived-from-measured-evidence`:
its markers are measured, its payload was assembled from an inventory rather than
promoted from bytes. A real capture replaces it, and the manifest's provenance becomes
`captured`. Two specific gaps close with it:

- **Tool and hook spans.** Never observed. Their attribute sets are documentation, not
  measurement, so nothing about them is mapped today.
- **Event-level attributes**, `workspace.host_paths` above all. Issue #11 requires it be
  treated as present until a capture shows otherwise, so the redaction rule covers it
  blind.

## 3. Prerequisites

- Claude Code installed and **interactively authenticated** (`claude` runs and answers
  without an auth error).
- Python 3.9+ — standard library only, nothing to install.
- A capture directory **outside this repository**. The receiver refuses to write inside
  the working tree, because a raw capture carries `user.id`, `user.email` and
  `organization.id` and this repository is public.

```bash
mkdir -p ~/plumbline-captures/$(date -u +%Y-%m-%d)
```

## 4. Capture

### 4.1 Start the receiver

In terminal 1, from the repository root:

```bash
python3 scripts/capture/otlp-file-receiver.py --out ~/plumbline-captures/$(date -u +%Y-%m-%d)
```

It prints one line per export request. Leave it running.

### 4.2 Configure a hook, so hook spans exist to capture

`claude_code.hook` spans are only emitted if a hook actually runs. In terminal 2, create
a throwaway project with a trivial hook — outside this repository, so nothing here is
touched:

```bash
mkdir -p ~/plumbline-capture-workspace/.claude && cd ~/plumbline-capture-workspace
cat > .claude/settings.json <<'JSON'
{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Write", "hooks": [{ "type": "command", "command": "echo captured-hook" }] }
    ]
  }
}
JSON
```

### 4.3 Run an interactive session with telemetry on

Still in terminal 2, in `~/plumbline-capture-workspace`:

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1
export OTEL_TRACES_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318
export OTEL_TRACES_EXPORT_INTERVAL=1000
export OTEL_METRICS_INCLUDE_SESSION_ID=false
export OTEL_METRICS_INCLUDE_ACCOUNT_UUID=false
claude
```

All three of the first environment variables are required for spans; the beta gate is
not optional (#10 §1). **`http/protobuf` rather than the `http/json` the P11 evidence
used**: for a fixture the bytes themselves are the artefact.

The two `OTEL_METRICS_INCLUDE_*` flags are set because #10 asks that what can be turned
off is turned off. Do not expect much from them: they are documented as metrics-scoped,
and the P11 capture found the identity block on **span** attributes. Redaction is what
actually removes it (§6).

Inside the session, do enough to exercise the span types that are missing. A prompt of
this shape is sufficient:

> Create a file `notes.txt` containing the word hello, then read it back, then run
> `echo done` in bash.

Then exit with `/exit`. Wait for the receiver to print a line or two after the session
ends — the exporter flushes on shutdown.

### 4.4 Stop the receiver

Ctrl-C in terminal 1. It prints how many export requests it captured.

## 5. What a good capture looks like

- **At least one file**, non-zero size, in the capture directory.
- The session **actually called tools**: you saw Write, Read and Bash run. If the model
  answered without using a tool, `claude_code.tool` spans do not exist in the capture and
  the run has to be repeated with a more explicit prompt.
- If the receiver printed nothing at all, telemetry never started: re-check that all
  three enabling variables are exported in the same shell that ran `claude`.

The capture cannot be inspected further by eye — it is binary protobuf. Verification is
step 6.

## 6. Hand it over

**Do not `git add` anything from the capture directory.** The raw bytes carry `user.id`,
`user.email`, `organization.id`, `user.account_uuid`, `user.account_id`, `session.id` and
possibly `workspace.host_paths`. `CLAUDE.md` forbids all of it in this repository,
fixtures and example payloads included, and the repository is public.

Tell Claude Code the capture directory path. It then:

1. Parses the payloads and reports what span and event types are present — the first
   real answer on tool and hook spans.
2. Redacts every identity field into the deterministic
   `[REDACTED:sha256:…]` markers the redaction rules already define
   (`normalization/redaction/v1/claude-code.yaml`), replacing values while preserving
   key, position and type.
3. Promotes the redacted payload to `testdata/fixtures/claude-code/`, flips the manifest
   to `provenance: captured` with the real capture date and emitter version, and records
   what the capture did and did not observe.
4. Updates `docs/evidence/claude-code-otel-capture.md` with the newly observed span and
   event types, since that file's §3 currently records them as unobserved.

The raw capture stays where you put it. Delete it when the fixture is merged.

## 7. If the capture still cannot reach tool spans

Record that outcome rather than retrying indefinitely: it is a finding about the emitter,
not a failed procedure. The fixture stays `derived-from-measured-evidence`, the manifest
keeps saying so, and the F4 dogfooding phase — where Claude Code is instrumented as a
live source anyway — inherits the gap. What must not happen is a fixture that claims
`captured` provenance for span types nobody has seen.
