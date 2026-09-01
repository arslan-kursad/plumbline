"""Read-only readout of live GCP state, as one structured artefact.

F2 completion directive v1.7, Decision 5. The directive's remaining verification
steps each need a handful of API reads; this collects all of them in one run so
that no F2 verification depends on a human pasting command output.

Every reading records the command that produced it alongside its output, because
this phase's evidence rule is that an API read is evidence and a summary of one
is not. A reading that fails is recorded as failed, with its stderr, rather than
omitted -- a missing reading and a zero reading must not look alike.

Nothing here mutates. `assert_read_only` enforces that against the command list
rather than against reviewer attention, and `--self-test` proves it rejects a
mutating command.

Entry point is `scripts/state-readout.sh`.
"""

import argparse
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys

# The shape rules for sensitive values already exist and are carefully reasoned
# (scrub_plan.py's docstring). Importing them rather than restating them means a
# rule this file cannot see is still enforced here, and an improvement there
# reaches this artefact without anyone remembering to copy it. A second, drifting
# copy of a redaction rule is the failure this reuse exists to avoid.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "ci"))
from scrub_plan import EMAIL_RE, RESIDUAL_RULES, walk_scalars  # noqa: E402

PROJECT = "plumbline-19458"
REGION = "us-central1"
DATASET = "plumbline"

# Verbs that change state. The guard matches whole arguments, so `list` never
# matches `blocklist` and the check cannot be defeated by a longer word.
MUTATING = frozenset(
    {
        "create", "delete", "update", "patch", "set", "add", "remove",
        "deploy", "apply", "destroy", "import", "insert", "rm", "mk",
        "publish", "ack", "seek", "purge", "replace", "enable", "disable",
        "grant", "revoke", "detach", "attach", "restart",
    }
)
# `run` is deliberately absent: it is Cloud Run's product group, so denying it
# would refuse every Cloud Run read. The mutating Cloud Run verbs -- `deploy`,
# `delete`, `update`, `replace` -- are each in the set on their own.


# Reads that this lane cannot perform, with the rule that stops each one. Named
# rather than worked around: directive v1.7 §7.9.
BLOCKED = {
    "billing_period_cost": {
        "why": "`Bash(gcloud billing:*)` is denied in .claude/settings.json, correctly.",
        "lane": "C",
        "needed_by": "Decision 16 -- the two-day spend escape hatch.",
        "how": "Maintainer reads gross cost for the period from the billing console.",
    }
}


# This artefact is archived in a public repository, so a human principal must not
# survive into it. Service accounts do: they name a role rather than a person, and
# they are already throughout docs/ (apply-identity-ledger.md names ci-deploy@ by
# address). The rule is the domain form, not a list of people -- a redaction rule
# written by example is a rule that publishes an example.
SERVICE_ACCOUNT_DOMAIN = re.compile(r"\.gserviceaccount\.com$")
REDACTED_PRINCIPAL = "<redacted-user-principal>"


class MutatingCommand(Exception):
    """Raised when a command would change state."""


class SensitiveValueSurvived(Exception):
    """Raised when the residual scan finds something that must not be published."""


def redact(node):
    """Replace every non-service-account address, everywhere in the document."""

    def _one(text):
        return EMAIL_RE.sub(
            lambda m: m.group(0)
            if SERVICE_ACCOUNT_DOMAIN.search(m.group(0).split("@", 1)[1])
            else REDACTED_PRINCIPAL,
            text,
        )

    if isinstance(node, dict):
        return {k: redact(v) for k, v in node.items()}
    if isinstance(node, list):
        return [redact(v) for v in node]
    if isinstance(node, str):
        return _one(node)
    return node


def residual_scan(document):
    """Refuse to emit a document still carrying a sensitive form.

    Reports the JSON path and the rule, never the value: this message goes to a
    terminal and possibly into a commit, both as public as the repository.
    """
    findings = []
    for path, raw in walk_scalars(document):
        if raw is None:
            continue
        value = raw if isinstance(raw, str) else str(raw)
        for name, pattern in RESIDUAL_RULES:
            if pattern.search(value):
                findings.append((path, name))
        for match in EMAIL_RE.finditer(value):
            if not SERVICE_ACCOUNT_DOMAIN.search(match.group(0).split("@", 1)[1]):
                findings.append((path, "non-service-account principal"))
    return findings


def assert_read_only(command):
    """Reject any command carrying a mutating verb.

    The guard is deliberately blunt: it refuses on the verb rather than trying to
    decide whether a particular subcommand is safe. A false positive here costs a
    renamed reading; a false negative costs a write from a script whose whole
    contract is that it does not write.
    """
    for token in command:
        if token.lower() in MUTATING:
            raise MutatingCommand(
                "refusing to run a command containing the mutating verb "
                f"{token!r}: {' '.join(command)}"
            )


def read(name, command, parse_json=True, display_command=None):
    """Run one read-only command and record it with its result.

    `display_command` is what the artefact records when the real command carries a
    credential. It is the only thing written down; the credential-bearing form
    exists as a local for the length of the call.
    """
    assert_read_only(command)

    entry = {"name": name, "command": display_command or command}
    proc = subprocess.run(command, capture_output=True, text=True)

    entry["exit_code"] = proc.returncode
    if proc.returncode != 0:
        entry["status"] = "failed"
        # Both streams, because `bq` reports query errors on stdout. Capturing
        # only stderr loses the message and leaves a failed reading that says
        # nothing about why -- the failure mode this function exists to avoid.
        entry["stderr"] = proc.stderr.strip()
        entry["stdout"] = proc.stdout.strip()
        return entry

    entry["status"] = "ok"
    if parse_json:
        try:
            entry["value"] = json.loads(proc.stdout or "null")
        except json.JSONDecodeError as exc:
            entry["status"] = "unparseable"
            entry["stderr"] = f"{exc}"
            entry["raw"] = proc.stdout
    else:
        entry["value"] = proc.stdout.strip()
    return entry


def names_from(entry, key="name"):
    """Pull bare resource names out of a list reading, tolerating a failure.

    `key` may be a dotted path, because Cloud Run nests the name under
    `metadata` while Artifact Registry and Pub/Sub put it at the top level.
    """
    if entry.get("status") != "ok" or not isinstance(entry.get("value"), list):
        return []
    out = []
    for item in entry["value"]:
        value = item
        for part in key.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if value:
            out.append(str(value).rsplit("/", 1)[-1])
    return out


def gcloud(*args):
    return ["gcloud", *args, "--project", PROJECT, "--format", "json"]


def collect(window_lower, window_upper):
    """Every reading Decision 5 enumerates, discovered rather than hardcoded.

    Resource names come from a list call and the describes follow from it. A
    hardcoded set would silently miss a resource created outside the gated path,
    which is the property DoD 5 asserts.
    """
    readings = []

    # --- Cloud Run: region, scaling bounds, CPU and memory, per service ---
    services = read(
        "cloud_run_services",
        gcloud("run", "services", "list", "--region", REGION),
    )
    readings.append(services)
    for service in names_from(services, key="metadata.name"):
        readings.append(
            read(
                f"cloud_run_service:{service}",
                gcloud("run", "services", "describe", service, "--region", REGION),
            )
        )

    # --- IAM: the bindings every setIamPolicy in the pending plan touches ---
    readings.append(
        read(
            "project_iam_policy",
            ["gcloud", "projects", "get-iam-policy", PROJECT, "--format", "json"],
        )
    )

    # --- BigQuery: deployed view DDL, in full, plus the base table ---
    tables = read("bigquery_tables", ["bq", f"--project_id={PROJECT}", "ls", "--format=json", DATASET])
    readings.append(tables)
    for table in [
        t.get("tableReference", {}).get("tableId")
        for t in (tables.get("value") or [])
        if isinstance(t, dict)
    ]:
        if table:
            readings.append(
                read(
                    f"bigquery_object:{table}",
                    ["bq", f"--project_id={PROJECT}", "show", "--format=prettyjson", f"{DATASET}.{table}"],
                )
            )

    # --- Pub/Sub: dead-letter policy and max delivery attempts ---
    subscriptions = read("pubsub_subscriptions", gcloud("pubsub", "subscriptions", "list"))
    readings.append(subscriptions)
    for subscription in names_from(subscriptions):
        readings.append(
            read(
                f"pubsub_subscription:{subscription}",
                gcloud("pubsub", "subscriptions", "describe", subscription),
            )
        )

    # --- DLQ depth: a Monitoring metric, so it comes from the REST API ---
    # `gcloud alpha monitoring` is denied and the GA surface carries no
    # time-series read, so this reads v3 directly with a short-lived token.
    readings.append(undelivered_depth())

    # --- Artifact Registry: the tags F2C-05 re-derives its pin against ---
    packages = read(
        "artifact_registry_packages",
        gcloud("artifacts", "packages", "list", "--repository", "plumbline", "--location", REGION),
    )
    readings.append(packages)
    for package in names_from(packages):
        readings.append(
            read(
                f"artifact_registry_tags:{package}",
                gcloud(
                    "artifacts", "docker", "tags", "list",
                    f"{REGION}-docker.pkg.dev/{PROJECT}/plumbline/{package}",
                ),
            )
        )

    # --- Row counts, over an explicit partition window (Decision 7's rule) ---
    readings.append(row_counts(window_lower, window_upper))

    return readings


def undelivered_depth():
    """Undelivered message count per subscription, from Monitoring v3."""
    name = "pubsub_undelivered_messages"
    token = subprocess.run(
        ["gcloud", "auth", "print-access-token"], capture_output=True, text=True
    )
    if token.returncode != 0:
        return {
            "name": name,
            "status": "failed",
            "exit_code": token.returncode,
            "stderr": token.stderr.strip(),
        }

    now = dt.datetime.now(dt.timezone.utc)
    start = now - dt.timedelta(minutes=30)
    metric = "pubsub.googleapis.com/subscription/num_undelivered_messages"
    url = (
        f"https://monitoring.googleapis.com/v3/projects/{PROJECT}/timeSeries"
        f'?filter=metric.type="{metric}"'
        f"&interval.startTime={start:%Y-%m-%dT%H:%M:%SZ}"
        f"&interval.endTime={now:%Y-%m-%dT%H:%M:%SZ}"
    )
    # The bearer token is passed to the process and never stored: `read` records
    # `display_command`, so there is no window in which the artefact holds it.
    entry = read(
        name,
        ["curl", "-sS", "-G", "-H", f"Authorization: Bearer {token.stdout.strip()}", url],
        display_command=["curl", "-sS", "-G", "-H", "Authorization: Bearer <redacted>", url],
    )

    if entry.get("status") == "ok":
        entry["depth"] = {
            series["resource"]["labels"]["subscription_id"]: int(
                series["points"][0]["value"]["int64Value"]
            )
            for series in (entry["value"] or {}).get("timeSeries", [])
            if series.get("points")
        }
    return entry


def row_counts(lower, upper):
    """Rows by `synthetic` and by run id, inside an explicit partition window.

    The window is a required argument rather than a default over all time:
    `require_partition_filter` rejects a missing predicate, but a broad scan
    satisfies it and still spends the query budget (Decision 7).

    This reads `spans_deduped` rather than the base table on purpose. DoD 3 is a
    claim about rows arriving *through the views*, so a base-table fallback would
    answer an easier question and look like the same evidence.

    Until Wave 4 deploys the corrected view this reading fails, and the failure is
    #61 itself: with the deployed two-column window the outer `start_time`
    predicate cannot be pushed below the window function, the inner scan of
    `spans` carries no partition predicate, and the guardrail refuses the query.
    That makes this reading the closure probe for #61 -- it succeeding against the
    cloud view is what Stage 3 step 11 asks for.
    """
    sql = (
        "SELECT synthetic, "
        # Resource attributes nest under `resource` in this column; the top-level path
        # returns NULL for every row and the grouping would silently collapse to one bucket.
        "JSON_VALUE(attributes, '$.resource.\"plumbline.e2e_run_id\"') AS e2e_run_id, "
        "COUNT(*) AS row_count "
        f"FROM `{PROJECT}.{DATASET}.spans_deduped` "
        f"WHERE DATE(start_time) BETWEEN '{lower}' AND '{upper}' "
        "GROUP BY synthetic, e2e_run_id ORDER BY synthetic, e2e_run_id"
    )
    entry = read(
        "bigquery_row_counts",
        ["bq", f"--project_id={PROJECT}", "query", "--nouse_legacy_sql", "--format=json", sql],
    )
    entry["partition_window"] = {"lower": lower, "upper": upper}
    return entry


def self_test():
    """Prove the read-only guard fires, in both directions."""
    failures = []

    for command in (
        ["gcloud", "run", "services", "delete", "collector"],
        ["bq", "rm", "-f", "plumbline.spans"],
        ["gcloud", "pubsub", "topics", "publish", "traces"],
    ):
        try:
            assert_read_only(command)
        except MutatingCommand:
            continue
        failures.append(f"guard did not refuse: {' '.join(command)}")

    for command in (
        ["gcloud", "run", "services", "list"],
        ["bq", "show", "--format=prettyjson", "plumbline.spans_deduped"],
        ["gcloud", "projects", "get-iam-policy", PROJECT],
    ):
        try:
            assert_read_only(command)
        except MutatingCommand as exc:
            failures.append(f"guard refused a read: {' '.join(command)} -- {exc}")

    # Redaction, both directions: a human address must not survive, and a service
    # account must. A rule that redacted everything would pass the first half and
    # make the artefact useless, so the second half is the one that constrains it.
    human = redact({"binding": {"members": ["user:someone@example.com"]}})
    if REDACTED_PRINCIPAL not in json.dumps(human):
        failures.append("redaction let a non-service-account principal through")

    role = "collector@plumbline-19458.iam.gserviceaccount.com"
    if redact({"m": f"serviceAccount:{role}"})["m"] != f"serviceAccount:{role}":
        failures.append("redaction rewrote a service account, which names a role")

    # The residual scan must refuse what redaction missed.
    if not residual_scan({"leak": "user:someone@example.com"}):
        failures.append("residual scan did not flag a surviving principal")
    if residual_scan(redact({"leak": "user:someone@example.com"})):
        failures.append("residual scan flagged an already-redacted document")

    for line in failures:
        print(f"self-test: {line}", file=sys.stderr)
    if failures:
        return 1
    print("self-test: read-only guard refuses mutation and permits reads")
    print("self-test: redaction removes human principals and keeps service accounts")
    print("self-test: residual scan refuses a surviving principal")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    today = dt.date.today()
    parser.add_argument("--window-lower", default=str(today - dt.timedelta(days=7)))
    parser.add_argument("--window-upper", default=str(today))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    readings = collect(args.window_lower, args.window_upper)
    document = {
        "meta": {
            "project": PROJECT,
            "read_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "commit": subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True
            ).stdout.strip(),
            "directive": "F2 completion directive v1.7, Decision 5",
            "lane": "A -- read-only; nothing here mutates",
        },
        "readings": readings,
        "blocked": BLOCKED,
    }
    document = redact(document)
    findings = residual_scan(document)
    if findings:
        # Nothing is printed. A partial artefact carrying one sensitive value is
        # worse than no artefact, and this one is destined for a public repository.
        for path, rule in findings:
            print(f"state-readout: {rule} survived at {path}", file=sys.stderr)
        raise SensitiveValueSurvived(f"{len(findings)} sensitive value(s) survived redaction")

    print(json.dumps(document, indent=2, sort_keys=False))

    failed = [r["name"] for r in readings if r.get("status") != "ok"]
    if failed:
        print(f"state-readout: {len(failed)} reading(s) failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
