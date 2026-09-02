#!/usr/bin/env python3
"""Mechanical cross-reference check for docs/ (F3 entry directive F3E-04, issue #7).

Two defect classes, both of which this repository has shipped:

  1. An internal section reference — `§7.2` — pointing at a section the containing
     document does not have. Sections get renumbered; the references do not.
  2. A relative link whose target does not exist.

The hard part is not finding dangling references. It is not reporting the ones that are
fine. Most `§N` in this repository refer to *another* document, and a check that flags
those has traded one manual pass for another (F3E-04 acceptance criterion 3).

Qualification is decided by binding, not by co-presence. A document mention binds to the
section reference nearest to it; a reference with no document bound to it is read as
local and checked against the containing file's own headings. That rule is what separates
the two references in this real line, which co-occur in one sentence and point at two
different documents:

    6. **§4's `architecture.md` pin is refreshed** — v0.3 is ten versions stale (§9.1).

`architecture.md` sits 8 characters from `§4` and ~50 from `§9.1`, so it binds to `§4`.
`§9.1` is local, and at the commit that shipped it, local had no §9.1.

Standard library only. Read-only. Exit 0 always unless --strict: this ships non-blocking,
and flipping it to blocking is a separate decision (F3E-04 acceptance criterion 5).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

SECTION_RE = re.compile(r"§\s?(\d+(?:\.\d+)*)")
# A document mention. A filename is the unambiguous form, but this repository qualifies
# references in prose far more often than by path — "F0 spec §0.2", "architecture §7",
# "ADR-0004 §5". Every alias below was added because leaving it out produced a false
# positive on real text, not because it might.
DOCNAME_RE = re.compile(
    r"[\w./-]+\.md"
    r"|F\d\s+spec"
    r"|ADR-\d{4}"
    r"|architecture"
    r"|eval[-\s]plan"
    r"|project brief|the brief"
    r"|clos(?:ure|ing)\s+note|completion note"
    r"|decision log"
    r"|runbook"
    r"|directive"
    r"|the spec\b",
    re.I,
)
# ATX headings that open with a section number: "## 7. Foo", "### 7.2 Bar", "#### 4.1 Baz"
HEADING_NUM_RE = re.compile(r"^#{2,6}\s+(\d+(?:\.\d+)*)\s*[.—-]?\s")
# Some documents number sub-points as bold paragraph openers rather than headings —
# `**3.1 — Points 2 and 3 …**`. rubric-v1.md §3 is written that way, and a reference to
# §3.6 from its own freeze checklist is correct even though no heading carries it.
BOLD_NUM_RE = re.compile(r"^\*\*(\d+\.\d+(?:\.\d+)*)\s*[—.-]")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def declared_sections(text: str) -> set[str]:
    """Section numbers this document defines, including implied parents.

    A document with `### 7.2` but no `## 7` still legitimately carries §7 references:
    the parent is implied by the child. Not inferring it would produce false positives
    on every document that numbers subsections without a numbered parent heading.
    """
    out: set[str] = set()
    for line in text.splitlines():
        m = HEADING_NUM_RE.match(line) or BOLD_NUM_RE.match(line)
        if not m:
            continue
        num = m.group(1)
        parts = num.split(".")
        for i in range(1, len(parts) + 1):
            out.add(".".join(parts[:i]))
    return out


def strip_code(text: str) -> str:
    """Blank out fenced blocks, keeping line numbering intact.

    A `§` inside a shell block or a quoted log line is data, not a reference.
    """
    lines = text.splitlines()
    out, in_fence, marker = [], False, ""
    for line in lines:
        m = FENCE_RE.match(line)
        if m and not in_fence:
            in_fence, marker = True, m.group(1)
            out.append("")
            continue
        if in_fence:
            out.append("")
            if line.strip().startswith(marker):
                in_fence = False
            continue
        out.append(line)
    return "\n".join(out)


def bind_documents(line: str) -> dict[int, str]:
    """Map each section-reference offset to the document bound to it, if any.

    Each document mention claims the single nearest section reference on the line. A
    reference no document claims is local.
    """
    refs = [m.start() for m in SECTION_RE.finditer(line)]
    if not refs:
        return {}
    bound: dict[int, str] = {}
    for dm in DOCNAME_RE.finditer(line):
        centre = (dm.start() + dm.end()) // 2
        nearest = min(refs, key=lambda r: abs(r - centre))
        bound[nearest] = dm.group(0)
    return bound


def default_referent(text: str) -> str | None:
    """Whether the document establishes another document as its default section space.

    A runbook opens with "(architecture §6.3, F2 spec D5)" and then uses bare `§3.2`
    throughout. The binding is made once, at the top, for the whole file. Reading only
    the line would call every one of those a dangling local reference — which is the
    false-positive class that made the first version of this check useless.
    """
    head = "\n".join(text.splitlines()[:40])
    for m in re.finditer(r"[\w./-]+\.md|architecture|eval[-\s]plan", head, re.I):
        # A document that merely links to others has not adopted their numbering; the
        # tell is a document name sitting immediately before a section reference.
        tail = head[m.end() : m.end() + 12]
        if SECTION_RE.search(tail):
            return m.group(0)
    return None


_SECTION_CACHE: dict[str, set[str]] = {}


def resolves_in(docname: str, num: str, from_path: str, root: str) -> bool:
    """Does `num` exist as a section in the document `docname` names?

    Resolution is by basename across the docs tree: prose writes "architecture §7",
    not a path. A name that matches no file, or more than one, resolves nothing — an
    ambiguous reference is not an excuse for a dangling one.
    """
    base = os.path.basename(docname)
    if not base.endswith(".md"):
        base += ".md"
    key = base.lower()
    if key not in _SECTION_CACHE:
        matches = []
        for dirpath, _d, filenames in os.walk(os.path.join(root, "docs")):
            for name in filenames:
                if name.lower() == key:
                    matches.append(os.path.join(dirpath, name))
        if len(matches) != 1:
            _SECTION_CACHE[key] = set()
        else:
            with open(matches[0], encoding="utf-8") as fh:
                _SECTION_CACHE[key] = declared_sections(fh.read())
    return num in _SECTION_CACHE[key]


def check_file(path: str, root: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    declared = declared_sections(raw)
    borrowed = default_referent(raw)
    body = strip_code(raw)
    findings: list[dict] = []
    rel = os.path.relpath(path, root)

    for lineno, line in enumerate(body.splitlines(), 1):
        bound = bind_documents(line)
        for m in SECTION_RE.finditer(line):
            if m.start() in bound:
                continue  # qualified: belongs to another document
            num = m.group(1)
            if num in declared:
                continue
            # A document with no numbering of its own cannot hold a dangling *internal*
            # reference: every bare section number in it is necessarily somebody else's.
            # The ADRs are the case that forced this — they head with
            # "**Architecture:** §2.2, §3.2, …" and then use bare §N throughout, so the
            # default referent is established once per document rather than per line.
            if not declared:
                continue
            # Outside this document's own top-level numbering range, a bare reference is
            # another document's by construction. Inside it, a number the document does
            # not have is what renumbering leaves behind — which is the defect (#7).
            top = num.split(".")[0]
            if top not in {d.split(".")[0] for d in declared}:
                continue
            # A borrowed numbering space only excuses a reference it can actually
            # resolve. api-keys.md borrows architecture's and its §3.2 resolves there,
            # so it is fine. freeze-a-prep.md borrows eval-plan's and its §9.1 resolves
            # in neither — which is the difference between a convention and a defect.
            if borrowed is not None and resolves_in(borrowed, num, path, root):
                continue
            findings.append(
                {
                    "kind": "dangling-section",
                    "file": rel,
                    "line": lineno,
                    "ref": f"§{num}",
                    "detail": f"no §{num} heading in this file",
                    "context": line.strip()[:100],
                }
            )

        for lm in LINK_RE.finditer(line):
            target = lm.group(1)
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            filepart = target.split("#", 1)[0]
            if not filepart:
                continue
            resolved = os.path.normpath(os.path.join(os.path.dirname(path), filepart))
            if not os.path.exists(resolved):
                findings.append(
                    {
                        "kind": "dead-link",
                        "file": rel,
                        "line": lineno,
                        "ref": target,
                        "detail": "link target does not exist",
                        "context": line.strip()[:100],
                    }
                )
    return findings


def walk(docs_dir: str, root: str) -> list[dict]:
    findings: list[dict] = []
    for dirpath, _dirnames, filenames in os.walk(docs_dir):
        for name in sorted(filenames):
            if name.endswith(".md"):
                findings.extend(check_file(os.path.join(dirpath, name), root))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--docs", default="docs", help="directory to scan")
    ap.add_argument("--root", default=".", help="path prefix stripped from reports")
    ap.add_argument("--json", dest="json_out", help="write findings as JSON to this path")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero on findings; off by default, this job is non-blocking",
    )
    args = ap.parse_args()

    if not os.path.isdir(args.docs):
        print(f"xref: no such directory: {args.docs}", file=sys.stderr)
        return 2

    findings = walk(args.docs, args.root)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump({"findings": findings}, fh, indent=2)
            fh.write("\n")

    if not findings:
        print(f"xref: no dangling references or dead links under {args.docs}/")
        return 0

    print(f"xref: {len(findings)} finding(s) under {args.docs}/\n")
    for f in findings:
        print(f"  {f['file']}:{f['line']}  {f['ref']}  — {f['detail']}")
        print(f"      {f['context']}")
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
