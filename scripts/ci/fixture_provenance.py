"""Fixture provenance gate (F2 directive W3C.2).

Guard fixtures are derived from real `terraform show -json` output, never
authored — `scripts/ci/testdata/README.md` states the rule and why. This is what
holds it.

Three assertions, and the third is the one that makes the rule bind rather than
merely exist:

1. every fixture on disk has a manifest entry — a file nobody declared has no
   stated provenance, and "no entry" would otherwise be the way around the gate;
2. every manifest entry names a file that exists, so the manifest cannot drift
   into a list of things that used to be true;
3. a fixture **added or modified in this change** must be `captured`, and the
   manifest must be updated in the same change.

The third is why legacy fixtures are grandfathered rather than rewritten. Thirteen
of them predate the rule; re-deriving all of them at once would mix "a guard's
verdict moved" in with "the file was regenerated", and the first is a finding that
must not arrive disguised as churn. Touching one upgrades it — which puts the cost
on the change that is already looking at the file.
"""

import json
import os
import sys

CAPTURED = "captured"
LEGACY = "hand-authored-legacy"
VALID = {CAPTURED, LEGACY}

MANIFEST_NAME = "fixtures.manifest.json"


def load(manifest_path):
    with open(manifest_path, encoding="utf-8") as handle:
        document = json.load(handle)
    return document.get("fixtures", {})


def on_disk(testdata_dir):
    return {
        name
        for name in os.listdir(testdata_dir)
        if name.endswith(".json") and name != MANIFEST_NAME
    }


def check(fixtures, present, changed, manifest_changed):
    """Returns a list of violations. `changed` is fixture basenames only."""
    violations = []

    for name in sorted(present - set(fixtures)):
        violations.append(
            f"{name}: on disk with no entry in {MANIFEST_NAME}. Every fixture "
            "states where it came from; an undeclared file is how the rule gets "
            "bypassed without anyone deciding to bypass it."
        )

    for name in sorted(set(fixtures) - present):
        violations.append(
            f"{name}: has a manifest entry but no file. Remove the entry in the "
            "same change that removed the fixture, or the manifest becomes a "
            "record of what used to be true."
        )

    for name, entry in sorted(fixtures.items()):
        provenance = entry.get("provenance")
        if provenance not in VALID:
            violations.append(
                f"{name}: provenance is {provenance!r}, must be one of "
                f"{sorted(VALID)}."
            )

    for name in sorted(changed):
        entry = fixtures.get(name)
        if entry is None:
            # Already reported above as an undeclared file; do not say it twice.
            continue

        if entry.get("provenance") != CAPTURED:
            violations.append(
                f"{name}: changed in this commit, so it must be derived from real "
                "`terraform show -json` output through scripts/ci/scrub_plan.py "
                f"and recorded as {CAPTURED!r} — it is {entry.get('provenance')!r}. "
                "Legacy fixtures are grandfathered only until something touches "
                "them; this is the change that touched it."
            )

    if changed and not manifest_changed:
        listed = ", ".join(sorted(changed))
        violations.append(
            f"{MANIFEST_NAME} was not updated, but these fixtures changed: "
            f"{listed}. Provenance recorded in a later commit is provenance "
            "nobody checked at the time it mattered."
        )

    return violations


def main():
    if len(sys.argv) < 3:
        raise SystemExit(
            "usage: fixture_provenance.py <testdata-dir> <manifest-changed:0|1> "
            "[changed-path ...]"
        )

    testdata_dir = sys.argv[1]
    manifest_changed = sys.argv[2] == "1"
    changed = {
        os.path.basename(path)
        for path in sys.argv[3:]
        if path.endswith(".json") and os.path.basename(path) != MANIFEST_NAME
    }

    fixtures = load(os.path.join(testdata_dir, MANIFEST_NAME))
    present = on_disk(testdata_dir)

    violations = check(fixtures, present, changed, manifest_changed)

    print(
        f"fixture provenance: {len(fixtures)} declared, {len(present)} on disk, "
        f"{len(changed)} changed in this commit"
    )
    for name in sorted(changed):
        entry = fixtures.get(name, {})
        print(f"  changed: {name} ({entry.get('provenance', 'undeclared')})")

    if violations:
        print(f"fixture provenance: {len(violations)} violation(s)")
        for violation in violations:
            print(f"  {violation}")
        raise SystemExit(1)

    print("fixture provenance: clean")


if __name__ == "__main__":
    main()
