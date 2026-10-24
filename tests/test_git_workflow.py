"""SEQ-035 workflow fixtures using real Git and the repository runtime.

The runtime enforces claims and results. Context/handoff/preflight checks below
are test-only executions of the written procedure, not a product Git guard.
All writes and pushes stay inside StoreCase's disposable directory.
"""

import copy
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import test_store as fixtures
from session_flow import records, store


def checked_git(root: Path, *args: str) -> str:
    completed = fixtures.git(root, *args)
    if completed.returncode:
        raise AssertionError(f"git {args}: {completed.stderr}")
    return completed.stdout.strip()


def working_state(root: Path) -> dict:
    """Keep index contents distinct from working-file and untracked contents."""
    tracked = checked_git(root, "ls-files", "-z").split("\0")
    untracked = checked_git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return {
        "head": checked_git(root, "rev-parse", "HEAD"),
        "index": checked_git(root, "ls-files", "--stage"),
        "staged_patch": checked_git(root, "diff", "--cached", "--binary"),
        "unstaged_patch": checked_git(root, "diff", "--binary"),
        "tracked_bytes": {name: (root / name).read_bytes() for name in tracked if name},
        "untracked_bytes": {name: (root / name).read_bytes() for name in untracked if name},
    }


def context_matches(storage: dict, root: Path, namespace: str) -> bool:
    """Instruction-only comparison against the recorded coordination home."""
    return Path(storage["work_root"]).resolve() == root.resolve() and storage["namespace"] == namespace


def integration_problems(checkout: Path) -> list[str]:
    """Instruction-only preflight; observing a problem never changes Git state."""
    problems = ["dirty checkout"] if checked_git(checkout, "status", "--porcelain") else []
    for marker in ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD"):
        path = Path(checked_git(checkout, "rev-parse", "--git-path", marker))
        if (path if path.is_absolute() else checkout / path).exists():
            problems.append("interrupted Git operation")
    return problems


def handoff_problems(record: dict, checkout: Path, target: str, publishable: set[str]) -> list[str]:
    """Execute handoff checks from the reference, without adding product enforcement."""
    result = record["metadata"].get("result") or {}
    if result.get("outcome") != "passed" or not record["acceptance"]["applies"]:
        return ["no applicable passed result"]
    if not result.get("checks"):
        return ["missing checks"]
    summary = json.loads(result["summary"])
    head = summary.get("submitted_head")
    if not head or head != result.get("evidence", {}).get("revision"):
        return ["submitted/evidence revision mismatch"]
    entries = zip(record["metadata"].get("evidence", []), record.get("evidence", []))
    applicable = [entry for entry, status in entries if status["applies"]
                  and entry.get("criteria") == result.get("evidence", {}).get("criteria")]
    if not applicable or applicable[-1].get("result") != "pass" or applicable[-1].get("revision") != head:
        return ["no applicable passing evidence for submitted commit"]
    if fixtures.git(checkout, "cat-file", "-e", head + "^{commit}").returncode:
        return ["submitted commit missing"]
    if head != checked_git(checkout, "rev-parse", "HEAD"):
        return ["source HEAD changed"]
    commits = set(checked_git(checkout, "rev-list", f"{target}..{head}").splitlines())
    return [] if commits <= publishable else ["unreviewed or unfinished ancestors"]


@unittest.skipUnless(fixtures.GIT_AVAILABLE, fixtures.NEEDS_GIT)
class GitWorkflowTest(fixtures.StoreCase):
    def setUp(self):
        super().setUp()
        template = records.read_record(store.record_path(self.root, "SEQ-001", "A1"))
        for task in ("A1", "B1", "I1", "I2"):
            metadata = dict(template["metadata"], task=task, title=f"Workflow fixture {task}")
            path = store.record_path(self.root, "SEQ-001", task)
            records.write_record_file(path, records.render_record(metadata, "Exercise isolated workflow.", ""))
            self.accept_fixture(task=task)
        (self.root / ".gitignore").write_text(".state/\n")
        self.call("render")
        fixtures.initialize_repository(self.root)
        self.integration = self.project / "integration"
        self.integration.mkdir()
        (self.integration / "shared.txt").write_text("base\n")
        fixtures.initialize_repository(self.integration)
        self.origin = self.project / "application.git"
        checked_git(self.project, "init", "--bare", "-b", "main", str(self.origin))
        checked_git(self.integration, "remote", "add", "origin", str(self.origin))
        checked_git(self.integration, "push", "-u", "origin", "main")
        self.base = checked_git(self.integration, "rev-parse", "HEAD")
        self.a = self.add_worktree("task-a")
        self.b = self.add_worktree("task-b")
        self.integration_scope = str(self.integration.resolve()) + "/**"

    def add_worktree(self, branch: str, base: str = "origin/main") -> Path:
        path = self.project / branch
        checked_git(self.integration, "worktree", "add", "-b", branch, str(path), base)
        return path

    def call(self, command: str, document=None, task=None, cwd=None, project=None, ok=True) -> dict:
        args = [sys.executable, "-B", str(fixtures.ENTRYPOINT), command,
                "--project-root", str(project or self.project)]
        if task:
            args += ["--seq", "SEQ-001", "--task", task]
        if document is not None:
            args += ["--input", str(self.payload_file(document))]
        completed = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
        answer = json.loads(completed.stdout)
        self.assertEqual(ok, answer["ok"], answer)
        self.assertEqual(0 if ok else 1, completed.returncode, completed.stderr)
        return answer["result"] if ok else answer["error"]

    def show(self, task: str, cwd=None) -> dict:
        return self.call("show", task=task, cwd=cwd)

    def mutation(self, task: str, actor: str, **fields) -> dict:
        return dict(seq="SEQ-001", task=task, actor=actor, coordinator=actor,
                    expect_revision=self.show(task)["identity"]["revision"], **fields)

    def claim(self, task: str, actor: str, paths: list[str], cwd=None) -> None:
        self.call("claim", self.mutation(task, actor, allowed_paths=paths), task, cwd)

    def note(self, task: str, actor: str, note: dict) -> None:
        current = self.show(task)
        self.call("revise", {"expect_revision": current["identity"]["revision"],
                              "actor": actor, "coordinator": actor,
                              "body": current["body"] + "\n" + json.dumps(note)}, task)

    def commit_file(self, checkout: Path, name: str, text: str) -> str:
        (checkout / name).write_text(text)
        checked_git(checkout, "add", "--", name)
        checked_git(checkout, "commit", "-m", "Fixture change")
        return checked_git(checkout, "rev-parse", "HEAD")

    def report(self, task: str, actor: str, checkout: Path, head: str) -> None:
        result = {
            "outcome": "passed",
            "summary": json.dumps({"repository": str(self.origin), "checkout": str(checkout),
                                   "branch": checked_git(checkout, "branch", "--show-current"),
                                   "base": self.base, "submitted_head": head, "ready": True}),
            "checks": [{"command": "git show HEAD:task-a.txt", "observed": "task A\n"}],
            "evidence": {"criteria": "Fixture task content checked", "revision": head,
                         "environment": "disposable local Git", "limitations": "synthetic"},
        }
        self.call("record-result", self.mutation(task, actor, result=result), task, checkout)

    def ready_a(self) -> str:
        self.claim("A1", "terminal:a", ["task-a.txt"], self.a)
        self.note("A1", "terminal:a", {
            "actor": "terminal:a", "checkout": str(self.a), "branch": "task-a",
            "base": self.base, "repository": str(self.origin), "remote_default": "origin/main",
            "runtime_project_root": str(self.project), "physical_work_root": str(self.root.resolve()),
            "namespace": fixtures.NAMESPACE,
        })
        head = self.commit_file(self.a, "task-a.txt", "task A\n")
        self.assertEqual("task A", checked_git(self.a, "show", head + ":task-a.txt"))
        self.report("A1", "terminal:a", self.a, head)
        return head

    def settle_integration(self, head: str) -> None:
        result = {"outcome": "passed", "summary": "Integration receipt saved; local publication checked",
                  "checks": [{"command": "git rev-parse main (local bare remote)", "observed": head}],
                  "evidence": {"criteria": "Integrated and published fixture A with exact source",
                               "revision": head, "environment": "local bare remote", "limitations": "synthetic"}}
        self.call("record-result", self.mutation("I1", "terminal:integrator", result=result), "I1")
        self.assertEqual("done", self.show("I1")["metadata"]["lifecycle"])

    def test_independent_contexts_report_to_later_integrator_and_preserve_other_work(self):
        integration_before = working_state(self.integration)
        for checkout in (self.a, self.b):
            storage = self.call("doctor", cwd=checkout)["storage"]
            self.assertTrue(context_matches(storage, self.root, fixtures.NAMESPACE))
        self.claim("B1", "terminal:b", ["shared.txt", "untracked.bin"], self.b)
        (self.b / "shared.txt").write_bytes(b"staged B\n")
        checked_git(self.b, "add", "shared.txt")
        (self.b / "shared.txt").write_bytes(b"unstaged B\n")
        (self.b / "untracked.bin").write_bytes(b"\x00unfinished B\xff")
        before = working_state(self.b)
        self.assertTrue(before["staged_patch"] and before["unstaged_patch"] and before["untracked_bytes"])
        head = self.ready_a()
        self.assertEqual(integration_before, working_state(self.integration))
        record = self.show("A1", self.integration)
        self.assertEqual("done", record["metadata"]["lifecycle"])
        self.assertEqual([], handoff_problems(record, self.a, self.base, {head}))
        self.assertNotIn("result", self.show("B1")["metadata"])
        self.claim("I1", "terminal:integrator", [self.integration_scope], self.integration)
        checked_git(self.integration, "fetch", "origin")
        checked_git(self.integration, "merge", "--no-ff", head, "-m", "Integrate task A")
        integrated = checked_git(self.integration, "rev-parse", "HEAD")
        self.assertEqual("task A", checked_git(self.integration, "show", integrated + ":task-a.txt"))
        checked_git(self.integration, "push", "origin", "main")
        published = checked_git(self.origin, "rev-parse", "main")
        self.assertEqual(integrated, published)
        build = self.project / "build"
        checked_git(self.project, "clone", str(self.origin), str(build))
        checked_git(build, "checkout", "--detach", integrated)
        self.assertEqual(integrated, checked_git(build, "rev-parse", "HEAD"))
        self.assertEqual("", checked_git(build, "status", "--porcelain"))
        self.note("I1", "terminal:integrator", {"submitted": head, "integrated": integrated,
                                                 "published": published, "build_source": integrated})
        self.assertIsNone(self.show("I1")["metadata"].get("result"))
        self.settle_integration(integrated)
        self.assertEqual(before, working_state(self.b))
        checked_git(self.integration, "fetch", "origin")
        followup = self.add_worktree("task-c")
        self.assertEqual(published, checked_git(followup, "rev-parse", "HEAD"))
        self.assertEqual(before, working_state(self.b))
        self.assertTrue((self.project / "_devdocs" / "SEQUENCE.md").is_file())
        self.assertEqual("", checked_git(self.integration, "status", "--porcelain"))
        self.assertEqual(published, checked_git(self.integration, "rev-parse", "HEAD"))

    def test_copied_root_with_same_namespace_fails_physical_context_check(self):
        copied = self.project / "copied-project"
        shutil.copytree(self.root, copied / "_devdocs" / "work", ignore=shutil.ignore_patterns(".git"))
        observed = self.call("doctor", project=copied)["storage"]
        self.assertEqual(fixtures.NAMESPACE, observed["namespace"])
        self.assertFalse(context_matches(observed, self.root, fixtures.NAMESPACE))
        self.assertTrue(context_matches(self.call("doctor")["storage"], self.root, fixtures.NAMESPACE))

    def test_separate_process_integration_claim_race_has_one_owner(self):
        tasks = ("I1", "I2")
        payloads = [self.mutation(task, "race:" + task, allowed_paths=[self.integration_scope]) for task in tasks]
        script = "import os,sys; print('ready',flush=True); sys.stdin.read(1); os.execv(sys.executable, [sys.executable]+sys.argv[1:])"
        processes = []
        for task, document in zip(tasks, payloads):
            args = [sys.executable, "-u", "-c", script, "-B", str(fixtures.ENTRYPOINT), "claim",
                    "--project-root", str(self.project), "--seq", "SEQ-001", "--task", task,
                    "--input", str(self.payload_file(document))]
            process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True)
            processes.append(process)
            self.addCleanup(lambda p=process: p.poll() is None and p.kill())
            self.assertEqual("ready\n", process.stdout.readline())
        for process in processes:
            process.stdin.write("x")
            process.stdin.flush()
        answers = [json.loads(process.communicate(timeout=30)[0]) for process in processes]
        self.assertEqual(1, sum(answer["ok"] for answer in answers), answers)
        loser = next(index for index, answer in enumerate(answers) if not answer["ok"])
        self.assertIn(answers[loser]["error"]["code"], ("root-busy", "invalid-request"))
        error = self.call("claim", payloads[loser], tasks[loser], ok=False)
        self.assertEqual("invalid-request", error["code"])
        self.assertEqual("race:" + tasks[1 - loser], error["detail"]["holder"])
        owners = [self.show(task)["metadata"].get("claim", {}).get("actor") for task in tasks]
        self.assertEqual(1, sum(actor is not None for actor in owners))

    def test_unique_actors_are_required_and_result_releases_exclusion(self):
        self.claim("I1", "owner:one", [self.integration_scope])
        rejected = self.call("claim", self.mutation("I2", "owner:two", allowed_paths=[self.integration_scope]), "I2", ok=False)
        self.assertEqual("invalid-request", rejected["code"])
        self.claim("I2", "owner:one", [self.integration_scope])
        self.assertEqual("owner:one", self.show("I2")["metadata"]["claim"]["actor"])
        for task in ("I1", "I2"):
            self.call("record-result", self.mutation(task, "owner:one", result={"outcome": "unknown", "summary": "Interrupted; inspect checkout"}), task)
        self.claim("A1", "owner:next", [self.integration_scope])
        self.assertEqual("active", self.show("I1")["metadata"]["lifecycle"])
        self.assertIsNotNone(self.show("I1")["metadata"]["result"])

    def test_explicit_takeover_preserves_receipt_and_refuses_interrupted_git_state(self):
        self.claim("I1", "owner:first", [self.integration_scope])
        submitted = self.commit_file(self.a, "shared.txt", "task version\n")
        self.commit_file(self.integration, "shared.txt", "integration version\n")
        conflict = fixtures.git(self.integration, "merge", submitted)
        self.assertNotEqual(0, conflict.returncode)
        before = working_state(self.integration)
        receipt = {"submitted": submitted, "publication": "not attempted", "next": "owner reviews merge conflict"}
        self.note("I1", "owner:first", receipt)
        self.call("record-result", self.mutation("I1", "owner:first", result={"outcome": "unknown", "summary": "Merge interrupted"}), "I1")
        attempt = self.mutation("I1", "owner:next", allowed_paths=[self.integration_scope])
        self.assertEqual("missing-authority", self.call("claim", attempt, "I1", ok=False)["code"])
        attempt["takeover_claim"] = fixtures.TAKEOVER_AUTHORITY
        self.call("claim", attempt, "I1")
        record = self.show("I1")
        self.assertEqual("owner:first", record["metadata"]["claim"]["reassigned_from"])
        self.assertIn(json.dumps(receipt), record["body"])
        self.assertIsNone(record["metadata"].get("result"))
        self.assertEqual(["dirty checkout", "interrupted Git operation"], integration_problems(self.integration))
        self.assertEqual(before, working_state(self.integration))
        self.assertEqual(self.base, checked_git(self.origin, "rev-parse", "main"))

    def test_handoff_refuses_changed_head_missing_checks_and_wrong_evidence(self):
        head = self.ready_a()
        valid = self.show("A1")
        self.assertEqual([], handoff_problems(valid, self.a, self.base, {head}))
        for field in ("checks", "revision"):
            candidate = copy.deepcopy(valid)
            if field == "checks":
                candidate["metadata"]["result"]["checks"] = []
            else:
                candidate["metadata"]["result"]["evidence"]["revision"] = self.base
            self.assertTrue(handoff_problems(candidate, self.a, self.base, {head}))
        newer = self.commit_file(self.a, "task-a.txt", "unchecked change\n")
        self.assertNotEqual(head, newer)
        self.assertEqual(["source HEAD changed"], handoff_problems(valid, self.a, self.base, {head, newer}))
        self.assertEqual(self.base, checked_git(self.integration, "rev-parse", "HEAD"))

    def test_handoff_refuses_unfinished_ancestor_and_unreported_task(self):
        self.assertEqual(["no applicable passed result"], handoff_problems(self.show("B1"), self.b, self.base, set()))
        self.claim("A1", "terminal:a", ["task-a.txt"])
        unfinished = self.commit_file(self.a, "unfinished.txt", "not approved\n")
        submitted = self.commit_file(self.a, "task-a.txt", "task A\n")
        self.report("A1", "terminal:a", self.a, submitted)
        record = self.show("A1")
        self.assertEqual(["unreviewed or unfinished ancestors"], handoff_problems(record, self.a, self.base, {submitted}))
        self.assertIn(unfinished, checked_git(self.a, "rev-list", self.base + "..HEAD"))
        self.assertEqual(self.base, checked_git(self.origin, "rev-parse", "main"))

    def test_reaccepted_scope_cannot_reuse_stale_passing_commit_evidence(self):
        head = self.ready_a()
        current = self.show("A1")
        self.call("revise", {"actor": "terminal:a", "expect_revision": current["identity"]["revision"],
                              "scope": "Exercise isolated workflow and a newly required preservation check.",
                              "metadata": {"lifecycle": "active"},
                              "correction": {"actor": "maintainer", "reason": "Fixture requirement expanded"}}, "A1")
        self.call("accept", {"actor": "terminal:a", "expect_revision": self.show("A1")["identity"]["revision"],
                              "authority": {"source": "Fixture acceptance of expanded scope", "revision": "2"},
                              "scope": ["implement", "verify"], "lifecycle": "active"}, "A1")
        changed = self.show("A1")
        self.assertTrue(changed["acceptance"]["applies"])
        self.assertEqual("passed", changed["metadata"]["result"]["outcome"])
        self.assertEqual(head, changed["metadata"]["result"]["evidence"]["revision"])
        self.assertEqual([False], [entry["applies"] for entry in changed["evidence"]])
        self.assertEqual(["no applicable passing evidence for submitted commit"],
                         handoff_problems(changed, self.a, self.base, {head}))
        self.assertEqual(self.base, checked_git(self.integration, "rev-parse", "HEAD"))

    def test_handoff_requires_applicable_pass_evidence_matching_submitted_commit(self):
        head = self.ready_a()
        valid = self.show("A1")
        for defect in ("missing", "wrong revision", "failed"):
            with self.subTest(defect=defect):
                candidate = copy.deepcopy(valid)
                if defect == "missing":
                    candidate["metadata"]["evidence"] = []
                    candidate["evidence"] = []
                elif defect == "wrong revision":
                    candidate["metadata"]["evidence"][-1]["revision"] = self.base
                else:
                    candidate["metadata"]["evidence"][-1]["result"] = "fail"
                self.assertEqual(["no applicable passing evidence for submitted commit"],
                                 handoff_problems(candidate, self.a, self.base, {head}))

    def test_remote_advance_rejects_old_push_then_revalidates_combined_history(self):
        head = self.ready_a()
        self.claim("I1", "integrator:advance", [self.integration_scope])
        checked_git(self.integration, "merge", "--ff-only", head)
        other = self.project / "other-publisher"
        checked_git(self.project, "clone", str(self.origin), str(other))
        checked_git(other, "config", "user.email", "fixture@example.invalid")
        checked_git(other, "config", "user.name", "Other fixture publisher")
        advanced = self.commit_file(other, "remote.txt", "new canonical work\n")
        checked_git(other, "push", "origin", "main")
        rejected = fixtures.git(self.integration, "push", "origin", "main")
        self.assertNotEqual(0, rejected.returncode)
        self.assertEqual(advanced, checked_git(self.origin, "rev-parse", "main"))
        checked_git(self.integration, "fetch", "origin")
        self.assertNotEqual(self.base, checked_git(self.integration, "rev-parse", "origin/main"))
        checked_git(self.integration, "merge", "--no-ff", "origin/main", "-m", "Revalidate advanced target")
        revised = checked_git(self.integration, "rev-parse", "HEAD")
        self.assertNotEqual(head, revised)
        self.assertEqual("task A", checked_git(self.integration, "show", revised + ":task-a.txt"))
        self.assertEqual("new canonical work", checked_git(self.integration, "show", revised + ":remote.txt"))
        checked_git(self.integration, "merge-base", "--is-ancestor", advanced, revised)
        checked_git(self.integration, "merge-base", "--is-ancestor", head, revised)
        checked_git(self.integration, "push", "origin", "main")
        self.assertEqual(revised, checked_git(self.origin, "rev-parse", "main"))

    def state_remote(self) -> Path:
        remote = self.project / "state.git"
        checked_git(self.project, "init", "--bare", "-b", "main", str(remote))
        checked_git(self.root, "remote", "add", "origin", str(remote))
        return remote

    def test_backup_reports_uncommitted_state_and_excludes_other_workspace_data(self):
        remote = self.state_remote()
        outside = self.project / "_devdocs" / "SEQUENCE.md"
        outside.write_text(outside.read_text() + "\nexternal view change\n")
        (self.root / ".state" / "private-checkpoint").write_text("ignored journal\n")
        note = self.root / "seq-001" / "uncommitted.md"
        note.write_text("not backed up\n")
        before = working_state(self.integration)
        result = self.call("backup", {"remote": "origin"})
        self.assertTrue(result["pushed"])
        self.assertFalse(result["complete"])
        self.assertEqual(["seq-001/uncommitted.md"], result["uncommitted"])
        self.assertEqual(result["commit"], checked_git(remote, "rev-parse", "main"))
        paths = checked_git(remote, "ls-tree", "-r", "--name-only", "main").splitlines()
        self.assertFalse(any(name.startswith(".state/") for name in paths))
        self.assertNotIn("SEQUENCE.md", paths)
        self.assertNotIn("seq-001/uncommitted.md", paths)
        note.unlink()
        result = self.call("backup")
        self.assertTrue(result["complete"], "complete only checks nonignored paths inside state root")
        self.assertEqual(before, working_state(self.integration))
        self.assertIn("external view change", outside.read_text())

    def test_backup_missing_remote_and_divergence_are_reported_without_rewrite(self):
        self.assertEqual("invalid-identity", self.call("backup", ok=False)["code"])
        remote = self.state_remote()
        self.assertTrue(self.call("backup")["pushed"])
        other = self.project / "other-state"
        checked_git(self.project, "clone", str(remote), str(other))
        checked_git(other, "config", "user.email", "fixture@example.invalid")
        checked_git(other, "config", "user.name", "Other state owner")
        advanced = self.commit_file(other, "remote-state.md", "other state\n")
        checked_git(other, "push", "origin", "main")
        self.claim("A1", "state:writer", ["task-a.txt"])
        local = checked_git(self.root, "rev-parse", "HEAD")
        result = self.call("backup")
        self.assertFalse(result["pushed"])
        self.assertFalse(result["complete"])
        self.assertIn("git push failed", result["reason"])
        self.assertEqual(advanced, checked_git(remote, "rev-parse", "main"))
        self.assertEqual(local, checked_git(self.root, "rev-parse", "HEAD"))


if __name__ == "__main__":
    unittest.main()
