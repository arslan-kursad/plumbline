"""The cloud end-to-end harness: run-scoped corpus, guards, and the queries that prove DoD 3.

F2 completion directive v1.7, Decisions 6-13. Entry points are
`scripts/e2e/run-cloud.sh` (`make e2e-cloud`) and its `--drill` form
(`make e2e-cloud-drill`).

Read this before changing anything here: **the first cloud execution of this harness is
the DoD 7b exam, and the exam is taken once.** Everything in `arming` exists so that an
accidental invocation cannot spend it.
"""

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys

PROJECT = "plumbline-19458"
DATASET = "plumbline"
REPO = pathlib.Path(__file__).resolve().parents[2]
SQL_DIR = REPO / "analytics" / "sql"
FIXTURES = REPO / "testdata" / "fixtures"

# Stages, in the order the pipeline traverses them. The names are the branches of the
# fault tree in docs/runbooks/wave4-first-delivery.md, so a failure here names the section
# of the runbook that triages it instead of leaving that mapping to whoever is on call.
STAGES = ("view_provenance", "publish", "push_auth", "normalize", "write", "query", "complete")

# Where the run id actually lands in the `attributes` column.
#
# Resource attributes are nested under `resource` by the normalizer -- the column holds
# {"resource": {...}, "scope": {...}, "span": {...}} -- so the obvious top-level path
# returns NULL for every row. A run-scoped query written that way matches nothing and its
# assertions pass over an empty set, which is the failure mode that would have surfaced
# during the DoD 7b exam rather than before it. Pinned by a test against a committed
# golden file (cloud_test.py), not by this comment.
RUN_ID_JSON_PATH = '$.resource."plumbline.e2e_run_id"'
RUN_ID_ATTRIBUTE = "plumbline.e2e_run_id"


class Refused(Exception):
    """A guard refused. Carries the reason the operator needs, not a stack trace."""


# --- Decision 10: the cloud target is armed explicitly, never by default ----------------


def arming(env, run_id):
    """Refuse a cloud run that was not asked for twice.

    Amendment 6 forbids running this against the cloud before F2C-11, because the first
    cloud run *is* the DoD 7b exam. A prohibition guarded by a remembered rule is this
    project's named anti-pattern, so it is a mechanism here: the default target is the
    emulator, and cloud needs both an explicit variable and a run id on the command line.
    """
    target = env.get("PLUMBLINE_E2E_TARGET", "emulator")
    if target != "cloud":
        return "emulator"

    if not run_id:
        raise Refused(
            "PLUMBLINE_E2E_TARGET=cloud needs an explicit --run-id.\n"
            "The first cloud run of this harness is the DoD 7b exam (directive F2C-11) "
            "and it is taken once; it is not spent by an argumentless invocation."
        )
    # Must start and end alphanumeric. The run id is written into every span, queried
    # back verbatim, and used in file names and evidence archives -- a trailing hyphen
    # reads as a truncation, and an ambiguous identifier in an evidence artefact is the
    # thing that has to be re-derived later to be trusted.
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", run_id):
        raise Refused(
            f"run id {run_id!r} is not usable: lowercase letters, digits and hyphens, "
            "starting and ending alphanumeric, 3-63 characters. "
            "It is written into every span and queried back verbatim."
        )
    return "cloud"


# --- Decision 7: no query can be issued without a partition window ---------------------


class PartitionWindow:
    """An explicit `(lower, upper)` window on `start_time`, required by construction.

    `require_partition_filter` refuses a query with no predicate, so a convention would
    merely fail loudly. The reason this is a type rather than a habit is the second
    invariant: a broad scan satisfies the filter and still spends the query budget. The
    window comes from the run's own emission timestamps, never from `CURRENT_DATE()`.
    """

    def __init__(self, lower: dt.date, upper: dt.date):
        if upper < lower:
            raise Refused(f"partition window ends before it starts: {lower} .. {upper}")
        if (upper - lower).days > 7:
            raise Refused(
                f"partition window spans {(upper - lower).days} days ({lower} .. {upper}). "
                "A run emits within minutes; a window this wide is a full scan wearing a filter."
            )
        self.lower, self.upper = lower, upper

    @classmethod
    def around(cls, moment: dt.datetime, margin_days: int = 1):
        """The window one instant implies, with a day either side for UTC edges."""
        day = moment.astimezone(dt.timezone.utc).date()
        return cls(day - dt.timedelta(days=margin_days), day + dt.timedelta(days=margin_days))

    @classmethod
    def for_corpus(cls, corpus_dir: pathlib.Path, margin_days: int = 1):
        """The window the corpus's own `start_time` values imply.

        Decision 7 says the window comes from the run's emission timestamps and **not**
        from `CURRENT_DATE()`. Deriving it from wall-clock time was wrong in the quiet
        direction and was caught only by querying by hand: the fixtures carry static
        timestamps -- 2026-08-19 -- and Decision 6 deliberately leaves `start_time`
        untouched, so a now-shaped window never overlaps the data. Every scoped query then
        returns nothing, and *every* assertion passes over an empty set: rows equal
        distinct spans equal zero, unflagged is zero, leaked is zero. A perfect result and
        no data (decision log W3.18).
        """
        moments = []
        for twin in sorted(corpus_dir.glob("*.otlp.json")):
            payload = json.loads(twin.read_text())
            for resource_spans in payload.get("resourceSpans", []):
                for scope_spans in resource_spans.get("scopeSpans", []):
                    for span in scope_spans.get("spans", []):
                        nanos = span.get("startTimeUnixNano")
                        if nanos:
                            moments.append(int(nanos) / 1_000_000_000)
        if not moments:
            raise Refused(
                f"no span timestamps under {corpus_dir}; the window cannot be derived from "
                "the corpus, and deriving it from the clock is what Decision 7 forbids"
            )
        lower = dt.datetime.fromtimestamp(min(moments), dt.timezone.utc).date()
        upper = dt.datetime.fromtimestamp(max(moments), dt.timezone.utc).date()
        return cls(lower - dt.timedelta(days=margin_days), upper + dt.timedelta(days=margin_days))

    def predicate(self, column: str = "start_time") -> str:
        return f"DATE({column}) BETWEEN '{self.lower}' AND '{self.upper}'"

    def __repr__(self):
        return f"PartitionWindow({self.lower} .. {self.upper})"


def scoped_query(window: PartitionWindow, run_id: str, select: str, view: str) -> str:
    """Every query the harness issues comes through here. There is no other path."""
    if not isinstance(window, PartitionWindow):
        raise Refused("a query was built without a PartitionWindow; that is the one thing this refuses")
    return (
        f"SELECT {select} FROM `{PROJECT}.{DATASET}.{view}` "
        f"WHERE {window.predicate()} "
        f"AND JSON_VALUE(attributes, '{RUN_ID_JSON_PATH}') = '{run_id}'"
    )


# --- Decision 6 (+ issue #102): run-derived identity, so a second run is a second run ---


def derive_id(run_id: str, original: str) -> str:
    """A per-run identifier of the same length, derived deterministically.

    Decision 6 scopes the harness by a run-id resource attribute. That attribute lands in
    the lossless `attributes` column, which is not in the dedup window and cannot be -- so
    on its own it does not make a re-run a new run: `spans_deduped` keeps one row per
    `(trace_id, span_id, start_time)`, and a second send of a static corpus collapses into
    the first. Issue #102.

    Deriving identity from the run id fixes that without touching `start_time`, which would
    move rows between partitions and make Decision 7's window a function of the run rather
    than of the data. Deterministic because Decision 12 normalizes the same corpus locally
    and both sides have to produce the same ids from the same run id.
    """
    digest = hashlib.sha256(f"{run_id}/{original}".encode()).hexdigest()
    return digest[: len(original)]


def build_corpus(run_id: str, out_dir: pathlib.Path) -> list[pathlib.Path]:
    """Write the run's OTLP/JSON twins: every fixture, re-identified and flagged.

    Poison fixtures are excluded here and sent only by the drill (Decision 9): the happy
    path and the failure path are separate exams and a single corpus would fire both.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    for twin in sorted(FIXTURES.glob("*/*/request.otlp.json")):
        if twin.parent.name == "poison":
            continue
        payload = json.loads(twin.read_text())

        for resource_spans in payload.get("resourceSpans", []):
            attributes = resource_spans.setdefault("resource", {}).setdefault("attributes", [])
            # Decision 2, and Decision 6. Both are resource attributes so they apply to
            # every span under the resource without being repeated per span.
            attributes.append({"key": "synthetic", "value": {"boolValue": True}})
            attributes.append({"key": "plumbline.e2e_run_id", "value": {"stringValue": run_id}})

            for scope_spans in resource_spans.get("scopeSpans", []):
                for span in scope_spans.get("spans", []):
                    for field in ("traceId", "spanId", "parentSpanId"):
                        if span.get(field):
                            span[field] = derive_id(run_id, span[field])

        target = out_dir / f"{twin.parent.parent.name}-{twin.parent.name}.otlp.json"
        target.write_text(json.dumps(payload, indent=2) + "\n")
        written.append(target)

    if not written:
        raise Refused(f"no fixture twins found under {FIXTURES}")
    return written


# --- Decision 8: stage 0 is view-definition provenance ---------------------------------


def repo_window_clause(sql_path: pathlib.Path) -> str:
    """The window's PARTITION BY columns as the repository declares them."""
    from seed import strip_sql_comments  # same stripper; comments are not the definition

    text = strip_sql_comments(sql_path.read_text())
    match = re.search(r"PARTITION\s+BY\s+([^\n)]+)", text, re.IGNORECASE)
    if not match:
        raise Refused(f"{sql_path.name} declares no window; provenance cannot be checked")
    return normalise_columns(match.group(1))


def normalise_columns(clause: str) -> str:
    return ", ".join(part.strip().strip("`") for part in clause.split(",") if part.strip())


def deployed_window_clause(view: str, runner=subprocess.run) -> str:
    """The same clause, read from the deployed view rather than from intent."""
    proc = runner(
        ["bq", f"--project_id={PROJECT}", "show", "--format=prettyjson", f"{DATASET}.{view}"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise Refused(f"could not read deployed view {view}:\n{proc.stdout or proc.stderr}")
    query = json.loads(proc.stdout).get("view", {}).get("query", "")
    match = re.search(r"PARTITION\s+BY\s+([^\n)]+)", query, re.IGNORECASE)
    if not match:
        raise Refused(f"deployed {view} declares no window")
    return normalise_columns(match.group(1))


def check_provenance(view: str = "spans_deduped", runner=subprocess.run) -> str:
    """Abort before sending anything if the deployed view is not the one in the repository.

    A stale view fails the golden diff with a normalization-shaped error that is really a
    deployment-shaped one. This phase has already spent four days on one misread failure
    (W2.16); the cost of being wrong about which layer failed is measured in days, and this
    check costs one API read.
    """
    expected = repo_window_clause(SQL_DIR / "002_spans_deduped.sql")
    actual = deployed_window_clause(view, runner=runner)
    if expected != actual:
        raise Refused(
            f"deployed {view} does not match the repository.\n"
            f"  repo:     PARTITION BY {expected}\n"
            f"  deployed: PARTITION BY {actual}\n"
            "This is a deployment gap, not a normalization one. Apply Wave 4 first (#61)."
        )
    return actual


# --- Decision 11: the result names the stage it reached --------------------------------


class Result:
    """Machine-readable progress, written whether the run passes or fails."""

    def __init__(self, run_id: str, target: str):
        self.run_id, self.target = run_id, target
        self.stage = STAGES[0]
        self.started = dt.datetime.now(dt.timezone.utc)
        self.notes: list[str] = []
        self.failure: str | None = None

    def reached(self, stage: str):
        if stage not in STAGES:
            raise Refused(f"{stage!r} is not one of the declared stages: {', '.join(STAGES)}")
        self.stage = stage
        return self

    def note(self, text: str):
        self.notes.append(text)
        return self

    def document(self) -> dict:
        return {
            "run_id": self.run_id,
            "target": self.target,
            "stage": self.stage,
            # An empty string is not a failure. The driver passes "${2:-}" when it
            # records completion, so an `is None` check reported `passed: false` on a run
            # that had reached `complete` -- wrong in the safe direction, and still wrong
            # for the one field this artefact exists to state (W3.18).
            "passed": not self.failure and self.stage == "complete",
            "failure": self.failure,
            "started": self.started.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "notes": self.notes,
        }

    def write(self, path: pathlib.Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.document(), indent=2) + "\n")


# --- Decision 13: DoD 3's walling proof is a query over rows ---------------------------


def walling_queries(window: PartitionWindow, run_id: str) -> dict[str, str]:
    """The two assertions DoD 3 actually makes, as SQL.

    The harness knowing it set the flag proves nothing about what landed; DoD 3 is a claim
    about rows, and the only evidence for a claim about rows is a query over rows.
    """
    return {
        "distinct_identity": scoped_query(
            window, run_id,
            "COUNT(*) AS rows_seen, COUNT(DISTINCT CONCAT(trace_id, span_id)) AS distinct_spans",
            "spans_deduped",
        ),
        "unflagged_rows": scoped_query(
            window, run_id,
            "COUNTIF(synthetic IS NOT TRUE) AS unflagged",
            "spans_deduped",
        ),
    }


# --- Decision 12: the cloud half of the golden diff ------------------------------------


def projection() -> list[tuple[str, str]]:
    """Every column and its type, from the one file that defines the table.

    Reuses the parse `seed.py` already performs against `001_spans_table.sql`, so the
    harness cannot acquire a private idea of the schema that drifts from the seeder's.
    """
    from seed import table_schema, strip_sql_comments

    ddl = strip_sql_comments((SQL_DIR / "001_spans_table.sql").read_text())
    fields = table_schema(ddl)
    if not fields:
        raise Refused("could not parse a schema out of 001_spans_table.sql")
    return [(f["name"], f["type"]) for f in fields]


def select_list() -> str:
    """Ask SQL for the exact wire shape rather than trusting the tool's rendering.

    `bq query --format=json` renders a TIMESTAMP as `2026-08-31 12:00:00` -- measured, and
    it silently drops the microseconds. The golden files carry microsecond precision, so a
    diff over that rendering fails on every row for a formatting reason and says
    "normalization" while meaning "wire format". Timestamps are therefore formatted in the
    query, to the same shape `Timestamps.Format` produces.
    """
    parts = []
    for name, kind in projection():
        if kind == "TIMESTAMP":
            parts.append(f"FORMAT_TIMESTAMP('%Y-%m-%dT%H:%M:%E6SZ', {name}) AS {name}")
        elif kind == "JSON":
            parts.append(f"TO_JSON_STRING({name}) AS {name}")
        else:
            parts.append(name)
    return ", ".join(parts)


def convert(value, kind: str):
    """bq tags every scalar as a string; put the types back, once, in one place."""
    if value is None:
        return None
    if kind == "INTEGER":
        return int(value)
    if kind == "FLOAT":
        return float(value)
    if kind == "BOOLEAN":
        return value in (True, "true")
    if kind == "JSON":
        return json.loads(value) if isinstance(value, str) else value
    return value


def fetch_rows(window: PartitionWindow, run_id: str, view: str = "spans_deduped",
               runner=subprocess.run) -> list[dict]:
    """The run's rows, as the same JSON objects the local normalization writes."""
    sql = scoped_query(window, run_id, select_list(), view) + " ORDER BY trace_id, span_id"
    proc = runner(
        ["bq", f"--project_id={PROJECT}", "query", "--nouse_legacy_sql", "--format=json", sql],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise Refused(f"query against {view} failed:\n{proc.stdout or proc.stderr}")

    kinds = dict(projection())
    rows = []
    for raw in json.loads(proc.stdout or "[]"):
        row = {name: convert(raw.get(name), kind) for name, kind in kinds.items()}
        for column in VOLATILE:
            row.pop(column, None)
        rows.append(row)
    return rows


# Kept in step with worker/Plumbline.Fixtures/VolatileFields.cs by a test, not by hope.
VOLATILE = ("ingest_time",)


def load_ndjson(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def diff_rows(local: list[dict], cloud_rows: list[dict]) -> list[str]:
    """Every difference between the two normalizations, by span and by field.

    Fails closed. A field that is not on the volatile allowlist and differs is a failure,
    including one nobody thought about when this was written -- which is the difference
    between an allowlist and a denylist, and the reason Decision 12 asks for the former.
    """
    def key(row):
        return (row.get("trace_id"), row.get("span_id"))

    local_by, cloud_by = {key(r): r for r in local}, {key(r): r for r in cloud_rows}
    findings = []

    for missing in sorted(set(local_by) - set(cloud_by)):
        findings.append(f"{missing[0]}/{missing[1]}: normalized locally, absent from the cloud view")
    for extra in sorted(set(cloud_by) - set(local_by)):
        findings.append(f"{extra[0]}/{extra[1]}: in the cloud view, not in the corpus")

    for identity in sorted(set(local_by) & set(cloud_by)):
        here, there = local_by[identity], cloud_by[identity]
        for column in sorted(set(here) | set(there)):
            if column in VOLATILE:
                continue
            if here.get(column) != there.get(column):
                findings.append(
                    f"{identity[0]}/{identity[1]}.{column}: "
                    f"local={here.get(column)!r} cloud={there.get(column)!r}"
                )
    return findings


def dlq_depth(subscription: str = "traces-dlq-pull", runner=subprocess.run) -> int:
    """Undelivered messages, from Monitoring v3 -- the same read the state readout takes."""
    token = runner(["gcloud", "auth", "print-access-token"], capture_output=True, text=True)
    if token.returncode != 0:
        raise Refused(f"could not mint a read token: {token.stderr.strip()}")

    now = dt.datetime.now(dt.timezone.utc)
    metric = "pubsub.googleapis.com/subscription/num_undelivered_messages"
    url = (
        f"https://monitoring.googleapis.com/v3/projects/{PROJECT}/timeSeries"
        f'?filter=metric.type="{metric}"'
        f"&interval.startTime={now - dt.timedelta(minutes=30):%Y-%m-%dT%H:%M:%SZ}"
        f"&interval.endTime={now:%Y-%m-%dT%H:%M:%SZ}"
    )
    proc = runner(
        ["curl", "-sS", "-G", "-H", f"Authorization: Bearer {token.stdout.strip()}", url],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise Refused(f"depth read failed: {proc.stderr.strip()}")

    for series in json.loads(proc.stdout or "{}").get("timeSeries", []):
        if series["resource"]["labels"].get("subscription_id") == subscription and series.get("points"):
            return int(series["points"][0]["value"]["int64Value"])
    raise Refused(f"no depth series for {subscription}; the drill cannot assert against a missing metric")


def exclusion_query(window: PartitionWindow, run_id: str) -> str:
    """F2C-09's second consequence: `spans_real` must not show this run at all.

    Kept separate from `walling_queries` because it is a different claim about a different
    view. Decision 13 is about what landed through `spans_deduped`; this is the first live
    test of the walled-off-synthetic invariant -- taken now, while a synthetic run is the
    only traffic there is and the test is therefore free.

    Without the flag these rows would sit in `spans_real` and contaminate F4's 14-day
    real-source window, which F4 has no cheap way to clean afterwards.
    """
    return scoped_query(window, run_id, "COUNT(*) AS leaked", "spans_real")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-id")
    parser.add_argument("--corpus-out", default=".e2e-cloud/corpus")
    parser.add_argument("--emit",
                        choices=("corpus", "queries", "provenance", "diff", "depth", "result"),
                        default="corpus")
    parser.add_argument("--stage", choices=STAGES)
    parser.add_argument("--failure")
    parser.add_argument("--local-rows")
    parser.add_argument("--result")
    args = parser.parse_args(argv)

    import os

    # Writing the result document is a local file write, and deliberately ahead of the
    # arming gate: a run that stops *at* arming still has a stage worth recording, and
    # gating the recorder behind the thing it records is how Decision 11 ended up off the
    # path the first time.
    if args.emit == "result":
        if not args.stage:
            print("e2e-cloud: --emit result needs --stage", file=sys.stderr)
            return 2
        record = Result(args.run_id or "unknown", os.environ.get("PLUMBLINE_E2E_TARGET", "emulator"))
        record.reached(args.stage)
        record.failure = args.failure
        target_path = pathlib.Path(args.result or ".e2e-cloud/result.json")
        record.write(target_path)
        print(f"  stage={args.stage} -> {target_path}")
        return 0

    try:
        target = arming(os.environ, args.run_id)
    except Refused as refusal:
        print(f"e2e-cloud: {refusal}", file=sys.stderr)
        return 2

    if target != "cloud":
        print("e2e-cloud: target is the emulator; use make e2e for the local run")
        return 0

    try:
        if args.emit == "provenance":
            print(f"deployed window matches the repository: PARTITION BY {check_provenance()}")
        elif args.emit == "queries":
            window = PartitionWindow.for_corpus(pathlib.Path(args.corpus_out))
            queries = dict(walling_queries(window, args.run_id))
            queries["spans_real_exclusion"] = exclusion_query(window, args.run_id)
            print(json.dumps(queries, indent=2))
        elif args.emit == "depth":
            print(dlq_depth())
        elif args.emit == "diff":
            if not args.local_rows:
                raise Refused("--emit diff needs --local-rows, the locally normalized corpus")
            window = PartitionWindow.for_corpus(pathlib.Path(args.corpus_out))
            findings = diff_rows(load_ndjson(pathlib.Path(args.local_rows)),
                                 fetch_rows(window, args.run_id))
            for line in findings:
                print(f"  diff  {line}")
            if findings:
                raise Refused(f"{len(findings)} difference(s) between the two normalizations")
            print("cloud rows match the corpus normalized locally")
        else:
            written = build_corpus(args.run_id, pathlib.Path(args.corpus_out))
            print(f"corpus: {len(written)} payload(s) for run {args.run_id}")
    except Refused as refusal:
        print(f"e2e-cloud: {refusal}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    raise SystemExit(main())
