"""SEQ-036 fix round 1: regression tests for F1 to F8, through the command line.

F1  a new record from `transition` is always `captured` and drops a delivery receipt, like `capture`
F2  a move to `done` through `revise` or `transition` is judged on the record as it would be written
F3  `claim` needs a lifecycle of `accepted`, `active` or `blocked`, and refuses before any write
F4  an appended evidence entry may not carry the `record-result` source
F5  stored evidence is compared type-strictly
F6  `evidence: null` is always refused
F7  reverted: `schema` keeps `seq` required for `claim` and `record-result`; `--seq` may still supply it
F8  an argument-error answer names a command only when the first positional word is one
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

import test_store as _store_tests  # noqa: E402

from session_flow import records  # noqa: E402

ENTRYPOINT = _store_tests.ENTRYPOINT
NAMESPACE = _store_tests.NAMESPACE
TAKEOVER_AUTHORITY = _store_tests.TAKEOVER_AUTHORITY
snapshot = _store_tests.snapshot

ACTOR = "agent:store-implementer"
COORDINATOR = _store_tests.FIXTURE_COORDINATOR
TARGET = ("--seq", "SEQ-001", "--task", "A1")
RECEIPT = {"required": True, "target": "a release", "delivered_at": "2026-09-07T12:00:00Z"}


class FixCase(_store_tests.StoreCase):
    """SEQ-001/A1 is `accepted`; helpers seed what a case needs."""

    def a1(self) -> dict:
        return self.record_metadata(task="A1")

    def revision(self) -> int:
        return self.a1()["revision"]

    def fingerprint(self) -> str:
        return records.scope_fingerprint(records.read_record(_store_tests.store.record_path(self.root, "SEQ-001", "A1")))

    def entry(self, criteria="check", **fields) -> dict:
        return dict({"criteria": criteria, "fingerprint": self.fingerprint(), "result": "pass"}, **fields)

    def seed_completable(self) -> None:
        """A1 is active, claimed by the coordinator, accepted and carries applicable evidence."""
        self.accept_fixture(task="A1")
        self.seed_claim(task="A1")
        self.patch_record({"lifecycle": "active", "evidence": [self.entry()]}, task="A1")

    def assert_refused(self, command, document, codes, *arguments) -> dict:
        before = snapshot(self.root)
        completed, answer = self.run_cli(command, document, *arguments)
        self.assertEqual(1, completed.returncode, completed.stdout)
        self.assertFalse(answer["ok"], answer)
        self.assertIn(answer["error"]["code"], codes, answer["error"]["message"])
        self.assertEqual(before, snapshot(self.root), "a refused command must not write")
        return answer["error"]

    def assert_succeeds(self, command, document, *arguments) -> dict:
        completed, answer = self.run_cli(command, document, *arguments)
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertTrue(answer["ok"], answer)
        return answer["result"]

    def revise_document(self, metadata=None, **changes) -> dict:
        document = {"expect_revision": self.revision(), "actor": COORDINATOR}
        if metadata is not None:
            document["metadata"] = metadata
        return dict(document, **changes)

    def transition_document(self, metadata=None, **change) -> dict:
        entry = {"seq": "SEQ-001", "task": "A1", "expect_revision": self.revision()}
        if metadata is not None:
            entry["metadata"] = metadata
        return {"coordinator": COORDINATOR, "actor": COORDINATOR, "changes": [dict(entry, **change)]}

    def revise(self, metadata=None, **changes) -> dict:
        return self.assert_succeeds("revise", self.revise_document(metadata, **changes), *TARGET)

    def new_record_document(self, metadata: dict) -> dict:
        return {
            "operation": "op-fixes-new-0001",
            "coordinator": "session-add-task",
            "actor": "session-add-task",
            "provenance": {"actor": "user", "source": "session-gatekeeper", "captured_at": "2026-09-07T10:05:00Z"},
            "changes": [{"new": True, "metadata": metadata, "scope": "A scope that acceptance binds to later.", "body": ""}],
        }


class F1NewRecordTest(FixCase):
    def test_a_new_record_is_captured_whatever_lifecycle_the_payload_names(self):
        for lifecycle in ("done", "active", "bogus"):
            with self.subTest(lifecycle=lifecycle):
                self.setUp()
                document = self.new_record_document({"title": "Planted", "lifecycle": lifecycle})
                self.assert_succeeds("transition", document)
                metadata = self.record_metadata(seq="SEQ-003")
                self.assertEqual("captured", metadata["lifecycle"])
                self.assertEqual("Planted", metadata["title"])

    def test_a_new_record_drops_a_delivery_receipt(self):
        self.assert_succeeds("transition", self.new_record_document({"title": "Delivered", "delivery": RECEIPT}))
        delivery = self.record_metadata(seq="SEQ-003").get("delivery", {})
        self.assertNotIn("delivered_at", delivery)
        self.assertEqual("a release", delivery.get("target"))

    def test_capture_drops_a_delivery_receipt_and_a_lifecycle(self):
        metadata = {"title": "Delivered", "delivery": RECEIPT, "lifecycle": "done"}
        self.assert_succeeds("capture", {"scope": "A scope.", "metadata": metadata}, "--namespace", NAMESPACE, "--seq", "SEQ-003")
        stored = self.record_metadata(seq="SEQ-003")
        self.assertEqual("captured", stored["lifecycle"])
        self.assertNotIn("delivered_at", stored.get("delivery", {}))


class F2CompletionJudgedOnPlannedRecordTest(FixCase):
    GATE_CODES = ("inapplicable-evidence", "missing-authority")

    def test_a_revise_that_changes_scope_and_sets_done_is_refused_and_writes_nothing(self):
        self.seed_completable()
        document = self.revise_document({"lifecycle": "done"}, scope="A different outcome than the one accepted.")
        self.assert_refused("revise", document, self.GATE_CODES, *TARGET)

    def test_a_transition_that_changes_scope_and_sets_done_is_refused_and_writes_nothing(self):
        self.seed_completable()
        document = self.transition_document({"lifecycle": "done"}, scope="A different outcome than the one accepted.")
        self.assert_refused("transition", document, self.GATE_CODES)

    def test_a_revise_that_sets_done_without_changing_scope_still_completes(self):
        self.seed_completable()
        self.revise({"lifecycle": "done"})
        self.assertEqual("done", self.a1()["lifecycle"])

    def test_a_transition_that_sets_done_without_changing_scope_still_completes(self):
        self.seed_completable()
        self.assert_succeeds("transition", self.transition_document({"lifecycle": "done"}))
        self.assertEqual("done", self.a1()["lifecycle"])

    def test_a_revise_to_done_with_new_applicable_evidence_is_judged_with_that_evidence(self):
        self.accept_fixture(task="A1")
        self.seed_claim(task="A1")
        self.patch_record({"lifecycle": "active"}, task="A1")
        self.assert_refused("revise", self.revise_document({"lifecycle": "done"}), self.GATE_CODES, *TARGET)
        self.revise({"lifecycle": "done", "evidence": [self.entry()]})
        self.assertEqual("done", self.a1()["lifecycle"])


class F3ClaimLifecycleTest(FixCase):
    def claim_document(self, **changes) -> dict:
        document = {
            "coordinator": "session-delegation",
            "actor": ACTOR,
            "seq": "SEQ-001",
            "task": "A1",
            "expect_revision": self.revision(),
            "allowed_paths": ["scripts/session_flow/store.py"],
        }
        return dict(document, **changes)

    def test_a_claim_with_takeover_on_a_done_task_is_refused_and_keeps_the_result(self):
        self.accept_fixture(task="A1")
        result = {"outcome": "passed", "recorded_at": "2026-09-07T12:00:00Z", "actor": COORDINATOR}
        self.patch_record({"lifecycle": "done", "result": result}, task="A1")
        self.seed_claim(task="A1")
        document = self.claim_document(takeover_claim=TAKEOVER_AUTHORITY)
        error = self.assert_refused("claim", document, ("missing-authority",))
        self.assertIn("done", error["message"])
        self.assertEqual(result, self.a1()["result"])

    def test_a_claim_on_a_cancelled_or_deferred_task_is_refused(self):
        for lifecycle in ("cancelled", "deferred"):
            with self.subTest(lifecycle=lifecycle):
                self.setUp()
                self.accept_fixture(task="A1")
                self.patch_record({"lifecycle": lifecycle}, task="A1")
                self.assert_refused("claim", self.claim_document(), ("missing-authority",))

    def test_a_claim_on_a_blocked_task_is_allowed(self):
        self.accept_fixture(task="A1")
        self.patch_record({"lifecycle": "blocked"}, task="A1")
        self.assert_succeeds("claim", self.claim_document())
        self.assertEqual(ACTOR, self.a1()["claim"]["actor"])

    def test_a_claim_on_an_active_task_by_its_holder_is_allowed(self):
        self.accept_fixture(task="A1")
        self.patch_record({"lifecycle": "active"}, task="A1")
        self.seed_claim(actor=ACTOR, task="A1")
        self.assert_succeeds("claim", self.claim_document())
        self.assertEqual("active", self.a1()["lifecycle"])


class F4ToF6EvidencePatchTest(FixCase):
    def test_an_appended_entry_with_the_record_result_source_is_refused(self):
        self.patch_record({"evidence": [self.entry("stored")]}, task="A1")
        stored = self.a1()["evidence"]
        forged = self.entry("forged", source="record-result")
        for command, document in (
            ("revise", self.revise_document({"evidence": stored + [forged]})),
            ("transition", self.transition_document({"evidence": stored + [forged]})),
        ):
            with self.subTest(command=command):
                arguments = TARGET if command == "revise" else ()
                error = self.assert_refused(command, document, ("invalid-request",), *arguments)
                self.assertIn("record-result", error["message"])

    def test_an_appended_entry_with_another_source_is_accepted(self):
        stored = self.entry("stored", source="record-result")
        self.patch_record({"evidence": [stored]}, task="A1")
        fresh = self.entry("fresh", source="session-verify")
        self.revise({"evidence": [stored, fresh]})
        self.assertEqual([stored, fresh], self.a1()["evidence"])

    def test_stored_evidence_is_compared_type_strictly(self):
        self.patch_record({"evidence": [self.entry("flag", limitations=1)]}, task="A1")
        stored = self.a1()["evidence"]
        changed = [dict(stored[0], limitations=True)]
        self.assert_refused("revise", self.revise_document({"evidence": changed}), ("invalid-request",), *TARGET)
        self.assert_refused("transition", self.transition_document({"evidence": changed}), ("invalid-request",))

    def test_stored_evidence_sent_back_unchanged_is_accepted(self):
        self.patch_record({"evidence": [self.entry("flag", limitations=1)]}, task="A1")
        stored = self.a1()["evidence"]
        self.revise({"evidence": stored, "title": "Retitled"})
        self.assertEqual(stored, self.a1()["evidence"])

    def test_evidence_null_is_refused_when_nothing_is_stored(self):
        self.assertNotIn("evidence", self.a1())
        self.assert_refused("revise", self.revise_document({"evidence": None}), ("invalid-request",), *TARGET)
        self.assert_refused("transition", self.transition_document({"evidence": None}), ("invalid-request",))

    def test_evidence_null_is_refused_when_entries_are_stored(self):
        self.patch_record({"evidence": [self.entry()]}, task="A1")
        error = self.assert_refused("revise", self.revise_document({"evidence": None}), ("invalid-request",), *TARGET)
        self.assertIn("evidence", error["message"])


class RejectedChangeInATwoChangeTransitionTest(FixCase):
    def test_a_refused_second_change_leaves_the_valid_first_change_unwritten(self):
        self.seed_claim(task="A1")
        self.patch_record({"evidence": [self.entry()]}, task="A1")
        first = {"seq": "SEQ-001", "task": "A1", "expect_revision": self.revision(), "metadata": {"title": "Never written"}}
        second = {"seq": "SEQ-001", "expect_revision": 1, "metadata": {"evidence": None}}
        document = {"coordinator": COORDINATOR, "actor": COORDINATOR, "changes": [first, second]}
        self.assert_refused("transition", document, ("invalid-request",))
        self.assertNotEqual("Never written", self.a1().get("title"))

    def test_a_second_change_that_completes_unearned_work_leaves_the_first_unwritten(self):
        self.seed_claim(task="A1")
        self.seed_claim(task=None)
        self.patch_record({"lifecycle": "active"})
        first = {"seq": "SEQ-001", "task": "A1", "expect_revision": self.revision(), "metadata": {"title": "Never written"}}
        second = {"seq": "SEQ-001", "expect_revision": 1, "metadata": {"lifecycle": "done"}}
        document = {"coordinator": COORDINATOR, "actor": COORDINATOR, "changes": [first, second]}
        self.assert_refused("transition", document, ("inapplicable-evidence", "missing-authority"))
        self.assertNotEqual("Never written", self.a1().get("title"))


class F7F8CommandLineTest(FixCase):
    def cli(self, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(ENTRYPOINT), *arguments], capture_output=True, text=True, check=False)

    def schema(self, command: str) -> dict:
        completed = self.cli("schema", command, "--project-root", str(self.project))
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        return json.loads(completed.stdout)["result"]

    def test_a_claim_with_seq_and_task_only_on_the_command_line_is_accepted(self):
        self.accept_fixture(task="A1")
        document = {"coordinator": "session-delegation", "actor": ACTOR, "expect_revision": self.revision()}
        self.assert_succeeds("claim", document, *TARGET)
        self.assertEqual(ACTOR, self.a1()["claim"]["actor"])

    def argument_error(self, *arguments: str) -> dict:
        completed = self.cli(*arguments)
        self.assertEqual(2, completed.returncode, completed.stdout + completed.stderr)
        answer = json.loads(completed.stdout)
        self.assertEqual("invalid-request", answer["error"]["code"])
        return answer

    def test_the_command_is_null_when_an_option_value_looks_like_a_command(self):
        self.assertIsNone(self.argument_error("--input", "claim", "bogus")["command"])

    def test_the_word_after_a_bare_double_dash_is_the_command(self):
        self.assertEqual("show", self.argument_error("--", "show", "extra")["command"])

    def test_the_command_is_null_for_an_unknown_command(self):
        self.assertIsNone(self.argument_error("frobnicate", "claim")["command"])

    def test_the_command_is_named_when_it_is_the_first_positional_word(self):
        answer = self.argument_error("show", "--project-root", str(self.project), "stray")
        self.assertEqual("show", answer["command"])

    def test_the_command_is_named_after_options_with_values(self):
        answer = self.argument_error("--project-root", str(self.project), "--seq", "SEQ-001", "show", "--bogus")
        self.assertEqual("show", answer["command"])


if __name__ == "__main__":
    unittest.main()
