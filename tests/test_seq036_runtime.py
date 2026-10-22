"""SEQ-036 acceptance tests for the runtime gaps left after SEQ-032 (tasks B1, B2 and B3).

B1  a `revise` metadata edit cannot rewrite helper-owned or identity fields; `capture` drops helper-owned ones
B2  a `transition` change to an existing record is judged by the same rules; `claim` needs applicable
    acceptance; a `passed` result on a non-active task names only the remedy that applies
B3  argument errors answer in JSON with exit 2; `schema` lists a field as required only when leaving it out
    is refused

The cases reuse the temp-root helpers of `test_store` and only ever write inside a temporary directory.
They go through the command line, so they pin behaviour, not the name of the records.py check.
"""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

import test_store as _store_tests  # noqa: E402

from session_flow import records, store  # noqa: E402

ENTRYPOINT = _store_tests.ENTRYPOINT
NAMESPACE = _store_tests.NAMESPACE
StoreCase = _store_tests.StoreCase
snapshot = _store_tests.snapshot

ACTOR = "agent:store-implementer"
COORDINATOR = "session-next"
STALE_FINGERPRINT = "sha256:" + "0" * 64
IDENTITY_FIELDS = {"format": 2, "namespace": "00000000-0000-4000-8000-000000000000", "seq": "SEQ-002", "task": "A2"}


class SeededCase(StoreCase):
    """SEQ-001/A1 is `accepted` with no claim and no acceptance; helpers seed what a case needs."""

    def a1(self) -> dict:
        return self.record_metadata(task="A1")

    def revision(self, task="A1") -> int:
        return self.record_metadata(task=task)["revision"]

    def fingerprint(self, task="A1") -> str:
        return records.scope_fingerprint(records.read_record(store.record_path(self.root, "SEQ-001", task)))

    def accept(self, task="A1", fingerprint=None) -> None:
        self.patch_record(
            {
                "acceptance": {
                    "actor": "user:fixture",
                    "accepted_at": "2026-09-07T10:00:00Z",
                    "authority": {"source": "user request", "revision": "2026-09-07T10:00:00Z"},
                    "fingerprint": fingerprint or self.fingerprint(task),
                    "scope": ["implement", "verify"],
                }
            },
            task=task,
        )

    def evidence_entries(self, count=2) -> list:
        return [
            {"criteria": "check %d" % number, "fingerprint": self.fingerprint(), "result": "pass"}
            for number in range(1, count + 1)
        ]

    def seed_evidence(self, count=2) -> list:
        entries = self.evidence_entries(count)
        self.patch_record({"evidence": entries}, task="A1")
        return entries

    def seed_result(self) -> dict:
        result = {"outcome": "failed", "recorded_at": "2026-09-07T12:00:00Z", "actor": ACTOR}
        self.patch_record({"result": result}, task="A1")
        return result

    def seed_corrections(self) -> list:
        corrections = [{"actor": "user:fixture", "at": "2026-09-07T12:00:00Z", "reason": "reopened"}]
        self.patch_record({"corrections": corrections}, task="A1")
        return corrections

    def seed_runtime_fields(self) -> None:
        self.accept()
        self.patch_record(
            {"scope_checks": [{"kind": "accepted", "fingerprint": self.fingerprint(), "at": "2026-09-07T10:00:00Z"}]},
            task="A1",
        )

    def assert_refused(self, command: str, document: dict, code: str, *words: str, arguments=()) -> dict:
        before = snapshot(self.root)
        completed, answer = self.run_cli(command, document, *arguments)
        self.assertEqual(1, completed.returncode, completed.stdout)
        self.assertFalse(answer["ok"], answer)
        self.assertEqual(code, answer["error"]["code"], answer["error"]["message"])
        message = answer["error"]["message"].lower()
        for word in words:
            self.assertIn(word.lower(), message, "the refusal should name %r: %s" % (word, message))
        self.assertEqual(before, snapshot(self.root), "a refused command must not write")
        return answer["error"]

    def assert_succeeds(self, command: str, document: dict, arguments=()) -> dict:
        completed, answer = self.run_cli(command, document, *arguments)
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertTrue(answer["ok"], answer)
        return answer["result"]


# --------------------------------------------------------------------------- B1


class B1RecordsTest(SeededCase):
    """`revise` judges a metadata edit against the stored metadata; `capture` drops helper-owned keys."""

    TARGET = ("--seq", "SEQ-001", "--task", "A1")

    def revise_document(self, metadata: dict, **changes) -> dict:
        document = {"expect_revision": self.revision(), "actor": COORDINATOR, "metadata": metadata}
        document.update(changes)
        return document

    def refuse_revise(self, metadata: dict, code: str, *words: str) -> dict:
        return self.assert_refused("revise", self.revise_document(metadata), code, *words, arguments=self.TARGET)

    def revise(self, metadata: dict, **changes) -> dict:
        return self.assert_succeeds("revise", self.revise_document(metadata, **changes), self.TARGET)

    # helper-owned fields

    def test_b1_a_changed_claim_is_refused_and_names_the_claim_command(self):
        self.seed_claim(task="A1")
        self.refuse_revise({"claim": {"actor": "agent:thief", "coordinator": "x", "allowed_paths": []}}, "invalid-request", "claim")

    def test_b1_a_claim_planted_on_an_unclaimed_record_is_refused(self):
        self.assertNotIn("claim", self.a1())
        self.refuse_revise({"claim": {"actor": ACTOR, "coordinator": COORDINATOR, "allowed_paths": []}}, "invalid-request", "claim")

    def test_b1_a_cleared_claim_is_refused(self):
        self.seed_claim(task="A1")
        self.refuse_revise({"claim": None}, "invalid-request", "claim")

    def test_b1_a_changed_result_is_refused_and_names_record_result(self):
        self.seed_result()
        self.refuse_revise({"result": {"outcome": "passed", "actor": ACTOR}}, "invalid-request", "record-result")

    def test_b1_a_result_planted_on_a_record_without_one_is_refused(self):
        self.refuse_revise({"result": {"outcome": "passed", "actor": ACTOR}}, "invalid-request", "record-result")

    def test_b1_changed_corrections_are_refused_and_point_at_the_correction_key(self):
        self.seed_corrections()
        self.refuse_revise({"corrections": []}, "invalid-request", "correction")

    def test_b1_the_stored_claim_result_and_corrections_sent_back_unchanged_are_accepted(self):
        claim = self.seed_claim(task="A1")
        result = self.seed_result()
        corrections = self.seed_corrections()
        self.revise({"claim": claim, "result": result, "corrections": corrections, "title": "A new title"})
        metadata = self.a1()
        self.assertEqual("A new title", metadata["title"])
        self.assertEqual(claim, metadata["claim"])
        self.assertEqual(result, metadata["result"])
        self.assertEqual(corrections, metadata["corrections"])

    def test_b1_a_payload_built_from_show_output_is_accepted(self):
        claim = self.seed_claim(task="A1")
        self.seed_evidence()
        shown = self.assert_succeeds("show", None, self.TARGET)
        metadata = dict(shown["metadata"], title="Edited from show output")
        self.revise(metadata)
        self.assertEqual("Edited from show output", self.a1()["title"])
        self.assertEqual(claim, self.a1()["claim"])

    # evidence is append-only

    def test_b1_removing_an_evidence_entry_is_refused(self):
        stored = self.seed_evidence()
        self.refuse_revise({"evidence": stored[:1]}, "invalid-request", "evidence")

    def test_b1_emptying_the_evidence_list_is_refused(self):
        self.seed_evidence()
        self.refuse_revise({"evidence": []}, "invalid-request", "evidence")

    def test_b1_sending_null_for_evidence_is_refused(self):
        self.seed_evidence()
        self.refuse_revise({"evidence": None}, "invalid-request", "evidence")

    def test_b1_editing_a_stored_evidence_entry_is_refused(self):
        stored = self.seed_evidence()
        edited = [dict(stored[0], result="fail"), stored[1]]
        self.refuse_revise({"evidence": edited}, "invalid-request", "evidence")

    def test_b1_reordering_the_stored_evidence_entries_is_refused(self):
        stored = self.seed_evidence()
        self.refuse_revise({"evidence": [stored[1], stored[0]]}, "invalid-request", "evidence")

    def test_b1_putting_a_new_entry_before_the_stored_ones_is_refused(self):
        stored = self.seed_evidence()
        fresh = {"criteria": "inserted first", "fingerprint": self.fingerprint(), "result": "pass"}
        self.refuse_revise({"evidence": [fresh] + stored}, "invalid-request", "evidence")

    def test_b1_appending_entries_after_the_stored_ones_is_accepted(self):
        stored = self.seed_evidence()
        fresh = {"criteria": "appended", "fingerprint": self.fingerprint(), "result": "pass"}
        self.revise({"evidence": stored + [fresh]})
        self.assertEqual(stored + [fresh], self.a1()["evidence"])

    def test_b1_sending_the_stored_evidence_unchanged_is_accepted(self):
        stored = self.seed_evidence()
        self.revise({"evidence": stored, "title": "Evidence untouched"})
        self.assertEqual(stored, self.a1()["evidence"])

    def test_b1_the_first_evidence_on_a_record_without_any_is_accepted(self):
        self.assertNotIn("evidence", self.a1())
        fresh = self.evidence_entries(1)
        self.revise({"evidence": fresh})
        self.assertEqual(fresh, self.a1()["evidence"])

    # identity and runtime fields

    def test_b1_a_changed_identity_field_is_refused_as_invalid_identity(self):
        for field, value in IDENTITY_FIELDS.items():
            with self.subTest(field=field):
                self.refuse_revise({field: value}, "invalid-identity", field)

    def test_b1_a_changed_identity_field_names_capture_as_the_way_to_a_new_identity(self):
        error = self.refuse_revise({"seq": "SEQ-002"}, "invalid-identity", "seq")
        self.assertIn("capture", error["message"].lower())

    def test_b1_a_changed_revision_is_refused(self):
        self.refuse_revise({"revision": self.revision() + 40}, "invalid-request", "revision")

    def test_b1_a_written_acceptance_is_refused_and_names_accept(self):
        forged = {"actor": "agent:forger", "fingerprint": self.fingerprint(), "scope": ["implement"]}
        self.refuse_revise({"acceptance": forged}, "invalid-request", "acceptance", "accept")

    def test_b1_a_changed_stored_acceptance_is_refused(self):
        self.accept()
        stored = self.a1()["acceptance"]
        self.refuse_revise({"acceptance": dict(stored, actor="agent:forger")}, "invalid-request", "acceptance", "accept")

    def test_b1_changed_scope_checks_are_refused_and_name_accept(self):
        forged = [{"kind": "accepted", "fingerprint": self.fingerprint()}]
        self.refuse_revise({"scope_checks": forged}, "invalid-request", "scope_checks", "accept")

    def test_b1_every_identity_and_runtime_field_sent_with_its_stored_value_is_accepted(self):
        self.seed_runtime_fields()
        stored = self.a1()
        sent = {key: stored[key] for key in ("format", "namespace", "seq", "task", "revision", "acceptance", "scope_checks")}
        self.assertEqual(NAMESPACE, sent["namespace"])
        self.revise(dict(sent, title="Identity echoed back"))
        after = self.a1()
        self.assertEqual("Identity echoed back", after["title"])
        for key in ("format", "namespace", "seq", "task", "acceptance", "scope_checks"):
            self.assertEqual(stored[key], after[key], key)
        self.assertEqual(stored["revision"] + 1, after["revision"])

    def test_b1_a_refusal_leaves_the_other_edits_of_the_same_request_unwritten(self):
        self.refuse_revise({"title": "Never written", "seq": "SEQ-002"}, "invalid-identity", "seq")
        self.assertNotEqual("Never written", self.a1()["title"])

    def test_b1_ordinary_metadata_edits_still_work(self):
        self.revise({"title": "Plainly retitled", "priority": "P1"})
        self.assertEqual("Plainly retitled", self.a1()["title"])
        self.assertEqual("P1", self.a1()["priority"])

    def test_b1_a_correction_still_appends_through_the_correction_key(self):
        self.seed_corrections()
        before = list(self.a1()["corrections"])
        self.revise({}, correction={"actor": "user:fixture", "at": "2026-09-08T09:00:00Z", "reason": "second"})
        after = self.a1()["corrections"]
        self.assertEqual(before, after[: len(before)])
        self.assertEqual(len(before) + 1, len(after))

    # capture

    def test_b1_capture_drops_claim_result_evidence_and_corrections(self):
        planted = {
            "title": "A captured record",
            "claim": {"actor": ACTOR, "coordinator": COORDINATOR, "allowed_paths": []},
            "result": {"outcome": "passed", "actor": ACTOR},
            "evidence": [{"criteria": "planted", "fingerprint": STALE_FINGERPRINT, "result": "pass"}],
            "corrections": [{"actor": "user:fixture", "reason": "planted"}],
        }
        self.assert_succeeds("capture", {"scope": "A scope to bind later.", "metadata": planted}, ("--namespace", NAMESPACE, "--seq", "SEQ-003"))
        metadata = self.record_metadata(seq="SEQ-003")
        self.assertEqual("A captured record", metadata["title"])
        self.assertEqual("captured", metadata["lifecycle"])
        for key in ("claim", "result", "evidence", "corrections"):
            self.assertNotIn(key, metadata)

    def test_b1_capture_of_a_task_drops_the_same_keys(self):
        planted = {"title": "A captured task", "evidence": self.evidence_entries(1), "claim": {"actor": ACTOR}}
        arguments = ("--namespace", NAMESPACE, "--seq", "SEQ-001", "--task", "A9")
        self.assert_succeeds("capture", {"scope": "A task scope.", "metadata": planted}, arguments)
        metadata = self.record_metadata(task="A9")
        for key in ("claim", "result", "evidence", "corrections"):
            self.assertNotIn(key, metadata)


# --------------------------------------------------------------------------- B2


class B2StoreTest(SeededCase):
    """`transition` judges changes to existing records like `revise`; `claim` and `not_closed` follow acceptance."""

    def change(self, metadata: dict, task="A1", **changes) -> dict:
        change = {"seq": "SEQ-001", "task": task, "expect_revision": self.revision(task), "metadata": metadata}
        change.update(changes)
        return change

    def transition_document(self, metadata: dict, **changes) -> dict:
        return {"coordinator": COORDINATOR, "actor": COORDINATOR, "changes": [self.change(metadata, **changes)]}

    def refuse_transition(self, metadata: dict, code: str, *words: str) -> dict:
        return self.assert_refused("transition", self.transition_document(metadata), code, *words)

    def transition(self, metadata: dict) -> dict:
        return self.assert_succeeds("transition", self.transition_document(metadata))

    # existing records: helper-owned fields

    def test_b2_a_transition_that_changes_the_claim_is_refused_and_names_claim(self):
        self.seed_claim(task="A1")
        self.refuse_transition({"claim": {"actor": "agent:thief", "coordinator": "x", "allowed_paths": []}}, "invalid-request", "claim")

    def test_b2_a_transition_that_plants_a_claim_is_refused(self):
        self.refuse_transition({"claim": {"actor": ACTOR, "coordinator": COORDINATOR, "allowed_paths": []}}, "invalid-request", "claim")

    def test_b2_a_transition_that_changes_the_result_is_refused_and_names_record_result(self):
        self.seed_result()
        self.refuse_transition({"result": {"outcome": "passed", "actor": ACTOR}}, "invalid-request", "record-result")

    def test_b2_a_transition_that_changes_corrections_is_refused(self):
        self.seed_corrections()
        self.refuse_transition({"corrections": []}, "invalid-request", "correction")

    def test_b2_the_stored_claim_result_and_corrections_sent_back_unchanged_are_accepted(self):
        claim = self.seed_claim(task="A1")
        result = self.seed_result()
        corrections = self.seed_corrections()
        self.transition({"claim": claim, "result": result, "corrections": corrections, "title": "Retitled by transition"})
        metadata = self.a1()
        self.assertEqual("Retitled by transition", metadata["title"])
        self.assertEqual(claim, metadata["claim"])
        self.assertEqual(result, metadata["result"])

    # existing records: evidence is append-only

    def test_b2_a_transition_cannot_remove_edit_reorder_or_null_the_stored_evidence(self):
        stored = self.seed_evidence()
        attempts = {
            "remove": stored[:1],
            "empty": [],
            "null": None,
            "edit": [dict(stored[0], result="fail"), stored[1]],
            "reorder": [stored[1], stored[0]],
        }
        for name, sent in attempts.items():
            with self.subTest(attempt=name):
                self.refuse_transition({"evidence": sent}, "invalid-request", "evidence")

    def test_b2_a_transition_can_append_evidence_after_the_stored_entries(self):
        stored = self.seed_evidence()
        fresh = {"criteria": "appended", "fingerprint": self.fingerprint(), "result": "pass"}
        self.transition({"evidence": stored + [fresh]})
        self.assertEqual(stored + [fresh], self.a1()["evidence"])

    # existing records: identity, acceptance and runtime fields

    def test_b2_a_transition_that_writes_acceptance_is_refused_and_names_accept(self):
        forged = {"actor": "agent:forger", "fingerprint": self.fingerprint(), "scope": ["implement"]}
        self.refuse_transition({"acceptance": forged}, "invalid-request", "acceptance", "accept")
        self.assertNotIn("acceptance", self.a1())

    def test_b2_a_transition_that_changes_scope_checks_or_revision_is_refused(self):
        self.refuse_transition({"scope_checks": [{"kind": "accepted"}]}, "invalid-request", "scope_checks")
        self.refuse_transition({"revision": self.revision() + 40}, "invalid-request", "revision")

    def test_b2_a_transition_that_changes_an_identity_field_is_refused_as_invalid_identity(self):
        for field, value in IDENTITY_FIELDS.items():
            with self.subTest(field=field):
                self.refuse_transition({field: value}, "invalid-identity", field)

    def test_b2_every_identity_and_runtime_field_sent_with_its_stored_value_is_accepted(self):
        self.seed_runtime_fields()
        stored = self.a1()
        sent = {key: stored[key] for key in ("format", "namespace", "seq", "task", "revision", "acceptance", "scope_checks")}
        self.transition(dict(sent, title="Identity echoed back"))
        after = self.a1()
        self.assertEqual("Identity echoed back", after["title"])
        for key in ("acceptance", "scope_checks", "seq", "task", "namespace"):
            self.assertEqual(stored[key], after[key], key)

    def test_b2_a_refused_change_leaves_every_record_of_the_operation_unwritten(self):
        second = {"seq": "SEQ-001", "expect_revision": 1, "metadata": {"title": "Never written"}}
        document = self.transition_document({"seq": "SEQ-002"})
        document["changes"].append(second)
        self.assert_refused("transition", document, "invalid-identity", "seq")
        self.assertNotEqual("Never written", self.record_metadata()["title"])

    def test_b2_an_ordinary_lifecycle_change_by_the_claim_holder_still_works(self):
        self.seed_claim(task="A1")
        self.transition({"lifecycle": "active"})
        self.assertEqual("active", self.a1()["lifecycle"])

    # new records

    def test_b2_a_new_record_drops_claim_result_evidence_and_corrections(self):
        document = {
            "operation": "op-b2-new-0001",
            "coordinator": "session-add-task",
            "actor": "session-add-task",
            "provenance": {"actor": "user", "source": "session-gatekeeper", "captured_at": "2026-09-07T10:05:00Z"},
            "changes": [
                {
                    "new": True,
                    "metadata": {
                        "title": "A planted new record",
                        "lifecycle": "captured",
                        "claim": {"actor": ACTOR, "coordinator": COORDINATOR, "allowed_paths": []},
                        "result": {"outcome": "passed", "actor": ACTOR},
                        "evidence": [{"criteria": "planted", "fingerprint": STALE_FINGERPRINT, "result": "pass"}],
                        "corrections": [{"actor": "user:fixture", "reason": "planted"}],
                    },
                    "scope": "A scope that acceptance will bind to later.",
                    "body": "",
                }
            ],
        }
        self.assert_succeeds("transition", document)
        metadata = self.record_metadata(seq="SEQ-003")
        self.assertEqual("A planted new record", metadata["title"])
        for key in ("claim", "result", "evidence", "corrections"):
            self.assertNotIn(key, metadata)

    # claim needs applicable acceptance

    def claim_document(self, task="A1", **changes) -> dict:
        document = {
            "coordinator": "session-delegation",
            "actor": ACTOR,
            "seq": "SEQ-001",
            "task": task,
            "expect_revision": self.revision(task),
            "allowed_paths": ["scripts/session_flow/store.py"],
        }
        document.update(changes)
        return document

    def test_b2_claim_on_a_captured_record_is_refused_and_leaves_it_unchanged(self):
        self.patch_record({"lifecycle": "captured"}, task="A1")
        error = self.assert_refused("claim", self.claim_document(), "missing-authority", "accept")
        self.assertIn("accept", error["message"].lower())
        self.assertEqual("captured", self.a1()["lifecycle"])
        self.assertNotIn("claim", self.a1())

    def test_b2_claim_on_a_captured_record_with_a_stale_acceptance_is_refused(self):
        self.patch_record({"lifecycle": "captured"}, task="A1")
        self.accept(fingerprint=STALE_FINGERPRINT)
        self.assert_refused("claim", self.claim_document(), "missing-authority")
        self.assertNotIn("claim", self.a1())

    def test_b2_claim_on_an_accepted_record_whose_scope_changed_after_acceptance_is_refused(self):
        self.accept(fingerprint=STALE_FINGERPRINT)
        self.assertEqual("accepted", self.a1()["lifecycle"])
        self.assert_refused("claim", self.claim_document(), "missing-authority", "accept")
        metadata = self.a1()
        self.assertEqual("accepted", metadata["lifecycle"])
        self.assertNotIn("claim", metadata)

    def test_b2_claim_on_a_record_that_was_never_accepted_is_refused(self):
        self.assertNotIn("acceptance", self.a1())
        self.assert_refused("claim", self.claim_document(), "missing-authority", "accept")

    def test_b2_claim_on_an_accepted_record_with_applicable_acceptance_moves_it_to_active(self):
        self.accept()
        self.assert_succeeds("claim", self.claim_document())
        metadata = self.a1()
        self.assertEqual("active", metadata["lifecycle"])
        self.assertEqual(ACTOR, metadata["claim"]["actor"])

    def test_b2_the_accept_command_makes_a_captured_record_claimable(self):
        self.patch_record({"lifecycle": "captured"}, task="A1")
        accept = {
            "expect_revision": self.revision(),
            "actor": "user:fixture",
            "authority": {"source": "user request", "revision": "2026-09-07T10:00:00Z"},
            "scope": ["implement", "verify"],
            "lifecycle": "accepted",
        }
        self.assert_succeeds("accept", accept, ("--seq", "SEQ-001", "--task", "A1"))
        self.assertTrue(records.acceptance_status(records.read_record(store.record_path(self.root, "SEQ-001", "A1")))["applies"])
        self.assert_succeeds("claim", self.claim_document())
        self.assertEqual("active", self.a1()["lifecycle"])

    # not_closed names only the remedy that applies

    def passed_result(self, task="A1") -> dict:
        return {
            "coordinator": "session-delegation",
            "actor": ACTOR,
            "seq": "SEQ-001",
            "task": task,
            "expect_revision": self.revision(task),
            "result": {"outcome": "passed", "summary": "Checked by hand.", "checks": [{"command": "true", "observed": "ok"}]},
        }

    def not_closed_for(self, lifecycle: str, accepted=True) -> str:
        """Record a passing result as the claim holder on a task seeded in `lifecycle`; return `not_closed`."""
        if accepted:
            self.accept()
        self.seed_claim(actor=ACTOR, task="A1")
        self.patch_record({"lifecycle": lifecycle}, task="A1")
        result = self.assert_succeeds("record-result", self.passed_result())
        self.assertEqual(lifecycle, self.a1()["lifecycle"], "a result on a non-active task moves nothing")
        self.assertIsInstance(result.get("not_closed"), str, result)
        return result["not_closed"]

    def test_b2_an_accepted_task_is_told_to_claim_then_record_again(self):
        text = self.not_closed_for("accepted")
        self.assertRegex(text, r"(?i)\bclaim")
        self.assertNotRegex(text, r"(?i)blocked")

    def test_b2_a_blocked_task_is_told_to_transition_to_active_as_the_claim_holder(self):
        text = self.not_closed_for("blocked")
        self.assertRegex(text, r"(?i)transition")
        self.assertRegex(text, r"(?i)active")
        self.assertRegex(text, r"(?i)claim holder|holder")
        self.assertNotRegex(text, r"(?i)claim an accepted|accepted task")

    def test_b2_a_done_task_is_told_it_is_already_closed_with_nothing_to_do(self):
        text = self.not_closed_for("done")
        self.assertRegex(text, r"(?i)already (closed|done|complete)|nothing")
        self.assertNotRegex(text, r"(?i)\bclaim|transition|move it to")

    def test_b2_a_captured_task_is_told_to_get_acceptance_or_a_correction(self):
        text = self.not_closed_for("captured", accepted=False)
        self.assertRegex(text, r"(?i)accept|correction")
        self.assertNotRegex(text, r"(?i)blocked|claim an accepted")

    def test_b2_a_deferred_task_is_told_to_get_acceptance_or_a_correction(self):
        text = self.not_closed_for("deferred", accepted=False)
        self.assertRegex(text, r"(?i)accept|correction")
        self.assertNotRegex(text, r"(?i)blocked|claim an accepted")

    def test_b2_a_cancelled_task_is_told_to_get_acceptance_or_a_correction(self):
        text = self.not_closed_for("cancelled", accepted=False)
        self.assertRegex(text, r"(?i)accept|correction")
        self.assertNotRegex(text, r"(?i)blocked|claim an accepted")


# --------------------------------------------------------------------------- B3


class B3CliTest(SeededCase):
    """Argument errors answer in JSON with exit 2; `schema` required lists match what the runtime refuses."""

    COMMANDS = ("capture", "accept", "revise", "transition", "claim", "record-result")

    def cli(self, *arguments: str) -> subprocess.CompletedProcess:
        call = [sys.executable, "-B", str(ENTRYPOINT), *arguments]
        return subprocess.run(call, capture_output=True, text=True, check=False)

    def assert_json_argument_error(self, *arguments: str) -> dict:
        completed = self.cli(*arguments)
        self.assertEqual(2, completed.returncode, completed.stdout + completed.stderr)
        self.assertTrue(completed.stdout.strip(), "stdout must carry the JSON error; stderr was: " + completed.stderr)
        answer = json.loads(completed.stdout)
        self.assertIsInstance(answer, dict)
        self.assertIs(False, answer["ok"], answer)
        self.assertEqual("invalid-request", answer["error"]["code"], answer)
        self.assertTrue(answer["error"]["message"].strip())
        return answer

    def test_b3_a_stray_positional_word_answers_in_json_with_exit_2(self):
        self.assert_json_argument_error("show", "foo", "--project-root", str(self.project), "--seq", "SEQ-001")

    def test_b3_an_unknown_option_answers_in_json_with_exit_2(self):
        self.assert_json_argument_error("show", "--bogus", "--project-root", str(self.project), "--seq", "SEQ-001")

    def test_b3_an_unknown_command_answers_in_json_with_exit_2(self):
        self.assert_json_argument_error("frobnicate", "--project-root", str(self.project))

    def test_b3_a_missing_command_answers_in_json_with_exit_2(self):
        self.assert_json_argument_error("--project-root", str(self.project))

    def test_b3_an_option_without_its_value_answers_in_json_with_exit_2(self):
        self.assert_json_argument_error("show", "--project-root", str(self.project), "--seq")

    def test_b3_the_error_envelope_names_the_protocol_and_command_like_any_answer(self):
        answer = self.assert_json_argument_error("show", "foo", "--project-root", str(self.project))
        self.assertEqual(1, answer["protocol"])

    def test_b3_valid_invocations_still_exit_0_with_one_json_object(self):
        completed = self.cli("show", "--project-root", str(self.project), "--seq", "SEQ-001")
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["ok"])

    # schema

    def schema(self, command: str) -> dict:
        completed = self.cli("schema", command, "--project-root", str(self.project))
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        return json.loads(completed.stdout)["result"]

    def test_b3_schema_transition_lists_actor_as_optional_not_required(self):
        description = self.schema("transition")
        self.assertNotIn("actor", description["required"])
        self.assertIn("actor", description["optional"])
        self.assertIn("changes", description["required"])

    def test_b3_a_transition_without_actor_is_accepted_by_the_runtime(self):
        self.seed_claim(task="A1")
        document = {
            "coordinator": COORDINATOR,
            "changes": [{"seq": "SEQ-001", "task": "A1", "expect_revision": 1, "metadata": {"title": "No actor named"}}],
        }
        self.assert_succeeds("transition", document)
        self.assertEqual("No actor named", self.a1()["title"])

    def test_b3_claim_and_record_result_keep_seq_and_expect_revision_required(self):
        for command in ("claim", "record-result"):
            with self.subTest(command=command):
                required = self.schema(command)["required"]
                self.assertIn("seq", required)
                self.assertIn("expect_revision", required)
        self.assertIn("result", self.schema("record-result")["required"])

    def example_run(self, command: str, example: dict, drop=None):
        """Send the schema's own example to a fresh fixture in a state where the whole example is valid."""
        self.setUp()
        document = {key: value for key, value in json.loads(json.dumps(example)).items() if key != drop}
        arguments = ()
        if command == "capture":
            arguments = ("--namespace", NAMESPACE, "--seq", "SEQ-003")
        elif command in ("accept", "revise"):
            arguments = ("--seq", "SEQ-001", "--task", "A1")
        elif command == "transition":
            self.seed_claim(task="A1")
        elif command == "record-result":
            self.accept()
            self.seed_claim(actor=document.get("actor", example["actor"]), task="A1")
            self.patch_record({"lifecycle": "active"}, task="A1")
            self.patch_record({"revision": 2}, task="A1")
        else:
            self.accept()
        completed, answer = self.run_cli(command, document, *arguments)
        return completed, answer

    def test_b3_each_schema_example_is_accepted_by_the_runtime_when_complete(self):
        for command in self.COMMANDS:
            with self.subTest(command=command):
                example = self.schema(command)["example"]
                completed, answer = self.example_run(command, example)
                self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
                self.assertTrue(answer["ok"], answer)

    def test_b3_dropping_any_required_field_from_the_example_is_refused(self):
        for command in self.COMMANDS:
            description = self.schema(command)
            for field in description["required"]:
                with self.subTest(command=command, dropped=field):
                    completed, answer = self.example_run(command, description["example"], drop=field)
                    self.assertNotEqual(0, completed.returncode, "%s without %s was accepted: %s" % (command, field, answer))
                    self.assertFalse(answer["ok"], answer)
                    self.assertIn(answer["error"]["code"], ("invalid-request", "invalid-identity", "missing-authority"))


if __name__ == "__main__":
    unittest.main()
