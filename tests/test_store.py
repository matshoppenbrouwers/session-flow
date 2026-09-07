"""Root lock, identity reservation, tombstones, and operation-journal behaviour.

Every rejection here must happen before a write, so the write-sensitive cases run
the real entrypoint against a temporary work root and compare a file snapshot
taken before and after the call. Only the temporary root is ever mutated.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = REPO_ROOT / "scripts"
ENTRYPOINT = SCRIPTS_ROOT / "session-flow.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lifecycle" / "store"
NAMESPACE = "6f1d4a02-3c58-4a1e-9b77-0c2f8d5e4411"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from session_flow import (  # noqa: E402
    InvalidIdentityError,
    InvalidRequestError,
    MissingAuthorityError,
    RootBusyError,
    records,
    store,
)

GIT_AVAILABLE = shutil.which("git") is not None
NEEDS_GIT = "git is required to version the work root"


def git(root: Path, *arguments) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *arguments], capture_output=True, text=True, check=False
    )


def initialize_repository(root: Path) -> None:
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "Fixture Coordinator")
    git(root, "add", "-A")
    git(root, "commit", "-m", "Initialize synthetic work records")


def payload(name: str) -> dict:
    return json.loads((FIXTURES / "payloads" / name).read_text(encoding="utf-8"))


def snapshot(root: Path) -> dict:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def temporary_files(root: Path) -> list:
    return [str(path) for path in root.rglob(store.TEMPORARY_PREFIX + "*")]


class StoreCase(unittest.TestCase):
    """A disposable project holding a copy of the synthetic work root."""

    def setUp(self):
        directory = tempfile.mkdtemp(prefix="session-flow-store-")
        self.addCleanup(shutil.rmtree, directory, True)
        self.project = Path(directory)
        self.root = self.project / "_devdocs" / "work"
        shutil.copytree(FIXTURES / "root", self.root)

    def request(self, command: str, document=None, seq=None, task=None) -> dict:
        return {
            "protocol": 1,
            "command": command,
            "project_root": str(self.project),
            "work_root": str(self.root),
            "sequence_path": str(self.project / "_devdocs" / "SEQUENCE.md"),
            "namespace": None,
            "seq": seq,
            "task": task,
            "input": document,
            "config": {},
        }

    def payload_file(self, document: dict) -> Path:
        path = self.project / ("payload-%d.json" % len(list(self.project.glob("payload-*.json"))))
        path.write_text(json.dumps(document), encoding="utf-8")
        return path

    def run_cli(self, command: str, document=None, *arguments, project=None):
        root = self.project if project is None else project
        call = [sys.executable, "-B", str(ENTRYPOINT), command, "--project-root", str(root)]
        if document is not None:
            call += ["--input", str(self.payload_file(document))]
        completed = subprocess.run(call + list(arguments), capture_output=True, text=True, check=False)
        return completed, json.loads(completed.stdout)

    def assert_fails_without_writing(self, command: str, document: dict, code: str) -> dict:
        before = snapshot(self.root)
        completed, answer = self.run_cli(command, document)
        self.assertEqual(1, completed.returncode, completed.stdout)
        self.assertFalse(answer["ok"])
        self.assertEqual(code, answer["error"]["code"], answer["error"]["message"])
        self.assertEqual(before, snapshot(self.root))
        return answer["error"]

    def install_owner(self, fixture: str, **overrides) -> dict:
        document = json.loads((FIXTURES / "lock" / fixture).read_text(encoding="utf-8"))
        document.update(overrides)
        store.lock_directory(self.root).mkdir(parents=True)
        store.write_json(store.owner_path(self.root), document)
        return document

    def install_prepared_operation(self, document=None) -> str:
        document = document or {"operation": "op-interrupted-0001"}
        operation_id = document["operation"]
        store.write_json(
            store.operation_path(self.root, operation_id),
            {
                "format": 1,
                "operation": operation_id,
                "command": "transition",
                "state": "prepared",
                "payload_fingerprint": records.digest(document),
                "changes": [],
            },
        )
        return operation_id

    def record_metadata(self, seq="SEQ-001", task=None) -> dict:
        return records.read_record(store.record_path(self.root, seq, task))["metadata"]


class RootLockTest(StoreCase):
    """The lock is a directory created exclusively, released only by its owner."""

    def test_the_first_lock_records_host_coordinator_and_token(self):
        ownership = store.acquire_lock(self.root, "session-next")
        self.addCleanup(store.release_lock, self.root, ownership)
        self.assertTrue(store.lock_directory(self.root).is_dir())
        owner = store.read_owner(self.root)
        self.assertEqual(store.current_host(), owner["host"])
        self.assertEqual("session-next", owner["coordinator"])
        self.assertEqual(os.getpid(), owner["pid"])
        self.assertEqual(ownership["token"], owner["token"])

    def test_a_second_coordinator_is_refused_and_told_who_holds_the_root(self):
        ownership = store.acquire_lock(self.root, "session-next")
        self.addCleanup(store.release_lock, self.root, ownership)
        with self.assertRaises(RootBusyError) as raised:
            store.acquire_lock(self.root, "session-delegation")
        self.assertEqual("alive", raised.exception.detail["liveness"])
        self.assertIn("session-next", str(raised.exception))

    def test_only_the_matching_lock_is_released(self):
        ownership = store.acquire_lock(self.root, "session-next")
        with self.assertRaises(RootBusyError):
            store.release_lock(self.root, {"token": "0" * 32})
        self.assertTrue(store.owner_path(self.root).is_file())
        store.release_lock(self.root, ownership)
        self.assertFalse(store.lock_directory(self.root).exists())

    def test_an_expired_timestamp_never_releases_a_live_owner(self):
        self.install_owner("live-owner.json", host=store.current_host(), pid=os.getpid())
        with self.assertRaises(RootBusyError):
            store.acquire_lock(self.root, "session-next")
        with self.assertRaises(RootBusyError) as raised:
            store.acquire_lock(self.root, "session-next", {"reason": "the timestamp looks old"})
        self.assertEqual("alive", raised.exception.detail["liveness"])

    def test_a_takeover_needs_the_owner_to_be_gone(self):
        held = self.install_owner("gone-owner.json", host=store.current_host())
        self.assertEqual("gone", store.owner_liveness(store.read_owner(self.root)))
        with self.assertRaises(RootBusyError):
            store.acquire_lock(self.root, "session-next")
        ownership = store.acquire_lock(self.root, "session-next", {"reason": "owner process is gone"})
        self.assertEqual(held["token"], ownership["took_over_from"]["token"])
        self.assertEqual(ownership["token"], store.read_owner(self.root)["token"])

    def test_an_unrecorded_owner_can_be_taken_over(self):
        store.lock_directory(self.root).mkdir(parents=True)
        self.assertEqual("unrecorded", store.owner_liveness(store.read_owner(self.root)))
        ownership = store.acquire_lock(self.root, "session-next", {"reason": "no owner was recorded"})
        self.assertEqual(store.current_host(), ownership["host"])

    def test_a_takeover_stops_while_a_prepared_operation_waits(self):
        self.install_owner("gone-owner.json", host=store.current_host())
        operation_id = self.install_prepared_operation()
        with self.assertRaises(RootBusyError) as raised:
            store.acquire_lock(self.root, "session-next", {"reason": "owner process is gone"})
        self.assertIn("reconcile", str(raised.exception))
        self.assertEqual([operation_id], raised.exception.detail["pending_operations"])

    def test_competing_coordinators_have_one_effective_owner(self):
        taken, refused = [], []
        barrier = threading.Barrier(8)

        def contend():
            barrier.wait()
            try:
                taken.append(store.acquire_lock(self.root, "session-next"))
            except RootBusyError:
                refused.append(True)

        threads = [threading.Thread(target=contend) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(1, len(taken))
        self.assertEqual(7, len(refused))
        self.assertEqual(taken[0]["token"], store.read_owner(self.root)["token"])


class ReservationTest(StoreCase):
    """Identities are allocated against retained items and the tombstone index."""

    def test_reservation_skips_retained_items_and_tombstoned_identities(self):
        self.assertEqual({"SEQ-001", "SEQ-002"}, store.taken_ids(self.root))
        self.assertEqual("SEQ-003", store.next_item_id(self.root))

    def test_a_crashed_reservation_keeps_its_identity_taken(self):
        first = store.reserve_item_id(self.root, "op-crash-0002")
        self.assertEqual("SEQ-003", first)
        self.assertFalse((self.root / "seq-003").exists())
        self.assertEqual("SEQ-004", store.reserve_item_id(self.root, "op-next-0003"))
        entries = {entry["seq"]: entry for entry in store.read_tombstones(self.root)["entries"]}
        self.assertEqual("op-crash-0002", entries["SEQ-003"]["operation"])
        self.assertEqual({"SEQ-001", "SEQ-002", "SEQ-003", "SEQ-004"}, store.taken_ids(self.root))

    def test_an_alias_in_the_index_is_never_reallocated(self):
        document = store.read_tombstones(self.root)
        document["entries"].append(
            {"seq": "SEQ-009", "state": "retired", "aliases": ["SEQ-011", "legacy-task-0042"]}
        )
        store.write_json(store.tombstones_path(self.root), document)
        self.assertEqual("SEQ-012", store.next_item_id(self.root))
        self.assertIn("legacy-task-0042", store.taken_ids(self.root))


class TransitionTest(StoreCase):
    """The transition sequence, its journal, and its rejections."""

    def test_a_transition_applies_the_change_and_journals_both_hashes(self):
        before_text = (self.root / "seq-001" / "intent.md").read_text(encoding="utf-8")
        completed, answer = self.run_cli("transition", payload("lifecycle-change.json"))
        self.assertEqual(0, completed.returncode, completed.stderr)
        result = answer["result"]
        self.assertEqual("applied", result["state"])
        self.assertFalse(result["replayed"])
        self.assertEqual(NAMESPACE, result["namespace"])
        self.assertEqual(2, result["records"][0]["revision"])
        self.assertIn("views", result)

        metadata = self.record_metadata()
        self.assertEqual("active", metadata["lifecycle"])
        self.assertEqual(2, metadata["revision"])

        after_text = (self.root / "seq-001" / "intent.md").read_text(encoding="utf-8")
        journal = store.load_operation(self.root, "op-lifecycle-0001")
        self.assertEqual("applied", journal["state"])
        self.assertEqual(records.digest(before_text), journal["changes"][0]["before"])
        self.assertEqual(records.digest(after_text), journal["changes"][0]["after"])
        self.assertEqual([], temporary_files(self.root))

    def test_the_scope_and_prose_survive_a_metadata_only_transition(self):
        original = records.read_record(self.root / "seq-001" / "intent.md")
        self.run_cli("transition", payload("lifecycle-change.json"))
        updated = records.read_record(self.root / "seq-001" / "intent.md")
        self.assertEqual(original["scope"], updated["scope"])
        self.assertEqual(original["body"], updated["body"])

    def test_a_stale_expected_revision_fails_before_any_write(self):
        error = self.assert_fails_without_writing(
            "transition", payload("stale-revision.json"), "stale-revision"
        )
        self.assertEqual(1, error["detail"]["held"])
        self.assertEqual(9, error["detail"]["expected"])

    def test_a_second_transition_applies_on_the_new_revision(self):
        self.run_cli("transition", payload("lifecycle-change.json"))
        document = payload("lifecycle-change.json")
        document["operation"] = "op-lifecycle-0002"
        document["changes"][0]["expect_revision"] = 2
        document["changes"][0]["metadata"] = {"lifecycle": "done"}
        completed, answer = self.run_cli("transition", document)
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(3, self.record_metadata()["revision"])

    def test_retrying_an_applied_operation_returns_the_prior_result(self):
        _, first = self.run_cli("transition", payload("lifecycle-change.json"))
        after_first = snapshot(self.root)
        completed, second = self.run_cli("transition", payload("lifecycle-change.json"))
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertTrue(second["result"]["replayed"])
        self.assertEqual(first["result"]["records"], second["result"]["records"])
        self.assertEqual(2, self.record_metadata()["revision"])
        self.assertEqual(after_first["seq-001/intent.md"], snapshot(self.root)["seq-001/intent.md"])

    def test_reusing_an_operation_identity_with_another_payload_fails(self):
        self.run_cli("transition", payload("lifecycle-change.json"))
        error = self.assert_fails_without_writing(
            "transition", payload("conflicting-change.json"), "invalid-identity"
        )
        self.assertEqual("op-lifecycle-0001", error["detail"]["operation"])
        self.assertEqual("active", self.record_metadata()["lifecycle"])

    def test_a_prepared_operation_blocks_another_operation(self):
        self.install_prepared_operation()
        error = self.assert_fails_without_writing(
            "transition", payload("lifecycle-change.json"), "root-busy"
        )
        self.assertIn("reconcile", error["message"])

    def test_retrying_a_prepared_operation_is_refused_rather_than_repeated(self):
        document = payload("lifecycle-change.json")
        self.install_prepared_operation(document)
        error = self.assert_fails_without_writing("transition", document, "root-busy")
        self.assertEqual("prepared", error["detail"]["state"])

    def test_a_new_item_reserves_the_next_identity_at_revision_one(self):
        completed, answer = self.run_cli("transition", payload("new-item.json"))
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(["SEQ-003"], answer["result"]["reserved"])
        metadata = self.record_metadata("SEQ-003")
        self.assertEqual(1, metadata["revision"])
        self.assertEqual(NAMESPACE, metadata["namespace"])
        self.assertEqual("captured", metadata["lifecycle"])
        reserved = [entry["seq"] for entry in store.read_tombstones(self.root)["entries"]]
        self.assertIn("SEQ-003", reserved)

    def test_a_change_without_an_expected_revision_is_refused(self):
        document = payload("lifecycle-change.json")
        document["changes"][0].pop("expect_revision")
        self.assert_fails_without_writing("transition", document, "invalid-request")

    def test_two_changes_to_one_record_are_refused(self):
        document = payload("lifecycle-change.json")
        document["changes"].append(dict(document["changes"][0]))
        self.assert_fails_without_writing("transition", document, "invalid-request")

    def intercept_canonical_write(self, replacement):
        original = store.apply_planned_changes
        store.apply_planned_changes = replacement
        self.addCleanup(setattr, store, "apply_planned_changes", original)
        return original

    def test_the_prepared_operation_is_durable_before_the_records_are_replaced(self):
        observed = {}

        def observe(plan):
            observed["journal"] = store.load_operation(self.root, "op-lifecycle-0001")
            observed["record"] = (self.root / "seq-001" / "intent.md").read_text(encoding="utf-8")
            return original(plan)

        original = self.intercept_canonical_write(observe)
        store.transition(self.request("transition", payload("lifecycle-change.json")))
        journal = observed["journal"]
        self.assertEqual("prepared", journal["state"])
        self.assertEqual(records.digest(observed["record"]), journal["changes"][0]["before"])
        self.assertNotEqual(journal["changes"][0]["before"], journal["changes"][0]["after"])
        self.assertEqual(2, self.record_metadata()["revision"])

    def test_an_interrupted_canonical_write_leaves_a_reconcilable_operation(self):
        def interrupt(plan):
            raise KeyboardInterrupt("the coordinator was stopped mid-write")

        self.intercept_canonical_write(interrupt)
        with self.assertRaises(KeyboardInterrupt):
            store.transition(self.request("transition", payload("lifecycle-change.json")))
        journal = store.load_operation(self.root, "op-lifecycle-0001")
        self.assertEqual("prepared", journal["state"])
        self.assertEqual(1, self.record_metadata()["revision"])
        self.assertFalse(store.lock_directory(self.root).exists())

        following = payload("lifecycle-change.json")
        following["operation"] = "op-lifecycle-0009"
        error = self.assert_fails_without_writing("transition", following, "root-busy")
        self.assertEqual(["op-lifecycle-0001"], error["detail"]["pending_operations"])

    def test_the_journal_names_the_coordinator_that_applied_it(self):
        self.run_cli("transition", payload("lifecycle-change.json"))
        owner = store.load_operation(self.root, "op-lifecycle-0001")["owner"]
        self.assertEqual("session-next", owner["coordinator"])
        self.assertEqual(store.current_host(), owner["host"])
        self.assertIn("token", owner)

    def test_a_takeover_request_that_is_not_an_object_is_refused(self):
        document = payload("lifecycle-change.json")
        document["takeover"] = True
        self.assert_fails_without_writing("transition", document, "invalid-request")

    def test_a_transition_without_a_payload_is_refused(self):
        completed, answer = self.run_cli("transition")
        self.assertEqual(1, completed.returncode)
        self.assertEqual("invalid-request", answer["error"]["code"])

    def test_a_locked_root_refuses_a_transition_without_writing(self):
        ownership = store.acquire_lock(self.root, "session-delegation")
        self.addCleanup(store.release_lock, self.root, ownership)
        error = self.assert_fails_without_writing(
            "transition", payload("lifecycle-change.json"), "root-busy"
        )
        self.assertEqual("session-delegation", error["detail"]["owner"]["coordinator"])

    def test_the_lock_is_released_after_an_applied_transition(self):
        self.run_cli("transition", payload("lifecycle-change.json"))
        self.assertFalse(store.lock_directory(self.root).exists())

    def test_the_lock_is_released_after_a_rejected_transition(self):
        self.run_cli("transition", payload("stale-revision.json"))
        self.assertFalse(store.lock_directory(self.root).exists())


class RootValidationTest(StoreCase):
    """Configuration and paths are validated before the canonical records change."""

    def test_a_missing_namespace_file_fails_before_any_write(self):
        (self.root / "namespace.json").unlink()
        self.assert_fails_without_writing(
            "transition", payload("lifecycle-change.json"), "invalid-identity"
        )

    def test_an_unknown_namespace_format_fails_before_any_write(self):
        shutil.copy(FIXTURES / "invalid" / "namespace-unknown-format.json", self.root / "namespace.json")
        self.assert_fails_without_writing(
            "transition", payload("lifecycle-change.json"), "unsupported-format"
        )

    def test_a_binding_that_is_not_a_directory_is_rejected(self):
        shutil.copy(FIXTURES / "invalid" / "namespace-missing-binding.json", self.root / "namespace.json")
        error = self.assert_fails_without_writing(
            "transition", payload("lifecycle-change.json"), "invalid-identity"
        )
        self.assertEqual("absent-companion", error["detail"]["binding"])

    def test_a_record_addressed_through_a_symbolic_link_is_rejected(self):
        elsewhere = self.project / "outside"
        elsewhere.mkdir()
        try:
            (self.root / "seq-004").symlink_to(elsewhere, target_is_directory=True)
        except (OSError, NotImplementedError) as failure:
            self.skipTest("this filesystem does not support symbolic links: %s" % failure)
        with self.assertRaises(InvalidIdentityError) as raised:
            store.record_path(self.root, "SEQ-004")
        self.assertIn("symbolic link", str(raised.exception))

    def test_a_special_file_in_the_work_root_is_rejected(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("this platform has no named pipes")
        try:
            os.mkfifo(str(self.root / "seq-005"))
        except (OSError, NotImplementedError) as failure:
            self.skipTest("this filesystem does not support named pipes: %s" % failure)
        with self.assertRaises(InvalidIdentityError) as raised:
            store.record_path(self.root, "SEQ-005")
        self.assertIn("regular file", str(raised.exception))

    def test_an_absent_work_root_is_named_rather_than_created(self):
        shutil.rmtree(self.root)
        with self.assertRaises(InvalidIdentityError):
            store.transition(self.request("transition", payload("lifecycle-change.json")))
        self.assertFalse(self.root.exists())


@unittest.skipUnless(GIT_AVAILABLE, "git is required to commit the work root")
class WorkRootVersioningTest(StoreCase):
    """History belongs to Git: an applied transition ends in a commit."""

    def git(self, *arguments) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(self.root), *arguments], capture_output=True, text=True, check=False
        )

    def initialize_repository(self):
        self.git("init", "-b", "main")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Fixture Coordinator")
        self.git("add", "-A")
        self.git("commit", "-m", "Initialize synthetic work records")

    def test_an_applied_transition_ends_in_a_commit(self):
        self.initialize_repository()
        _, answer = self.run_cli("transition", payload("lifecycle-change.json"))
        commit = answer["result"]["commit"]
        self.assertTrue(commit["committed"], commit)
        self.assertEqual(commit["commit"], self.git("rev-parse", "HEAD").stdout.strip())
        self.assertEqual("2", self.git("rev-list", "--count", "HEAD").stdout.strip())
        self.assertIn('"lifecycle": "active"', self.git("show", "HEAD:seq-001/intent.md").stdout)

    def test_an_unversioned_root_reports_that_it_was_not_committed(self):
        _, answer = self.run_cli("transition", payload("lifecycle-change.json"))
        commit = answer["result"]["commit"]
        self.assertFalse(commit["committed"])
        self.assertIn("backup and restore are unavailable", commit["reason"])


class ClaimAndResultTest(StoreCase):
    """A claim is a bounded assignment; a result is the claimed actor's own report."""

    def claim_the_task(self):
        return self.run_cli("claim", payload("claim.json"))

    def test_a_claim_records_actor_coordinator_and_allowed_paths(self):
        completed, answer = self.claim_the_task()
        self.assertEqual(0, completed.returncode, completed.stderr)
        claim = self.record_metadata(task="A1")["claim"]
        self.assertEqual("agent:store-implementer", claim["actor"])
        self.assertEqual("session-delegation", claim["coordinator"])
        self.assertEqual(["scripts/session_flow/store.py", "tests/test_store.py"], claim["allowed_paths"])
        self.assertEqual(2, answer["result"]["records"][0]["revision"])

    def test_a_second_actor_needs_authority_to_take_a_claim(self):
        self.claim_the_task()
        document = payload("claim.json")
        document.update({"operation": "op-claim-0002", "actor": "agent:other", "expect_revision": 2})
        self.assert_fails_without_writing("claim", document, "missing-authority")

    def test_an_explicit_takeover_reassigns_the_claim(self):
        self.claim_the_task()
        document = payload("claim.json")
        document.update(
            {
                "operation": "op-claim-0003",
                "actor": "agent:other",
                "expect_revision": 2,
                "takeover_claim": {"authority": "user request", "revision": "2026-09-07T11:00:00Z"},
            }
        )
        completed, _ = self.run_cli("claim", document)
        self.assertEqual(0, completed.returncode, completed.stderr)
        claim = self.record_metadata(task="A1")["claim"]
        self.assertEqual("agent:other", claim["actor"])
        self.assertEqual("agent:store-implementer", claim["reassigned_from"])

    def test_a_result_without_a_claim_is_refused(self):
        document = payload("result.json")
        document["expect_revision"] = 1
        self.assert_fails_without_writing("record-result", document, "missing-authority")

    def test_only_the_claiming_actor_records_the_result(self):
        self.claim_the_task()
        document = payload("result.json")
        document["actor"] = "agent:other"
        self.assert_fails_without_writing("record-result", document, "missing-authority")

    def test_the_claimed_outcome_is_recorded_with_its_evidence(self):
        self.claim_the_task()
        completed, answer = self.run_cli("record-result", payload("result.json"))
        self.assertEqual(0, completed.returncode, completed.stderr)
        result = self.record_metadata(task="A1")["result"]
        self.assertEqual("passed", result["outcome"])
        self.assertEqual("one effective writer", result["evidence"]["criteria"])
        self.assertIn("recorded_at", result)
        self.assertEqual(3, answer["result"]["records"][0]["revision"])

    def test_an_unknown_outcome_is_refused(self):
        self.claim_the_task()
        document = payload("result.json")
        document["result"]["outcome"] = "probably fine"
        self.assert_fails_without_writing("record-result", document, "invalid-request")

    def test_a_claim_carries_no_schedule_or_execution_instruction(self):
        self.claim_the_task()
        claim = self.record_metadata(task="A1")["claim"]
        self.assertEqual(
            {"actor", "coordinator", "host", "claimed_at", "allowed_paths"}, set(claim)
        )

    def test_a_claim_on_an_unknown_task_is_refused_before_any_write(self):
        document = payload("claim.json")
        document.update({"operation": "op-claim-0004", "task": "Z9"})
        self.assert_fails_without_writing("claim", document, "invalid-identity")


class DirectCallTest(StoreCase):
    """The handlers keep the documented request/response signature."""

    def test_transition_answers_the_dispatch_signature(self):
        result = store.transition(self.request("transition", payload("lifecycle-change.json")))
        self.assertEqual("applied", result["state"])
        self.assertEqual(2, result["records"][0]["revision"])

    def test_a_missing_claim_raises_the_named_authority_error(self):
        document = payload("result.json")
        document["expect_revision"] = 1
        with self.assertRaises(MissingAuthorityError):
            store.record_result(self.request("record-result", document))


class RecoveryCase(StoreCase):
    """A work root left mid-operation by an interruption injected at one stage."""

    def crash_during(self, stage: str, document: dict) -> None:
        with mock.patch.object(store, stage, side_effect=KeyboardInterrupt("the coordinator stopped")):
            with self.assertRaises(KeyboardInterrupt):
                store.transition(self.request("transition", document))

    def apply_only_the_first_change(self, document: dict) -> None:
        def half(plan):
            store.finish_change(plan[0])
            raise KeyboardInterrupt("the coordinator stopped between canonical writes")

        with mock.patch.object(store, "apply_planned_changes", half):
            with self.assertRaises(KeyboardInterrupt):
                store.transition(self.request("transition", document))

    def install_contentless_operation(self) -> str:
        document = json.loads(
            (FIXTURES / "invalid" / "operation-without-content.json").read_text(encoding="utf-8")
        )
        path = self.root / "seq-001" / "intent.md"
        document["changes"][0]["path"] = str(path)
        document["changes"][0]["before"] = records.digest(path.read_text(encoding="utf-8"))
        store.write_json(store.operation_path(self.root, document["operation"]), document)
        return document["operation"]

    def reconcile(self, document=None) -> dict:
        return store.reconcile(self.request("reconcile", document))

    def revision(self, seq="SEQ-001", task=None) -> int:
        return self.record_metadata(seq, task)["revision"]

    def task_text(self) -> str:
        return (self.root / "seq-001" / "tasks" / "A1.md").read_text(encoding="utf-8")


class InterruptedOperationTest(RecoveryCase):
    """An interruption at every stage either resolves or stays explicitly blocked."""

    def test_an_interrupted_reservation_keeps_its_identity_taken(self):
        self.crash_during("write_prepared_operation", payload("new-item.json"))
        self.assertIn("SEQ-003", store.taken_ids(self.root))
        self.assertFalse((self.root / "seq-003").exists())
        self.assertIsNone(store.load_operation(self.root, "op-capture-0001"))

        answer = self.reconcile()
        self.assertEqual("resolved", answer["state"])
        self.assertEqual([], answer["operations"])
        self.assertIn("SEQ-003", answer["reserved"])

        completed, following = self.run_cli("transition", payload("new-item.json"))
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(["SEQ-004"], following["result"]["reserved"])

    def test_an_interrupted_prepared_write_leaves_nothing_to_recover(self):
        self.crash_during("write_prepared_operation", payload("lifecycle-change.json"))
        self.assertIsNone(store.load_operation(self.root, "op-lifecycle-0001"))
        self.assertEqual(1, self.revision())
        self.assertFalse(store.lock_directory(self.root).exists())
        self.assertEqual([], self.reconcile()["operations"])

        completed, _ = self.run_cli("transition", payload("lifecycle-change.json"))
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(2, self.revision())

    def test_reconcile_finishes_an_operation_whose_records_were_never_replaced(self):
        self.crash_during("apply_planned_changes", payload("two-record-change.json"))
        self.assertEqual("prepared", store.load_operation(self.root, "op-two-record-0001")["state"])
        self.assertEqual(1, self.revision())
        self.assertEqual(1, self.revision(task="A1"))

        answer = self.reconcile()
        self.assertEqual("resolved", answer["state"])
        self.assertEqual(["op-two-record-0001"], answer["resolved"])
        self.assertEqual([], answer["blocked"])
        self.assertEqual("active", self.record_metadata()["lifecycle"])
        self.assertEqual(2, self.revision())
        self.assertEqual(2, self.revision(task="A1"))

        journal = store.load_operation(self.root, "op-two-record-0001")
        self.assertEqual("applied", journal["state"])
        self.assertTrue(journal["result"]["recovered"])
        self.assertEqual([], temporary_files(self.root))

    def test_reconcile_finishes_a_partially_applied_operation(self):
        self.apply_only_the_first_change(payload("two-record-change.json"))
        self.assertEqual(2, self.revision())
        self.assertEqual(1, self.revision(task="A1"))

        answer = self.reconcile()
        self.assertEqual("resolved", answer["state"])
        states = {entry["task"]: entry["state"] for entry in answer["operations"][0]["changes"]}
        self.assertEqual({None: "applied", "A1": "pending"}, states)
        self.assertEqual(2, self.revision(task="A1"))
        self.assertEqual("active", self.record_metadata(task="A1")["lifecycle"])

    def test_an_interrupted_view_refresh_leaves_an_applied_operation(self):
        self.crash_during("regenerate_views", payload("lifecycle-change.json"))
        journal = store.load_operation(self.root, "op-lifecycle-0001")
        self.assertEqual("applied", journal["state"])
        self.assertNotIn("views", journal)
        self.assertEqual(2, self.revision())

        answer = self.reconcile()
        self.assertEqual("resolved", answer["state"])
        self.assertEqual([], answer["operations"])
        self.assertTrue(answer["views"]["refreshed"], answer["views"])

        completed, retried = self.run_cli("transition", payload("lifecycle-change.json"))
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertTrue(retried["result"]["replayed"])
        self.assertEqual(2, self.revision())

    def test_reconcile_is_reachable_through_the_entrypoint(self):
        self.crash_during("apply_planned_changes", payload("two-record-change.json"))
        completed, answer = self.run_cli("reconcile")
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual("resolved", answer["result"]["state"])
        self.assertEqual(["op-two-record-0001"], answer["result"]["resolved"])
        self.assertEqual(2, self.revision(task="A1"))

    def test_reconcile_repeats_no_external_effect(self):
        self.crash_during("apply_planned_changes", payload("two-record-change.json"))
        observed = []
        original = store.run_git

        def watch(work_root, arguments):
            observed.append(list(arguments))
            return original(work_root, arguments)

        with mock.patch.object(store, "run_git", watch):
            self.assertEqual("resolved", self.reconcile()["state"])
        self.assertTrue(observed)
        self.assertEqual(
            [], [call for call in observed if call[0] in ("push", "fetch", "clone", "remote")]
        )

    @unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
    def test_a_reconciled_operation_ends_in_a_commit(self):
        initialize_repository(self.root)
        self.crash_during("apply_planned_changes", payload("two-record-change.json"))
        answer = self.reconcile()
        self.assertTrue(answer["commit"]["committed"], answer["commit"])
        self.assertIn('"lifecycle": "active"', git(self.root, "show", "HEAD:seq-001/tasks/A1.md").stdout)


class DivergenceTest(RecoveryCase):
    """Unexplained divergence stops reconciliation rather than overwriting it."""

    def diverge_the_task_record(self) -> str:
        self.apply_only_the_first_change(payload("two-record-change.json"))
        foreign = self.task_text() + "\nEdited outside the runtime.\n"
        (self.root / "seq-001" / "tasks" / "A1.md").write_text(foreign, encoding="utf-8")
        return foreign

    def test_unexplained_divergence_blocks_instead_of_overwriting(self):
        foreign = self.diverge_the_task_record()
        answer = self.reconcile()
        self.assertEqual("blocked", answer["state"])
        self.assertEqual(["op-two-record-0001"], answer["blocked"])
        self.assertEqual([], answer["resolved"])
        self.assertEqual(foreign, self.task_text())
        self.assertEqual("prepared", store.load_operation(self.root, "op-two-record-0001")["state"])
        self.assertFalse(answer["commit"]["committed"])
        self.assertIn("divergence", answer["commit"]["reason"])

    def test_the_blocked_change_names_why_it_could_not_be_finished(self):
        self.diverge_the_task_record()
        answer = self.reconcile()
        diverged = [entry for entry in answer["operations"][0]["changes"] if entry["state"] == "diverged"]
        self.assertEqual(1, len(diverged))
        self.assertEqual("A1", diverged[0]["task"])
        self.assertIn("outside this runtime", diverged[0]["reason"])
        self.assertNotEqual(diverged[0]["expected"], diverged[0]["found"])

    def test_a_diverged_operation_keeps_refusing_new_operations(self):
        self.diverge_the_task_record()
        self.reconcile()
        error = self.assert_fails_without_writing(
            "transition", payload("lifecycle-change.json"), "root-busy"
        )
        self.assertEqual(["op-two-record-0001"], error["detail"]["pending_operations"])

    def test_a_repeated_reconcile_stays_blocked_rather_than_forcing_the_change(self):
        foreign = self.diverge_the_task_record()
        self.assertEqual("blocked", self.reconcile()["state"])
        self.assertEqual("blocked", self.reconcile()["state"])
        self.assertEqual(foreign, self.task_text())

    def test_a_journal_entry_without_rendered_content_cannot_be_finished(self):
        operation = self.install_contentless_operation()
        before = (self.root / "seq-001" / "intent.md").read_text(encoding="utf-8")
        answer = self.reconcile()
        self.assertEqual("blocked", answer["state"])
        self.assertEqual([operation], answer["blocked"])
        self.assertIn("no rendered content", answer["operations"][0]["changes"][0]["reason"])
        self.assertEqual(before, (self.root / "seq-001" / "intent.md").read_text(encoding="utf-8"))


class ReconcileOwnershipTest(RecoveryCase):
    """Recovery inspects the owner before it takes the root over."""

    def test_reconcile_is_refused_while_a_live_coordinator_holds_the_root(self):
        ownership = store.acquire_lock(self.root, "session-delegation")
        self.addCleanup(store.release_lock, self.root, ownership)
        with self.assertRaises(RootBusyError) as raised:
            self.reconcile()
        self.assertEqual("alive", raised.exception.detail["liveness"])

    def test_reconcile_takes_over_from_a_coordinator_that_is_gone(self):
        self.crash_during("apply_planned_changes", payload("two-record-change.json"))
        self.install_owner("gone-owner.json", host=store.current_host())
        answer = self.reconcile()
        self.assertEqual("resolved", answer["state"])
        self.assertEqual(2, self.revision(task="A1"))
        self.assertFalse(store.lock_directory(self.root).exists())

    def test_a_retired_identity_is_not_reported_as_an_unwritten_reservation(self):
        document = store.read_tombstones(self.root)
        document["entries"].append({"seq": "SEQ-007", "state": "retired", "aliases": ["SEQ-008"]})
        store.write_json(store.tombstones_path(self.root), document)
        self.assertIn("SEQ-007", store.taken_ids(self.root))
        self.assertEqual(["SEQ-002"], self.reconcile()["reserved"])


@unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
class BackupTest(StoreCase):
    """Backup verifies the configured remote and pushes. It defines no archive format."""

    def setUp(self):
        super().setUp()
        initialize_repository(self.root)
        self.remote = self.project / "records.git"
        git(self.project, "init", "--bare", "-b", "main", str(self.remote))
        git(self.root, "remote", "add", "origin", str(self.remote))

    def test_backup_pushes_the_configured_remote(self):
        completed, answer = self.run_cli("backup", {"remote": "origin"})
        self.assertEqual(0, completed.returncode, completed.stderr)
        result = answer["result"]
        self.assertTrue(result["pushed"], result)
        self.assertTrue(result["complete"])
        self.assertEqual("origin", result["remote"])
        self.assertEqual(str(self.remote), result["url"])
        self.assertEqual("main", result["branch"])
        self.assertIsNone(result["reason"])
        self.assertEqual(result["commit"], git(self.remote, "rev-parse", "HEAD").stdout.strip())

    def test_backup_reports_records_the_push_does_not_carry(self):
        (self.root / "seq-001" / "notes.md").write_text("Written outside a transition.\n", encoding="utf-8")
        _, answer = self.run_cli("backup")
        result = answer["result"]
        self.assertTrue(result["pushed"])
        self.assertFalse(result["complete"])
        self.assertEqual(["seq-001/notes.md"], result["uncommitted"])
        self.assertIn("not committed", result["reason"])

    def test_backup_without_a_remote_names_the_command_that_adds_one(self):
        git(self.root, "remote", "remove", "origin")
        completed, answer = self.run_cli("backup")
        self.assertEqual(1, completed.returncode)
        self.assertEqual("invalid-identity", answer["error"]["code"])
        self.assertIn("remote add", answer["error"]["message"])

    def test_a_remote_name_that_is_not_a_remote_name_is_refused(self):
        completed, answer = self.run_cli("backup", {"remote": "--upload-pack=touch"})
        self.assertEqual(1, completed.returncode)
        self.assertEqual("invalid-request", answer["error"]["code"])


@unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
class RestoreTest(StoreCase):
    """Restore is a checkout of the repository that already holds the records."""

    def setUp(self):
        super().setUp()
        initialize_repository(self.root)
        self.target = self.project / "restored"

    def build_source(self) -> str:
        completed, _ = self.run_cli("accept", payload("acceptance.json"), "--seq", "SEQ-001")
        self.assertEqual(0, completed.returncode, completed.stderr)
        operation = self.install_prepared_operation()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-m", "Accept SEQ-001 and leave one operation prepared")
        return operation

    def restore_request(self, document) -> dict:
        return dict(self.request("restore", document), work_root=str(self.target))

    def restored_record(self) -> dict:
        return records.read_record(self.target / "seq-001" / "intent.md")

    def test_a_restore_into_an_empty_root_reproduces_the_records(self):
        operation = self.build_source()
        source_text = (self.root / "seq-001" / "intent.md").read_text(encoding="utf-8")

        result = store.restore(self.restore_request({"source": str(self.root)}))
        self.assertTrue(result["restored"])
        self.assertEqual(NAMESPACE, result["namespace"])
        self.assertEqual(["SEQ-001"], result["identities"])
        self.assertEqual(["SEQ-002"], result["reserved"])
        self.assertEqual([operation], result["pending_operations"])
        self.assertEqual(source_text, (self.target / "seq-001" / "intent.md").read_text(encoding="utf-8"))
        self.assertEqual(
            git(self.root, "rev-parse", "HEAD").stdout.strip(),
            git(self.target, "rev-parse", "HEAD").stdout.strip(),
        )

    def test_the_restored_acceptance_still_applies_to_the_restored_scope(self):
        self.build_source()
        store.restore(self.restore_request({"source": str(self.root)}))
        restored = self.restored_record()
        acceptance = restored["metadata"]["acceptance"]
        self.assertEqual("maintainer", acceptance["actor"])
        self.assertEqual("maintainer decision", acceptance["authority"]["source"])
        self.assertEqual(records.scope_fingerprint(restored), acceptance["fingerprint"])
        self.assertTrue(records.acceptance_applies(restored))

    def test_a_named_revision_is_checked_out_rather_than_the_default_branch(self):
        self.build_source()
        first = git(self.root, "rev-list", "--max-parents=0", "HEAD").stdout.strip()
        result = store.restore(self.restore_request({"source": str(self.root), "revision": first}))
        self.assertEqual(first, result["commit"])
        self.assertEqual([], result["pending_operations"])
        self.assertEqual(1, self.restored_record()["identity"]["revision"])
        self.assertNotIn("acceptance", self.restored_record()["metadata"])

    def test_a_root_that_already_holds_records_is_never_overwritten(self):
        self.build_source()
        with self.assertRaises(InvalidIdentityError) as raised:
            store.restore(self.request("restore", {"source": str(self.root)}))
        self.assertIn("empty work root", str(raised.exception))
        self.assertEqual(2, self.record_metadata()["revision"])

    def test_restore_needs_a_source_repository(self):
        with self.assertRaises(InvalidRequestError):
            store.restore(self.restore_request({}))
        self.assertFalse(self.target.exists())

    def test_a_source_that_looks_like_a_git_option_is_refused(self):
        with self.assertRaises(InvalidRequestError):
            store.restore(self.restore_request({"source": "--upload-pack=touch /tmp/pwned"}))
        self.assertFalse(self.target.exists())

    def test_a_revision_that_looks_like_a_git_option_is_refused(self):
        self.build_source()
        with self.assertRaises(InvalidRequestError):
            store.restore(
                self.restore_request({"source": str(self.root), "revision": "--exec=touch /tmp/pwned"})
            )

    def test_restore_is_reachable_through_the_entrypoint(self):
        self.build_source()
        project = self.project / "elsewhere"
        project.mkdir()
        (project / ".session-flow.json").write_text(
            json.dumps({"paths": {"work": "work"}}), encoding="utf-8"
        )
        completed, answer = self.run_cli(
            "restore", {"source": str(self.root)}, project=project
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(["SEQ-001"], answer["result"]["identities"])
        self.assertTrue((project / "work" / "namespace.json").is_file())


@unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
class VersioningReportTest(StoreCase):
    """What versions the work root: its own repository, an enclosing one, or nothing.

    `git rev-parse --show-toplevel` run inside the root answers for the nearest
    enclosing repository, so the report must not read that as the root being versioned.
    """

    def ignore_the_work_root(self) -> None:
        (self.project / ".gitignore").write_text("_devdocs/work/\n", encoding="utf-8")

    def report(self) -> dict:
        return store.versioning_report(self.root)

    def test_a_root_that_is_its_own_repository_is_versioned(self):
        initialize_repository(self.root)
        report = self.report()
        self.assertTrue(report["versioned"])
        self.assertTrue(report["own_repository"])
        self.assertEqual(os.path.realpath(self.root), os.path.realpath(report["repository"]))

    def test_a_root_ignored_by_the_enclosing_repository_is_unversioned(self):
        self.ignore_the_work_root()
        initialize_repository(self.project)
        report = self.report()
        self.assertFalse(report["versioned"])
        self.assertEqual(
            os.path.realpath(self.project), os.path.realpath(report["enclosing_repository"])
        )
        self.assertIn("ignored by the enclosing repository", report["limitations"][0])

    def test_a_root_tracked_by_the_enclosing_repository_is_versioned_by_it(self):
        initialize_repository(self.project)
        report = self.report()
        self.assertTrue(report["versioned"])
        self.assertFalse(report["own_repository"])
        self.assertEqual(os.path.realpath(self.project), os.path.realpath(report["repository"]))

    def test_a_root_in_no_repository_at_all_is_unversioned(self):
        report = self.report()
        self.assertFalse(report["versioned"])
        self.assertNotIn("enclosing_repository", report)
        self.assertIn("is not a Git repository", report["limitations"][0])

    def test_doctor_reports_an_ignored_nested_root_as_unversioned(self):
        self.ignore_the_work_root()
        initialize_repository(self.project)
        completed, answer = self.run_cli("doctor")
        self.assertEqual(0, completed.returncode, completed.stderr)
        storage = answer["result"]["storage"]
        self.assertFalse(storage["versioned"])
        self.assertTrue(
            any("ignored by the enclosing repository" in line for line in storage["limitations"]),
            storage["limitations"],
        )


class BindNamespaceTest(StoreCase):
    """`bind-namespace` creates the work root's namespace.json and binds repositories into it."""

    def bind(self, document=None, *, project=None):
        completed, answer = self.run_cli("bind-namespace", document, project=project)
        return completed, answer

    def namespace_document(self) -> dict:
        return json.loads((self.root / "namespace.json").read_text(encoding="utf-8"))

    def test_an_unbound_root_gets_a_namespace_written_by_the_runtime(self):
        (self.root / "namespace.json").unlink()
        completed, answer = self.bind()
        self.assertEqual(0, completed.returncode, completed.stderr)
        result = answer["result"]
        self.assertTrue(result["created"])
        self.assertEqual(records.parse_namespace(result["namespace"]), result["namespace"])
        self.assertEqual(store.RECORD_FORMAT_VERSION, self.namespace_document()["format"])
        self.assertEqual([], self.namespace_document()["repositories"])

    def test_an_absent_work_root_is_created_with_its_namespace(self):
        shutil.rmtree(self.root)
        completed, answer = self.bind()
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertTrue(answer["result"]["created"])
        self.assertTrue((self.root / "namespace.json").is_file())

    def test_a_second_call_never_reallocates_the_namespace(self):
        before = self.namespace_document()
        completed, answer = self.bind()
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertFalse(answer["result"]["created"])
        self.assertFalse(answer["result"]["changed"])
        self.assertEqual(before, self.namespace_document())

    def test_a_repository_binding_is_added_once(self):
        (self.project / "sibling").mkdir()
        existing = self.namespace_document()["repositories"]
        binding = {"repository": {"name": "sibling", "path": "../../sibling"}}
        _, first = self.bind(binding)
        self.assertTrue(first["result"]["changed"])
        self.assertEqual(existing + [binding["repository"]], self.namespace_document()["repositories"])
        _, second = self.bind(binding)
        self.assertFalse(second["result"]["changed"])
        self.assertEqual(existing + [binding["repository"]], self.namespace_document()["repositories"])

    def test_a_binding_that_is_not_a_directory_is_refused_before_writing(self):
        error = self.assert_fails_without_writing(
            "bind-namespace", {"repository": {"name": "gone", "path": "../../gone"}}, "invalid-identity"
        )
        self.assertIn("not a directory", error["message"])

    def test_a_name_already_bound_elsewhere_is_a_conflict_rather_than_an_overwrite(self):
        (self.project / "sibling").mkdir()
        (self.project / "other").mkdir()
        self.bind({"repository": {"name": "sibling", "path": "../../sibling"}})
        error = self.assert_fails_without_writing(
            "bind-namespace", {"repository": {"name": "sibling", "path": "../../other"}}, "invalid-identity"
        )
        self.assertIn("already bound", error["message"])

    def test_a_locked_root_refuses_to_bind(self):
        self.install_owner("live-owner.json", pid=os.getpid())
        self.assert_fails_without_writing("bind-namespace", None, "root-busy")


class DoctorStorageTest(StoreCase):
    """`doctor` reports the work root's recovery and versioning state as limitations."""

    def storage(self) -> dict:
        completed, answer = self.run_cli("doctor")
        self.assertEqual(0, completed.returncode, completed.stderr)
        return answer["result"]["storage"]

    def assert_limitation(self, storage: dict, fragment: str) -> None:
        self.assertTrue(
            any(fragment in limitation for limitation in storage["limitations"]),
            storage["limitations"],
        )

    def test_an_unversioned_work_root_is_named_as_a_limitation(self):
        storage = self.storage()
        self.assertFalse(storage["versioned"])
        self.assert_limitation(storage, "backup and restore are unavailable")
        self.assert_limitation(storage, "init -b main")

    @unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
    def test_a_versioned_root_without_a_remote_names_that_limitation(self):
        initialize_repository(self.root)
        storage = self.storage()
        self.assertTrue(storage["versioned"])
        self.assertEqual("main", storage["branch"])
        self.assertEqual([], storage["remotes"])
        self.assert_limitation(storage, "no Git remote")

    @unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
    def test_a_versioned_root_with_a_remote_reports_no_versioning_limitation(self):
        initialize_repository(self.root)
        git(self.root, "remote", "add", "origin", str(self.project / "records.git"))
        storage = self.storage()
        self.assertEqual(["origin"], storage["remotes"])
        self.assertEqual(
            [], [line for line in storage["limitations"] if "backup" in line or "remote" in line]
        )

    def test_doctor_reports_pending_operations_and_unwritten_reservations(self):
        operation = self.install_prepared_operation()
        storage = self.storage()
        self.assertEqual([operation], storage["pending_operations"])
        self.assertEqual(["SEQ-002"], storage["reserved"])

    def test_an_unreadable_namespace_is_a_limitation_rather_than_a_crash(self):
        (self.root / "namespace.json").write_text("{ this is not JSON", encoding="utf-8")
        completed, answer = self.run_cli("doctor")
        self.assertEqual(0, completed.returncode, completed.stderr)
        storage = answer["result"]["storage"]
        self.assertIsNone(storage["namespace"])
        self.assert_limitation(storage, "namespace.json")

    def test_an_absent_work_root_is_named_rather_than_created(self):
        shutil.rmtree(self.root)
        storage = self.storage()
        self.assertFalse(storage["versioned"])
        self.assert_limitation(storage, "session-init")
        self.assertFalse(self.root.exists())

    def test_doctor_reports_the_lock_state_of_the_work_root(self):
        self.assertFalse(self.storage()["locked"])
        ownership = store.acquire_lock(self.root, "session-next")
        self.addCleanup(store.release_lock, self.root, ownership)
        self.assertTrue(self.storage()["locked"])


class UnversionedRootTest(StoreCase):
    """Without Git there is no backup and no restore, and the runtime says so."""

    def test_backup_on_an_unversioned_root_is_refused(self):
        completed, answer = self.run_cli("backup")
        self.assertEqual(1, completed.returncode)
        self.assertEqual("invalid-identity", answer["error"]["code"])
        self.assertIn("backup is unavailable", answer["error"]["message"])

    def test_reconcile_reports_that_an_unversioned_recovery_was_not_committed(self):
        answer = store.reconcile(self.request("reconcile"))
        self.assertFalse(answer["commit"]["committed"])
        self.assertIn("backup and restore are unavailable", answer["commit"]["reason"])


if __name__ == "__main__":
    unittest.main()
