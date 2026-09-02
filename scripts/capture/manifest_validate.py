#!/usr/bin/env python3
"""Fixture manifest validator — SC-1 row 1.2 admissibility (F3E-02, #42, #138).

Row 1.2 sets two independent conditions, and the second is the one that bites:

    ≥1 fixture per dialect **captured from a real emitter**, not hand-authored;
    a fixture missing any manifest field is not admissible evidence

So a manifest fails here for either of two reasons — it was not captured, or it was
captured and does not say enough about the capture to be checked. Both are reported, and
they are reported separately, because "we have no capture yet" and "we have a capture we
cannot audit" are different problems with different owners.

**This is not `scripts/ci/fixture_provenance.py`.** That guard covers the Terraform plan
fixtures under `scripts/ci/testdata/`, with its own manifest and its own vocabulary
(`captured` / `hand-authored-legacy`). This one covers the OTLP corpus under
`testdata/fixtures/`, whose manifests say `constructed` and
`derived-from-measured-evidence`. Two corpora, two manifests, one word — which is the
identifier confusion this repository keeps finding, so it is named here rather than left
for the next reader.

No third-party YAML dependency: the manifests are flat enough to read with a narrow
parser, and adding PyYAML to CI for this would be a dependency for one file. The parser
refuses what it does not recognise rather than skipping it, for the same reason
`bq_schema.py` does — a parser that silently skips a line it cannot read drops a field
and produces a manifest that looks complete.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

CAPTURED = "captured"

# Row 1.2's five fields, mapped onto the manifest keys this corpus uses. The mapping is
# stated here rather than assumed, because the row names properties and the manifests
# name keys, and nothing else in the repository writes the correspondence down.
REQUIRED_WHEN_CAPTURED = {
    "capture_origin": "row 1.2 'capture origin'",
    "captured_on": "row 1.2 'the capture date'",
    "otel_sdk_version": "row 1.2 'emitter SDK + version'",
    "semconv_version_emitted": "row 1.2 'the semconv version actually emitted'",
    "otel_semconv_stability_opt_in": "row 1.2 'the OTEL_SEMCONV_STABILITY_OPT_IN value'",
    # Not in row 1.2 as written; #10 places it there for eval-plan v0.2, and the corpus
    # already carries it. Required here because a redacted capture is not raw emitter
    # output, and row 1.3's losslessness check has to know which artefact it validates.
    "redacted_fields": "#10 — redacted_fields",
    "redaction_rules": "#10 — the rule file the redaction was applied from",
}

KEY_RE = re.compile(r"^([a-z][a-z0-9_]*):(.*)$")
LIST_ITEM_RE = re.compile(r"^\s+-\s+(.*)$")


def parse(path: str) -> dict[str, object]:
    """Read top-level keys from a manifest.

    Values are returned as strings, or as lists for block sequences. Nested mappings are
    recorded as present with an empty value — enough to answer "is this key declared",
    which is all row 1.2 asks.
    """
    out: dict[str, object] = {}
    current: str | None = None
    folding = False
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip():
                folding = False if not line.startswith((" ", "\t")) else folding
                continue
            if line.lstrip().startswith("#"):
                continue

            # A folded or literal block scalar puts its value on the following indented
            # lines. Treating the `>` line as the whole value reports every such field as
            # empty, which the self-test caught: three keys in the real corpus are written
            # this way, and a validator that rejects them rejects correct manifests.
            if folding and line.startswith((" ", "\t")) and current is not None:
                previous = out.get(current) or ""
                if isinstance(previous, str):
                    out[current] = (previous + " " + line.strip()).strip()
                continue

            m = KEY_RE.match(line)
            if m:
                current = m.group(1)
                value = m.group(2).strip()
                # Strip a trailing inline comment, but only when it is one: a `#` inside
                # a quoted value is data.
                if "#" in value and not value.startswith(('"', "'")):
                    value = value.split("#", 1)[0].strip()
                folding = value in (">", "|", ">-", "|-")
                out[current] = "" if folding or value == "" else value.strip('"')
                continue

            folding = False
            item = LIST_ITEM_RE.match(line)
            if item and current is not None:
                existing = out.get(current)
                if isinstance(existing, list):
                    existing.append(item.group(1).strip())
                elif not existing:
                    out[current] = [item.group(1).strip()]
    return out


def validate(path: str) -> tuple[bool, list[str]]:
    manifest = parse(path)
    problems: list[str] = []

    dialect = manifest.get("dialect") or "?"
    provenance = manifest.get("provenance")

    if provenance != CAPTURED:
        problems.append(
            f"not admissible: provenance is {provenance!r}, row 1.2 requires "
            f"'captured from a real emitter, not hand-authored'"
        )

    for key, why in REQUIRED_WHEN_CAPTURED.items():
        value = manifest.get(key)
        if value is None:
            problems.append(f"missing field {key!r} ({why})")
        elif value == "" and key != "redacted_fields":
            problems.append(f"field {key!r} is declared but empty ({why})")

    # `unset` is a value, not an absence. Row 1.2 says so explicitly, and a manifest that
    # omitted the key entirely would otherwise be indistinguishable from one recording
    # that the variable was not exported.
    optin = manifest.get("otel_semconv_stability_opt_in")
    if optin == "":
        problems.append(
            "otel_semconv_stability_opt_in is empty; row 1.2 requires the value, "
            "recorded as 'unset' when absent"
        )

    return (not problems, [f"{dialect}: {p}" for p in problems])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifests", nargs="+", help="manifest.yaml paths")
    ap.add_argument(
        "--expect-fail",
        action="store_true",
        help="invert: succeed only if every manifest is inadmissible (used by --self-test)",
    )
    args = ap.parse_args()

    admissible, inadmissible = [], []
    for path in args.manifests:
        if not os.path.exists(path):
            print(f"manifest-validate: no such manifest: {path}", file=sys.stderr)
            return 2
        ok, problems = validate(path)
        (admissible if ok else inadmissible).append((path, problems))

    for path, _ in admissible:
        print(f"  admissible    {path}")
    for path, problems in inadmissible:
        print(f"  INADMISSIBLE  {path}")
        for p in problems:
            print(f"                  {p}")

    if args.expect_fail:
        return 0 if not admissible else 1
    return 0 if not inadmissible else 1


if __name__ == "__main__":
    sys.exit(main())
