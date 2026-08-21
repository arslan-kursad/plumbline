#!/usr/bin/env python3
"""Queries a view in the local BigQuery stand-in and writes rows as newline-delimited JSON.

The output is the same shape the golden files hold, so the comparison in the verify step
is against the fixtures themselves rather than against a second description of them.

BigQuery returns every value as a string in its REST response, tagged by the schema, so
the conversion back to typed JSON happens here — once, in one place.
"""

import argparse
import datetime
import json
import sys
import urllib.error
import urllib.request

PROJECT = "plumbline-local"


def query(base: str, sql: str) -> dict:
    request = urllib.request.Request(
        f"{base}/bigquery/v2/projects/{PROJECT}/queries",
        data=json.dumps({"query": sql, "useLegacySql": False}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        print(f"query failed: HTTP {error.code}\n{error.read().decode()[:800]}", file=sys.stderr)
        raise SystemExit(2)


def timestamp(raw: str) -> str:
    """Epoch seconds (BigQuery's wire form) back to the microsecond ISO form the rows use."""
    micros = round(float(raw) * 1_000_000)
    moment = datetime.datetime.fromtimestamp(micros / 1_000_000, datetime.timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{micros % 1_000_000:06d}Z"


def convert(value, kind: str):
    if value is None:
        return None
    if kind == "TIMESTAMP":
        return timestamp(value)
    if kind == "INTEGER":
        return int(value)
    if kind == "FLOAT":
        return float(value)
    if kind == "BOOLEAN":
        return value in (True, "true")
    if kind == "JSON":
        return json.loads(value) if isinstance(value, str) else value
    return value


def rows(result: dict) -> list[dict]:
    fields = result.get("schema", {}).get("fields", [])
    out = []
    for row in result.get("rows", []):
        values = row.get("f", [])
        out.append({
            field["name"]: convert(cell.get("v"), field.get("type", "STRING"))
            for field, cell in zip(fields, values)
        })
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bigquery", default="http://localhost:9050")
    parser.add_argument("--view", default="spans_deduped")
    parser.add_argument("--out", required=True)
    parser.add_argument("--count-only", action="store_true")
    args = parser.parse_args()

    # The partition filter is required on the base table and applies through the views
    # (architecture §7). A query without it is refused, and that refusal is the control
    # working — so the end-to-end path writes one the same way a dashboard has to.
    sql = (
        f"SELECT * FROM `{PROJECT}.plumbline.{args.view}` "
        "WHERE start_time >= TIMESTAMP('2020-01-01') "
        "ORDER BY trace_id, span_id"
    )

    result = rows(query(args.bigquery, sql))

    if args.count_only:
        print(len(result))
        return 0

    with open(args.out, "w", encoding="utf-8") as handle:
        for row in result:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")

    print(f"  {args.view}: {len(result)} row(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
