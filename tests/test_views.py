"""Sequence import, generated views, and selection eligibility.

The import cases assert token fidelity, the render cases assert that generated
output is derived and replaceable, and the select cases assert that a refusal
carries its reason.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = REPO_ROOT / "scripts"
ENTRYPOINT = SCRIPTS_ROOT / "session-flow.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lifecycle" / "views"
NAMESPACE = "8c3a1f6e-2d47-4b19-9a05-7e6b1c4d2f80"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from session_flow import InvalidIdentityError  # noqa: E402
from session_flow import views  # noqa: E402


def sequence_lines(text):
    kept = ("- [", "<!-- session-flow:")
    return [line for line in text.splitlines() if line.startswith(kept)]


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
        self.assertEqual(self.result["tombstones"], sorted(self.items))
        self.assertIn("SEQ-101", self.result["tombstones"])
        self.assertIn("SEQ-102", self.result["tombstones"])

    def test_no_record_carries_acceptance_or_a_changed_lifecycle(self):
        for metadata in self.items.values():
            self.assertNotIn("acceptance", metadata)
            self.assertEqual(metadata["revision"], 1)

    def test_import_writes_nothing(self):
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

    def test_import_without_a_namespace_is_refused(self):
        request = request_for(self.project_root, "sequence-mixed.md")
        request["namespace"] = None
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


if __name__ == "__main__":
    unittest.main()
