"""Assertions run by terraform-plan-guard.sh against a Terraform plan.

Kept separate from the shell wrapper so the logic is readable and testable on
its own; the wrapper owns argument handling and `terraform show -json`.
"""

import json
import re
import sys

REGION = "us-central1"

# Resources whose scaling bounds are checked, and where the plan carries them.
SCALING_PATHS = {
    "google_cloud_run_v2_service": ("template", "scaling"),
    "google_cloudfunctions2_function": ("service_config",),
}


def allowlist(architecture_path):
    """Resource types listed in the architecture §7.1 table.

    Only table rows count. The section also names forbidden types in prose, and
    reading those as permitted would invert the control.
    """
    text = open(architecture_path, encoding="utf-8").read()

    match = re.search(
        r"^###\s+7\.1\s+.*?$(.*?)(?=^##\s|\Z)", text, re.MULTILINE | re.DOTALL
    )
    if not match:
        raise SystemExit(
            f"{architecture_path}: section 7.1 not found; the allowlist has no source"
        )

    types = set()
    for line in match.group(1).splitlines():
        if not line.lstrip().startswith("|"):
            continue
        types.update(re.findall(r"`(google_[a-z0-9_]+)`", line))

    if len(types) < 10:
        raise SystemExit(
            f"{architecture_path}: parsed only {len(types)} allowed types from §7.1; "
            "refusing to run against an allowlist that looks broken"
        )
    return types


def nested(mapping, path):
    """Walk a plan value by key, unwrapping the single-element lists Terraform
    uses to represent nested blocks in JSON output."""
    for key in path:
        if isinstance(mapping, list):
            mapping = mapping[0] if mapping else None
        if not isinstance(mapping, dict):
            return None
        mapping = mapping.get(key)

    if isinstance(mapping, list):
        mapping = mapping[0] if mapping else None
    return mapping


def check(plan, allowed):
    violations = []

    for change in plan.get("resource_changes", []):
        actions = change.get("change", {}).get("actions", [])
        if not ({"create", "update"} & set(actions)):
            continue

        address = change.get("address", change.get("type", "?"))
        rtype = change.get("type", "")
        after = change.get("change", {}).get("after") or {}

        if rtype not in allowed:
            violations.append(
                f"{address}: resource type {rtype} is not in the architecture "
                "§7.1 allowlist"
            )

        if rtype in SCALING_PATHS:
            scaling = nested(after, SCALING_PATHS[rtype]) or {}
            minimum = scaling.get("min_instance_count") or 0
            maximum = scaling.get("max_instance_count")

            if minimum != 0:
                violations.append(
                    f"{address}: min_instance_count is {minimum}, must be 0 "
                    "(scale to zero is a cost invariant)"
                )
            if maximum is None or maximum > 2:
                violations.append(
                    f"{address}: max_instance_count is {maximum}, must be set and at most 2"
                )

        for key in ("location", "region"):
            value = after.get(key)
            if isinstance(value, str) and value.lower() != REGION:
                violations.append(
                    f"{address}: {key} is {value}, must be {REGION}"
                )

        if rtype == "google_pubsub_topic" and after.get("message_retention_duration"):
            violations.append(
                f"{address}: message_retention_duration is set; topic-level "
                "retention is a paid feature and is forbidden on every topic"
            )

    return violations


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: plan_guard.py <architecture.md> <plan.json>")

    architecture_path, plan_path = sys.argv[1], sys.argv[2]
    allowed = allowlist(architecture_path)

    with open(plan_path, encoding="utf-8") as handle:
        plan = json.load(handle)

    violations = check(plan, allowed)
    if violations:
        print(f"plan guard: {len(violations)} violation(s)")
        for violation in violations:
            print(f"  {violation}")
        raise SystemExit(1)

    print(f"plan guard: clean ({len(allowed)} resource types allowed by §7.1)")


if __name__ == "__main__":
    main()
