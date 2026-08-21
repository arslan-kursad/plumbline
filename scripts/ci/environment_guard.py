"""Assertions run by environment-guard.sh against a GitHub deployment environment.

Kept separate from the shell wrapper so the logic is readable and testable on its
own; the wrapper owns argument handling and the self-test loop. Python rather than
jq for the same reason `plan_guard.py` is: it is present on the runner and on a
maintainer's machine alike, so the control can be exercised in both places.

Exit codes are three-valued on purpose. 0 protected, 1 unprotected, 2 unusable
input — because "cannot tell" must never collapse into "fine".
"""

import json
import sys


def check(body):
    """Returns (status, lines)."""
    try:
        environment = json.loads(body)
    except (ValueError, TypeError):
        return 2, [
            "environment guard: input is not JSON; refusing rather than "
            "assuming a gate exists"
        ]

    if not isinstance(environment, dict):
        return 2, ["environment guard: input is not an environment object"]

    name = environment.get("name") or "(unnamed)"

    # Counted rather than tested for presence: GitHub returns the rule object with
    # an empty reviewer list when every reviewer has been removed, and a rule with
    # nobody on it stops nothing.
    reviewers = 0
    for rule in environment.get("protection_rules") or []:
        if isinstance(rule, dict) and rule.get("type") == "required_reviewers":
            reviewers += len(rule.get("reviewers") or [])

    if reviewers < 1:
        return 1, [
            f"environment guard: {name} has no required reviewer",
            "  the deploy workflow applies only behind this gate; without it an "
            "apply runs unreviewed.",
            "  Configure it under Settings -> Environments.",
        ]

    lines = []
    policy = environment.get("deployment_branch_policy") or {}
    if not isinstance(policy, dict):
        policy = {}
    if not policy.get("protected_branches") and not policy.get("custom_branch_policies"):
        lines += [
            f"environment guard: {name} has no deployment branch policy (warning)",
            "  the workflow refuses any ref but main on its own, so this is a "
            "second line rather than the only one.",
        ]

    lines.append(
        f"environment guard: {name} protected by {reviewers} required reviewer(s)"
    )
    return 0, lines


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: environment_guard.py <environment.json|->")

    source = sys.argv[1]
    if source == "-":
        body = sys.stdin.read()
    else:
        try:
            with open(source, encoding="utf-8") as handle:
                body = handle.read()
        except OSError as error:
            print(f"environment guard: cannot read {source}: {error}")
            raise SystemExit(2)

    status, lines = check(body)
    for line in lines:
        print(line)
    raise SystemExit(status)


if __name__ == "__main__":
    main()
