"""Run repair's survey, separate setup, and import against a pre-v2 repository."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from test_repair import FIXTURES, RepairRun, git, in_process_request, store, tree


class BootstrapRepair(RepairRun):
    fixture = FIXTURES / "uninitialized"
    namespace = None

    def cli(self, command, payload=None, namespace=True):
        return super().cli(command, payload, namespace=namespace and self.namespace is not None)

    def payload(self, **extra):
        return {
            "operation": "bootstrap-import",
            "source": "_devdocs/todo/SEQUENCE.md",
            **extra,
        }

    def survey(self):
        completed, body = self.cli("import", self.payload())
        self.assertEqual(completed.returncode, 0, body)
        return body["result"]

    def bind(self):
        payload = {
            "operation": "bootstrap-bind",
            "repository": {"name": self.project.name, "path": "../.."},
        }
        completed, body = self.cli("bind-namespace", payload, namespace=False)
        self.assertEqual(completed.returncode, 0, body)
        self.namespace = body["result"]["namespace"]
        return body["result"]

    def apply(self, fingerprint, **extra):
        return self.cli("import", self.payload(
            apply=True, expected_survey_fingerprint=fingerprint, **extra,
        ))

    def test_missing_root_doctor_and_survey_write_nothing(self):
        before, status, commits = tree(self.project), self.status(), self.commits()
        storage = self.storage()
        self.assertTrue(storage["bootstrap"]["eligible"])
        self.assertIsNone(storage["namespace"])
        self.assertIn("/session-repair", " ".join(storage["limitations"]))
        plan = self.survey()
        self.assertEqual(len(plan["items"]), 3)
        self.assertEqual(len(plan["tombstones"]), 4)
        self.assertEqual(plan["unclassified"], [])
        self.assertEqual(plan["unresolved_links"], [])
        self.assertEqual(plan["items"][0]["metadata"]["links"]["anchor"], "phase-1")
        self.assertEqual(plan["historical"], [
            str(self.project / "_devdocs/todo"), str(self.project / "_devdocs/todo/tasks"),
        ])
        self.assertEqual(plan["work_root"], str(self.work))
        self.assertEqual(plan["sequence_path"], str(self.sequence))
        self.assertEqual((before, status, commits), (tree(self.project), self.status(), self.commits()))
        self.assertFalse(self.work.exists())

    def test_setup_then_import_in_enclosing_repository(self):
        before = self.commits()
        archive = tree(self.project / "_devdocs/todo")
        plan = self.survey()
        setup = self.bind()
        self.assertTrue(setup["commit"]["committed"])
        self.assertEqual(int(self.commits()), int(before) + 1)
        self.assertFalse(self.sequence.exists())
        self.assertEqual(self.status(), "")
        self.assertEqual(self.survey()["survey_fingerprint"], plan["survey_fingerprint"])
        completed, body = self.apply(plan["survey_fingerprint"])
        self.assertEqual(completed.returncode, 0, body)
        result = body["result"]
        self.assertEqual(result["verification"]["entries"], 3)
        self.assertTrue(result["verification"]["verified"])
        self.assertNotEqual(result["operation"]["commit"]["commit"], setup["commit"]["commit"])
        self.assertEqual(int(self.commits()), int(before) + 2)
        self.assertEqual(tree(self.project / "_devdocs/todo"), archive)
        self.assertEqual(sorted(self.retired()), ["SEQ-600", "SEQ-601", "SEQ-602", "SEQ-603"])
        self.assertEqual(setup["repositories"], [{"name": self.project.name, "path": "../.."}])

    def test_ignored_root_uses_local_history_without_changing_project(self):
        ignore = self.project / ".gitignore"
        ignore.write_text("/_devdocs/\n", encoding="utf-8")
        git(self.project, "add", ".gitignore")
        git(self.project, "commit", "-m", "Keep work local")
        project_head = git(self.project, "rev-parse", "HEAD").stdout
        plan = self.survey()
        self.work.mkdir()
        self.assertEqual(git(self.work, "init", "-b", "main").returncode, 0)
        git(self.work, "config", "user.name", "Fixture Coordinator")
        git(self.work, "config", "user.email", "fixture@example.invalid")
        self.assertTrue(self.storage()["bootstrap"]["eligible"])
        setup = self.bind()
        self.assertTrue(setup["commit"]["committed"])
        self.assertTrue(self.storage()["own_repository"])
        completed, body = self.apply(plan["survey_fingerprint"])
        self.assertEqual(completed.returncode, 0, body)
        self.assertTrue(body["result"]["verification"]["verified"])
        self.assertEqual(git(self.work, "rev-list", "--count", "HEAD").stdout.strip(), "2")
        self.assertEqual(git(self.work, "status", "--porcelain").stdout, "")
        self.assertEqual(git(self.work, "remote").stdout, "")
        self.assertEqual(git(self.project, "rev-parse", "HEAD").stdout, project_head)
        self.assertEqual(ignore.read_text(encoding="utf-8"), "/_devdocs/\n")

    def test_restart_after_setup_preserves_uuid_and_does_not_recommit(self):
        plan = self.survey()
        setup = self.bind()
        commits = self.commits()
        again = self.bind()
        self.assertFalse(again["changed"])
        self.assertEqual(again["namespace"], setup["namespace"])
        self.assertEqual(self.commits(), commits)
        completed, body = self.apply(plan["survey_fingerprint"])
        self.assertEqual(completed.returncode, 0, body)
        completed, body = self.apply(plan["survey_fingerprint"], operation="second-import")
        self.assertEqual(completed.returncode, 0, body)
        self.assertFalse(body["result"]["operation"]["changed"])

    def test_survey_reads_existing_namespace_when_argument_is_omitted(self):
        setup = self.bind()
        completed, body = self.cli("import", self.payload(), namespace=False)
        self.assertEqual(completed.returncode, 0, body)
        self.assertEqual(body["result"]["namespace"], setup["namespace"])
        for item in body["result"]["items"]:
            self.assertEqual(item["metadata"]["namespace"], setup["namespace"])
            self.assertIsInstance(item["text"], str)

    def test_source_changes_after_setup_refuse_import(self):
        plan = self.survey()
        self.bind()
        source = Path(plan["source"])
        source.write_text(source.read_text(encoding="utf-8") + "\nA changed source.\n", encoding="utf-8")
        before = tree(self.project)
        completed, body = self.apply(plan["survey_fingerprint"])
        self.assertEqual(completed.returncode, 1, body)
        self.assertIn("survey changed", body["error"]["message"])
        self.assertEqual(tree(self.project), before)
        self.assertEqual(self.item_directories(), [])

    def test_new_historical_identity_changes_fingerprint(self):
        plan = self.survey()
        self.bind()
        task = self.project / "_devdocs/todo/tasks/0601-retries.md"
        task.write_text(task.read_text(encoding="utf-8") + "\nAlso SEQ-599.\n", encoding="utf-8")
        completed, body = self.apply(plan["survey_fingerprint"])
        self.assertEqual(completed.returncode, 1, body)
        self.assertIn("survey changed", body["error"]["message"])

    def test_namespace_mismatch_refuses_without_writing(self):
        self.bind()
        self.namespace = "00000000-0000-4000-8000-000000000000"
        before = tree(self.project)
        for apply in (False, True):
            completed, body = self.cli("import", self.payload(apply=apply))
            self.assertEqual(completed.returncode, 1, body)
            self.assertIn("differs", body["error"]["message"])
            self.assertEqual(tree(self.project), before)

    def test_missing_namespace_with_existing_contents_is_not_bootstrap(self):
        self.work.mkdir()
        for path in ("seq-601", ".state", "unknown"):
            with self.subTest(path=path):
                (self.work / path).mkdir()
                before = tree(self.project)
                self.assertFalse(self.storage()["bootstrap"]["eligible"])
                completed, body = self.cli("import", self.payload())
                self.assertEqual(completed.returncode, 1, body)
                self.assertEqual(tree(self.project), before)
                (self.work / path).rmdir()

    def test_malformed_namespace_is_not_replaced(self):
        self.work.mkdir()
        (self.work / "namespace.json").write_text("{broken", encoding="utf-8")
        before = tree(self.project)
        completed, body = self.cli("import", self.payload())
        self.assertEqual(completed.returncode, 1, body)
        self.assertEqual(body["error"]["code"], "unsupported-format")
        self.assertEqual(tree(self.project), before)

    def test_source_cannot_equal_generated_output(self):
        config_path = self.project / ".session-flow.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["paths"]["sequence"] = self.payload()["source"]
        config_path.write_text(json.dumps(config), encoding="utf-8")
        before = tree(self.project)
        completed, body = self.cli("import", self.payload())
        self.assertEqual(completed.returncode, 1, body)
        self.assertIn("also the generated sequence", body["error"]["message"])
        self.assertEqual(tree(self.project), before)

    def test_dirty_project_is_detected_before_setup(self):
        (self.project / "uncommitted.txt").write_text("user work", encoding="utf-8")
        request = in_process_request(self, self.payload())
        outstanding = store.project_changes(request, self.work)
        with self.assertRaises(store.InvalidIdentityError):
            store.refuse_uncommitted(self.project, outstanding, "project tree")
        self.assertFalse(self.work.exists())

    def test_failed_setup_commit_leaves_explicit_recovery_before_import(self):
        plan = self.survey()
        request = in_process_request(self, {"repository": {"name": self.project.name, "path": "../.."}})
        with patch.object(store, "commit_work_root", return_value=store.git_failure("git commit failed")):
            setup = store.bind_namespace(request)
        self.assertFalse(setup["commit"]["committed"])
        self.namespace = setup["namespace"]
        before = tree(self.project)
        completed, body = self.apply(plan["survey_fingerprint"])
        self.assertEqual(completed.returncode, 1, body)
        self.assertIn("uncommitted", body["error"]["message"])
        self.assertEqual(tree(self.project), before)
        self.assertEqual(self.item_directories(), [])


if __name__ == "__main__":
    unittest.main()
