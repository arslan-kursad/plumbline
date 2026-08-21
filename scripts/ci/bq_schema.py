"""Derive a BigQuery table schema from the DDL the local stand-in applies.

`analytics/sql/001_spans_table.sql` is the authored definition of the `spans`
column set (architecture §4.1). Terraform needs the same columns as a BigQuery
JSON schema, and a second hand-written copy of thirty columns is the silent
divergence D4 exists to prevent — a column added in one place and forgotten in the
other produces a local test that passes against a shape the cloud does not have.

So the JSON is generated from the DDL and guarded by a diff in CI
(`bq-schema-guard.sh`). The DDL stays authored, comments and all; the JSON stays
mechanical.

Parsing is deliberately narrow. It reads the column list of one CREATE TABLE and
refuses anything it does not recognise, because a parser that silently skips a
line it cannot read would drop a column and produce a schema that looks fine.
"""

import json
import re
import sys

# BigQuery's REST schema uses the legacy type names, not the standard SQL ones the
# DDL is written in. Mapping them explicitly beats hoping the API accepts both.
TYPES = {
    "TIMESTAMP": "TIMESTAMP",
    "STRING": "STRING",
    "BOOL": "BOOLEAN",
    "INT64": "INTEGER",
    "FLOAT64": "FLOAT",
    "JSON": "JSON",
    "DATE": "DATE",
    "NUMERIC": "NUMERIC",
    "BYTES": "BYTES",
}

COLUMN = re.compile(
    r"""^\s+
        (?P<name>[a-z_][a-z0-9_]*)\s+
        (?P<type>[A-Z0-9]+)
        (?P<required>\s+NOT\s+NULL)?
        \s*,?\s*
        (--.*)?$
    """,
    re.VERBOSE,
)


def columns(ddl):
    """Yields the column list of the first CREATE TABLE in `ddl`."""
    body = re.search(
        r"CREATE\s+TABLE[^(]*\((.*?)^\)", ddl, re.DOTALL | re.MULTILINE
    )
    if not body:
        raise SystemExit("no CREATE TABLE column list found")

    for number, line in enumerate(body.group(1).splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue

        match = COLUMN.match(line)
        if not match:
            raise SystemExit(
                f"line {number} of the column list is not a column this parser "
                f"understands, and skipping it would silently drop a column:\n  {stripped}"
            )

        sql_type = match.group("type")
        if sql_type not in TYPES:
            raise SystemExit(f"unknown column type {sql_type!r} on: {stripped}")

        yield {
            "name": match.group("name"),
            "type": TYPES[sql_type],
            "mode": "REQUIRED" if match.group("required") else "NULLABLE",
        }


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: bq_schema.py <table.sql>")

    with open(sys.argv[1], encoding="utf-8") as handle:
        schema = list(columns(handle.read()))

    if not schema:
        raise SystemExit("parsed no columns; refusing to emit an empty schema")

    print(json.dumps(schema, indent=2))


if __name__ == "__main__":
    main()
