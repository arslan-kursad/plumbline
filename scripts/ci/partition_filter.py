#!/usr/bin/env python3
"""Every query against the spans dataset must constrain `start_time`.

`require_partition_filter = TRUE` is enforced by BigQuery in the cloud and by nothing at
all locally: the stand-in cannot create a partitioned table, so the local table carries no
such requirement (T1-01, closed as unsatisfiable). What that leaves is recorded in
`docs/evidence/f3e-01b-rejection-probe.md`:

    a query written outside the e2e path -- a view, a dashboard, an eval-engine read --
    meets no local objection. That is the gap, and it is a gap in coverage rather than in
    behaviour.

This closes the reachable half. It does not restore emulator fidelity and does not claim
to: it constrains the repository where the engine cannot be constrained, so a query that
forgets the predicate is caught by review rather than by a production refusal.

Four things it must not do, each of which would make it worse than nothing:

1. **Flag a view definition.** `002_spans_deduped.sql` reads `FROM spans` with no
   predicate, deliberately: the consumer's `start_time` filter is pushed below the window
   (ADR-0007 D2). Requiring a predicate there would mean requiring the views to be wrong.
2. **Flag a query whose predicate is supplied by interpolation.** `cloud.py`'s
   `scoped_query` builds `WHERE {window.predicate()}`, and `predicate()` is where
   `start_time` lives. That path is the most rigorously filtered in the repository -- eight
   tests in `cloud_test.py` assert it -- and reporting it as unfiltered would be exactly
   backwards. It is reported as *unverifiable here*, which is what it is.
3. **Flag a query that is deliberately unfiltered.** `scripts/probe/rejection-probe.sh`
   issues queries with no predicate on purpose, because their refusal is the measurement.
   Those carry a marker, so the intent is declared in the file rather than hidden in an
   exclusion list inside this checker.
4. **Miss a query because its table name is interpolated.** `query-rows.py` selects from
   `{PROJECT}.plumbline.{args.view}`. Module-level string constants are resolved, and a
   reference landing in the `plumbline` dataset counts as a site even when the view name
   does not survive.

Usage:
    python3 scripts/ci/partition_filter.py [<root>...]
"""

import ast
import pathlib
import re
import sys

TABLES = ("spans", "spans_deduped", "spans_real")
DATASET = "plumbline"

# A site is a FROM/JOIN against a backticked reference. The reference is matched loosely
# because half of them are built by interpolation.
SITE = re.compile(r"\b(?:FROM|JOIN)\s+`([^`]*)`", re.IGNORECASE)
CREATE_VIEW = re.compile(r"\bCREATE\s+(?:OR\s+REPLACE\s+)?VIEW\b", re.IGNORECASE)

# The predicate itself is interpolated -- `WHERE {…}` -- so this file cannot see whether
# it constrains start_time. Narrow on purpose: `WHERE x = {…}` is not this case, and must
# still be required to name start_time somewhere.
INTERPOLATED_PREDICATE = re.compile(r"\bWHERE\s+\{\?\}", re.IGNORECASE)

# Declared, not excluded. A query that is meant to carry no predicate says so where it is
# written, and the reason travels with it.
MARKER = "partition-filter: intentionally-absent"

PLACEHOLDER = "{?}"


def targets_spans(reference: str) -> bool:
    """Does a backticked reference address the spans dataset?"""
    tail = reference.rsplit(".", 1)[-1]
    if tail in TABLES:
        return True
    # An interpolated view name still counts when the dataset is named: the query is
    # against this dataset whatever the view turns out to be.
    return PLACEHOLDER in tail and f".{DATASET}." in reference


def classify(text: str) -> str:
    if CREATE_VIEW.search(text):
        return "view-definition"
    if re.search(r"\bstart_time\b", text):
        return "filtered"
    if INTERPOLATED_PREDICATE.search(text):
        return "interpolated-predicate"
    return "UNFILTERED"


def sites_in(text: str) -> bool:
    return any(targets_spans(ref) for ref in SITE.findall(text))


def render(node, consts):
    """A string or f-string as text, with module-level constants resolved.

    Adjacent literal concatenation is folded by the parser, so a query built as a
    parenthesised run of literals arrives here as one node -- which is what makes the
    SELECT and its WHERE visible together.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out = []
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                out.append(part.value)
            elif isinstance(part, ast.FormattedValue):
                inner = part.value
                if isinstance(inner, ast.Name) and inner.id in consts:
                    out.append(consts[inner.id])
                else:
                    out.append(PLACEHOLDER)
        return "".join(out)
    return None


def declared(lines, index) -> bool:
    """Is the site marked, on its own line or in the comment block above it?

    The block is walked rather than a fixed number of lines being checked: a marker
    carrying its reason often runs to two or three comment lines, and a reason long enough
    to be useful must not push the marker itself out of range.
    """
    if index < len(lines) and MARKER in lines[index]:
        return True
    cursor = index - 1
    while cursor >= 0:
        stripped = lines[cursor].strip()
        if not (stripped.startswith("#") or stripped.startswith("--") or not stripped):
            break
        if MARKER in lines[cursor]:
            return True
        cursor -= 1
    return False


def analyze_python(text, path, findings):
    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        findings.append((str(path), 0, "UNPARSEABLE", f"{error}"))
        return

    consts = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant) \
                    and isinstance(node.value.value, str):
                consts[target.id] = node.value.value

    lines = text.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Constant, ast.JoinedStr)):
            continue
        rendered = render(node, consts)
        if not rendered or not sites_in(rendered):
            continue
        line = getattr(node, "lineno", 1)
        if declared(lines, line - 1):
            findings.append((str(path), line, "declared-absent", ""))
            continue
        findings.append((str(path), line, classify(rendered), first_line(rendered)))


def analyze_sql(text, path, findings):
    lines = text.splitlines()
    offset = 1
    for statement in text.split(";"):
        if sites_in(statement):
            line = offset + statement[:statement.lower().find("from")].count("\n")
            if declared(lines, line - 1):
                findings.append((str(path), line, "declared-absent", ""))
            else:
                findings.append((str(path), line, classify(statement), first_line(statement)))
        offset += statement.count("\n")


def analyze_shell(text, path, findings):
    """The unit is the logical line, so a backslash continuation stays with its command.

    It has to be: the SQL sits on the continuation and the marker sits in the comment
    block above the command, with the command itself in between. Scanning physical lines
    would put the marker out of reach of the site it belongs to.
    """
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        start = index
        logical = lines[index]
        while logical.rstrip().endswith("\\") and index + 1 < len(lines):
            index += 1
            logical = logical.rstrip()[:-1] + lines[index]
        index += 1

        if logical.lstrip().startswith("#") or not sites_in(logical):
            continue
        if declared(lines, start):
            findings.append((str(path), start + 1, "declared-absent", ""))
            continue
        findings.append((str(path), start + 1, classify(logical), first_line(logical)))


def first_line(text):
    return " ".join(text.split())[:110]


def scan(roots):
    findings = []
    for root in roots:
        base = pathlib.Path(root)
        # Fixture corpora are skipped when scanning the tree and scanned when named
        # directly -- otherwise the self-test would scan nothing and pass, which is the
        # failure mode this checker is built to refuse in other people's code.
        inside_fixtures = "testdata" in base.parts
        paths = [base] if base.is_file() else sorted(
            p for p in base.rglob("*") if p.suffix in (".sql", ".py", ".sh"))
        for path in paths:
            if "__pycache__" in path.parts:
                continue
            if not inside_fixtures and "testdata" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if path.suffix == ".py":
                analyze_python(text, path, findings)
            elif path.suffix == ".sql":
                analyze_sql(text, path, findings)
            elif path.suffix == ".sh":
                analyze_shell(text, path, findings)
    return findings


def main(argv):
    roots = argv[1:] or ["analytics/sql", "scripts"]
    findings = scan(roots)

    counts = {}
    for _, _, kind, _ in findings:
        counts[kind] = counts.get(kind, 0) + 1

    print(f"partition filter: {len(findings)} query site(s) against the {DATASET} dataset")
    for kind in sorted(counts):
        print(f"  {counts[kind]:3d}  {kind}")

    bad = [f for f in findings if f[2] in ("UNFILTERED", "UNPARSEABLE")]

    # A scan that finds no site at all is not a clean tree -- it is a broken scanner, and
    # it would report success forever. The corpus is known to contain query sites.
    if not findings:
        print("\nno query site found at all; the scanner is looking in the wrong place",
              file=sys.stderr)
        return 2

    if bad:
        print("", file=sys.stderr)
        for path, line, kind, excerpt in bad:
            print(f"  {path}:{line}  {kind}", file=sys.stderr)
            if excerpt:
                print(f"      {excerpt}", file=sys.stderr)
        print(f"\n{len(bad)} query site(s) reach the {DATASET} dataset without constraining "
              "start_time", file=sys.stderr)
        return 1

    print("\nevery query site constrains start_time, is a view definition, "
          "or declares its absence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
