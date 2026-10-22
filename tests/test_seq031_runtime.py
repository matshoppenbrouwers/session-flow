"""SEQ-031 acceptance tests: commit ownership and serialized writes (tasks A1 to A4).

A1  render rewrites only the touched task views and skips unchanged files
A2  doctor reports whether the work root can be committed and whether hooks run
A3  an operation commits only its own paths, stops on interference, and says how to recover
A4  accept, revise and capture run under the root lock and make their own commit

The cases reuse the temp-root helpers of `test_store` and only ever write inside a
temporary directory. They exercise the repository's own scripts, never an installed plugin.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS_ROOT = Path(__file__).resolve().parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

import test_store as _store_tests  # noqa: E402

from session_flow import records, store, views  # noqa: E402

payload = _store_tests.payload
git = _store_tests.git
initialize_repository = _store_tests.initialize_repository
snapshot = _store_tests.snapshot
NAMESPACE = _store_tests.NAMESPACE
FIXTURE_COORDINATOR = _store_tests.FIXTURE_COORDINATOR
GIT_AVAILABLE = _store_tests.GIT_AVAILABLE
NEEDS_GIT = _store_tests.NEEDS_GIT
OLD_MTIME = 946684800  # 2000-01-01, far enough back that any rewrite moves it
VIEW_NAMESPACE = "8c3a1f6e-2d47-4b19-9a05-7e6b1c4d2f80"
OTHER_ITEM = "SEQ-003"
TASK_VIEW = Path("tasks") / "_index.md"


def age(path: Path) -> None:
    os.utime(path, (OLD_MTIME, OLD_MTIME))


def untouched(path: Path) -> bool:
    return int(path.stat().st_mtime) == OLD_MTIME


def written_files(result: dict, request: dict) -> dict:
    """Map each `written` entry to its resolved file, whether its path is absolute or relative."""
    found = {}
    bases = (Path(request["work_root"]), Path(request["project_root"]))
    for entry in result["written"]:
        path = Path(entry["path"])
        candidates = [path] if path.is_absolute() else [base / path for base in bases]
        resolved = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
        found[resolved.resolve()] = entry["digest"]
    return found


# --------------------------------------------------------------------------- A1


def view_request(project_root: Path) -> dict:
    return {
        "protocol": 1,
        "command": "render",
        "project_root": str(project_root),
        "work_root": str(project_root / "work"),
        "sequence_path": str(project_root / "SEQUENCE.md"),
        "namespace": VIEW_NAMESPACE,
        "seq": None,
        "task": None,
        "input": None,
        "config": {},
    }


class A1ViewsTest(unittest.TestCase):
    """Three open items, each holding one task, so each has its own task view."""

    ITEMS = ("SEQ-301", "SEQ-302", "SEQ-303")

    def setUp(self):
        self.project_root = Path(tempfile.mkdtemp(prefix="session-flow-seq031-views-"))
        self.addCleanup(shutil.rmtree, self.project_root, True)
        self.request = view_request(self.project_root)
        self.work = Path(self.request["work_root"])
        self.sequence = Path(self.request["sequence_path"])
        for index, seq in enumerate(self.ITEMS, start=1):
            self.write_item(seq, index, title="Item %d" % index, task_lifecycle="accepted")

    def write_item(self, seq: str, order: int, title: str, task_lifecycle: str) -> None:
        metadata = {
            "format": 1, "namespace": VIEW_NAMESPACE, "seq": seq, "revision": 1,
            "title": title, "lifecycle": "accepted", "order": order, "priority": "P2",
        }
        directory = self.work / seq.lower()
        (directory / "tasks").mkdir(parents=True, exist_ok=True)
        (directory / "intent.md").write_text(
            records.render_record(metadata, "Scope for %s" % seq, ""), encoding="utf-8"
        )
        task = dict(metadata, task="A1", lifecycle=task_lifecycle, title="Task of %s" % seq)
        (directory / "tasks" / "A1.md").write_text(
            records.render_record(task, "Task scope for %s" % seq, ""), encoding="utf-8"
        )

    def task_view(self, seq: str) -> Path:
        return self.work / seq.lower() / TASK_VIEW

    def all_views(self) -> list:
        return [self.sequence] + [self.task_view(seq) for seq in self.ITEMS]

    def age_views(self) -> None:
        for path in self.all_views():
            age(path)

    # write_generated

    def test_a1_write_generated_leaves_an_unchanged_file_untouched_and_says_so(self):
        path = self.project_root / "view.md"
        path.write_text("same text\n", encoding="utf-8")
        age(path)
        wrote = views.write_generated(path, "same text\n")
        self.assertFalse(wrote)
        self.assertTrue(untouched(path), "an unchanged view was rewritten")
        self.assertEqual("same text\n", path.read_text(encoding="utf-8"))

    def test_a1_write_generated_rewrites_changed_text_and_says_so(self):
        path = self.project_root / "view.md"
        path.write_text("old text\n", encoding="utf-8")
        age(path)
        self.assertTrue(views.write_generated(path, "new text\n"))
        self.assertEqual("new text\n", path.read_text(encoding="utf-8"))
        self.assertFalse(untouched(path))

    def test_a1_write_generated_writes_a_missing_file_and_says_so(self):
        path = self.project_root / "fresh.md"
        self.assertTrue(views.write_generated(path, "first text\n"))
        self.assertEqual("first text\n", path.read_text(encoding="utf-8"))

    # render

    def test_a1_render_without_touched_writes_every_view_and_reports_each_with_its_digest(self):
        result = views.render(self.request)
        for key in ("sequence", "generated", "items", "written"):
            self.assertIn(key, result)
        written = written_files(result, self.request)
        expected = {path.resolve() for path in self.all_views()}
        self.assertEqual(expected, set(written))
        for path, digest in written.items():
            with self.subTest(path=str(path)):
                self.assertEqual(records.digest(path.read_text(encoding="utf-8")), digest)

    def test_a1_a_second_render_rewrites_nothing(self):
        views.render(self.request)
        self.age_views()
        result = views.render(self.request)
        self.assertEqual([], result["written"])
        for path in self.all_views():
            with self.subTest(path=str(path)):
                self.assertTrue(untouched(path), "an unchanged view was rewritten")

    def test_a1_touched_renders_only_the_named_items_task_views(self):
        views.render(self.request)
        self.age_views()
        self.write_item("SEQ-301", 1, title="Item 1", task_lifecycle="active")
        self.write_item("SEQ-302", 2, title="Item 2", task_lifecycle="active")
        result = views.render(self.request, touched={"SEQ-301"})
        self.assertFalse(untouched(self.task_view("SEQ-301")), "the touched item's view was not rewritten")
        self.assertIn("SEQ-301/A1 | active |", self.task_view("SEQ-301").read_text(encoding="utf-8"))
        self.assertTrue(untouched(self.task_view("SEQ-302")), "an untouched item's view was rewritten")
        self.assertNotIn("SEQ-302/A1 | active |", self.task_view("SEQ-302").read_text(encoding="utf-8"))
        written = written_files(result, self.request)
        self.assertIn(self.task_view("SEQ-301").resolve(), written)
        self.assertNotIn(self.task_view("SEQ-302").resolve(), written)
        self.assertNotIn(self.task_view("SEQ-303").resolve(), written)

    def test_a1_touched_still_renders_the_sequence(self):
        views.render(self.request)
        self.age_views()
        self.write_item("SEQ-302", 2, title="Renamed second item", task_lifecycle="accepted")
        result = views.render(self.request, touched={"SEQ-301"})
        self.assertIn("Renamed second item", self.sequence.read_text(encoding="utf-8"))
        written = written_files(result, self.request)
        self.assertIn(self.sequence.resolve(), written)
        self.assertEqual(records.digest(self.sequence.read_text(encoding="utf-8")), written[self.sequence.resolve()])
        self.assertTrue(untouched(self.task_view("SEQ-302")))

    def test_a1_an_empty_touched_set_renders_no_task_view(self):
        views.render(self.request)
        self.age_views()
        self.write_item("SEQ-301", 1, title="Item 1", task_lifecycle="active")
        views.render(self.request, touched=set())
        for seq in self.ITEMS:
            with self.subTest(seq=seq):
                self.assertTrue(untouched(self.task_view(seq)))

    def test_a1_the_render_command_still_rewrites_every_changed_view(self):
        views.render(self.request)
        self.age_views()
        self.write_item("SEQ-301", 1, title="Item 1", task_lifecycle="active")
        self.write_item("SEQ-302", 2, title="Item 2", task_lifecycle="active")
        (self.project_root / ".session-flow.json").write_text(
            json.dumps({"paths": {"work": "work", "sequence": "SEQUENCE.md"}}), encoding="utf-8"
        )
        completed = subprocess.run(
            [sys.executable, "-B", str(_store_tests.ENTRYPOINT), "render", "--project-root", str(self.project_root)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        for seq in ("SEQ-301", "SEQ-302"):
            with self.subTest(seq=seq):
                self.assertIn("%s/A1 | active |" % seq, self.task_view(seq).read_text(encoding="utf-8"))
        self.assertTrue(untouched(self.task_view("SEQ-303")))


# ------------------------------------------------------------- shared Git root


class GitRootCase(_store_tests.StoreCase):
    """The store fixture plus a second item with a task, rendered and committed in Git.

    SEQ-001 holds the claim the transition payloads need. SEQ-003 is another item
    whose records and task view an operation on SEQ-001 must leave alone.
    """

    def setUp(self):
        super().setUp()
        self.add_other_item()
        (self.root / ".gitignore").write_text(".state/\n", encoding="utf-8")
        views.render(self.request("render"))
        initialize_repository(self.root)
        self.assertEqual("1", self.commit_count(), "the fixture repository was not created")

    def add_other_item(self) -> None:
        for task in (None, "A1"):
            source = records.read_record(store.record_path(self.root, "SEQ-001", task))
            metadata = dict(source["metadata"], seq=OTHER_ITEM, title="Another session's item")
            metadata.pop(store.CLAIM_FIELD, None)
            target = store.record_path(self.root, OTHER_ITEM, task)
            target.parent.mkdir(parents=True, exist_ok=True)
            records.write_record_file(target, records.render_record(metadata, source["scope"], source["body"]))

    def other_record(self) -> Path:
        return store.record_path(self.root, OTHER_ITEM)

    def edit_other_record(self) -> str:
        path = self.other_record()
        text = path.read_text(encoding="utf-8") + "\nAnother session is still editing this.\n"
        path.write_text(text, encoding="utf-8")
        return text

    def commit_count(self) -> str:
        return git(self.root, "rev-list", "--count", "HEAD").stdout.strip()

    def head_paths(self) -> set:
        output = git(self.root, "show", "--name-only", "--format=", "HEAD").stdout
        return {line for line in output.splitlines() if line.strip()}

    def unstaged_paths(self) -> set:
        return set(git(self.root, "diff", "--name-only").stdout.split())

    def staged_paths(self) -> set:
        return set(git(self.root, "diff", "--cached", "--name-only").stdout.split())

    def committed_text(self, relative: str) -> str:
        return git(self.root, "show", "HEAD:" + relative).stdout

    def assert_only_item_paths(self, paths: set, seq: str) -> None:
        prefix = seq.lower() + "/"
        self.assertTrue(paths, "the commit holds no path")
        self.assertTrue(all(path.startswith(prefix) for path in paths), paths)
        allowed = {prefix + "intent.md", prefix + str(TASK_VIEW).replace(os.sep, "/")}
        self.assertLessEqual(paths, allowed, "the commit holds more than the record and its view")

    def transition_answer(self, document=None) -> dict:
        completed, answer = self.run_cli("transition", document or payload("lifecycle-change.json"))
        self.assertEqual(0, completed.returncode, answer)
        return answer["result"]


@unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
class A1TouchedViewsThroughTransitionTest(GitRootCase):
    """Spec test 8: a transition on one item leaves another item's task view file untouched."""

    def test_a1_a_transition_on_one_item_leaves_another_items_task_view_untouched(self):
        other_view = self.root / OTHER_ITEM.lower() / TASK_VIEW
        self.assertTrue(other_view.is_file(), "the fixture render produced no task view for the other item")
        age(other_view)
        before = other_view.read_bytes()
        self.transition_answer()
        self.assertEqual(before, other_view.read_bytes())
        self.assertTrue(untouched(other_view), "the other item's task view was rewritten")


# --------------------------------------------------------------------------- A2


class A2DoctorReadinessTest(_store_tests.StoreCase):
    """`doctor` reports `storage.commit_readiness`: can this work root be committed, and do its hooks run."""

    KEYS = {"versioned", "git_dir", "git_dir_writable", "hooks_path", "non_executable_hooks"}

    def readiness(self) -> dict:
        completed, answer = self.run_cli("doctor")
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        storage = answer["result"]["storage"]
        self.assertIn("commit_readiness", storage, "doctor reports no commit_readiness section")
        section = storage["commit_readiness"]
        self.assertIsInstance(section, dict, "storage.commit_readiness is not the readiness section")
        self.assertLessEqual(self.KEYS, set(section))
        return section

    def test_a2_storage_work_root_is_still_the_work_root_path(self):
        completed, answer = self.run_cli("doctor")
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertEqual(str(self.root), answer["result"]["storage"]["work_root"])

    def git_directory(self) -> Path:
        return (self.root / ".git").resolve()

    def resolved(self, reported) -> Path:
        path = Path(reported)
        return (path if path.is_absolute() else self.root / path).resolve()

    def hook(self, directory: Path, name: str, mode: int) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        os.chmod(path, mode)

    def test_a2_an_unversioned_root_reports_false_and_nulls(self):
        section = self.readiness()
        self.assertIs(False, section["versioned"])
        self.assertIsNone(section["git_dir"])
        self.assertIsNone(section["git_dir_writable"])
        self.assertIsNone(section["hooks_path"])
        self.assertIn(section["non_executable_hooks"], (None, []))

    @unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
    def test_a2_a_versioned_root_reports_its_git_dir_and_hooks_path(self):
        initialize_repository(self.root)
        section = self.readiness()
        self.assertIs(True, section["versioned"])
        self.assertTrue(Path(section["git_dir"]).is_absolute(), section["git_dir"])
        self.assertEqual(self.git_directory(), Path(section["git_dir"]).resolve())
        self.assertIs(True, section["git_dir_writable"])
        self.assertEqual(self.git_directory() / "hooks", self.resolved(section["hooks_path"]))
        self.assertEqual([], section["non_executable_hooks"])

    @unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
    def test_a2_a_read_only_git_dir_is_reported_not_writable(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root bypasses directory permissions")
        initialize_repository(self.root)
        git_dir = self.git_directory()
        mode = git_dir.stat().st_mode
        os.chmod(git_dir, 0o555)
        self.addCleanup(os.chmod, git_dir, mode)
        if os.access(git_dir, os.W_OK):
            self.skipTest("this filesystem ignores directory permissions")
        section = self.readiness()
        self.assertIs(True, section["versioned"])
        self.assertIs(False, section["git_dir_writable"])

    @unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
    def test_a2_a_non_executable_hook_is_listed_and_samples_are_ignored(self):
        initialize_repository(self.root)
        hooks = self.git_directory() / "hooks"
        self.hook(hooks, "pre-commit", 0o644)
        self.hook(hooks, "post-commit", 0o755)
        self.hook(hooks, "pre-push.sample", 0o644)
        section = self.readiness()
        self.assertEqual(["pre-commit"], section["non_executable_hooks"])

    @unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
    def test_a2_core_hooks_path_is_the_one_reported_and_inspected(self):
        initialize_repository(self.root)
        git(self.root, "config", "core.hooksPath", "custom-hooks")
        custom = self.root / "custom-hooks"
        self.hook(custom, "pre-commit", 0o644)
        self.hook(self.git_directory() / "hooks", "commit-msg", 0o644)
        section = self.readiness()
        self.assertEqual(custom.resolve(), self.resolved(section["hooks_path"]))
        self.assertEqual(["pre-commit"], section["non_executable_hooks"])


# --------------------------------------------------------------------------- A3


@unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
class A3CommitOwnershipTest(GitRootCase):
    """An operation's commit holds exactly the records it wrote and the views it changed."""

    def test_a3_another_items_uncommitted_edit_stays_uncommitted(self):
        original = self.committed_text("seq-003/intent.md")
        edited = self.edit_other_record()
        commit = self.transition_answer()["commit"]
        self.assertTrue(commit["committed"], commit)
        self.assertEqual("2", self.commit_count())
        self.assert_only_item_paths(self.head_paths(), "SEQ-001")
        self.assertIn("seq-003/intent.md", self.unstaged_paths())
        self.assertEqual(original, self.committed_text("seq-003/intent.md"))
        self.assertEqual(edited, self.other_record().read_text(encoding="utf-8"))
        self.assertIn('"lifecycle": "active"', self.committed_text("seq-001/intent.md"))

    def test_a3_a_staged_change_to_another_path_stays_staged_and_out_of_the_commit(self):
        self.edit_other_record()
        git(self.root, "add", "--", "seq-003/intent.md")
        self.assertEqual({"seq-003/intent.md"}, self.staged_paths())
        commit = self.transition_answer()["commit"]
        self.assertTrue(commit["committed"], commit)
        self.assertNotIn("seq-003/intent.md", self.head_paths())
        self.assert_only_item_paths(self.head_paths(), "SEQ-001")
        self.assertEqual({"seq-003/intent.md"}, self.staged_paths())

    def test_a3_a_transition_that_creates_a_record_commits_the_new_file(self):
        self.edit_other_record()
        result = self.transition_answer(payload("new-item.json"))
        self.assertTrue(result["commit"]["committed"], result["commit"])
        created = result["reserved"][0]
        relative = created.lower() + "/intent.md"
        self.assertIn(relative, self.head_paths())
        self.assertIn(created, self.committed_text(relative))
        self.assertEqual("", git(self.root, "status", "--porcelain", "--", relative).stdout)
        self.assertNotIn("seq-003/intent.md", self.head_paths())

    def test_a3_a_file_changed_between_write_and_commit_stops_the_commit_and_is_named(self):
        intent = store.record_path(self.root, "SEQ-001")
        commit_work_root = store.commit_work_root
        interference = "\nWritten by another session after the operation wrote this record.\n"

        def interfere(*arguments, **options):
            intent.write_text(intent.read_text(encoding="utf-8") + interference, encoding="utf-8")
            return commit_work_root(*arguments, **options)

        with mock.patch.object(store, "commit_work_root", side_effect=interfere):
            result = store.transition(self.request("transition", payload("lifecycle-change.json")))
        commit = result["commit"]
        self.assertFalse(commit["committed"], commit)
        self.assertIn("seq-001/intent.md", json.dumps(commit).replace("\\\\", "/"))
        self.assertEqual("1", self.commit_count())
        self.assertTrue(intent.read_text(encoding="utf-8").endswith(interference), "the interfering edit was lost")
        self.assertNotIn('"lifecycle": "active"', self.committed_text("seq-001/intent.md"))

    def test_a3_an_index_lock_leaves_the_records_written_and_a_command_that_commits_them(self):
        lock = self.root / ".git" / "index.lock"
        lock.write_text("", encoding="utf-8")
        commit = self.transition_answer()["commit"]
        self.assertFalse(commit["committed"], commit)
        self.assertLessEqual({"committed", "reason", "paths", "command"}, set(commit))
        self.assertIn("add --", commit["command"])
        self.assertIn("commit -m", commit["command"])
        self.assertEqual("active", self.record_metadata()["lifecycle"])
        self.assertEqual("1", self.commit_count())

        lock.unlink()
        recovered = subprocess.run(commit["command"], shell=True, capture_output=True, text=True, check=False)
        self.assertEqual(0, recovered.returncode, recovered.stdout + recovered.stderr)
        self.assertEqual("2", self.commit_count())
        self.assertIn('"lifecycle": "active"', self.committed_text("seq-001/intent.md"))
        self.assert_only_item_paths(self.head_paths(), "SEQ-001")

    def test_a3_an_index_lock_released_during_the_retries_still_commits(self):
        lock = self.root / ".git" / "index.lock"
        lock.write_text("", encoding="utf-8")
        original = store.run_git
        locked_calls = []
        later_successes = []

        def release_after_first_lock_failure(work_root, arguments):
            outcome = original(work_root, arguments)
            failed = getattr(outcome, "returncode", 1) != 0
            if failed and "index.lock" in str(getattr(outcome, "stderr", "")):
                locked_calls.append(list(arguments))
                if lock.exists():
                    lock.unlink()
            elif locked_calls and list(arguments) == locked_calls[0] and not failed:
                later_successes.append(list(arguments))
            return outcome

        with mock.patch.object(store, "run_git", side_effect=release_after_first_lock_failure):
            result = store.transition(self.request("transition", payload("lifecycle-change.json")))
        self.assertEqual(1, len(locked_calls), locked_calls)
        self.assertEqual(locked_calls[:1], later_successes[:1], "the git call that hit index.lock was not retried")
        self.assertTrue(result["commit"]["committed"], result["commit"])
        self.assertEqual("2", self.commit_count())

    def test_a3_commit_work_root_commits_only_the_expected_paths_inside_the_root(self):
        intent = store.record_path(self.root, "SEQ-001")
        intent.write_text(intent.read_text(encoding="utf-8") + "\nA direct edit.\n", encoding="utf-8")
        outside = self.project / "outside.md"
        outside.write_text("outside the work root\n", encoding="utf-8")
        self.edit_other_record()
        expected = {
            str(intent): records.digest(intent.read_text(encoding="utf-8")),
            str(outside): records.digest(outside.read_text(encoding="utf-8")),
        }
        result = store.commit_work_root(self.root, "Commit one record", expected)
        self.assertTrue(result["committed"], result)
        self.assertEqual({"seq-001/intent.md"}, self.head_paths())
        self.assertIn("seq-003/intent.md", self.unstaged_paths())

    def test_a3_commit_work_root_refuses_a_digest_that_no_longer_matches(self):
        intent = store.record_path(self.root, "SEQ-001")
        written = intent.read_text(encoding="utf-8") + "\nWhat the operation wrote.\n"
        intent.write_text(written + "And what someone added after.\n", encoding="utf-8")
        result = store.commit_work_root(self.root, "Commit one record", {str(intent): records.digest(written)})
        self.assertFalse(result["committed"], result)
        self.assertLessEqual({"committed", "reason", "paths", "command"}, set(result))
        self.assertIn("seq-001/intent.md", json.dumps(result).replace("\\\\", "/"))
        self.assertEqual("1", self.commit_count())
        self.assertIn("And what someone added after.", intent.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- A4


CAPTURE_PAYLOAD = {
    "scope": "A captured item that another session should not see committed with its own work.",
    "body": "## Original request\n\nCapture this under the root lock.",
    "metadata": {"title": "Capture under the root lock"},
}


@unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
class A4SerializedWritesTest(GitRootCase):
    """accept, revise and capture take the root lock and commit only what they wrote."""

    def accept_document(self) -> dict:
        return dict(payload("acceptance.json"), actor=FIXTURE_COORDINATOR, expect_revision=1)

    def revise_document(self) -> dict:
        return {"expect_revision": 1, "metadata": {"priority": "P0"}}

    def capture_arguments(self) -> tuple:
        return ("--seq", "SEQ-004", "--namespace", NAMESPACE)

    def call(self, command: str):
        if command == "accept":
            return self.run_cli("accept", self.accept_document(), "--seq", "SEQ-001")
        if command == "revise":
            return self.run_cli("revise", self.revise_document(), "--seq", "SEQ-001")
        return self.run_cli("capture", CAPTURE_PAYLOAD, *self.capture_arguments())

    def hold_lock(self) -> None:
        ownership = store.acquire_lock(self.root, "session-delegation")
        self.addCleanup(store.release_lock, self.root, ownership)

    def assert_busy(self, command: str) -> None:
        before = snapshot(self.root)
        completed, answer = self.call(command)
        self.assertEqual(1, completed.returncode, completed.stdout)
        self.assertFalse(answer["ok"], answer)
        self.assertEqual("root-busy", answer["error"]["code"], answer["error"]["message"])
        self.assertEqual(before, snapshot(self.root))
        self.assertEqual("1", self.commit_count())

    def assert_own_commit(self, command: str, seq: str) -> dict:
        self.edit_other_record()
        completed, answer = self.call(command)
        self.assertEqual(0, completed.returncode, answer)
        result = answer["result"]
        self.assertIn("views", result)
        self.assertTrue(result["commit"]["committed"], result["commit"])
        self.assertEqual("2", self.commit_count(), "the command did not make exactly one commit")
        self.assertIn(seq.lower() + "/intent.md", self.head_paths())
        self.assert_only_item_paths(self.head_paths(), seq)
        self.assertIn("seq-003/intent.md", self.unstaged_paths())
        self.assertFalse(store.lock_directory(self.root).exists(), "the root lock was not released")
        return result

    def test_a4_accept_is_refused_while_another_holder_has_the_root_lock(self):
        self.hold_lock()
        self.assert_busy("accept")

    def test_a4_revise_is_refused_while_another_holder_has_the_root_lock(self):
        self.hold_lock()
        self.assert_busy("revise")

    def test_a4_capture_is_refused_while_another_holder_has_the_root_lock(self):
        self.hold_lock()
        self.assert_busy("capture")

    def test_a4_accept_makes_one_commit_holding_only_its_record_and_views(self):
        self.assert_own_commit("accept", "SEQ-001")
        self.assertIn('"acceptance"', self.committed_text("seq-001/intent.md"))

    def test_a4_revise_makes_one_commit_holding_only_its_record_and_views(self):
        self.assert_own_commit("revise", "SEQ-001")
        self.assertIn('"priority": "P0"', self.committed_text("seq-001/intent.md"))

    def test_a4_capture_makes_one_commit_holding_only_its_record_and_views(self):
        self.assert_own_commit("capture", "SEQ-004")
        self.assertIn("Capture under the root lock", self.committed_text("seq-004/intent.md"))


if __name__ == "__main__":
    unittest.main()
