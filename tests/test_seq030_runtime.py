"""SEQ-030 acceptance tests for the runtime contract changes (tasks A1 to A4).

A1  one revision key, `expect_revision`, with `expected_revision` as a deprecated alias
A2  strict decision `scope` and strict top-level payload keys
A3  latest evidence per criterion, and the tighter completion gate
A4  a claim on a record that carries a result clears that result

The cases reuse the temp-root helpers of `test_records` and `test_store` and only ever
write inside a temporary directory.
"""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

import test_records as _records_tests  # noqa: E402
import test_store as _store_tests  # noqa: E402

from session_flow import InapplicableEvidenceError, records, store  # noqa: E402

AUTHORITY = _records_tests.AUTHORITY
snapshot = _records_tests.snapshot
payload = _store_tests.payload
STALE_FINGERPRINT = "sha256:" + "0" * 64
LIST_FORM = re.compile(r'\[\s*"[^"]+"')


class RecordsCase(_records_tests.MutationTest):
    """A temporary root holding SEQ-002 at revision 4, with acceptance that applies."""

    def send(self, command: str, **fields):
        return self.call(command, fields)

    def assert_refused(self, command: str, fields: dict, *needles: str, code="invalid-request"):
        before = snapshot(self.work)
        _, response = self.call(command, fields)
        self.assertFalse(response["ok"], response)
        self.assertEqual(code, response["error"]["code"], response["error"]["message"])
        for needle in needles:
            self.assertIn(needle, response["error"]["message"])
        self.assertEqual(before, snapshot(self.work))
        return response["error"]["message"]


class A1RevisionKeyTest(RecordsCase):
    def test_a1_expect_revision_accepted_by_revise_and_accept(self):
        _, response = self.send("revise", expect_revision=4, metadata={"priority": "P0"})
        self.assertTrue(response["ok"], response)
        self.assertEqual("P0", self.stored()["metadata"]["priority"])
        _, response = self.send("accept", **dict(AUTHORITY, expect_revision=5))
        self.assertTrue(response["ok"], response)

    def test_a1_alias_accepted(self):
        _, response = self.send("revise", expected_revision=4, metadata={"priority": "P0"})
        self.assertTrue(response["ok"], response)
        self.assertEqual("P0", self.stored()["metadata"]["priority"])
        _, response = self.send("accept", **dict(AUTHORITY, expected_revision=5))
        self.assertTrue(response["ok"], response)

    def test_a1_both_keys_with_the_same_value_are_accepted(self):
        _, response = self.send("revise", expect_revision=4, expected_revision=4, metadata={"priority": "P0"})
        self.assertTrue(response["ok"], response)

    def test_a1_conflicting_values_are_refused_naming_expect_revision(self):
        self.assert_refused(
            "revise", {"expect_revision": 4, "expected_revision": 3, "metadata": {"priority": "P0"}}, "expect_revision"
        )

    def test_a1_conflicting_values_are_refused_by_accept_too(self):
        self.assert_refused(
            "accept", dict(AUTHORITY, expect_revision=4, expected_revision=3), "expect_revision"
        )

    def test_a1_a_missing_revision_names_expect_revision(self):
        self.assert_refused("revise", {"metadata": {"priority": "P0"}}, "expect_revision")


class A2DecisionScopeTest(RecordsCase):
    def test_a2_accept_refuses_a_string_scope_and_shows_the_list_form(self):
        message = self.assert_refused(
            "accept", dict(AUTHORITY, expect_revision=4, scope="implement"), "scope"
        )
        self.assertRegex(message, LIST_FORM)

    def test_a2_same_meaning_refuses_a_string_scope(self):
        message = self.assert_refused(
            "revise",
            {"expect_revision": 4, "metadata": {"priority": "P0"}, "same_meaning": dict(AUTHORITY, scope="implement")},
            "scope",
        )
        self.assertRegex(message, LIST_FORM)

    def test_a2_preparation_refuses_a_string_scope(self):
        message = self.assert_refused(
            "revise",
            {"expect_revision": 4, "metadata": {"priority": "P0"}, "preparation": dict(AUTHORITY, scope="implement")},
            "scope",
        )
        self.assertRegex(message, LIST_FORM)

    def test_a2_a_list_with_a_non_string_entry_is_refused(self):
        self.assert_refused("accept", dict(AUTHORITY, expect_revision=4, scope=["implement", 7]), "scope")

    def test_a2_a_list_of_strings_is_accepted_everywhere(self):
        _, response = self.send("accept", **dict(AUTHORITY, expect_revision=4, scope=["implement", "verify"]))
        self.assertTrue(response["ok"], response)
        _, response = self.send(
            "revise",
            expect_revision=5,
            metadata={"priority": "P0"},
            preparation=dict(AUTHORITY, scope=["task preparation"]),
        )
        self.assertTrue(response["ok"], response)


class A2UnknownKeyRecordsTest(RecordsCase):
    def test_a2_accept_refuses_an_unknown_key_and_lists_the_valid_ones(self):
        self.assert_refused(
            "accept",
            dict(AUTHORITY, expect_revision=4, bogus_key=1),
            "bogus_key",
            "expect_revision",
            "authority",
            "actor",
        )

    def test_a2_revise_refuses_an_unknown_key_and_lists_the_valid_ones(self):
        self.assert_refused(
            "revise",
            {"expect_revision": 4, "metadata": {"priority": "P0"}, "bogus_key": 1},
            "bogus_key",
            "expect_revision",
            "metadata",
            "scope",
        )

    def test_a2_capture_refuses_an_unknown_key_and_lists_the_valid_ones(self):
        data = dict(_records_tests.CaptureAndAcceptTest.payload, bogus_key=1)
        before = snapshot(self.work)
        _, response = _records_tests.run_cli(
            self.root,
            "capture",
            "--seq",
            "SEQ-003",
            "--namespace",
            _records_tests.NAMESPACE,
            "--input",
            self.payload_file(data),
        )
        self.assertFalse(response["ok"], response)
        error = response["error"]
        self.assertEqual("invalid-request", error["code"], error["message"])
        for needle in ("bogus_key", "scope", "body", "metadata"):
            self.assertIn(needle, error["message"])
        self.assertEqual(before, snapshot(self.work))


class A2UnknownKeyStoreTest(_store_tests.StoreCase):
    def assert_unknown_key(self, command: str, document: dict, *valid: str) -> None:
        error = self.assert_fails_without_writing(command, dict(document, bogus_key=1), "invalid-request")
        for needle in ("bogus_key",) + valid:
            self.assertIn(needle, error["message"])

    def test_a2_transition_refuses_an_unknown_key_and_lists_the_valid_ones(self):
        self.assert_unknown_key("transition", payload("lifecycle-change.json"), "changes", "coordinator")

    def test_a2_claim_refuses_an_unknown_key_and_lists_the_valid_ones(self):
        self.assert_unknown_key("claim", payload("claim.json"), "allowed_paths", "actor", "expect_revision")

    def test_a2_record_result_refuses_an_unknown_key_and_lists_the_valid_ones(self):
        self.run_cli("claim", payload("claim.json"))
        self.assert_unknown_key("record-result", payload("result.json"), "result", "actor", "expect_revision")


def completion_record(entries: list, acceptance_applies: bool = True) -> dict:
    """SEQ-002 with the given evidence. An entry is (criteria, result, applies)."""
    path = _records_tests.FIXTURES / "acceptance" / "seq-002" / "intent.md"
    record = records.parse_record(path.read_text(encoding="utf-8"))
    fingerprint = records.scope_fingerprint(record)
    record["metadata"]["evidence"] = [
        {"criteria": criteria, "result": result, "fingerprint": fingerprint if applies else STALE_FINGERPRINT}
        for criteria, result, applies in entries
    ]
    if not acceptance_applies:
        record["metadata"]["acceptance"] = dict(record["metadata"]["acceptance"], fingerprint=STALE_FINGERPRINT)
    return record


class A3CompletionGateTest(unittest.TestCase):
    def setUp(self):
        workdir = tempfile.TemporaryDirectory()
        self.addCleanup(workdir.cleanup)
        self.work = Path(workdir.name)

    def check(self, entries: list, **options) -> None:
        records.check_completion(self.work, completion_record(entries, **options))

    def assert_refused(self, entries: list, *needles: str, **options) -> str:
        with self.assertRaises(InapplicableEvidenceError) as raised:
            self.check(entries, **options)
        message = str(raised.exception)
        for needle in needles:
            self.assertIn(needle, message)
        return message

    def test_a3_an_applicable_passing_entry_completes(self):
        self.check([("criterion one", "pass", True)])

    def test_a3_a_stale_entry_followed_by_an_applicable_one_completes(self):
        entries = [("criterion one", "pass", False), ("criterion one", "pass", True)]
        self.check(entries)
        self.assertEqual([], records.stale_evidence(completion_record(entries)))

    def test_a3_only_the_latest_entry_per_criteria_counts(self):
        entries = [("criterion one", "pass", True), ("criterion one", "pass", False)]
        self.assertEqual(1, len(records.stale_evidence(completion_record(entries))))
        self.assert_refused(entries, "criterion one")

    def test_a3_a_stale_entry_of_another_criteria_still_blocks(self):
        self.assert_refused([("criterion two", "pass", False), ("criterion one", "pass", True)], "criterion two")

    def test_a3_no_applicable_entry_is_refused_and_says_what_to_record(self):
        message = self.assert_refused([])
        self.assertRegex(message, r"(?i)record|append")
        self.assertRegex(message, r"(?i)evidence")

    def test_a3_only_stale_entries_are_refused(self):
        self.assert_refused([("criterion one", "pass", False)], "criterion one")

    def test_a3_a_latest_failing_entry_is_refused_and_named(self):
        for entries in (
            [("criterion one", "fail", True)],
            [("criterion one", "pass", True), ("criterion one", "fail", True)],
            [("criterion one", "pass", True), ("criterion two", "fail", True)],
        ):
            with self.subTest(entries=entries):
                message = self.assert_refused(entries, "fail")
                self.assertRegex(message, r"(?i)record|re-run|rerun|append")

    def test_a3_a_failure_followed_by_a_pass_completes(self):
        self.check([("criterion one", "fail", True), ("criterion one", "pass", True)])

    def test_a3_acceptance_that_no_longer_applies_is_refused_and_says_what_to_record(self):
        message = self.assert_refused([("criterion one", "pass", True)], acceptance_applies=False)
        self.assertRegex(message, r"(?i)accept")

    def test_a3_waived_and_unverified_entries_still_count_as_recorded(self):
        for result in ("waived", "unverified"):
            with self.subTest(result=result):
                self.check([("criterion one", result, True)])


class A3StoreGateTest(_store_tests.StoreCase):
    """The same rules, reached through `transition` against a stored record."""

    def setUp(self):
        super().setUp()
        self.patch_record({"lifecycle": "active"})
        self.patch_record({"lifecycle": "done"}, task="A1")
        fingerprint = self.fingerprint()
        self.patch_record(
            {
                "acceptance": {
                    "fingerprint": fingerprint,
                    "actor": "maintainer",
                    "authority": {"source": "user-request", "revision": "2026-09-07T09:00:00Z"},
                    "scope": ["complete"],
                    "accepted_at": "2026-09-07T09:00:00Z",
                }
            }
        )

    def fingerprint(self) -> str:
        return records.scope_fingerprint(records.read_record(store.record_path(self.root, "SEQ-001")))

    def complete(self) -> dict:
        document = payload("lifecycle-change.json")
        document["changes"][0].update({"expect_revision": 1, "metadata": {"lifecycle": "done"}})
        return document

    def evidence(self, *entries) -> None:
        self.patch_record(
            {
                "evidence": [
                    {
                        "criteria": criteria,
                        "result": result,
                        "fingerprint": self.fingerprint() if applies else STALE_FINGERPRINT,
                    }
                    for criteria, result, applies in entries
                ]
            }
        )

    def test_a3_store_refuses_completion_without_any_evidence(self):
        error = self.assert_fails_without_writing("transition", self.complete(), "inapplicable-evidence")
        self.assertRegex(error["message"], r"(?i)evidence")

    def test_a3_store_completes_after_a_stale_entry_is_superseded(self):
        self.evidence(("one effective writer", "pass", False), ("one effective writer", "pass", True))
        completed, answer = self.run_cli("transition", self.complete())
        self.assertEqual(0, completed.returncode, answer)
        self.assertEqual("done", self.record_metadata()["lifecycle"])

    def test_a3_store_refuses_a_latest_failing_entry(self):
        self.evidence(("one effective writer", "fail", True))
        error = self.assert_fails_without_writing("transition", self.complete(), "inapplicable-evidence")
        self.assertIn("one effective writer", error["message"])


class A4ReclaimTest(_store_tests.StoreCase):
    def test_a4_reclaiming_after_a_failed_result_clears_it_and_reserves_the_paths(self):
        self.run_cli("claim", payload("claim.json"))
        failed = payload("result.json")
        failed["result"]["outcome"] = "failed"
        completed, answer = self.run_cli("record-result", failed)
        self.assertEqual(0, completed.returncode, answer)
        self.assertEqual("failed", self.record_metadata(task="A1")["result"]["outcome"])

        reclaim = dict(payload("claim.json"), operation="op-claim-0002", expect_revision=3)
        completed, answer = self.run_cli("claim", reclaim)
        self.assertEqual(0, completed.returncode, answer)
        metadata = self.record_metadata(task="A1")
        self.assertNotIn("result", metadata)
        self.assertEqual("agent:store-implementer", metadata["claim"]["actor"])

        self.drop_claim()
        other = {
            "operation": "op-claim-0003",
            "coordinator": "session-delegation",
            "actor": "agent:other",
            "seq": "SEQ-001",
            "task": None,
            "expect_revision": 1,
            "allowed_paths": ["scripts/session_flow"],
        }
        error = self.assert_fails_without_writing("claim", other, "invalid-request")
        self.assertEqual("agent:store-implementer", error["detail"]["holder"])

    def test_a4_the_operation_journal_still_holds_the_earlier_result(self):
        self.run_cli("claim", payload("claim.json"))
        failed = payload("result.json")
        failed["result"]["outcome"] = "failed"
        self.run_cli("record-result", failed)
        self.run_cli("claim", dict(payload("claim.json"), operation="op-claim-0002", expect_revision=3))
        journal = json.loads(store.operation_path(self.root, "op-result-0001").read_text(encoding="utf-8"))
        self.assertIn("failed", json.dumps(journal))


if __name__ == "__main__":
    unittest.main()
