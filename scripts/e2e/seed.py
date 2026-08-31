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


def strip_sql_comments(sql: str) -> str:
    """Remove `--` line comments and `/* */` blocks, preserving everything else.

    Comments are semantically inert in SQL, so this changes nothing under test. It
    exists because the local stand-in is not inert about them: `goccy/bigquery-emulator`
    0.8.1 scans the statement text for the keywords that open a partitioning clause,
    finds them in a comment, and answers the whole file with HTTP 200, a result set and
    no view -- silently (decision log W2.16, issue #91).

    Real BigQuery parses the same text correctly; `bq query --dry_run` against the pre-fix
    comment returns `Query successfully validated.` (W2.17). So this is not a fix to our
    SQL, which was never wrong, but a translation for one third-party parser -- placed in
    our code because 0.8.1 is that project's latest release and there is no upgrade to take.

    Quoting is tracked rather than ignored, because a `--` inside a string literal is data
    and removing it would change the statement. Newlines survive so that a parse error
    still points at the line the author wrote.

    The alternative -- a gate forbidding those keywords in `analytics/sql/*.sql` comments --
    is rejected and stays rejected: F2C-02 requires an explanatory premise comment in
    exactly these files, so a keyword ban makes them hostile to documentation the directive
    itself mandates.
    """
    out = []
    quote = None          # "'", '"' or "`" while inside a literal or quoted identifier
    comment = None        # "line" or "block" while inside a comment
    i = 0
    while i < len(sql):
        pair = sql[i:i + 2]
        char = sql[i]

        if comment == "line":
            if char == "\n":
                comment = None
                out.append(char)
            i += 1
            continue

        if comment == "block":
            if pair == "*/":
                comment = None
                i += 2
                continue
            # Newlines are kept so line numbers do not shift under the stripper.
            if char == "\n":
                out.append(char)
            i += 1
            continue

        if quote:
            out.append(char)
            if char == "\\" and i + 1 < len(sql):
                out.append(sql[i + 1])
                i += 2
                continue
            if char == quote:
                quote = None
            i += 1
            continue

        if pair == "--":
            comment = "line"
            i += 2
            continue
        if pair == "/*":
            comment = "block"
            i += 2
            continue
        if char in "'\"`":
            quote = char

        out.append(char)
        i += 1

    return "".join(out)


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

    ddl = strip_sql_comments((sql_dir / "001_spans_table.sql").read_text())
    fields = table_schema(ddl)
    if not fields:
        print("  FAILED  could not parse a schema out of 001_spans_table.sql", file=sys.stderr)
        return 1

    # Columns only. The stand-in refuses `CREATE TABLE ... PARTITION BY` outright, and a
    # table created through this API carrying `timePartitioning` does not resolve on its
    # Storage Write default stream either — measured, both times, in CI.
    #
    # So the local table is an unpartitioned, unclustered copy of the same columns. That
    # is a real difference from the cloud table and it is printed on every run rather
    # than buried here: `require_partition_filter` is a cost invariant (architecture §7)
    # and it is Terraform, not this file, that carries it in F2. What the local stack can
    # still check is that every query written against these views carries a partition
    # filter anyway — which the query step does, exactly as a dashboard would have to.
    resource = {
        "tableReference": {"projectId": PROJECT, "datasetId": DATASET, "tableId": "spans"},
        "schema": {"fields": fields},
    }

    status, body = request("POST", tables, resource)
    report(f"table {DATASET}.spans ({len(fields)} columns, unpartitioned — see the comment in this file)",
           status, body)
    if status >= 400 and status != 409 and "already exists" not in body.lower():
        return 1

    failures = 0
    for path in sorted(sql_dir.glob("*.sql")):
        if path.name.startswith("001_"):
            continue  # created above, through the API the stand-in supports
        # Read once and strip once. The statement that is POSTed and the statement the
        # existence check below reads have to be the same text, or the check verifies a
        # claim about a file rather than about what was sent.
        statement = strip_sql_comments(path.read_text())
        status, body = request("POST", queries, {"query": statement, "useLegacySql": False})

        # A 200 is not success. The stand-in answers some rejected statements with
        # HTTP 200 and the failure inside the payload, and answers others with a
        # clean 200 while creating nothing at all. Status and payload are two
        # different claims, and neither is the same claim as "the object exists".
        if status < 400 and '"errors"' in body:
            status = 400

        report(f"sql {path.name}", status, body)
        if status >= 400:
            failures += 1
            continue

        # The claim that matters. A DDL reported `ok` that produced no object made
        # the *next* file fail with `Table not found`, naming a symptom one statement
        # away from its cause. Ask the stand-in what it actually holds.
        created = re.findall(r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+`?[\w-]*\.?(\w+)`?",
                             statement, re.IGNORECASE)
        for name in created:
            if name not in existing_tables(base):
                print(f"  FAILED  sql {path.name}: reported ok but {DATASET}.{name} does not exist",
                      file=sys.stderr)
                failures += 1

    print(f"  dataset now holds: {sorted(existing_tables(base))}")
    return failures


def existing_tables(base: str) -> set[str]:
    """What the stand-in actually holds, as opposed to what it accepted."""
    status, body = request(
        "GET", f"{base}/bigquery/v2/projects/{PROJECT}/datasets/{DATASET}/tables")
    if status >= 400:
        return set()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return set()
    return {t.get("tableReference", {}).get("tableId", "") for t in payload.get("tables", [])}


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
