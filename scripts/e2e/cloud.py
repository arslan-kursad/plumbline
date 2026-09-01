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
        """The window a run's own emission time implies, with a day either side for UTC edges."""
        day = moment.astimezone(dt.timezone.utc).date()
        return cls(day - dt.timedelta(days=margin_days), day + dt.timedelta(days=margin_days))

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
        f"AND JSON_VALUE(attributes, '$.\"plumbline.e2e_run_id\"') = '{run_id}'"
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
            "passed": self.failure is None and self.stage == "complete",
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-id")
    parser.add_argument("--corpus-out", default=".e2e-cloud/corpus")
    parser.add_argument("--emit", choices=("corpus", "queries", "provenance"), default="corpus")
    args = parser.parse_args(argv)

    import os

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
            window = PartitionWindow.around(dt.datetime.now(dt.timezone.utc))
            print(json.dumps(walling_queries(window, args.run_id), indent=2))
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
