#!/usr/bin/env python3
"""Seeds the local stand-ins: Pub/Sub topology and the BigQuery table and views.

Talks to both emulators over their REST APIs from the host, so the seeding step needs no
container of its own and its failures are readable rather than buried in compose output.

Idempotent: every create tolerates "already exists", so a partially seeded stack can be
re-seeded rather than torn down.
"""

import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

PROJECT = "plumbline-local"
DATASET = "plumbline"


def request(method: str, url: str, body: dict | None = None) -> tuple[int, str]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def pubsub(base: str, worker_push_url: str) -> int:
    """Topics, the push subscription, and the dead-letter path (architecture §3.2, §3.4)."""
    root = f"{base}/v1/projects/{PROJECT}"

    for topic in ("traces", "traces-dlq"):
        status, body = request("PUT", f"{root}/topics/{topic}", {})
        report(f"topic {topic}", status, body)

    # max_delivery_attempts = 5, then traces-dlq. The worker never decides a message has
    # failed enough times; this policy does.
    status, body = request("PUT", f"{root}/subscriptions/traces-push", {
        "topic": f"projects/{PROJECT}/topics/traces",
        "pushConfig": {"pushEndpoint": worker_push_url},
        "ackDeadlineSeconds": 10,
        "deadLetterPolicy": {
            "deadLetterTopic": f"projects/{PROJECT}/topics/traces-dlq",
            "maxDeliveryAttempts": 5,
        },
    })
    report("subscription traces-push", status, body)

    # A pull subscription with no consumer, so a dead-lettered message is retained and
    # countable rather than discarded (§3.4).
    status, body = request("PUT", f"{root}/subscriptions/traces-dlq-pull", {
        "topic": f"projects/{PROJECT}/topics/traces-dlq",
    })
    report("subscription traces-dlq-pull", status, body)

    return 0


SQL_TO_BIGQUERY = {
    "TIMESTAMP": "TIMESTAMP",
    "STRING": "STRING",
    "BOOL": "BOOLEAN",
    "INT64": "INTEGER",
    "FLOAT64": "FLOAT",
    "JSON": "JSON",
}


def table_schema(ddl: str) -> list[dict]:
    """Derives the table's field list from analytics/sql/001_spans_table.sql.

    The SQL file stays the single definition of the table. The local stand-in cannot
    execute `CREATE TABLE ... PARTITION BY`, so the table is created here through the
    REST API instead — from the same file, parsed, rather than from a second schema
    written by hand that would drift from it the first time a column is added.
    """
    fields = []
    for match in re.finditer(
        r"^  ([a-z][a-z0-9_]*)\s+(TIMESTAMP|STRING|BOOL|INT64|FLOAT64|JSON)(\s+NOT NULL)?",
        ddl,
        re.MULTILINE,
    ):
        name, sql_type, not_null = match.groups()
        fields.append({
            "name": name,
            "type": SQL_TO_BIGQUERY[sql_type],
            "mode": "REQUIRED" if not_null else "NULLABLE",
        })
    return fields


def bigquery(base: str, sql_dir: pathlib.Path) -> int:
    """Creates the table from 001_spans_table.sql, then applies the view DDL."""
    tables = f"{base}/bigquery/v2/projects/{PROJECT}/datasets/{DATASET}/tables"
    queries = f"{base}/bigquery/v2/projects/{PROJECT}/queries"

    ddl = (sql_dir / "001_spans_table.sql").read_text()
    fields = table_schema(ddl)
    if not fields:
        print("  FAILED  could not parse a schema out of 001_spans_table.sql", file=sys.stderr)
        return 1

    resource = {
        "tableReference": {"projectId": PROJECT, "datasetId": DATASET, "tableId": "spans"},
        "schema": {"fields": fields},
        "timePartitioning": {"type": "DAY", "field": "start_time", "requirePartitionFilter": True},
        "clustering": {"fields": ["trace_id", "span_id"]},
    }

    status, body = request("POST", tables, resource)
    if status >= 400 and status != 409 and "already exists" not in body.lower():
        # The stand-in may refuse partitioning or clustering outright. Retry without them
        # and say so: a local table that is not partitioned is a difference between this
        # stack and the cloud, and a difference nobody was told about is the kind that
        # gets discovered in F2.
        print(f"  note    partitioned table refused by the stand-in; creating an unpartitioned one\n"
              f"          ({body[:200]})")
        resource.pop("timePartitioning")
        resource.pop("clustering")
        status, body = request("POST", tables, resource)

    report(f"table {DATASET}.spans ({len(fields)} columns)", status, body)
    if status >= 400 and status != 409 and "already exists" not in body.lower():
        return 1

    failures = 0
    for path in sorted(sql_dir.glob("*.sql")):
        if path.name.startswith("001_"):
            continue  # created above, through the API the stand-in supports
        status, body = request("POST", queries, {"query": path.read_text(), "useLegacySql": False})
        report(f"sql {path.name}", status, body)
        if status >= 400:
            failures += 1

    return failures


def report(what: str, status: int, body: str) -> None:
    if status < 400:
        print(f"  ok      {what}")
        return

    if "already exists" in body.lower() or status == 409:
        print(f"  exists  {what}")
        return

    print(f"  FAILED  {what}: HTTP {status}\n          {body[:400]}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pubsub", default="http://localhost:8085")
    parser.add_argument("--bigquery", default="http://localhost:9050")
    parser.add_argument("--worker-push", default="http://worker:8080/push")
    parser.add_argument("--sql", default="analytics/sql")
    args = parser.parse_args()

    print("seeding pub/sub")
    failures = pubsub(args.pubsub, args.worker_push)

    print("seeding bigquery")
    failures += bigquery(args.bigquery, pathlib.Path(args.sql))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
