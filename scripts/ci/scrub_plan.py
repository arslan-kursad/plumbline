"""Turn a captured `terraform show -json` plan into a guard fixture.

The sanctioned path from a real plan to a file under `testdata/`, and the only
one: fixtures are derived, never authored (see `testdata/README.md`).

Two properties do the work, and both exist because of a defect this repository
already paid for.

**No key is ever removed.** A hand-authored fixture carries the fields the checks
of its day happened to read and is silent about everything else, so it is a trap
for every assertion written afterwards — and it springs in the expensive
direction, because a guard firing on a fixture looks like a broken guard and the
cheap response is to loosen it. That is what `plan-wave2.json` did to the
`allUsers` invoker check (decision log W3.6). Substitution replaces *values*;
structure, key sets and list lengths come through untouched, and the tool asserts
that rather than trusting it.

**No secret is named in this file.** A captured plan is a secret-bearing artifact:
`variables` alone carries `alert_email` and `billing_account_id` in plaintext, and
`prior_state` repeats them. This repository is public, so a fixture that leaked
one could not be recalled. The rules for those two are therefore *shape-based* —
this tool recognises "an email address" and "a billing account ID" by their form
and never holds an example of either. Only the project ID and project number are
passed in by value, and neither is a secret: both appear throughout `docs/` and in
fixtures that predate this tool.

The scan afterwards is what makes the shape rules trustworthy. Anything still
matching a sensitive form when substitution is done is a **failure**, naming the
path and the rule but never the value. Passing an unrecognised secret through
silently is the one outcome that cannot be undone.
"""

import argparse
import json
import re
import sys

# --- placeholders ----------------------------------------------------------
#
# Chosen so that a scrubbed fixture is obviously not a real plan at a glance, and
# so that re-running this tool over its own output changes nothing: every
# placeholder is already in its final form under every rule below. Idempotence is
# asserted in the self-test rather than assumed from that reading.

PROJECT_ID = "example-project"
PROJECT_NUMBER = "000000000000"
# Not `000000-000000-000000`: digits are inside `[0-9A-F]`, so that form matches
# the residual rule below and a scrubbed plan would fail its own scan — and would
# stop being idempotent, since the second pass rewrites what the first produced.
# The fix is a placeholder outside the alphabet the rule scans, not an exclusion
# for it; an exclusion is how a scanner stops covering the case that matters.
BILLING_ACCOUNT = "XXXXXX-XXXXXX-XXXXXX"
EMAIL = "alerts@example.invalid"
RUN_APP_HASH = "xxxxxxxxxx"

# --- the declared substitution table ---------------------------------------
#
# Ordered, and the order matters: the project number is rewritten inside
# service-account local parts before anything looks at the address as a whole,
# and Google-managed service-account domains are settled before the generic email
# rule runs — otherwise the generic rule would flatten every runtime identity in
# the plan into one address and the fixture would stop being able to tell the
# collector from the worker.
#
# `billing account` and `generic email` carry no example of what they match. That
# is the point: this file is in a public repository and a rule written by example
# is a rule that publishes one.

SUBSTITUTIONS = [
    (
        "project number in a service agent address",
        re.compile(r"\bservice-\d{9,15}@"),
        f"service-{PROJECT_NUMBER}@",
    ),
    (
        "project number in a default compute address",
        re.compile(r"\b\d{9,15}-compute@"),
        f"{PROJECT_NUMBER}-compute@",
    ),
    (
        "project number in a resource path",
        re.compile(r"(?<=projects/)\d{9,15}(?=/|\b)"),
        PROJECT_NUMBER,
    ),
    (
        "billing account id",
        re.compile(r"\b[0-9A-F]{6}-[0-9A-F]{6}-[0-9A-F]{6}\b"),
        BILLING_ACCOUNT,
    ),
    (
        "cloud run generated host",
        re.compile(r"(?<=-)[a-z0-9]{10}(?=-[a-z]{2}\.a\.run\.app)"),
        RUN_APP_HASH,
    ),
]

# Domains an address may still carry once substitution has run. Everything here is
# either a placeholder or a Google-managed service domain that identifies a role
# rather than a person.
ALLOWED_EMAIL_DOMAINS = {
    f"{PROJECT_ID}.iam.gserviceaccount.com",
    "gcp-sa-pubsub.iam.gserviceaccount.com",
    "appspot.gserviceaccount.com",
    "developer.gserviceaccount.com",
    "cloudbuild.gserviceaccount.com",
    "example.invalid",
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# --- the residual scan -----------------------------------------------------
#
# Run over the finished document. Each rule states a form that must not survive,
# and each reports the JSON path and the rule name — never the value, because a
# failure message is written to a CI log that is as public as the repository.
#
# The API-key rule is written so it cannot match its own text: the separators are
# bracketed, which is the convention Gate F established for the same reason. A
# scanner that trips on its own source gets an exclusion list, and an exclusion
# list is how a scanner stops covering the file that matters.

RESIDUAL_RULES = [
    ("billing account id", re.compile(r"\b[0-9A-F]{6}-[0-9A-F]{6}-[0-9A-F]{6}\b")),
    ("issued API key", re.compile(r"plb[_](local|live)[_][0-9a-f]{32}")),
    ("private key material", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer or access token", re.compile(r"\bya29\.[A-Za-z0-9_-]{20,}")),
]


def walk_strings(node, path="$"):
    """Yield (path, value) for every string in a *value* position.

    Keys are never yielded, so nothing this tool does can rename or drop one.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk_strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_strings(value, f"{path}[{index}]")
    elif isinstance(node, str):
        yield path, node


def walk_scalars(node, path="$"):
    """Yield (path, value) for every leaf, whatever its type.

    The scan uses this rather than `walk_strings`, because a plan carries
    `project_number` as a JSON **integer** and a scanner that only reads strings
    reports clean over it. That is not hypothetical: it is how the first version
    of this tool passed a plan whose project number had survived in four places.
    A rule that looks like coverage and is not is worse than an absent one.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk_scalars(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_scalars(value, f"{path}[{index}]")
    else:
        yield path, node


def shape(node):
    """A structural fingerprint: key sets, list lengths and value types.

    Compared before and after so that "no key removed" is a checked property
    rather than a claim about how the substitution loop is written.
    """
    if isinstance(node, dict):
        return {key: shape(value) for key, value in sorted(node.items())}
    if isinstance(node, list):
        return [shape(value) for value in node]
    return type(node).__name__


def substitute(text, project_id, project_number):
    """Apply the declared table to one string. Values only."""
    if project_number:
        text = re.sub(rf"\b{re.escape(project_number)}\b", PROJECT_NUMBER, text)
    if project_id:
        text = re.sub(rf"\b{re.escape(project_id)}\b", PROJECT_ID, text)

    for _name, pattern, replacement in SUBSTITUTIONS:
        text = pattern.sub(replacement, text)

    # Last, because the rules above settle every address that identifies a role
    # rather than a person. What reaches here is a human's address or an address
    # from a domain nobody declared, and both are scrubbed to one placeholder.
    def _email(match):
        address = match.group(0)
        domain = address.split("@", 1)[1]
        return address if domain in ALLOWED_EMAIL_DOMAINS else EMAIL

    return EMAIL_RE.sub(_email, text)


def transform(node, project_id, project_number):
    if isinstance(node, dict):
        return {k: transform(v, project_id, project_number) for k, v in node.items()}
    if isinstance(node, list):
        return [transform(v, project_id, project_number) for v in node]
    if isinstance(node, str):
        return substitute(node, project_id, project_number)

    # A plan carries `project_number` as an integer, not a string, so the
    # substitution above never sees it. `bool` is checked first because it is a
    # subclass of `int` in Python and a rewritten `true` would be a changed
    # meaning rather than a scrubbed value.
    if project_number and isinstance(node, int) and not isinstance(node, bool):
        if str(node) == str(project_number):
            return int(PROJECT_NUMBER)

    return node


def residual_findings(document):
    """Sensitive forms that survived. Path and rule only — never the value."""
    findings = []
    for path, raw in walk_scalars(document):
        if raw is None:
            continue
        value = raw if isinstance(raw, str) else str(raw)

        for name, pattern in RESIDUAL_RULES:
            if pattern.search(value):
                findings.append((path, name))

        for match in EMAIL_RE.finditer(value):
            domain = match.group(0).split("@", 1)[1]
            if domain not in ALLOWED_EMAIL_DOMAINS:
                findings.append((path, f"email address at undeclared domain {domain!r}"))
    return findings


def scrub(document, project_id, project_number):
    """Returns the scrubbed document. Raises if a property was violated."""
    result = transform(document, project_id, project_number)

    if shape(document) != shape(result):
        raise SystemExit(
            "scrub_plan: the scrubbed document has a different structure from its "
            "source. Substitution replaces values; it must not add, drop or retype "
            "a key, and a fixture missing a field is the defect this tool exists "
            "to prevent."
        )

    # The tool must be held to its own claim. Everything above is a rule that
    # *should* replace these two; this reads the finished document and checks that
    # it did, at every leaf and whatever the type. The first version of this tool
    # passed a plan with four surviving project numbers because they were JSON
    # integers, and nothing noticed — the substitution rules all looked correct and
    # the scan only read strings. An assertion against the input values is the one
    # check that cannot be fooled by a rule with a blind spot.
    for label, actual in (("project ID", project_id), ("project number", project_number)):
        if not actual:
            continue
        survived = [path for path, value in walk_scalars(result) if str(actual) in str(value)]
        if survived:
            listed = "\n".join(f"  {path}" for path in sorted(survived)[:20])
            more = "" if len(survived) <= 20 else f"\n  ... and {len(survived) - 20} more"
            raise SystemExit(
                f"scrub_plan: the real {label} survived substitution at "
                f"{len(survived)} leaf/leaves, so a rule has a blind spot. Fix the "
                f"rule; do not edit the output.\n{listed}{more}"
            )

    findings = residual_findings(result)
    if findings:
        lines = "\n".join(f"  {path}: {name}" for path, name in sorted(set(findings)))
        raise SystemExit(
            "scrub_plan: sensitive values survived substitution, so this plan is "
            "not safe to commit. Each finding names where it is and what matched, "
            "and deliberately not what the value is — this message goes to a public "
            "log. Add a rule to SUBSTITUTIONS rather than editing the output by "
            f"hand.\n{lines}"
        )

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Derive a plan-guard fixture from captured `terraform show -json` output."
    )
    parser.add_argument("plan", help="captured plan JSON, or - for stdin")
    parser.add_argument(
        "--project-id",
        help="real project ID to replace; defaults to variables.project_id in the plan",
    )
    parser.add_argument(
        "--project-number",
        help="real project number to replace; inferred from the plan when omitted",
    )
    parser.add_argument("-o", "--output", help="write here instead of stdout")
    args = parser.parse_args()

    raw = sys.stdin.read() if args.plan == "-" else open(args.plan, encoding="utf-8").read()
    document = json.loads(raw)

    project_id = args.project_id
    if not project_id:
        project_id = (document.get("variables", {}).get("project_id") or {}).get("value")

    project_number = args.project_number
    if not project_number:
        found = re.findall(r"\bservice-(\d{9,15})@|\bprojects/(\d{9,15})[/\"]", raw)
        numbers = {n for pair in found for n in pair if n}
        if len(numbers) == 1:
            project_number = numbers.pop()
        elif len(numbers) > 1:
            raise SystemExit(
                "scrub_plan: the plan names more than one project number "
                f"({len(numbers)} distinct); pass --project-number to say which is "
                "this project's rather than letting the tool guess."
            )

    result = scrub(document, project_id, project_number)
    text = json.dumps(result, indent=2, sort_keys=False) + "\n"

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"scrub_plan: wrote {args.output}")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
