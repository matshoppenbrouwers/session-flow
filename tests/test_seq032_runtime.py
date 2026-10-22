"""SEQ-032 acceptance tests: a self-describing runtime and a two-call close-out (tasks A1 to A4).

A1  `schema <command>` prints required fields, optional fields and one valid example per command
A2  `show` returns the record body, the scope fingerprint, and acceptance and evidence status
A3  a payload without `operation` gets a generated id; `claim` moves an accepted record to active
A4  `record-result` closes a task on `passed`, blocks it on `blocked`, and never closes an item

The cases reuse the temp-root helpers of `test_store` and only ever write inside a temporary
directory. They exercise the repository's own scripts, never an installed plugin. `session_flow.schema`
is imported inside the A1 cases, so the other classes still collect while that module is missing.
"""

import importlib
import json
import re
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

import test_store as _store_tests  # noqa: E402

from session_flow import SessionFlowError, records, store  # noqa: E402

payload = _store_tests.payload
snapshot = _store_tests.snapshot
ENTRYPOINT = _store_tests.ENTRYPOINT
StoreCase = _store_tests.StoreCase

ACTOR = "agent:store-implementer"
OPERATION_ID = re.compile(r"^op-[0-9a-f-]{36}$")
COMMANDS = ("capture", "accept", "revise", "transition", "claim", "record-result")
VALID_KEYS = {
    "capture": records.CAPTURE_KEYS,
    "accept": records.ACCEPT_KEYS,
    "revise": records.REVISE_KEYS,
    "transition": store.TRANSITION_KEYS,
    "claim": store.CLAIM_KEYS,
    "record-result": store.RESULT_KEYS,
}


def load_schema():
    return importlib.import_module("session_flow.schema")


# --------------------------------------------------------------------------- A1


class A1SchemaTest(StoreCase):
    """The runtime describes each mutating command's payload from one table the validators share."""

    def schema_cli(self, *names: str):
        call = [sys.executable, "-B", str(ENTRYPOINT), "schema", *names, "--project-root", str(self.project)]
        return subprocess.run(call, capture_output=True, text=True, check=False)

    def test_a1_schema_has_an_example_for_every_mutating_command(self):
        schema = load_schema()
        self.assertEqual(set(COMMANDS), set(schema.EXAMPLES))
        self.assertEqual(set(COMMANDS), set(schema.REQUIRED))

    def test_a1_describe_returns_required_optional_and_example_for_each_command(self):
        schema = load_schema()
        for command in COMMANDS:
            with self.subTest(command=command):
                description = schema.describe(command)
                for key in ("required", "optional", "example"):
                    self.assertIn(key, description)
                self.assertIsInstance(description["required"], list)
                self.assertIsInstance(description["optional"], list)
                self.assertIsInstance(description["example"], dict)
                self.assertTrue(description["required"], "%s has no required field" % command)

    def test_a1_required_and_optional_are_disjoint_and_together_the_valid_key_set(self):
        schema = load_schema()
        for command in COMMANDS:
            with self.subTest(command=command):
                description = schema.describe(command)
                required, optional = set(description["required"]), set(description["optional"])
                self.assertEqual(set(), required & optional)
                self.assertEqual(len(description["required"]), len(required), "a required field is repeated")
                self.assertEqual(len(description["optional"]), len(optional), "an optional field is repeated")
                self.assertEqual(set(VALID_KEYS[command]), required | optional)

    def test_a1_operation_is_never_required_and_optional_where_accepted(self):
        schema = load_schema()
        accepting = ("transition", "claim", "record-result")
        for command in COMMANDS:
            with self.subTest(command=command):
                description = schema.describe(command)
                self.assertNotIn("operation", description["required"])
                if command in accepting:
                    self.assertIn("operation", description["optional"])
                else:
                    self.assertNotIn("operation", description["optional"])

    def test_a1_each_example_passes_key_validation_and_holds_every_required_field(self):
        schema = load_schema()
        for command in COMMANDS:
            with self.subTest(command=command):
                example = schema.describe(command)["example"]
                records.check_payload_keys(example, command, VALID_KEYS[command])
                self.assertLessEqual(set(schema.describe(command)["required"]), set(example))
                self.assertNotIn("operation", example)

    def test_a1_the_example_table_and_describe_agree(self):
        schema = load_schema()
        for command in COMMANDS:
            with self.subTest(command=command):
                self.assertEqual(schema.EXAMPLES[command], schema.describe(command)["example"])

    def test_a1_the_schema_command_prints_the_description_for_each_command(self):
        schema = load_schema()
        for command in COMMANDS:
            with self.subTest(command=command):
                completed = self.schema_cli(command)
                self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
                answer = json.loads(completed.stdout)
                self.assertTrue(answer["ok"], answer)
                expected = schema.describe(command)
                for key in ("required", "optional", "example"):
                    self.assertEqual(expected[key], answer["result"][key])

    def test_a1_the_schema_command_needs_no_work_root_or_input(self):
        completed = subprocess.run(
            [sys.executable, "-B", str(ENTRYPOINT), "schema", "claim", "--project-root", str(self.project / "absent")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["ok"])

    def test_a1_schema_without_a_command_name_fails_and_lists_the_valid_names(self):
        completed = self.schema_cli()
        self.assertNotEqual(0, completed.returncode)
        output = completed.stdout + completed.stderr
        for command in COMMANDS:
            self.assertIn(command, output)

    def test_a1_schema_with_an_unknown_name_fails_and_lists_the_valid_names(self):
        completed = self.schema_cli("frobnicate")
        self.assertNotEqual(0, completed.returncode)
        output = completed.stdout + completed.stderr
        for command in COMMANDS:
            self.assertIn(command, output)

    def test_a1_doctor_lists_schema_as_a_builtin_command(self):
        completed, answer = self.run_cli("doctor")
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        listed = answer["result"]["commands"]
        self.assertIn("schema", listed)
        self.assertEqual("builtin", listed["schema"]["handler"])
        self.assertTrue(listed["schema"]["available"])


# --------------------------------------------------------------------------- A2


class A2ShowTest(StoreCase):
    """`show` adds body, fingerprint, acceptance status and evidence status to what it already returned."""

    def stored(self, task=None) -> dict:
        return records.read_record(store.record_path(self.root, "SEQ-001", task))

    def shown(self, task=None) -> dict:
        return records.show(self.request("show", seq="SEQ-001", task=task))

    def accept(self, task=None, fingerprint=None) -> None:
        fingerprint = fingerprint or records.scope_fingerprint(self.stored(task))
        self.patch_record(
            {
                "acceptance": {
                    "actor": "user:fixture",
                    "accepted_at": "2026-09-07T10:00:00Z",
                    "authority": {"source": "user request", "revision": "2026-09-07T10:00:00Z"},
                    "fingerprint": fingerprint,
                    "scope": ["implement", "verify"],
                }
            },
            task=task,
        )

    def test_a2_the_existing_keys_are_unchanged(self):
        for task in (None, "A1"):
            with self.subTest(task=task):
                record, shown = self.stored(task), self.shown(task)
                self.assertEqual(
                    str(store.record_path(self.root, "SEQ-001", task).resolve()), str(Path(shown["path"]).resolve())
                )
                self.assertEqual(record["identity"], shown["identity"])
                self.assertEqual(record["metadata"], shown["metadata"])
                self.assertEqual(record["scope"], shown["scope"])

    def test_a2_show_returns_the_record_body(self):
        for task in (None, "A1"):
            with self.subTest(task=task):
                self.assertEqual(self.stored(task)["body"], self.shown(task)["body"])
        self.assertIn("## Approach", self.shown()["body"])

    def test_a2_show_returns_the_scope_fingerprint(self):
        for task in (None, "A1"):
            with self.subTest(task=task):
                shown = self.shown(task)
                self.assertEqual(records.scope_fingerprint(self.stored(task)), shown["fingerprint"])
                self.assertTrue(shown["fingerprint"].startswith("sha256:"))

    def test_a2_an_unaccepted_record_reports_acceptance_that_does_not_apply(self):
        shown = self.shown("A1")
        self.assertEqual(records.acceptance_status(self.stored("A1")), shown["acceptance"])
        self.assertIs(False, shown["acceptance"]["accepted"])
        self.assertIs(False, shown["acceptance"]["applies"])

    def test_a2_an_accepted_record_reports_acceptance_that_applies(self):
        self.accept("A1")
        shown = self.shown("A1")
        self.assertEqual(records.acceptance_status(self.stored("A1")), shown["acceptance"])
        self.assertIs(True, shown["acceptance"]["applies"])

    def test_a2_acceptance_of_another_scope_reports_that_it_does_not_apply(self):
        self.accept("A1", fingerprint="sha256:" + "0" * 64)
        shown = self.shown("A1")
        self.assertEqual(records.acceptance_status(self.stored("A1")), shown["acceptance"])
        self.assertIs(True, shown["acceptance"]["accepted"])
        self.assertIs(False, shown["acceptance"]["applies"])

    def test_a2_a_record_without_evidence_reports_an_empty_list(self):
        self.assertEqual([], self.shown("A1")["evidence"])

    def test_a2_each_evidence_entry_reports_whether_it_applies(self):
        current = records.scope_fingerprint(self.stored("A1"))
        self.patch_record(
            {
                "evidence": [
                    {"criteria": "old check", "fingerprint": "sha256:" + "1" * 64, "result": "pass"},
                    {"criteria": "new check", "fingerprint": current, "result": "pass"},
                ]
            },
            task="A1",
        )
        shown = self.shown("A1")
        self.assertEqual(records.evidence_status(self.stored("A1")), shown["evidence"])
        self.assertEqual([False, True], [entry["applies"] for entry in shown["evidence"]])
        self.assertEqual(["old check", "new check"], [entry["criteria"] for entry in shown["evidence"]])

    def test_a2_the_command_line_envelope_carries_the_new_fields(self):
        self.accept("A1")
        completed, answer = self.run_cli("show", None, "--seq", "SEQ-001", "--task", "A1")
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        result = answer["result"]
        record = self.stored("A1")
        self.assertEqual(record["body"], result["body"])
        self.assertEqual(records.scope_fingerprint(record), result["fingerprint"])
        self.assertEqual(records.acceptance_status(record), result["acceptance"])
        self.assertEqual(records.evidence_status(record), result["evidence"])
        for key in ("path", "identity", "metadata", "scope"):
            self.assertIn(key, result)


# ------------------------------------------------------------- shared close-out case


class OperationCase(StoreCase):
    """A task record SEQ-001/A1 that is accepted, plus helpers that send payloads without `operation`."""

    EVIDENCE = {
        "criteria": "one effective writer",
        "revision": "5a1c3e9",
        "environment": "WSL Ubuntu, ext4 fixture root",
        "limitations": ["no multi-host run was attempted"],
    }

    def setUp(self):
        super().setUp()
        self.accept()

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

    def claim_document(self, task="A1", **changes) -> dict:
        document = {
            "coordinator": "session-delegation",
            "actor": ACTOR,
            "seq": "SEQ-001",
            "expect_revision": self.revision(task),
            "allowed_paths": ["scripts/session_flow/store.py", "tests/test_store.py"],
        }
        if task:
            document["task"] = task
        document.update(changes)
        return document

    def result_document(self, outcome="passed", evidence="default", task="A1", actor=ACTOR, **changes) -> dict:
        body = {"outcome": outcome, "checks": [{"command": "python3 -B -m unittest", "observed": "ok"}]}
        if evidence == "default":
            evidence = self.EVIDENCE
        if evidence is not None:
            body["evidence"] = json.loads(json.dumps(evidence))
        document = {
            "coordinator": "session-delegation",
            "actor": actor,
            "seq": "SEQ-001",
            "expect_revision": self.revision(task),
            "result": body,
        }
        if task:
            document["task"] = task
        document.update(changes)
        return document

    def ok(self, command: str, document: dict) -> dict:
        completed, answer = self.run_cli(command, document)
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertTrue(answer["ok"], answer)
        return answer["result"]

    def claim_the_task(self, task="A1") -> dict:
        return self.ok("claim", self.claim_document(task))

    def add_dependent_task(self, depends_on="SEQ-001/A1") -> None:
        source = records.read_record(store.record_path(self.root, "SEQ-001", "A1"))
        metadata = dict(source["metadata"], task="A2", title="A task that waits on the first", revision=1)
        for key in (store.CLAIM_FIELD, store.RESULT_FIELD, "evidence", "acceptance"):
            metadata.pop(key, None)
        metadata["lifecycle"] = "accepted"
        metadata[store.DEPENDS_FIELD] = [depends_on]
        target = store.record_path(self.root, "SEQ-001", "A2")
        records.write_record_file(target, records.render_record(metadata, source["scope"], source["body"]))


# --------------------------------------------------------------------------- A3


class A3OperationIdAndClaimTest(OperationCase):
    """The runtime generates the operation id when none is sent, and a claim starts the work."""

    def without_operation(self, document: dict) -> dict:
        document = dict(document)
        document.pop("operation", None)
        return document

    def transition_document(self) -> dict:
        return self.without_operation(payload("lifecycle-change.json"))

    def document_for(self, command: str) -> dict:
        if command == "transition":
            return self.transition_document()
        if command == "claim":
            return self.claim_document()
        self.claim_the_task()
        return self.result_document(outcome="failed", evidence=None)

    # generated ids

    def test_a3_each_operation_command_returns_a_generated_id_when_none_is_sent(self):
        for command in ("transition", "claim", "record-result"):
            with self.subTest(command=command):
                self.setUp()
                result = self.ok(command, self.document_for(command))
                self.assertRegex(result["operation"], OPERATION_ID)
                self.assertEqual(4, uuid.UUID(result["operation"][3:]).version)
                self.assertFalse(result.get("replayed"))

    def test_a3_two_operations_without_an_id_get_different_ids(self):
        self.claim_the_task()
        first = self.ok("record-result", self.result_document(outcome="failed", evidence=None))
        second = self.ok("record-result", self.result_document(outcome="unknown", evidence=None))
        self.assertRegex(first["operation"], OPERATION_ID)
        self.assertRegex(second["operation"], OPERATION_ID)
        self.assertNotEqual(first["operation"], second["operation"])
        self.assertFalse(first.get("replayed"))
        self.assertFalse(second.get("replayed"))

    def test_a3_a_supplied_operation_id_is_kept_and_returned(self):
        result = self.ok("claim", payload("claim.json"))
        self.assertEqual("op-claim-0001", result["operation"])

    def test_a3_the_same_payload_with_the_returned_id_replays_the_earlier_result(self):
        for command in ("transition", "claim", "record-result"):
            with self.subTest(command=command):
                self.setUp()
                document = self.document_for(command)
                first = self.ok(command, document)
                before = snapshot(self.root)
                replay = self.ok(command, dict(document, operation=first["operation"]))
                self.assertTrue(replay["replayed"])
                self.assertEqual(first["operation"], replay["operation"])
                self.assertEqual(first["records"], replay["records"])
                self.assertEqual(before["seq-001/intent.md"], snapshot(self.root)["seq-001/intent.md"])
                self.assertEqual(before["seq-001/tasks/A1.md"], snapshot(self.root)["seq-001/tasks/A1.md"])

    def test_a3_the_same_payload_without_an_id_is_a_new_operation_not_a_replay(self):
        document = self.claim_document()
        first = self.ok("claim", document)
        before = snapshot(self.root)
        completed, answer = self.run_cli("claim", document)
        self.assertEqual(1, completed.returncode, completed.stdout)
        self.assertFalse(answer["ok"])
        self.assertEqual("stale-revision", answer["error"]["code"], answer["error"]["message"])
        self.assertEqual(before, snapshot(self.root))
        self.assertRegex(first["operation"], OPERATION_ID)

    def test_a3_in_process_callers_get_the_same_generated_id(self):
        result = store.transition(self.request("transition", self.transition_document()))
        self.assertRegex(result["operation"], OPERATION_ID)
        self.assertEqual("active", self.record_metadata()["lifecycle"])

    def test_a3_import_still_refuses_a_payload_without_operation(self):
        before = snapshot(self.root)
        with self.assertRaises(SessionFlowError) as raised:
            store.apply_import(self.request("import", {"apply": True}), {"coordinator": "session-next"}, {})
        self.assertIn("operation", str(raised.exception))
        self.assertEqual(before, snapshot(self.root))

    # claim starts the work

    def test_a3_claiming_an_accepted_task_leaves_it_active_with_the_claim_recorded(self):
        self.assertEqual("accepted", self.record_metadata(task="A1")["lifecycle"])
        result = self.claim_the_task()
        metadata = self.record_metadata(task="A1")
        self.assertEqual("active", metadata["lifecycle"])
        self.assertEqual(ACTOR, metadata["claim"]["actor"])
        self.assertEqual("session-delegation", metadata["claim"]["coordinator"])
        self.assertEqual(["scripts/session_flow/store.py", "tests/test_store.py"], metadata["claim"]["allowed_paths"])
        self.assertEqual(2, metadata["revision"], "the claim and the move to active are one operation")
        self.assertEqual(2, result["records"][0]["revision"])

    def test_a3_claiming_an_accepted_item_leaves_it_active_with_the_claim_recorded(self):
        self.drop_claim()
        self.accept(task=None)
        self.assertEqual("accepted", self.record_metadata()["lifecycle"])
        self.ok("claim", self.claim_document(task=None, allowed_paths=[]))
        metadata = self.record_metadata()
        self.assertEqual("active", metadata["lifecycle"])
        self.assertEqual(ACTOR, metadata["claim"]["actor"])

    def test_a3_a_claim_on_an_active_record_leaves_its_lifecycle_active(self):
        self.patch_record({"lifecycle": "active"}, task="A1")
        self.claim_the_task()
        metadata = self.record_metadata(task="A1")
        self.assertEqual("active", metadata["lifecycle"])
        self.assertEqual(ACTOR, metadata["claim"]["actor"])

    def test_a3_a_claim_held_by_another_actor_is_refused_and_leaves_the_record_unchanged(self):
        self.patch_record(
            {store.CLAIM_FIELD: {"actor": "agent:other", "coordinator": "agent:other", "host": "fixture",
                                 "claimed_at": "2026-09-07T11:00:00Z", "allowed_paths": []}},
            task="A1",
        )
        self.assert_fails_without_writing("claim", self.claim_document(), "missing-authority")
        metadata = self.record_metadata(task="A1")
        self.assertEqual("accepted", metadata["lifecycle"])
        self.assertEqual("agent:other", metadata["claim"]["actor"])

    def test_a3_a_claim_with_an_unmet_prerequisite_is_refused_and_leaves_the_record_unchanged(self):
        self.patch_record({store.DEPENDS_FIELD: ["SEQ-001"]}, task="A1")
        self.assert_fails_without_writing("claim", self.claim_document(), "invalid-request")
        metadata = self.record_metadata(task="A1")
        self.assertEqual("accepted", metadata["lifecycle"])
        self.assertNotIn("claim", metadata)

    def test_a3_a_claim_over_a_held_write_scope_is_refused_and_leaves_the_record_unchanged(self):
        self.patch_record(
            {store.CLAIM_FIELD: {"actor": "agent:other", "coordinator": "agent:other", "host": "fixture",
                                 "claimed_at": "2026-09-07T11:00:00Z", "allowed_paths": ["scripts/session_flow"]}}
        )
        self.assert_fails_without_writing("claim", self.claim_document(), "invalid-request")
        metadata = self.record_metadata(task="A1")
        self.assertEqual("accepted", metadata["lifecycle"])
        self.assertNotIn("claim", metadata)


# --------------------------------------------------------------------------- A4


class A4ResultCloseOutTest(OperationCase):
    """`record-result` closes a task on `passed`, blocks it on `blocked`, and never closes an item."""

    def evidence_entries(self, task="A1") -> list:
        return self.record_metadata(task=task).get("evidence") or []

    def claimed_and_accepted(self) -> None:
        """Start the task by seeding the claim, so these cases do not depend on how `claim` is implemented."""
        self.accept()
        self.patch_record({"lifecycle": "active"}, task="A1")
        self.seed_claim(actor=ACTOR, task="A1")

    def result_document(self, *arguments, **changes) -> dict:
        """Every result carries an explicit operation id, so these cases do not depend on generated ids."""
        self.sent = getattr(self, "sent", 0) + 1
        return super().result_document(*arguments, operation="op-a4-result-%d" % self.sent, **changes)

    def test_a4_a_passed_result_with_evidence_closes_the_task_in_one_operation(self):
        self.claimed_and_accepted()
        before = self.revision()
        result = self.ok("record-result", self.result_document())
        metadata = self.record_metadata(task="A1")
        self.assertEqual("done", metadata["lifecycle"])
        self.assertEqual("passed", metadata["result"]["outcome"])
        self.assertEqual(before + 1, metadata["revision"], "result, evidence and closure are one operation")
        self.assertEqual(before + 1, result["records"][0]["revision"])
        self.assertFalse(result.get("not_closed"))
        self.assertEqual(1, len(self.evidence_entries()))

    def test_a4_the_evidence_entry_carries_the_result_evidence_and_the_current_fingerprint(self):
        self.claimed_and_accepted()
        fingerprint = self.fingerprint()
        self.ok("record-result", self.result_document())
        entry = self.evidence_entries()[0]
        self.assertEqual(self.EVIDENCE["criteria"], entry["criteria"])
        self.assertEqual(self.EVIDENCE["revision"], entry["revision"])
        self.assertEqual(self.EVIDENCE["environment"], entry["environment"])
        self.assertEqual(self.EVIDENCE["limitations"], entry["limitations"])
        self.assertEqual(fingerprint, entry["fingerprint"])
        self.assertEqual("pass", entry["result"])
        status = records.evidence_status(records.read_record(store.record_path(self.root, "SEQ-001", "A1")))
        self.assertEqual([True], [item["applies"] for item in status])

    def test_a4_a_task_that_depends_on_the_closed_task_can_then_be_claimed(self):
        self.add_dependent_task()
        self.accept("A2")
        self.claimed_and_accepted()
        dependent_claim = self.claim_document("A2", allowed_paths=["docs/other.md"], operation="op-a4-claim-a2")
        self.assert_fails_without_writing("claim", dependent_claim, "invalid-request")
        self.ok("record-result", self.result_document())
        self.assertEqual("done", self.record_metadata(task="A1")["lifecycle"])
        self.ok("claim", dependent_claim)
        self.assertEqual(ACTOR, self.record_metadata(task="A2")["claim"]["actor"])

    def test_a4_a_passed_result_without_evidence_is_recorded_and_the_task_stays_active(self):
        self.claimed_and_accepted()
        result = self.ok("record-result", self.result_document(evidence=None))
        metadata = self.record_metadata(task="A1")
        self.assertEqual("active", metadata["lifecycle"])
        self.assertEqual("passed", metadata["result"]["outcome"])
        self.assertIsInstance(result["not_closed"], str)
        self.assertTrue(result["not_closed"].strip())
        self.assertRegex(result["not_closed"], r"(?i)evidence")
        self.assertEqual([], self.evidence_entries())

    def test_a4_acceptance_that_does_not_apply_records_result_and_evidence_but_does_not_close(self):
        self.claim_the_task()
        fingerprint = self.fingerprint()
        self.accept(fingerprint="sha256:" + "0" * 64)
        self.assertFalse(
            records.acceptance_status(records.read_record(store.record_path(self.root, "SEQ-001", "A1")))["applies"]
        )
        result = self.ok("record-result", self.result_document())
        metadata = self.record_metadata(task="A1")
        self.assertEqual("active", metadata["lifecycle"])
        self.assertEqual("passed", metadata["result"]["outcome"])
        entries = self.evidence_entries()
        self.assertEqual(1, len(entries))
        self.assertEqual(self.EVIDENCE["criteria"], entries[0]["criteria"])
        self.assertEqual(fingerprint, entries[0]["fingerprint"])
        self.assertEqual("pass", entries[0]["result"])
        self.assertIsInstance(result["not_closed"], str)
        self.assertRegex(result["not_closed"], r"(?i)accept")

    def test_a4_a_blocked_result_moves_the_task_to_blocked(self):
        self.claimed_and_accepted()
        self.ok("record-result", self.result_document(outcome="blocked", evidence=None))
        metadata = self.record_metadata(task="A1")
        self.assertEqual("blocked", metadata["lifecycle"])
        self.assertEqual("blocked", metadata["result"]["outcome"])

    def test_a4_failed_and_unknown_results_are_recorded_and_leave_the_task_active(self):
        for outcome in ("failed", "unknown"):
            with self.subTest(outcome=outcome):
                self.setUp()
                self.claimed_and_accepted()
                result = self.ok("record-result", self.result_document(outcome=outcome, evidence=None))
                metadata = self.record_metadata(task="A1")
                self.assertEqual("active", metadata["lifecycle"])
                self.assertEqual(outcome, metadata["result"]["outcome"])
                self.assertFalse(result.get("not_closed"))

    def prepare_closable_item(self) -> None:
        """An active, accepted item whose only task is done, so a passing result could close it."""
        self.patch_record({"lifecycle": "active"})
        self.patch_record({"lifecycle": "done"}, task="A1")
        self.accept(task=None)

    def item_result(self, outcome: str, evidence="default") -> dict:
        return self.result_document(outcome=outcome, evidence=evidence, task=None, actor="session-next",
                                    coordinator="session-next")

    def test_a4_a_passed_result_on_an_item_leaves_the_item_active(self):
        self.prepare_closable_item()
        self.ok("record-result", self.item_result("passed"))
        metadata = self.record_metadata()
        self.assertEqual("active", metadata["lifecycle"])
        self.assertEqual("passed", metadata["result"]["outcome"])

    def test_a4_no_outcome_changes_an_items_lifecycle(self):
        self.prepare_closable_item()
        for outcome in ("passed", "blocked", "failed", "unknown"):
            with self.subTest(outcome=outcome):
                self.ok("record-result", self.item_result(outcome))
                metadata = self.record_metadata()
                self.assertEqual("active", metadata["lifecycle"])
                self.assertEqual(outcome, metadata["result"]["outcome"])

    def test_a4_only_the_claim_holder_closes_a_task(self):
        self.claimed_and_accepted()
        self.assert_fails_without_writing(
            "record-result", self.result_document(actor="agent:other"), "missing-authority"
        )
        self.assertEqual("active", self.record_metadata(task="A1")["lifecycle"])

    def test_a4_replaying_a_closing_result_adds_no_second_evidence_entry(self):
        self.claimed_and_accepted()
        document = self.result_document()
        first = self.ok("record-result", document)
        replay = self.ok("record-result", dict(document, operation=first["operation"]))
        self.assertTrue(replay["replayed"])
        metadata = self.record_metadata(task="A1")
        self.assertEqual("done", metadata["lifecycle"])
        self.assertEqual(1, len(self.evidence_entries()))


if __name__ == "__main__":
    unittest.main()
