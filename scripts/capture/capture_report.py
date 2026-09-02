#!/usr/bin/env python3
"""What a Claude Code capture actually reached (F3E-03, #10, architecture §10 OQ-4).

Three capture attempts have been spent and every one failed at authentication before
reaching a tool call. That is recorded as a fact and has never been recorded as a
*diagnosis* — nothing turned the attempt into a statement about which span types the
session got to before it stopped.

This does. It reads the files the receiver wrote and reports, per span type, whether the
emitter produced it. Then it names a terminal state. **"Retry" is not one of them**: an
attempt that ends without a named outcome has spent the scarcest resource on the path to
2026-10-04 and bought nothing, which is the failure this tool exists to prevent.

**Detection is a byte scan, not a parse, and the limit is stated rather than hidden.** The
captures are `ExportTraceServiceRequest` protobuf; span names travel as length-delimited
UTF-8, so searching for the literal is reliable for presence and says nothing about
structure. It cannot tell you a span is well-formed, only that its name was emitted. That
is exactly the question OQ-4 has open, so it is enough here and would not be enough for a
fixture — the fixture is validated by the normalizer's golden tests instead.
"""

from __future__ import annotations

import argparse
import os
import sys

# Documented in #10 §2 and re-derived from the manifest's own "what is measured" note.
# `observed` records what the 2026-08-19 captures actually produced, so this tool can say
# whether a new attempt moved the boundary rather than merely repeating it.
SPAN_TYPES = [
    ("claude_code.interaction", True, "root span, one per user prompt"),
    ("claude_code.llm_request", True, "model call"),
    ("claude_code.tool", False, "tool invocation — the gap OQ-4 has open"),
    ("claude_code.tool.execution", False, "tool execution detail"),
    ("claude_code.tool.blocked_on_user", False, "tool awaiting confirmation"),
    ("claude_code.hook", False, "hook execution — needs a PostToolUse hook configured"),
]

EVENT_TYPES = [
    ("gen_ai.request.attempt", True, "the only event any capture has produced"),
]


def scan(directory: str) -> tuple[list[str], int, int]:
    """Return (filenames, total bytes, files that were empty)."""
    if not os.path.isdir(directory):
        return [], 0, 0
    names, total, empty = [], 0, 0
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        size = os.path.getsize(path)
        names.append(name)
        total += size
        if size == 0:
            empty += 1
    return names, total, empty


def present(directory: str, names: list[str], needle: str) -> bool:
    token = needle.encode()
    for name in names:
        try:
            with open(os.path.join(directory, name), "rb") as fh:
                if token in fh.read():
                    return True
        except OSError:
            continue
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("directory", help="the capture directory the receiver wrote to")
    args = ap.parse_args()

    names, total, empty = scan(args.directory)

    print(f"capture report — {args.directory}")
    print(f"  files: {len(names)}   bytes: {total}   empty files: {empty}\n")

    if not names:
        print("TERMINAL STATE: NO-EXPORT")
        print("  The receiver wrote nothing. The session never exported, which is upstream")
        print("  of every span question — most likely the beta gate was not set, the")
        print("  endpoint was wrong, or authentication failed before any work began.")
        print("  Next: scripts/capture/claude-code-preflight.sh, and read check 8.")
        return 1

    found, missing, new = [], [], []
    print("span types")
    for name, observed, note in SPAN_TYPES:
        hit = present(args.directory, names, name)
        mark = "yes" if hit else " no"
        flag = ""
        if hit and not observed:
            flag = "   ← NEW: never observed before this capture"
            new.append(name)
        print(f"  {mark}  {name:<34} {note}{flag}")
        (found if hit else missing).append(name)

    print("\nevents")
    for name, _observed, note in EVENT_TYPES:
        hit = present(args.directory, names, name)
        print(f"  {'yes' if hit else ' no'}  {name:<34} {note}")

    print()
    tool_like = [n for n in found if ".tool" in n or n.endswith(".hook")]

    if new:
        print("TERMINAL STATE: BOUNDARY MOVED")
        print("  Span types appeared that no previous capture produced:")
        for n in new:
            print(f"    {n}")
        print("  This capture answers part of OQ-4. Redact it, promote it to a fixture,")
        print("  and update architecture §10 OQ-4 and the claude-code manifest's")
        print("  'what is measured' note with what is now observed.")
        return 0

    if tool_like:
        print("TERMINAL STATE: COMPLETE-AS-BEFORE")
        print("  Tool or hook spans present, but all were already observed.")
        return 0

    if "claude_code.interaction" in found:
        print("TERMINAL STATE: REACHED-MODEL-NOT-TOOLS")
        print("  The session authenticated and called the model, and stopped before any")
        print("  tool ran. This is the same boundary the 2026-08-19 captures hit, and it")
        print("  is now a named outcome rather than a failed attempt.")
        print("  Two causes are distinguishable and the session transcript tells you which:")
        print("    - the model was never asked to use a tool → re-run with the runbook's")
        print("      prompt in §4.3, which names Write, Read and Bash explicitly;")
        print("    - it was asked and refused or errored → that is a finding about the")
        print("      emitter, record it against #10 and stop. Do not retry blind.")
        return 1

    print("TERMINAL STATE: EXPORTED-BUT-UNRECOGNISED")
    print("  Files were written and no known claude_code span name appears in them.")
    print("  Either the dialect changed its span names — which is itself an OQ-4 finding")
    print("  worth recording — or the capture is not Claude Code's. Inspect one file.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
