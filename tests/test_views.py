"""Sequence import, generated views, and selection eligibility.

The transformation cases assert token fidelity, the applying-import cases assert
that one legacy layout becomes one journalled operation whose round trip is
verified rather than assumed, the render cases assert that generated output is
derived and replaceable, and the select cases assert that a refusal carries its
reason.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = REPO_ROOT / "scripts"
ENTRYPOINT = SCRIPTS_ROOT / "session-flow.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lifecycle" / "views"
LEGACY = REPO_ROOT / "tests" / "fixtures" / "lifecycle" / "repair" / "legacy"
NAMESPACE = "8c3a1f6e-2d47-4b19-9a05-7e6b1c4d2f80"
LEGACY_NAMESPACE = "3f9c8b21-5d64-4e77-8a10-2b6f0c93e5d4"
LEGACY_SOURCE = "_devdocs/todo/SEQUENCE.md"
IMPORTED = ["SEQ-401", "SEQ-402", "SEQ-403", "SEQ-404", "SEQ-405", "SEQ-406"]
HISTORICAL_ONLY = ["SEQ-407", "SEQ-408"]
GIT_AVAILABLE = shutil.which("git") is not None
NEEDS_GIT = "git is required to version the work root"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from session_flow import InvalidIdentityError, RootBusyError  # noqa: E402
from session_flow import records, store, views  # noqa: E402


def sequence_lines(text):
    kept = ("- [", "<!-- session-flow:")
    return [line for line in text.splitlines() if line.startswith(kept)]


def git(root, *arguments):
    return subprocess.run(
        ["git", "-C", str(root), *arguments], capture_output=True, text=True, check=False
    )


def initialize_repository(root):
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "Fixture Coordinator")
    git(root, "add", "-A")
    git(root, "commit", "-m", "The pre-import layout")


def tree(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(Path(root).rglob("*"))
        if path.is_file()
    }


def request_for(project_root, source=None):
    project_root = Path(project_root)
    return {
        "protocol": 1,
        "command": "import",
        "project_root": str(project_root),
        "work_root": str(project_root / "work"),
        "sequence_path": str(project_root / "SEQUENCE.md"),
        "namespace": NAMESPACE,
        "seq": None,
        "task": None,
        "input": None if source is None else {"source": source},
        "config": {},
    }


class SequenceImport(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(tempfile.mkdtemp(prefix="session-flow-import-"))
        self.addCleanup(shutil.rmtree, self.project_root, True)
        for name in ("sequence-mixed.md", "sequence-duplicate.md", "sequence-unclassified.md"):
            shutil.copy(FIXTURES / name, self.project_root / name)
        self.result = views.import_sequence(request_for(self.project_root, "sequence-mixed.md"))
        self.items = {item["metadata"]["seq"]: item["metadata"] for item in self.result["items"]}

    def test_every_identity_and_marker_survives(self):
        self.assertEqual(
            sorted(self.items),
            ["SEQ-101", "SEQ-102", "SEQ-103", "SEQ-104", "SEQ-105", "SEQ-106"],
        )
        self.assertEqual(self.items["SEQ-101"]["lifecycle"], "done")
        self.assertEqual(self.items["SEQ-102"]["lifecycle"], "deferred")
        self.assertEqual(self.items["SEQ-103"]["lifecycle"], "captured")
        self.assertEqual(
            [self.items[seq]["priority"] for seq in ("SEQ-101", "SEQ-104", "SEQ-106")], ["P1", "P2", "P3"]
        )
        self.assertEqual([self.items[seq]["order"] for seq in ("SEQ-101", "SEQ-106")], [1, 6])

    def test_auto_marker_becomes_provenance_not_authority(self):
        self.assertTrue(self.items["SEQ-104"]["provenance"]["auto"])
        self.assertFalse(self.items["SEQ-103"]["provenance"]["auto"])
        self.assertNotIn("acceptance", self.items["SEQ-104"])

    def test_annotations_and_links_survive_with_their_anchors(self):
        self.assertEqual(
            self.items["SEQ-104"]["annotations"],
            ["https://github.com/example/demo/issues/18", "https://www.notion.so/example/abc123"],
        )
        self.assertEqual(self.items["SEQ-103"]["annotations"], ["https://github.com/example/demo/issues/17"])
        self.assertEqual(
            self.items["SEQ-105"]["links"],
            {"breakdown": "todo/2026-08-30-demo-plan.md", "anchor": "2A-1"},
        )
        self.assertTrue(self.items["SEQ-104"]["needs_breakdown"])
        self.assertNotIn("links", self.items["SEQ-104"])
        self.assertNotIn("needs_breakdown", self.items["SEQ-106"])
        self.assertNotIn("links", self.items["SEQ-106"])

    def test_comment_lines_beneath_an_entry_are_kept_escaped(self):
        notes = self.items["SEQ-104"]["notes"]
        self.assertEqual(len(notes), 1)
        self.assertNotIn("<!--", notes[0])
        self.assertIn("escalated to research-design", notes[0])

    def test_every_imported_identity_enters_the_allocation_index(self):
        retired = {entry["seq"]: entry["state"] for entry in self.result["tombstones"]}
        self.assertEqual(sorted(retired), sorted(self.items))
        self.assertEqual(retired["SEQ-101"], "imported")
        self.assertEqual(retired["SEQ-102"], "imported")

    def test_no_record_carries_acceptance_or_a_changed_lifecycle(self):
        for metadata in self.items.values():
            self.assertNotIn("acceptance", metadata)
            self.assertEqual(metadata["revision"], 1)

    def test_import_writes_nothing(self):
        self.assertFalse(self.result["applied"])
        self.assertFalse((self.project_root / "work").exists())
        self.assertEqual(
            sorted(path.name for path in self.project_root.iterdir()),
            ["sequence-duplicate.md", "sequence-mixed.md", "sequence-unclassified.md"],
        )

    def test_duplicate_identity_is_refused(self):
        with self.assertRaises(InvalidIdentityError) as caught:
            views.import_sequence(request_for(self.project_root, "sequence-duplicate.md"))
        self.assertEqual(caught.exception.detail["seq"], "SEQ-201")

    def test_unparsable_entry_is_reported_not_dropped(self):
        result = views.import_sequence(request_for(self.project_root, "sequence-unclassified.md"))
        self.assertEqual([item["metadata"]["seq"] for item in result["items"]], ["SEQ-301"])
        self.assertEqual(len(result["unclassified"]), 1)
        self.assertIn("Tidy the changelog", result["unclassified"][0]["text"])

    def test_survey_without_a_namespace_returns_unbound_previews(self):
        request = request_for(self.project_root, "sequence-mixed.md")
        request["namespace"] = None
        before = tree(self.project_root)
        result = views.import_sequence(request)
        self.assertIsNone(result["namespace"])
        self.assertEqual(len(result["items"]), len(self.result["items"]))
        for item in result["items"]:
            self.assertNotIn("namespace", item["metadata"])
            self.assertIsNone(item["text"])
        self.assertEqual(before, tree(self.project_root))

    def test_apply_still_requires_an_explicit_namespace(self):
        request = request_for(self.project_root, "sequence-mixed.md")
        request["namespace"] = None
        request["input"].update(apply=True, operation="unbound")
        with self.assertRaises(InvalidIdentityError):
            views.import_sequence(request)


class RoundTrip(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(tempfile.mkdtemp(prefix="session-flow-roundtrip-"))
        self.addCleanup(shutil.rmtree, self.project_root, True)
        self.source = self.project_root / "sequence-mixed.md"
        shutil.copy(FIXTURES / "sequence-mixed.md", self.source)
        self.request = request_for(self.project_root, "sequence-mixed.md")
        for item in views.import_sequence(self.request)["items"]:
            path = Path(self.request["work_root"]) / item["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(item["text"], encoding="utf-8")

    def test_the_regenerated_view_matches_the_source_entry_for_entry(self):
        views.render(self.request)
        generated = Path(self.request["sequence_path"]).read_text(encoding="utf-8")
        self.assertEqual(sequence_lines(generated), sequence_lines(self.source.read_text(encoding="utf-8")))

    def test_a_hand_edited_view_is_replaced_by_the_records(self):
        sequence_path = Path(self.request["sequence_path"])
        sequence_path.write_text("- [x] SEQ-999 P1: Hand-written authority\n", encoding="utf-8")
        views.render(self.request)
        regenerated = sequence_path.read_text(encoding="utf-8")
        self.assertNotIn("SEQ-999", regenerated)
        self.assertIn("- [x] SEQ-101 P1: Retire the legacy uploader", regenerated)

    def test_a_dropped_record_drops_its_entry(self):
        (Path(self.request["work_root"]) / "seq-105" / "intent.md").unlink()
        (Path(self.request["work_root"]) / "seq-105").rmdir()
        views.render(self.request)
        self.assertNotIn("SEQ-105", Path(self.request["sequence_path"]).read_text(encoding="utf-8"))


class GeneratedTaskViews(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(tempfile.mkdtemp(prefix="session-flow-render-"))
        self.addCleanup(shutil.rmtree, self.project_root, True)
        shutil.copytree(FIXTURES / "work", self.project_root / "work")
        self.request = request_for(self.project_root)
        self.result = views.render(self.request)

    def test_counts_and_indexes_are_derived_not_stored(self):
        view = (self.project_root / "work" / "seq-202" / "tasks" / "_index.md").read_text(encoding="utf-8")
        self.assertIn("2 tasks, 1 done.", view)
        self.assertIn("| 1 | SEQ-202/A1 | done |", view)
        self.assertIn("| 2 | SEQ-202/A2 | active |", view)
        for name in ("A1.md", "A2.md"):
            record = (self.project_root / "work" / "seq-202" / "tasks" / name).read_text(encoding="utf-8")
            self.assertNotIn("index", record)
            self.assertNotIn("task_counts", record)

    def test_only_items_holding_tasks_get_a_task_view(self):
        generated = {Path(path).name for path in self.result["generated"]}
        self.assertEqual(generated, {"SEQUENCE.md", "_index.md"})
        self.assertFalse((self.project_root / "work" / "seq-201" / "tasks").exists())

    def test_the_task_view_never_occupies_a_task_identity(self):
        from session_flow import records

        with self.assertRaises(records.InvalidIdentityError):
            records.parse_task_id("_index")


class Selection(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(tempfile.mkdtemp(prefix="session-flow-select-"))
        self.addCleanup(shutil.rmtree, self.project_root, True)
        shutil.copytree(FIXTURES / "work", self.project_root / "work")
        self.request = request_for(self.project_root)
        self.result = views.select(self.request)
        self.reasons = {entry["seq"]: entry for entry in self.result["considered"]}

    def test_a_manual_entry_outranks_an_auto_entry_of_the_same_priority(self):
        self.assertEqual(self.result["candidate"]["seq"], "SEQ-207")
        self.assertTrue(self.reasons["SEQ-206"]["eligible"])

    def test_captured_deferred_and_cancelled_work_is_refused_with_a_reason(self):
        for seq, state in (("SEQ-201", "captured"), ("SEQ-204", "deferred"), ("SEQ-205", "cancelled")):
            entry = self.reasons[seq]
            self.assertFalse(entry["eligible"], seq)
            self.assertTrue(any(state in reason for reason in entry["reasons"]), entry)

    def test_a_breakdown_link_alone_confers_no_eligibility(self):
        entry = self.reasons["SEQ-201"]
        self.assertFalse(entry["eligible"])
        self.assertTrue(any("link alone" in reason for reason in entry["reasons"]), entry)

    def test_stale_scope_is_refused_with_both_fingerprints(self):
        from session_flow import records

        record = records.read_record(self.project_root / "work" / "seq-203" / "intent.md")
        entry = self.reasons["SEQ-203"]
        self.assertFalse(entry["eligible"])
        reason = " ".join(entry["reasons"])
        self.assertIn(record["metadata"]["acceptance"]["fingerprint"], reason)
        self.assertIn(records.scope_fingerprint(record), reason)
        self.assertNotEqual(
            record["metadata"]["acceptance"]["fingerprint"], records.scope_fingerprint(record)
        )

    def test_an_item_awaiting_a_breakdown_is_refused(self):
        entry = self.reasons["SEQ-208"]
        self.assertFalse(entry["eligible"])
        self.assertTrue(any("needs breakdown" in reason for reason in entry["reasons"]), entry)

    def test_selecting_one_ineligible_identity_returns_no_candidate(self):
        request = dict(self.request, seq="SEQ-201")
        result = views.select(request)
        self.assertIsNone(result["candidate"])
        self.assertEqual(result["eligible"], 0)
        self.assertEqual([entry["seq"] for entry in result["considered"]], ["SEQ-201"])

    def test_select_reports_the_candidate_task_state_without_starting_it(self):
        result = views.select(dict(self.request, seq="SEQ-202"))
        candidate = result["candidate"]
        self.assertEqual(candidate["task_counts"], {"total": 2, "done": 1})
        self.assertEqual([task["task"] for task in candidate["tasks"]], ["A1", "A2"])
        self.assertNotIn("command", candidate)


class Boundary(unittest.TestCase):
    def test_select_answers_through_the_entrypoint(self):
        project_root = Path(tempfile.mkdtemp(prefix="session-flow-boundary-"))
        self.addCleanup(shutil.rmtree, project_root, True)
        shutil.copytree(FIXTURES / "work", project_root / "work")
        (project_root / ".session-flow.json").write_text(
            json.dumps({"paths": {"work": "work", "sequence": "SEQUENCE.md"}}), encoding="utf-8"
        )
        completed = subprocess.run(
            [sys.executable, "-B", str(ENTRYPOINT), "select", "--project-root", str(project_root),
             "--namespace", NAMESPACE],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        body = json.loads(completed.stdout)
        self.assertTrue(body["ok"], body)
        self.assertEqual(body["result"]["candidate"]["seq"], "SEQ-207")



@unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
class LegacyImport(unittest.TestCase):
    """A copy of the legacy fixture repository, committed as its pre-import self."""

    def setUp(self):
        directory = tempfile.mkdtemp(prefix="session-flow-repair-")
        self.addCleanup(shutil.rmtree, directory, True)
        self.project = Path(directory)
        shutil.copytree(LEGACY, self.project, dirs_exist_ok=True)
        self.work = self.project / "_devdocs" / "work"
        self.source = self.project / LEGACY_SOURCE
        self.archive = self.project / "_devdocs" / "todo"
        initialize_repository(self.project)

    def request(self, **payload):
        return {
            "protocol": 1,
            "command": "import",
            "project_root": str(self.project),
            "work_root": str(self.work),
            "sequence_path": str(self.project / "_devdocs" / "SEQUENCE.md"),
            "namespace": LEGACY_NAMESPACE,
            "seq": None,
            "task": None,
            "input": payload or None,
            "config": json.loads((self.project / ".session-flow.json").read_text(encoding="utf-8")),
        }

    def apply(self, operation="import-0001"):
        return views.import_sequence(
            self.request(operation=operation, source=LEGACY_SOURCE, apply=True)
        )

    def commits(self):
        return git(self.project, "rev-list", "--count", "HEAD").stdout.strip()

    def item_directories(self):
        return sorted(path.name for path in self.work.glob("seq-*"))

    def retired(self):
        return {entry["seq"]: entry for entry in store.read_tombstones(self.work)["entries"]}


class ImportPlan(LegacyImport):
    def setUp(self):
        super().setUp()
        self.plan = views.import_sequence(self.request(source=LEGACY_SOURCE))

    def test_the_plan_writes_nothing(self):
        self.assertFalse(self.plan["applied"])
        self.assertEqual(self.item_directories(), [])
        self.assertEqual(git(self.project, "status", "--porcelain").stdout, "")

    def test_the_plan_names_every_identity_the_survey_saw(self):
        self.assertEqual([item["metadata"]["seq"] for item in self.plan["items"]], IMPORTED)
        retired = {entry["seq"]: entry["state"] for entry in self.plan["tombstones"]}
        self.assertEqual(sorted(retired), IMPORTED + HISTORICAL_ONLY)
        for seq in HISTORICAL_ONLY:
            self.assertEqual(retired[seq], "historical")

    def test_an_unclassifiable_row_is_reported_and_refuses_the_apply(self):
        with self.source.open("a", encoding="utf-8") as handle:
            handle.write("- [~] SEQ-410 P1: A marker this grammar does not define\n")
        plan = views.import_sequence(self.request(source=LEGACY_SOURCE))
        self.assertEqual(len(plan["unclassified"]), 1)
        with self.assertRaises(InvalidIdentityError) as caught:
            self.apply()
        self.assertIn("cannot classify", str(caught.exception))
        self.assertEqual(self.item_directories(), [])

    def test_a_link_that_resolves_to_nothing_refuses_the_apply(self):
        (self.archive / "tasks" / "0403-fix-retry-backoff.md").unlink()
        plan = views.import_sequence(self.request(source=LEGACY_SOURCE))
        self.assertEqual([entry["seq"] for entry in plan["unresolved_links"]], ["SEQ-403"])
        with self.assertRaises(InvalidIdentityError):
            self.apply()
        self.assertEqual(self.item_directories(), [])


class ImportApplied(LegacyImport):
    def setUp(self):
        super().setUp()
        self.before = tree(self.archive)
        self.result = self.apply()

    def test_every_entry_becomes_one_record_under_one_commit(self):
        self.assertEqual(self.result["imported"], IMPORTED)
        self.assertEqual(self.item_directories(), [seq.lower() for seq in IMPORTED])
        self.assertEqual(self.commits(), "2")
        self.assertTrue(self.result["operation"]["commit"]["committed"])

    def test_the_operation_is_journalled_and_marked_applied(self):
        document = store.load_operation(self.work, "import-0001")
        self.assertEqual(document["state"], "applied")
        self.assertEqual(document["command"], "import")

    def test_every_annotation_and_marker_survives_verbatim(self):
        generated = (self.project / "_devdocs" / "SEQUENCE.md").read_text(encoding="utf-8")
        self.assertEqual(
            sequence_lines(generated), sequence_lines(self.source.read_text(encoding="utf-8"))
        )

    def test_the_round_trip_comparison_is_what_reports_success(self):
        self.assertEqual(self.result["verification"], {
            "verified": True, "entries": len(IMPORTED), "source": str(self.source)
        })

    def test_every_identity_is_retired_and_none_is_reallocated(self):
        retired = self.retired()
        self.assertEqual(sorted(retired), IMPORTED + HISTORICAL_ONLY)
        for seq in HISTORICAL_ONLY:
            self.assertEqual(retired[seq]["state"], "historical")
        self.assertEqual(store.next_item_id(self.work), "SEQ-409")

    def test_lifecycle_is_carried_across_and_nothing_is_completed(self):
        states = {}
        for seq in IMPORTED:
            record = records.read_record(self.work / seq.lower() / "intent.md")
            states[seq] = record["metadata"]["lifecycle"]
            self.assertNotIn("acceptance", record["metadata"])
            self.assertEqual(record["metadata"]["revision"], 1)
        self.assertEqual(states["SEQ-401"], "done")
        self.assertEqual(states["SEQ-402"], "deferred")
        self.assertEqual(states["SEQ-403"], "captured")
        self.assertTrue(records.read_record(self.work / "seq-404" / "intent.md")["metadata"]
                        ["provenance"]["auto"])

    def test_no_historical_file_is_moved_renamed_or_rewritten(self):
        self.assertEqual(tree(self.archive), self.before)
        self.assertTrue(self.source.is_file())

    def test_a_second_run_finds_nothing_to_do(self):
        second = self.apply(operation="import-0002")
        self.assertFalse(second["operation"]["changed"])
        self.assertEqual(second["operation"]["records"], [])
        self.assertIsNone(store.load_operation(self.work, "import-0002"))
        self.assertEqual(self.commits(), "2")
        self.assertEqual(self.retired().keys(), self.retired().keys())

    def test_retrying_the_same_operation_returns_its_prior_result(self):
        self.assertTrue(self.apply()["operation"]["replayed"])
        self.assertEqual(self.commits(), "2")


class ImportRecovery(LegacyImport):
    def interrupt(self):
        with unittest.mock.patch.object(
            store, "apply_planned_changes", side_effect=RuntimeError("the coordinator was killed")
        ):
            with self.assertRaises(RuntimeError):
                self.apply()

    def test_an_interrupted_run_resumes_from_the_journal(self):
        self.interrupt()
        self.assertEqual(self.item_directories(), [])
        self.assertEqual(store.load_operation(self.work, "import-0001")["state"], "prepared")
        resumed = self.apply()
        self.assertTrue(resumed["operation"]["resumed"])
        self.assertTrue(resumed["verification"]["verified"])
        self.assertEqual(self.item_directories(), [seq.lower() for seq in IMPORTED])
        self.assertEqual(store.next_item_id(self.work), "SEQ-409")

    def test_a_prepared_operation_blocks_a_different_one(self):
        self.interrupt()
        with self.assertRaises(RootBusyError) as caught:
            self.apply(operation="import-0002")
        self.assertIn("reconcile", str(caught.exception))
        self.assertEqual(self.item_directories(), [])

    def test_a_corrupted_import_fails_the_round_trip_and_names_the_commit(self):
        faithful = views.imported_item

        def without_annotations(entry, namespace, source, project_root):
            item = faithful(entry, namespace, source, project_root)
            item["metadata"].pop("annotations", None)
            item["text"] = views.render_record(item["metadata"], entry["title"], "")
            return item

        with unittest.mock.patch.object(views, "imported_item", without_annotations):
            with self.assertRaises(InvalidIdentityError) as caught:
                self.apply()
        failure = caught.exception
        self.assertEqual(failure.detail["mismatch"]["field"], "annotations")
        self.assertEqual(failure.detail["commit"], git(self.work, "rev-parse", "HEAD").stdout.strip())
        self.assertIn("revert that commit", str(failure))

    def assert_refused_before_writing(self):
        with self.assertRaises(InvalidIdentityError):
            self.apply()
        self.assertEqual(self.item_directories(), [])
        self.assertFalse(store.lock_directory(self.work).exists())

    def test_an_unversioned_work_root_stops_the_run(self):
        shutil.rmtree(self.project / ".git")
        self.assert_refused_before_writing()

    def test_an_uncommitted_project_tree_stops_the_run(self):
        (self.project / "README.md").write_text("uncommitted\n", encoding="utf-8")
        self.assert_refused_before_writing()

    def test_an_uncommitted_work_root_stops_the_run(self):
        (self.work / "notes.md").write_text("uncommitted\n", encoding="utf-8")
        self.assert_refused_before_writing()

    def test_a_lock_held_by_another_coordinator_stops_the_run(self):
        store.lock_directory(self.work).mkdir(parents=True)
        store.write_json(
            store.owner_path(self.work),
            {"host": "elsewhere", "coordinator": "another-session", "pid": 1, "token": "held"},
        )
        with self.assertRaises(RootBusyError):
            self.apply()
        self.assertEqual(self.item_directories(), [])


class ImportBoundary(LegacyImport):
    """The dispatch-table entry, exercised the way a host invokes it."""

    def test_the_apply_route_answers_through_the_entrypoint(self):
        payload = Path(tempfile.mkdtemp(prefix="session-flow-payload-"))
        self.addCleanup(shutil.rmtree, payload, True)
        document = payload / "import.json"
        document.write_text(
            json.dumps({"operation": "import-cli", "source": LEGACY_SOURCE, "apply": True}),
            encoding="utf-8",
        )
        completed = subprocess.run(
            [sys.executable, "-B", str(ENTRYPOINT), "import", "--project-root", str(self.project),
             "--namespace", LEGACY_NAMESPACE, "--input", str(document)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        body = json.loads(completed.stdout)
        self.assertTrue(body["ok"], body)
        self.assertEqual(body["result"]["imported"], IMPORTED)
        self.assertTrue(body["result"]["verification"]["verified"])
        self.assertEqual(self.item_directories(), [seq.lower() for seq in IMPORTED])


if __name__ == "__main__":
    unittest.main()
