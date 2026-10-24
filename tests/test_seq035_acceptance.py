"""Independent SEQ-035 acceptance checks, authored before implementation.

A1-A3 checks detect missing contract topics and workflow links, not prose meaning.
A4 checks the fixture/report deliverables; run test_git_workflow.py for mechanics.
A5 checks the inventory's required structure and evidence topics. Human review
must still assess instructions, fixture assertions, provenance and authority.
Nothing here proves live recovery or closes the parent work item.
"""

import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = "references/git-workflow.md"


class ContractCase(unittest.TestCase):
    def read(self, path: str) -> str:
        target = ROOT / path
        self.assertTrue(target.is_file(), f"Missing accepted deliverable: {path}")
        return target.read_text(encoding="utf-8")

    def topics(self, text: str, **patterns: str) -> None:
        normalized = re.sub(r"\s+", " ", text).lower()
        for label, pattern in patterns.items():
            with self.subTest(topic=label):
                self.assertRegex(normalized, pattern, f"Contract topic absent: {label}")

    def workflow_link(self, path: str) -> None:
        text = self.read(path)
        self.assertIn("git-workflow.md", text, f"{path} must route to the shared procedure")
        self.assertTrue((ROOT / WORKFLOW).is_file())


class A1ContextTest(ContractCase):
    def test_execution_skills_route_to_shared_workflow(self):
        for name in ("session-next", "session-delegation"):
            with self.subTest(skill=name):
                self.workflow_link(f"skills/{name}/SKILL.md")

    def test_context_covers_identity_and_resume(self):
        self.topics(
            self.read(WORKFLOW),
            runtime_root=r"canonical.{0,60}(runtime|project).{0,30}root",
            physical_identity=r"physical|realpath|resolve\(",
            namespace=r"namespace",
            actor=r"actor",
            source=r"repository|repositories",
            checkout=r"checkout|worktree",
            branch=r"branch",
            base=r"base.{0,25}(sha|commit|revision)",
            remote=r"remote",
            resume=r"resum",
            preservation=r"preserv|without reset|do not reset|never reset",
            assignment=r"revise",
            allowed_scope=r"allowed_paths|allowed.paths",
        )

    def test_handoff_uses_existing_result_fields_and_claim_holder(self):
        self.topics(
            self.read(WORKFLOW),
            summary=r"result\.summary",
            tested_revision=r"result\.evidence\.revision",
            success=r"passed",
            independent=r"independent",
            delegated=r"delegat",
            holder=r"claim.{0,30}(holder|owner)|claiming coordinator",
            submitted_head=r"submitted.{0,30}(head|sha|commit)",
            changed_head=r"chang.{0,80}(head|commit|code)|(head|commit).{0,80}chang",
            checks=r"checks|tests|tested",
        )


class A2IntegrationTest(ContractCase):
    def test_release_and_delivery_route_to_shared_workflow(self):
        for name in ("session-next", "session-release"):
            with self.subTest(skill=name):
                self.workflow_link(f"skills/{name}/SKILL.md")
                self.topics(self.read(f"skills/{name}/SKILL.md"), integration=r"integration")

    def test_ownership_and_interruption_are_explicit(self):
        self.topics(
            self.read(WORKFLOW),
            integration_task=r"integration.{0,60}(task|assignment)",
            common_scope=r"integration.{0,40}(directory|checkout)",
            claim=r"claim",
            receipts=r"receipt",
            held_assignment=r"held|holding|already.claim|overlap",
            takeover=r"takeover",
            authority=r"authoriz|authority",
            interrupted_state=r"interrupt|in.progress|unfinished merge",
            dirty_state=r"dirty|unclean|clean checkout|checkout.{0,20}clean",
        )

    def test_integration_tracks_canonical_publication_and_revalidation(self):
        self.topics(
            self.read(WORKFLOW),
            submitted=r"submitted",
            integrated=r"integrated",
            published=r"published",
            revision=r"sha|commit|revision",
            ancestry=r"ancestr|publishable history",
            squash=r"squash",
            rebase=r"rebase",
            retirement=r"retir",
            advance=r"advanc",
            validation=r"revalidat|re.validat|validat.{0,60}(again|new|candidate)",
            force_push=r"force.push",
            release=r"release.{0,80}(revision|sha|commit)|(revision|sha|commit).{0,80}release",
        )


class A3StateTest(ContractCase):
    def test_state_reference_routes_to_common_procedure(self):
        self.workflow_link("references/runtime-integration.md")
        self.workflow_link("skills/session-init/SKILL.md")

    def test_state_and_views_have_explicit_placement(self):
        self.topics(
            self.read("references/runtime-integration.md"),
            physical_root=r"physical",
            canonical_context=r"canonical",
            copied_records=r"copied|copies|copy",
            own_repository=r"own.{0,30}(git|repository)|separate.{0,30}(git|repository)",
            namespace=r"namespace",
            pinned_references=r"pinned|reference",
            generated_sequence=r"sequence",
            outside_views=r"outside",
            visibility=r"hosted|visibility|snapshot",
        )

    def test_backup_is_bounded_and_has_an_owner(self):
        combined = self.read("references/runtime-integration.md") + self.read("skills/session-init/SKILL.md")
        self.topics(
            combined,
            backup=r"backup",
            owner=r"owner",
            cadence=r"cadence|schedule|frequency",
            remote=r"remote",
            permission=r"authority|authoriz",
            incomplete=r"omission|incomplete|not.{0,30}(backup|snapshot)|does not.{0,30}(include|back up)",
            worktrees=r"worktree",
            journals=r"journal",
        )


class A4FixtureTest(ContractCase):
    def test_fixture_suite_contains_executable_unittests(self):
        tree = ast.parse(self.read("tests/test_git_workflow.py"))
        tests = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")]
        self.assertTrue(tests, "A4 must provide runnable fixture tests, not only a report")

    def test_report_covers_required_observations_and_limits(self):
        self.topics(
            self.read("_verification/seq-035-workflow.md"),
            command=r"command|python.{0,10}unittest",
            revision=r"revision|commit|sha",
            environment=r"environment|python|linux|wsl",
            concurrency=r"race|concurr|separate process",
            staged=r"\bstaged\b",
            unstaged=r"\bunstaged\b",
            untracked=r"\buntracked\b",
            canonical_base=r"canonical|fresh.{0,30}base",
            advance=r"advanc",
            backup=r"backup",
            limits=r"limitation|manual|instruction.only",
            live_recovery=r"live|phase 4",
        )


class A5InventoryTest(ContractCase):
    def test_inventory_has_required_sections(self):
        text = self.read("_verification/seq-035-recovery-inventory.md")
        for heading in ("Observations", "Unknowns", "Preservation", "Recovery proposal", "Remaining verification"):
            self.assertRegex(text, rf"(?m)^## {re.escape(heading)}\s*$")

    def test_inventory_distinguishes_evidence_and_authority(self):
        self.topics(
            self.read("_verification/seq-035-recovery-inventory.md"),
            date=r"\b20\d{2}-\d{2}-\d{2}\b",
            umbrella=r"umbrella|lat.lamp",
            application=r"lamp.badger",
            namespace=r"namespace",
            command=r"git |command",
            historical_work=r"seq.957",
            deployed_history=r"seq.855",
            historical=r"historical|user.reported",
            owner=r"owner",
            unknown=r"unknown|unavailable|unverified",
            protection=r"protection|protected",
            modes=r"filemode|file.mode|execute.bit",
            staged=r"\bstaged\b",
            unstaged=r"\bunstaged\b",
            untracked=r"\buntracked\b",
            authority=r"authority|authoriz|approval",
            live_cycle=r"live|subsequent",
        )


if __name__ == "__main__":
    unittest.main()
