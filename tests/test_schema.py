"""Unit tests for `session_flow.schema.describe` beyond the SEQ-032 acceptance cases."""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ENTRYPOINT = Path(__file__).resolve().parents[1] / "scripts" / "session-flow.py"
sys.path.insert(0, str(ENTRYPOINT.parent))

from session_flow import InvalidRequestError, records, schema  # noqa: E402


class DescribeRefusalTest(unittest.TestCase):
    def test_a_missing_or_unknown_command_is_refused_with_the_valid_names(self):
        for name in (None, "frobnicate"):
            with self.subTest(name=name):
                with self.assertRaises(InvalidRequestError) as raised:
                    schema.describe(name)
                for command in schema.VALID_KEYS:
                    self.assertIn(command, str(raised.exception))

    def test_every_required_field_is_a_valid_key(self):
        for command, required in schema.REQUIRED.items():
            with self.subTest(command=command):
                self.assertLessEqual(set(required), schema.VALID_KEYS[command])


class ExampleTest(unittest.TestCase):
    def test_the_record_result_example_carries_closing_evidence(self):
        evidence = schema.EXAMPLES["record-result"]["result"]["evidence"]
        self.assertEqual({"criteria", "revision", "environment", "limitations"}, set(evidence))

    def test_the_capture_example_shows_the_task_fields_and_passes_key_validation(self):
        example = schema.EXAMPLES["capture"]
        self.assertLessEqual(set(example), schema.VALID_KEYS["capture"])
        self.assertEqual(
            {"title", "parent", "priority", "order", "depends_on", "allowed_paths"}, set(example["metadata"])
        )
        records.check_payload_keys(example, "capture", records.CAPTURE_KEYS)


class CommandNameTest(unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, "-B", str(ENTRYPOINT), *arguments], capture_output=True, text=True, check=False
        )

    def test_a_name_is_refused_for_every_command_but_schema(self):
        for command in ("doctor", "show", "capture"):
            with self.subTest(command=command):
                completed = self.run_cli(command, "claim")
                self.assertEqual(2, completed.returncode, completed.stderr)
                self.assertIn("only `schema` takes a command name", completed.stderr)

    def test_schema_still_reads_its_name(self):
        completed = self.run_cli("schema", "claim")
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("required", json.loads(completed.stdout)["result"])

    def test_an_in_process_request_without_a_name_is_refused_as_a_usage_error(self):
        spec = importlib.util.spec_from_file_location("session_flow_cli", ENTRYPOINT)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        with self.assertRaises(InvalidRequestError):
            cli.run({"command": "schema"})


if __name__ == "__main__":
    unittest.main()
