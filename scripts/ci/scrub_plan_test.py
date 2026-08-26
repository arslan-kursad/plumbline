"""Tests for scrub_plan.py.

Every assertion here can fail: each is checked against a case that violates it,
not only against one that satisfies it. A test that has never been seen red is a
test whose subject nobody has confirmed it reads.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scrub_plan  # noqa: E402

PROJECT_ID = "realproject-12345"
PROJECT_NUMBER = "911930495850"


def sample():
    """A plan-shaped document carrying every form the tool has a rule for."""
    return {
        "format_version": "1.2",
        "variables": {
            "project_id": {"value": PROJECT_ID},
            # The two the capture path leaks. Shapes only — no real value is
            # written down here either, for the same reason the tool holds none.
            "alert_email": {"value": "Someone.Real@example-mail.com"},
            "billing_account_id": {"value": "0AB12C-3DE456-789F01"},
            "region": {"value": "us-central1"},
        },
        "resource_changes": [
            {
                "address": "google_cloud_run_v2_service_iam_member.worker_push_invoker",
                "type": "google_cloud_run_v2_service_iam_member",
                "change": {
                    "actions": ["create"],
                    "after": {
                        "name": "ingestion-worker",
                        "location": "us-central1",
                        "role": "roles/run.invoker",
                        "member": f"serviceAccount:pubsub-push@{PROJECT_ID}.iam.gserviceaccount.com",
                        "condition": [],
                    },
                },
            },
            {
                "address": "google_pubsub_subscription.traces_push",
                "type": "google_pubsub_subscription",
                "change": {
                    "actions": ["create"],
                    "after": {
                        "name": "traces-push",
                        "topic": f"projects/{PROJECT_NUMBER}/topics/traces",
                        "push_config": [
                            {
                                "push_endpoint": "https://ingestion-worker-4w4sdms2mq-uc.a.run.app/push",
                                "oidc_token": [
                                    {
                                        "audience": "plumbline-ingestion-worker",
                                        "service_account_email": f"pubsub-push@{PROJECT_ID}.iam.gserviceaccount.com",
                                    }
                                ],
                            }
                        ],
                        "labels": {"component": "transport"},
                        "retain_acked_messages": False,
                        "ack_deadline_seconds": 60,
                    },
                },
            },
            {
                "address": "google_pubsub_topic_iam_member.pubsub_agent_publishes_dlq",
                "type": "google_pubsub_topic_iam_member",
                "change": {
                    "actions": ["create"],
                    "after": {
                        "topic": "traces-dlq",
                        "role": "roles/pubsub.publisher",
                        "member": f"serviceAccount:service-{PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com",
                    },
                },
            },
        ],
    }


def run(document):
    return scrub_plan.scrub(document, PROJECT_ID, PROJECT_NUMBER)


class KeyPreservation(unittest.TestCase):
    """The property the tool exists for: a fixture must not lose a field."""

    def test_structure_is_identical(self):
        source = sample()
        self.assertEqual(scrub_plan.shape(source), scrub_plan.shape(run(source)))

    def test_every_key_path_survives(self):
        source = sample()
        result = run(source)

        def paths(node, prefix="$"):
            out = set()
            if isinstance(node, dict):
                for key, value in node.items():
                    out.add(f"{prefix}.{key}")
                    out |= paths(value, f"{prefix}.{key}")
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    out |= paths(value, f"{prefix}[{index}]")
            return out

        self.assertEqual(paths(source), paths(result))

    def test_the_check_can_fail(self):
        """A transform that drops a key must be refused, not reported clean.

        Without this, `test_structure_is_identical` passes for a tool that never
        touches anything, and the property would be untested rather than held.
        """
        source = sample()
        lossy = json.loads(json.dumps(source))
        del lossy["resource_changes"][0]["change"]["after"]["name"]
        self.assertNotEqual(scrub_plan.shape(source), scrub_plan.shape(lossy))

    def test_non_string_values_are_untouched(self):
        result = run(sample())
        after = result["resource_changes"][1]["change"]["after"]
        self.assertIs(after["retain_acked_messages"], False)
        self.assertEqual(after["ack_deadline_seconds"], 60)


class NumericValues(unittest.TestCase):
    """A plan carries `project_number` as an integer, not a string.

    The first version of this tool substituted only strings and passed a real plan
    with four surviving project numbers. Every rule looked right and the scan read
    strings only, so nothing was red.
    """

    def test_numeric_project_number_is_substituted(self):
        document = sample()
        document["resource_changes"][0]["change"]["after"]["project_number"] = int(
            PROJECT_NUMBER
        )
        result = run(document)
        self.assertEqual(
            result["resource_changes"][0]["change"]["after"]["project_number"],
            int(scrub_plan.PROJECT_NUMBER),
        )

    def test_booleans_are_not_treated_as_integers(self):
        """`bool` subclasses `int`; rewriting one would change meaning."""
        result = run(sample())
        self.assertIs(
            result["resource_changes"][1]["change"]["after"]["retain_acked_messages"],
            False,
        )

    def test_a_surviving_project_number_is_refused(self):
        """The claim-check, which is what would have caught the original bug."""

        original = scrub_plan.transform

        def blind(node, project_id, project_number):
            # A rule with the exact blind spot the first version had.
            return original(node, project_id, None) if isinstance(node, int) else original(
                node, project_id, project_number
            )

        scrub_plan.transform = blind
        try:
            document = sample()
            document["resource_changes"][0]["change"]["after"]["project_number"] = int(
                PROJECT_NUMBER
            )
            with self.assertRaises(SystemExit) as caught:
                run(document)
            self.assertIn("project number", str(caught.exception))
            self.assertIn("blind spot", str(caught.exception))
        finally:
            scrub_plan.transform = original

    def test_the_scan_reads_non_string_leaves(self):
        findings = scrub_plan.residual_findings({"n": 1, "s": "ops@elsewhere.example"})
        self.assertTrue(findings)


class Idempotence(unittest.TestCase):
    def test_second_pass_changes_nothing(self):
        once = run(sample())
        twice = scrub_plan.scrub(json.loads(json.dumps(once)), PROJECT_ID, PROJECT_NUMBER)
        self.assertEqual(once, twice)

    def test_scrubbed_output_passes_its_own_residual_scan(self):
        self.assertEqual(scrub_plan.residual_findings(run(sample())), [])


class Substitution(unittest.TestCase):
    def test_project_id_and_number_are_replaced(self):
        text = json.dumps(run(sample()))
        self.assertNotIn(PROJECT_ID, text)
        self.assertNotIn(PROJECT_NUMBER, text)
        self.assertIn(scrub_plan.PROJECT_ID, text)
        self.assertIn(scrub_plan.PROJECT_NUMBER, text)

    def test_billing_account_is_replaced(self):
        result = run(sample())
        self.assertEqual(
            result["variables"]["billing_account_id"]["value"],
            scrub_plan.BILLING_ACCOUNT,
        )

    def test_personal_email_is_replaced(self):
        result = run(sample())
        self.assertEqual(result["variables"]["alert_email"]["value"], scrub_plan.EMAIL)

    def test_runtime_identities_stay_distinguishable(self):
        """The generic email rule must not flatten the service accounts.

        A fixture whose collector and worker share one address cannot support any
        assertion about which identity holds which grant, which is most of what
        these fixtures are read for.
        """
        result = run(sample())
        member = result["resource_changes"][0]["change"]["after"]["member"]
        self.assertEqual(
            member,
            f"serviceAccount:pubsub-push@{scrub_plan.PROJECT_ID}.iam.gserviceaccount.com",
        )
        agent = result["resource_changes"][2]["change"]["after"]["member"]
        self.assertIn(f"service-{scrub_plan.PROJECT_NUMBER}@gcp-sa-pubsub", agent)

    def test_cloud_run_host_is_replaced(self):
        endpoint = run(sample())["resource_changes"][1]["change"]["after"]["push_config"][0][
            "push_endpoint"
        ]
        self.assertNotIn("4w4sdms2mq", endpoint)
        self.assertIn(scrub_plan.RUN_APP_HASH, endpoint)
        self.assertTrue(endpoint.endswith("/push"), endpoint)


class ResidualScan(unittest.TestCase):
    """The scan is the reason the shape rules can be trusted."""

    def test_undeclared_email_domain_is_refused(self):
        document = sample()
        # Reached by a rule that does not know this form: an address planted where
        # substitution has already run cannot be caught by substitution.
        document["variables"]["alert_email"] = {"value": "ops@somewhere-else.example"}
        findings = scrub_plan.residual_findings(document)
        self.assertTrue(any("undeclared domain" in name for _path, name in findings))

    def test_api_key_shape_is_refused(self):
        document = sample()
        document["variables"]["region"]["value"] = "plb" + "_live_" + "a" * 32
        with self.assertRaises(SystemExit) as caught:
            run(document)
        self.assertIn("issued API key", str(caught.exception))

    def test_private_key_material_is_refused(self):
        document = sample()
        document["variables"]["region"]["value"] = "-----BEGIN RSA PRIVATE KEY-----"
        with self.assertRaises(SystemExit):
            run(document)

    def test_failure_message_names_the_path_and_not_the_value(self):
        document = sample()
        secret = "plb" + "_live_" + "b" * 32
        document["variables"]["region"]["value"] = secret
        with self.assertRaises(SystemExit) as caught:
            run(document)
        message = str(caught.exception)
        self.assertIn("$.variables.region.value", message)
        self.assertNotIn(secret, message)

    def test_a_clean_document_produces_no_findings(self):
        self.assertEqual(scrub_plan.residual_findings(run(sample())), [])


class CommandLine(unittest.TestCase):
    def test_runs_end_to_end_over_stdin(self):
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent / "scrub_plan.py"),
                "-",
                "--project-id",
                PROJECT_ID,
                "--project-number",
                PROJECT_NUMBER,
            ],
            input=json.dumps(sample()),
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(json.loads(result.stdout), run(sample()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
