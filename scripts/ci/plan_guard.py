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

# The ingress posture each Cloud Run service is allowed to have, by service name.
#
# The two services are deliberately opposite — the collector is the project's only
# public endpoint because agents authenticate with an API key rather than a Google
# identity (architecture §6.1), and the worker is internal-only because its caller
# is a Pub/Sub push subscription inside this project. Nothing asserted either until
# a 404 investigation went looking for it, and both failure modes are quiet: a
# worker set to `all` is an open ingestion endpoint whose only protection is the
# OIDC check, and a collector set to `internal` accepts nothing from the agents it
# exists to serve while every dashboard stays green.
#
# A service missing from this map is refused rather than skipped. Adding one is
# then a deliberate line stating its exposure, which is the property worth having:
# the alternative defaults a new service into whatever was copied from the block
# above it.
INGRESS_POSTURE = {
    "collector": "INGRESS_TRAFFIC_ALL",
    "ingestion-worker": "INGRESS_TRAFFIC_INTERNAL_ONLY",
}

# Cloud Run services that may be invoked without authentication, by service name.
#
# `allUsers` (or `allAuthenticatedUsers`) holding `roles/run.invoker` *is* what
# "unauthenticated invocations enabled" means — there is no separate switch. So the
# worker's protection is the absence of such a member, and an absence is the one
# thing a configuration review reads past: nothing is on the screen to notice.
#
# The collector is deliberately public (architecture §6.1) and is the project's only
# unauthenticated endpoint. Every other service, in this phase and later ones, is a
# violation if it acquires one — which is the check DoD 7's "the push service account
# is the sole invoker" needs, since that claim is false the moment anyone else holds
# the role regardless of what the push binding says.
PUBLIC_INVOKER_ALLOWED = {"collector"}

# Members that make a service publicly invokable.
UNAUTHENTICATED_MEMBERS = {"allUsers", "allAuthenticatedUsers"}


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


def budget_topic_bindings(plan):
    """Addresses of budgets whose notifications publish to a Pub/Sub topic.

    Read off the planned attribute rather than the resource name, because what
    matters is where a budget *publishes*, and a resource can be renamed without
    changing that (ADR-0004 Amendment 4, D3).
    """
    bound = []
    for change in plan.get("resource_changes", []):
        if change.get("type") != "google_billing_budget":
            continue
        actions = change.get("change", {}).get("actions", [])
        if not ({"create", "update"} & set(actions)):
            continue

        after = change.get("change", {}).get("after") or {}
        topic = nested(after, ("all_updates_rule", "pubsub_topic"))
        if topic:
            bound.append((change.get("address", "?"), topic))
    return bound


def check(plan, allowed):
    """Returns (violations, checked).

    `checked` records the scaling assertions that actually ran, by address. A
    guard that only reports silence cannot be shown to have evaluated anything:
    "clean" reads identically whether it examined a Cloud Run service or skipped
    it because the plan nested `scaling` somewhere this code does not look. F2
    DoD 6 asks for evidence that these resources were evaluated, so the evidence
    is the guard's own output rather than an assumption about its reach.
    """
    violations = []
    checked = []

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

            checked.append(
                f"{address}: min_instance_count={minimum}, "
                f"max_instance_count={maximum if maximum is not None else 'unset'}"
            )

            if minimum != 0:
                violations.append(
                    f"{address}: min_instance_count is {minimum}, must be 0 "
                    "(scale to zero is a cost invariant)"
                )
            if maximum is None or maximum > 2:
                violations.append(
                    f"{address}: max_instance_count is {maximum}, must be set and at most 2"
                )

        if rtype == "google_cloud_run_v2_service":
            name = after.get("name")
            ingress = after.get("ingress")
            expected = INGRESS_POSTURE.get(name)

            if expected is None:
                violations.append(
                    f"{address}: Cloud Run service {name!r} declares no ingress posture; "
                    "add it to INGRESS_POSTURE so its exposure is stated rather than inherited"
                )
            else:
                checked.append(f"{address}: ingress={ingress}")
                if ingress != expected:
                    violations.append(
                        f"{address}: ingress is {ingress}, must be {expected} "
                        f"for service {name!r} (architecture §6.1)"
                    )

        if rtype in (
            "google_cloud_run_v2_service_iam_member",
            "google_cloud_run_service_iam_member",
        ):
            # v2 calls the service `name`; v1 calls it `service`.
            service = after.get("name") or after.get("service")
            member = after.get("member")
            role = after.get("role")

            if role == "roles/run.invoker":
                # An invoker binding this code cannot read is not a clean binding.
                # Both fields are known at plan time in this configuration —
                # verified against a real Wave 3 plan, where `name` renders as
                # `ingestion-worker` — so an absence means either a value computed
                # at apply time or a plan shape this check does not understand, and
                # in both cases it has asserted nothing. Reporting that as clean is
                # the failure W2.13 found: the control stays green over a gap.
                if service is None or member is None:
                    violations.append(
                        f"{address}: roles/run.invoker binding with "
                        f"service={service!r} member={member!r}; both must be known "
                        "at plan time for the public-invoker check to mean anything"
                    )
                    continue

                checked.append(f"{address}: invoker {member} on {service}")

                if (
                    member in UNAUTHENTICATED_MEMBERS
                    and service not in PUBLIC_INVOKER_ALLOWED
                ):
                    violations.append(
                        f"{address}: {member} holds roles/run.invoker on {service!r}, "
                        "which is what makes a service publicly invokable; only "
                        f"{sorted(PUBLIC_INVOKER_ALLOWED)} may be public (§6.1)"
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

    # Exactly one budget may reach the kill-switch (ADR-0004 Amendment 4, D3).
    #
    # The gross-cost alert budget reports a figure that is non-zero during
    # entirely free operation. If it ever gained a Pub/Sub binding to the topic
    # the function listens on, it would detach billing on ordinary usage — the
    # failure this amendment exists to remove, re-created by a resource that
    # looks like a notification.
    bound = budget_topic_bindings(plan)
    if len(bound) > 1:
        listed = "; ".join(f"{address} -> {topic}" for address, topic in bound)
        violations.append(
            f"{len(bound)} budgets publish to a Pub/Sub topic ({listed}); "
            "exactly one budget may reach the kill-switch function"
        )
    if bound:
        checked.append(f"{bound[0][0]}: publishes to {bound[0][1]}")

    return violations, checked


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: plan_guard.py <architecture.md> <plan.json>")

    architecture_path, plan_path = sys.argv[1], sys.argv[2]
    allowed = allowlist(architecture_path)

    with open(plan_path, encoding="utf-8") as handle:
        plan = json.load(handle)

    violations, checked = check(plan, allowed)

    # Printed on both paths: on a failure it says what else was examined, and on a
    # clean run it is the only evidence that anything was.
    if checked:
        print("plan guard: asserted")
        for entry in checked:
            print(f"  {entry}")
    else:
        print("plan guard: nothing in this plan carries a checked attribute")

    if violations:
        print(f"plan guard: {len(violations)} violation(s)")
        for violation in violations:
            print(f"  {violation}")
        raise SystemExit(1)

    print(f"plan guard: clean ({len(allowed)} resource types allowed by §7.1)")


if __name__ == "__main__":
    main()
