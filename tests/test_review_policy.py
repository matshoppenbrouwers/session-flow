"""Exercise review-policy initialization against disposable project directories."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
HELPER = REPO / "scripts" / "session_flow" / "review_policy.py"
TEMPLATE = REPO / "references" / "review-policy-template.md"
START = b"<!-- session-flow:review -->"
END = b"<!-- /session-flow:review -->"


class ReviewPolicyTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="session flow review ")
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)

    def initialize(self, root=None):
        return subprocess.run(
            [sys.executable, "-B", str(HELPER), "--project-root", str(root or self.project)],
            capture_output=True, text=True, check=False,
        )

    def test_fresh_project_gets_policy_and_both_host_instruction_bridges(self):
        result = self.initialize()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.project / "REVIEW.md").read_bytes(), TEMPLATE.read_bytes())
        for name in ("CLAUDE.md", "AGENTS.md"):
            bridge = (self.project / name).read_bytes()
            self.assertIn(b"REVIEW.md", bridge)
            self.assertEqual(bridge.count(START), 1)
            self.assertEqual(bridge.count(END), 1)
        self.assertEqual(set(p.name for p in self.project.iterdir()), {"REVIEW.md", "CLAUDE.md", "AGENTS.md"})
        self.assertEqual(json.loads(result.stdout)["files"]["REVIEW.md"], "created")

    def test_existing_policy_is_preserved_byte_for_byte(self):
        policy = b"\xef\xbb\xbf# Our rules\r\n\r\nNever change our billing currency.\r\n"
        (self.project / "REVIEW.md").write_bytes(policy)
        result = self.initialize()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.project / "REVIEW.md").read_bytes(), policy)
        self.assertEqual(json.loads(result.stdout)["files"]["REVIEW.md"], "preserved")

    def test_existing_instructions_keep_bom_crlf_and_unrelated_text(self):
        original = b"\xef\xbb\xbf# Project\r\n\r\nOur instructions.\r\n"
        for name in ("CLAUDE.md", "AGENTS.md"):
            (self.project / name).write_bytes(original)
        result = self.initialize()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("CLAUDE.md", "AGENTS.md"):
            updated = (self.project / name).read_bytes()
            self.assertTrue(updated.startswith(original))
            self.assertNotIn(b"\n", updated.replace(b"\r\n", b""))

    def test_rerun_changes_no_bytes(self):
        first = self.initialize()
        self.assertEqual(first.returncode, 0, first.stderr)
        before = {p.name: p.read_bytes() for p in self.project.iterdir()}
        second = self.initialize()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.project.iterdir()})
        self.assertEqual(set(json.loads(second.stdout)["files"].values()), {"preserved"})

    def test_only_owned_bridge_is_updated(self):
        original = b"# Before\n\n" + START + b"\nOld instructions\n" + END + b"\n\n# After\nKeep this.\n"
        (self.project / "CLAUDE.md").write_bytes(original)
        result = self.initialize()
        self.assertEqual(result.returncode, 0, result.stderr)
        updated = (self.project / "CLAUDE.md").read_bytes()
        self.assertTrue(updated.startswith(b"# Before\n\n"))
        self.assertTrue(updated.endswith(b"\n\n# After\nKeep this.\n"))
        self.assertNotIn(b"Old instructions", updated)
        self.assertEqual(updated.count(START), 1)

    def test_invalid_bridge_refuses_before_creating_any_file(self):
        for malformed in (START, END, END + b"\n" + START, START + b"\n" + START + b"\n" + END):
            with self.subTest(malformed=malformed):
                (self.project / "AGENTS.md").write_bytes(malformed)
                result = self.initialize()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("malformed", json.loads(result.stderr)["error"])
                self.assertEqual((self.project / "AGENTS.md").read_bytes(), malformed)
                self.assertEqual(set(p.name for p in self.project.iterdir()), {"AGENTS.md"})

    def test_directory_in_place_of_policy_is_not_replaced(self):
        (self.project / "REVIEW.md").mkdir()
        result = self.initialize()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a regular file", json.loads(result.stderr)["error"])
        self.assertTrue((self.project / "REVIEW.md").is_dir())
        self.assertFalse((self.project / "CLAUDE.md").exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlink_target_is_not_modified(self):
        outside = self.project / "outside.txt"
        outside.write_bytes(b"Do not edit me.\n")
        try:
            (self.project / "CLAUDE.md").symlink_to(outside)
        except OSError as error:
            self.skipTest(str(error))
        result = self.initialize()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a regular file", json.loads(result.stderr)["error"])
        self.assertEqual(outside.read_bytes(), b"Do not edit me.\n")
        self.assertFalse((self.project / "REVIEW.md").exists())

    def test_missing_project_is_not_created(self):
        missing = self.project / "missing"
        result = self.initialize(missing)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stderr)["ok"])
        self.assertFalse(missing.exists())

    @unittest.skipUnless(shutil.which("bash"), "bash is required for standalone installation")
    def test_installed_helper_resolves_its_packaged_template(self):
        (self.project / ".claude").mkdir()
        installed = subprocess.run(
            ["bash", str(REPO / "install.sh"), "--scope", "project"],
            cwd=self.project, capture_output=True, text=True, check=False,
        )
        self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
        helper = self.project / ".claude" / "scripts" / "session_flow" / "review_policy.py"
        result = subprocess.run(
            [sys.executable, "-B", str(helper), "--project-root", str(self.project)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.project / "REVIEW.md").read_bytes(), TEMPLATE.read_bytes())
        self.assertTrue((self.project / ".claude" / "references" / "code-review.md").is_file())


if __name__ == "__main__":
    unittest.main()
