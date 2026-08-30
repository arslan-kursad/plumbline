"""Refuse a plan that would apply nothing.

Arming a wave costs a required-reviewer approval, and `deploy.yml` has no way to
tell whether the ref it planned actually carries the wave. On 2026-08-26 two
dispatches ran against a `main` that had not yet taken the Wave 3 merge. Both
planned cleanly, both passed every existing guard, and both reached the
`gcp-production` gate asking a human to approve a plan that would change nothing.

A reviewer facing that either approves it — spending an arming and stamping a
timestamped, attributable "wave applied" record on an apply that applied nothing —
or learns that the gate sometimes means nothing. The second outcome is worse and
it is permanent, because it is the only control Lane B has.

**Two conditions, and the second is the one that matters.** A converged plan does
not come back empty: Terraform emits an entry for every resource in state, each
with `actions: ["no-op"]`. The real capture in `testdata/plan-noop.json` carries
twenty of them. A check written as "is the list empty" reads that as a plan full
of changes and passes it — which is exactly the artifact that reached the gate
twice. `testdata/plan-empty.json`, captured from a configuration with no
resources at all, is the other shape: `resource_changes` absent entirely.
"""

import json
import sys

# Terraform's verbs, split into the ones that mutate and the one that does not.
NO_OP = "no-op"


def counts(plan):
    """`terraform plan`'s own summary line, recomputed from the JSON.

    Returned rather than parsed out of the human-readable output, so the number
    the reviewer sees above the approval gate comes from the same document the
    fingerprint is computed over.
    """
    added = changed = destroyed = 0

    for change in plan.get("resource_changes") or []:
        actions = change.get("change", {}).get("actions", [])
        if actions == [NO_OP] or not actions:
            continue
        if "create" in actions and "delete" in actions:
            # Replacement: Terraform counts it in both columns, and so does this.
            added += 1
            destroyed += 1
        elif "create" in actions:
            added += 1
        elif "delete" in actions:
            destroyed += 1
        elif "update" in actions:
            changed += 1

    return added, changed, destroyed


def mutating(plan):
    """Addresses the plan would actually change."""
    return [
        change.get("address", "?")
        for change in plan.get("resource_changes") or []
        if change.get("change", {}).get("actions", []) not in ([NO_OP], [])
    ]


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: plan_nonempty.py <plan.json>")

    with open(sys.argv[1], encoding="utf-8") as handle:
        plan = json.load(handle)

    entries = plan.get("resource_changes")
    changing = mutating(plan)
    added, changed, destroyed = counts(plan)

    # Printed on both paths. On a refusal it says what was examined; on a pass it
    # is the line the job summary carries to the reviewer.
    total = len(entries) if entries else 0
    print(f"plan: {added} to add, {changed} to change, {destroyed} to destroy")
    print(f"      ({total} resource(s) in the plan, {total - len(changing)} unchanged)")

    if changing:
        for address in sorted(changing)[:50]:
            print(f"  will change: {address}")
        return

    # `GITHUB_*` are absent when this runs locally; the message stays useful.
    import os

    ref = os.environ.get("GITHUB_REF_NAME", "(unknown ref)")
    sha = os.environ.get("GITHUB_SHA", "(unknown commit)")

    if entries is None:
        detail = "the plan carries no `resource_changes` at all"
    elif not entries:
        detail = "`resource_changes` is empty"
    else:
        detail = f"all {total} entries are no-op, so the configuration is already converged"

    raise SystemExit(
        f"plan produces no change — {detail}.\n"
        f"Planned against ref {ref} at commit {sha}.\n"
        "Arming is refused: approving this would spend a required-reviewer "
        "approval on an apply that changes nothing, and would record that ref as "
        "the commit a wave was applied from. If the wave's code is on a branch, "
        "merge it before dispatching; if the wave is already applied, there is "
        "nothing to arm."
    )


if __name__ == "__main__":
    main()
