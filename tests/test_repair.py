"""Repair scenarios: what the repository looks like around each `/session-repair` stage.

`test_views` proves the transformation itself. These checks drive the entrypoint the
way the skill does — one process per stage, reading the response body — and assert the
state around it: that a refusal leaves the work root exactly as it found it, that the
read-only stages change no byte and no Git status, that the integrity rules hold on a
committed fixture repository, and that reconcile mode reports drift rather than
correcting it.

Two checks reach past the entrypoint on purpose. An interruption and a corrupted
transformation cannot be provoked from outside the process, so both are staged
in-process and then observed from the outside: the interrupted run is resumed through
the entrypoint, and the corrupted one is caught by the round-trip comparison.
"""

import json
import re
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
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lifecycle" / "repair"
LEGACY = FIXTURES / "legacy"
DRIFTED = FIXTURES / "drifted"
LEGACY_NAMESPACE = "3f9c8b21-5d64-4e77-8a10-2b6f0c93e5d4"
DRIFTED_NAMESPACE = "b17a5c30-9e42-4d6b-8f01-3c5d2a7e6b94"
LEGACY_SOURCE = "_devdocs/todo/SEQUENCE.md"
IMPORTED = ["SEQ-401", "SEQ-402", "SEQ-403", "SEQ-404", "SEQ-405", "SEQ-406"]
HISTORICAL_ONLY = ["SEQ-407", "SEQ-408"]
ENTRY_LINE_RE = re.compile(r"^- \[(?P<marker> |x|DEFERRED)\] (?P<seq>SEQ-[0-9]{3,6})\b")
ANNOTATION_RE = re.compile(r" ⇄ (\S+)")
GIT_AVAILABLE = shutil.which("git") is not None
NEEDS_GIT = "git is required to version the work root"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from session_flow import InvalidIdentityError  # noqa: E402
from session_flow import records, store, views  # noqa: E402


def git(root, *arguments):
    return subprocess.run(
        ["git", "-C", str(root), *arguments], capture_output=True, text=True, check=False
    )


def initialize_repository(root):
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "Fixture Coordinator")
    git(root, "add", "-A")
    git(root, "commit", "-m", "The layout as the repair run finds it")


def tree(root):
    root = Path(root)
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.parts
    }


def entry_lines(text):
    return [line for line in text.splitlines() if ENTRY_LINE_RE.match(line)]


def annotations_in(text):
    return sorted(ANNOTATION_RE.findall(text))


def marked_done(text):
    return sorted(
        match.group("seq")
        for match in (ENTRY_LINE_RE.match(line) for line in text.splitlines())
        if match and match.group("marker") == "x"
    )


@unittest.skipUnless(GIT_AVAILABLE, NEEDS_GIT)
class RepairRun(unittest.TestCase):
    """A copy of a fixture repository, committed as the repair run finds it."""

    fixture = LEGACY
    namespace = LEGACY_NAMESPACE

    def setUp(self):
        directory = tempfile.mkdtemp(prefix="session-flow-repair-")
        self.addCleanup(shutil.rmtree, directory, True)
        self.project = Path(directory)
        shutil.copytree(self.fixture, self.project, dirs_exist_ok=True)
        self.work = self.project / "_devdocs" / "work"
        self.sequence = self.project / "_devdocs" / "SEQUENCE.md"
        initialize_repository(self.project)

    def cli(self, command, payload=None, namespace=True):
        arguments = [sys.executable, "-B", str(ENTRYPOINT), "--project-root", str(self.project)]
        if namespace:
            arguments += ["--namespace", self.namespace]
        if payload is not None:
            document = self.project.parent / f"{self.project.name}-{payload['operation']}.json"
            document.write_text(json.dumps(payload), encoding="utf-8")
            self.addCleanup(document.unlink, True)
            arguments += ["--input", str(document)]
        completed = subprocess.run(arguments + [command], capture_output=True, text=True)
        return completed, json.loads(completed.stdout)

    def storage(self):
        return self.cli("doctor", namespace=False)[1]["result"]["storage"]

    def status(self):
        return git(self.project, "status", "--porcelain").stdout

    def commits(self):
        return git(self.project, "rev-list", "--count", "HEAD").stdout.strip()

    def item_directories(self):
        return sorted(path.name for path in self.work.glob("seq-*"))

    def retired(self):
        return {entry["seq"]: entry["state"] for entry in store.read_tombstones(self.work)["entries"]}


class LegacyRepair(RepairRun):
    """The migrate entry condition: a legacy layout that has never been imported."""

    def payload(self, operation="repair-0001", **extra):
        return dict(
            {
                "operation": operation,
                "coordinator": "session-repair",
                "source": LEGACY_SOURCE,
            },
            **extra,
        )

    def survey(self):
        return self.cli("import", self.payload())[1]

    def apply(self, operation="repair-0001", **extra):
        return self.cli("import", self.payload(operation, apply=True, **extra))

    def source_text(self):
        return (self.project / LEGACY_SOURCE).read_text(encoding="utf-8")

    def record_metadata(self, seq):
        return records.read_record(self.work / seq.lower() / "intent.md")["metadata"]


class ReadOnlyStages(LegacyRepair):
    """Stages 1 and 3 report; neither is allowed to change a byte."""

    def setUp(self):
        super().setUp()
        self.before = tree(self.project)

    def test_the_survey_stage_writes_nothing(self):
        body = self.survey()
        self.assertTrue(body["ok"], body)
        self.assertFalse(body["result"]["applied"])
        self.assertEqual(self.status(), "")
        self.assertEqual(tree(self.project), self.before)
        self.assertFalse((self.work / ".state").exists())

    def test_the_survey_names_every_identity_annotation_and_link_it_saw(self):
        result = self.survey()["result"]
        self.assertEqual([item["metadata"]["seq"] for item in result["items"]], IMPORTED)
        retired = {entry["seq"]: entry["state"] for entry in result["tombstones"]}
        self.assertEqual(sorted(retired), IMPORTED + HISTORICAL_ONLY)
        self.assertEqual([retired[seq] for seq in HISTORICAL_ONLY], ["historical", "historical"])
        self.assertEqual(result["unclassified"], [])
        self.assertEqual(result["unresolved_links"], [])
        found = [url for item in result["items"] for url in item["metadata"].get("annotations", [])]
        self.assertEqual(sorted(found), annotations_in(self.source_text()))

    def test_the_plan_stage_writes_nothing_and_names_each_target_directory(self):
        result = self.survey()["result"]
        self.assertEqual(
            [item["path"] for item in result["items"]],
            [f"{seq.lower()}/intent.md" for seq in IMPORTED],
        )
        self.assertEqual(self.status(), "")
        self.assertEqual(tree(self.project), self.before)
        self.assertEqual(self.item_directories(), [])


class RefusalsBeforeTheFirstWrite(LegacyRepair):
    """Stage 2 stops on unsafe ground, and nothing clears a refusal but fixing it."""

    def refuse(self, **extra):
        """Apply against ground Stage 2 must reject, from a recorded pre-run baseline."""
        self.baseline = self.commits()
        return self.apply(**extra)

    def assert_refused(self, completed, body, code, clearing):
        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertFalse(body["ok"], body)
        self.assertEqual(body["error"]["code"], code)
        self.assertIn(clearing, body["error"]["message"])
        self.assertEqual(self.item_directories(), [])
        self.assertFalse(store.tombstones_path(self.work).exists())
        self.assertFalse(self.sequence.exists())
        self.assertEqual(self.commits(), self.baseline)

    def test_a_work_root_that_is_not_a_git_repository_stops_the_run(self):
        shutil.rmtree(self.project / ".git")
        self.assertFalse(self.storage()["versioned"])
        completed, body = self.refuse()
        self.assert_refused(completed, body, "invalid-identity", "init -b main")

    def test_an_uncommitted_project_tree_stops_the_run(self):
        (self.project / "README.md").write_text("uncommitted\n", encoding="utf-8")
        completed, body = self.refuse()
        self.assert_refused(completed, body, "invalid-identity", "status")
        self.assertEqual(body["error"]["detail"]["uncommitted"], ["README.md"])

    def test_an_uncommitted_work_root_stops_the_run(self):
        (self.work / "notes.md").write_text("uncommitted\n", encoding="utf-8")
        completed, body = self.refuse()
        self.assert_refused(completed, body, "invalid-identity", "status")
        self.assertIn("work root", body["error"]["message"])

    def test_an_unapplied_journal_operation_stops_a_different_run(self):
        interrupt(self)
        self.assertEqual(self.storage()["pending_operations"], ["repair-0001"])
        completed, body = self.refuse(operation="repair-0002")
        self.assert_refused(completed, body, "root-busy", "reconcile")

    def test_a_lock_held_by_another_coordinator_stops_the_run(self):
        store.lock_directory(self.work).mkdir(parents=True)
        store.write_json(
            store.owner_path(self.work),
            {"host": "elsewhere", "coordinator": "another-session", "pid": 1, "token": "held"},
        )
        self.assertTrue(self.storage()["locked"])
        completed, body = self.refuse()
        self.assert_refused(completed, body, "root-busy", "another-session")

    def test_an_unclassifiable_shape_is_reported_and_stops_the_run(self):
        with (self.project / LEGACY_SOURCE).open("a", encoding="utf-8") as handle:
            handle.write("- [~] SEQ-410 P1: A marker this grammar does not define\n")
        git(self.project, "commit", "-am", "A row the grammar does not define")
        survey = self.survey()["result"]
        self.assertEqual(len(survey["unclassified"]), 1)
        self.assertIn("SEQ-410", survey["unclassified"][0]["text"])
        completed, body = self.refuse()
        self.assert_refused(completed, body, "invalid-identity", "sequence-grammar.md")

    def test_no_force_clears_a_refusal(self):
        (self.project / "README.md").write_text("uncommitted\n", encoding="utf-8")
        completed, body = self.refuse(force=True)
        self.assert_refused(completed, body, "invalid-identity", "commit or stash")
        rejected = subprocess.run(
            [sys.executable, "-B", str(ENTRYPOINT), "--project-root", str(self.project),
             "--force", "import"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("unrecognized arguments", rejected.stderr)


class IntegrityRules(LegacyRepair):
    """What Stage 4 must carry across, and what it must leave alone."""

    def setUp(self):
        super().setUp()
        self.archive_before = tree(self.project / "_devdocs" / "todo")
        completed, self.body = self.apply()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.result = self.body["result"]

    def test_the_import_lands_as_one_journalled_commit(self):
        self.assertEqual(self.result["imported"], IMPORTED)
        self.assertEqual(self.commits(), "2")
        self.assertEqual(store.load_operation(self.work, "repair-0001")["state"], "applied")
        self.assertTrue(self.result["verification"]["verified"])

    def test_every_identity_ever_seen_is_retired_and_none_is_reallocated(self):
        self.assertEqual(sorted(self.retired()), IMPORTED + HISTORICAL_ONLY)
        for seq in HISTORICAL_ONLY:
            self.assertEqual(self.retired()[seq], "historical")
        self.assertEqual(store.next_item_id(self.work), "SEQ-409")

    def test_every_annotation_and_marker_survives_verbatim(self):
        source = self.source_text()
        self.assertEqual(
            entry_lines(self.sequence.read_text(encoding="utf-8")), entry_lines(source)
        )
        stored = [
            url
            for seq in IMPORTED
            for url in self.record_metadata(seq).get("annotations", [])
        ]
        self.assertEqual(sorted(stored), annotations_in(source))
        self.assertTrue(self.record_metadata("SEQ-404")["provenance"]["auto"])
        self.assertFalse(self.record_metadata("SEQ-403")["provenance"]["auto"])

    def test_no_historical_file_is_moved_renamed_or_renumbered(self):
        self.assertEqual(tree(self.project / "_devdocs" / "todo"), self.archive_before)
        self.assertTrue((self.project / LEGACY_SOURCE).is_file())

    def test_nothing_external_is_created_and_nothing_is_completed(self):
        source = self.source_text()
        done = [seq for seq in IMPORTED if self.record_metadata(seq)["lifecycle"] == "done"]
        self.assertEqual(done, marked_done(source))
        self.assertEqual(self.record_metadata("SEQ-402")["lifecycle"], "deferred")
        for seq in IMPORTED:
            metadata = self.record_metadata(seq)
            self.assertNotIn("acceptance", metadata)
            self.assertNotIn("claim", metadata)
            self.assertNotIn("result", metadata)
        self.assertEqual(
            annotations_in(self.sequence.read_text(encoding="utf-8")), annotations_in(source)
        )


class IdempotenceAndResumption(LegacyRepair):
    def test_a_second_run_finds_nothing_to_do(self):
        self.apply()
        applied = tree(self.work)
        completed, body = self.apply(operation="repair-0002")
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertFalse(body["result"]["operation"]["changed"])
        self.assertIn("wrote nothing", body["result"]["operation"]["reason"])
        self.assertIsNone(store.load_operation(self.work, "repair-0002"))
        self.assertEqual(self.commits(), "2")
        self.assertEqual(tree(self.work), applied)

    def test_an_interrupted_run_resumes_from_the_journal(self):
        interrupt(self)
        self.assertEqual(self.item_directories(), [])
        self.assertEqual(store.load_operation(self.work, "repair-0001")["state"], "prepared")
        completed, body = self.apply()
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertTrue(body["result"]["operation"]["resumed"])
        self.assertTrue(body["result"]["verification"]["verified"])
        self.assertEqual(self.item_directories(), [seq.lower() for seq in IMPORTED])
        self.assertEqual(sorted(self.retired()), IMPORTED + HISTORICAL_ONLY)


def in_process_request(case, payload):
    return {
        "protocol": 1,
        "command": "import",
        "project_root": str(case.project),
        "work_root": str(case.work),
        "sequence_path": str(case.sequence),
        "namespace": case.namespace,
        "seq": None,
        "task": None,
        "input": payload,
        "config": json.loads((case.project / ".session-flow.json").read_text(encoding="utf-8")),
    }


def interrupt(case):
    """Kill one apply between its journal entry and its first record write."""
    request = in_process_request(case, case.payload(apply=True))
    with unittest.mock.patch.object(
        store, "apply_planned_changes", side_effect=RuntimeError("the coordinator was killed")
    ):
        with case.assertRaises(RuntimeError):
            views.import_sequence(request)


class RoundTripVerification(LegacyRepair):
    """Stage 5 decides success, and it decides it by comparison."""

    def corrupt_import(self, damage):
        faithful = views.imported_item

        def damaged(entry, namespace, source, project_root):
            item = faithful(entry, namespace, source, project_root)
            damage(item)
            item["text"] = records.render_record(item["metadata"], entry["title"], "")
            return item

        request = in_process_request(self, self.payload(apply=True))
        with unittest.mock.patch.object(views, "imported_item", damaged):
            with self.assertRaises(InvalidIdentityError) as caught:
                views.import_sequence(request)
        return caught.exception

    def test_a_dropped_provenance_marker_fails_the_comparison(self):
        failure = self.corrupt_import(
            lambda item: item["metadata"]["provenance"].update({"auto": False})
        )
        self.assertEqual(failure.detail["mismatch"]["field"], "auto")
        self.assertEqual(failure.detail["mismatch"]["seq"], "SEQ-404")

    def test_a_dropped_annotation_fails_the_comparison(self):
        failure = self.corrupt_import(lambda item: item["metadata"].pop("annotations", None))
        self.assertEqual(failure.detail["mismatch"]["field"], "annotations")

    def test_the_failure_names_the_commit_to_revert_rather_than_reporting_success(self):
        failure = self.corrupt_import(lambda item: item["metadata"].pop("links", None))
        self.assertEqual(self.commits(), "2")
        self.assertEqual(
            failure.detail["commit"], git(self.work, "rev-parse", "HEAD").stdout.strip()
        )
        self.assertIn("revert that commit", str(failure))


class ReconcileDrift(RepairRun):
    """The reconcile entry condition: a current layout whose views and index have drifted."""

    fixture = DRIFTED
    namespace = DRIFTED_NAMESPACE

    def sequence_ids(self):
        text = self.sequence.read_text(encoding="utf-8")
        return [ENTRY_LINE_RE.match(line).group("seq") for line in entry_lines(text)]

    def claim_of(self, seq):
        return records.read_record(self.work / seq.lower() / "intent.md")["metadata"]["claim"]

    def test_the_survey_names_each_drift_it_found(self):
        self.assertEqual(self.item_directories(), ["seq-501", "seq-502", "seq-503"])
        self.assertEqual(self.sequence_ids(), ["SEQ-501", "SEQ-502", "SEQ-504"])
        self.assertNotIn("SEQ-503", self.retired())
        self.assertEqual(self.claim_of("SEQ-502")["actor"], "agent:another-session")
        self.assertIn("no record says so", self.sequence.read_text(encoding="utf-8"))

    def test_render_repairs_the_derived_view_and_git_holds_both_versions(self):
        completed, body = self.cli("render")
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertEqual(body["result"]["items"], 3)
        self.assertEqual(self.sequence_ids(), ["SEQ-501", "SEQ-502", "SEQ-503"])
        diff = git(self.project, "diff", "--", str(self.sequence)).stdout
        self.assertIn("-- [ ] SEQ-504", diff)
        self.assertIn("-<!-- security review wants this", diff)
        self.assertIn("+- [ ] SEQ-503", diff)

    def test_render_changes_no_record(self):
        before = tree(self.work)
        self.cli("render")
        self.assertEqual(tree(self.work), before)

    def test_a_stale_claim_is_never_reassigned_by_a_repair(self):
        before = self.claim_of("SEQ-502")
        self.cli("render")
        self.cli("reconcile", {"operation": "repair-reconcile", "coordinator": "session-repair"})
        self.assertEqual(self.claim_of("SEQ-502"), before)

    def test_a_missing_tombstone_is_reported_not_invented(self):
        self.cli("render")
        completed, body = self.cli(
            "reconcile", {"operation": "repair-reconcile", "coordinator": "session-repair"}
        )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertEqual(body["result"]["state"], "resolved")
        self.assertNotIn("SEQ-503", self.retired())
        self.assertEqual(store.next_item_id(self.work), "SEQ-504")


if __name__ == "__main__":
    unittest.main()
