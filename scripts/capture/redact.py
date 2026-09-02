#!/usr/bin/env python3
"""Mechanical redaction for a fresh capture (F3E-02, ADR-0006, #10).

**The problem this is shaped around.** A denylist cannot be authored for an emitter
nobody has observed. `normalization/redaction/v1/claude-code.yaml` exists because a
capture came first and the rules were written from it; for the LangGraph adjudicator and
the .NET agent there is no capture, so there is no rule file, and there cannot be one yet.

So redaction here is **discovery-driven and refusing**, not declarative. It applies a rule
file when one exists, and it scans every attribute key and value against shapes that are
personal data in any dialect. Anything it matches and cannot account for **stops the
capture from being promoted**, with the key named.

That inversion is the point. A silent pass would mean "nothing matched my list", which for
an unobserved emitter is a statement about the list rather than about the data — and this
repository is public, where that difference is the whole risk (CLAUDE.md).

Operates on the OTLP JSON twin (`*.otlp.json`), which is the artefact the corpus already
carries beside each `request.pb` and the one the normalizer tests read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys

# Keys that are personal data whatever the dialect calls itself. Derived from the OTel
# resource semconv plus the identity block measured on the Claude Code emitter
# (docs/evidence/claude-code-otel-capture.md §4) — the second is included because a key
# observed on one real emitter is a shape, not a coincidence.
SUSPECT_KEYS = re.compile(
    r"(^|\.)(user|owner|author|customer|person)(\.|_|$)"
    r"|e[-_]?mail"
    r"|(^|\.)(session|organization|org|account|tenant)(\.|_)?id$"
    r"|account[-_]?uuid"
    r"|host[-_]?paths?"
    r"|(^|\.)(ip|client[-_]?ip|remote[-_]?addr)$"
    r"|api[-_]?key|token|secret|password|credential",
    re.I,
)

# Value shapes that are personal data regardless of the key they arrive under, because an
# emitter is free to put an email in a field called `note`.
SUSPECT_VALUES = [
    ("email address", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}")),
    ("absolute home path", re.compile(r"(/(?:home|Users)/[^/\s\"]+)")),
    ("bearer-ish token", re.compile(r"\b(?:sk|pk|ghp|gho|plb)_[A-Za-z0-9]{16,}")),
]


def marker(value: str) -> str:
    """ADR-0006's deterministic marker. Unkeyed, and the ADR states that limit."""
    return f"[REDACTED:sha256:{hashlib.sha256(value.encode()).hexdigest()[:8]}]"


def walk(node, path=""):
    """Yield (json_path, key, value) for every scalar under an OTLP document."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, path.split(".")[-1], node


def attribute_pairs(doc):
    """OTLP attributes are `{key, value:{stringValue: …}}`, not plain mappings.

    Walking raw JSON paths would report the literal keys `key` and `stringValue` instead
    of the attribute name, so the pairs are reconstructed here.
    """
    pairs = []

    def visit(node):
        if isinstance(node, dict):
            if "key" in node and "value" in node and isinstance(node["value"], dict):
                v = node["value"]
                scalar = next(
                    (v[t] for t in ("stringValue", "intValue", "doubleValue", "boolValue") if t in v),
                    None,
                )
                if scalar is not None:
                    pairs.append((node["key"], str(scalar), node["value"]))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(doc)
    return pairs


def load_rule_keys(path: str | None) -> set[str]:
    if not path:
        return set()
    keys = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^\s*-\s*key:\s*(\S+)", line)
            if m:
                keys.add(m.group(1))
    return keys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("payload", help="captured *.otlp.json")
    ap.add_argument("--rules", help="normalization/redaction/v1/<dialect>.yaml, when one exists")
    ap.add_argument("--out", help="write the redacted document here")
    ap.add_argument(
        "--allow",
        action="append",
        default=[],
        help="attribute key reviewed and declared safe; repeatable. Every use is a human "
             "decision and belongs in the manifest's rationale.",
    )
    args = ap.parse_args()

    with open(args.payload, encoding="utf-8") as fh:
        doc = json.load(fh)

    rule_keys = load_rule_keys(args.rules)
    allowed = set(args.allow)

    redacted_keys: set[str] = set()
    unaccounted: list[str] = []

    for key, scalar, value_obj in attribute_pairs(doc):
        reason = None
        if key in rule_keys:
            reason = "rule file"
        elif SUSPECT_KEYS.search(key):
            reason = "suspect key shape"
        else:
            for label, pattern in SUSPECT_VALUES:
                if pattern.search(scalar):
                    reason = f"suspect value shape: {label}"
                    break

        if reason is None:
            continue
        if key in allowed:
            continue

        if reason == "rule file":
            if "stringValue" in value_obj:
                value_obj["stringValue"] = marker(scalar)
            redacted_keys.add(key)
        else:
            unaccounted.append(f"{key}  — {reason}")

    if unaccounted:
        print("redact: REFUSED — keys matched that no rule file accounts for:\n", file=sys.stderr)
        for u in sorted(set(unaccounted)):
            print(f"  {u}", file=sys.stderr)
        print(
            "\nAdd each to normalization/redaction/v1/<dialect>.yaml with its reason, or "
            "pass --allow <key> after reviewing it. Neither is automatic: an unobserved "
            "emitter's denylist is written from its first capture, not before it.",
            file=sys.stderr,
        )
        return 1

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    print(f"redact: {len(redacted_keys)} key(s) redacted, 0 unaccounted")
    for k in sorted(redacted_keys):
        print(f"  {k}")
    print("\nrecord these under `redacted_fields:` in the fixture manifest (#10)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
