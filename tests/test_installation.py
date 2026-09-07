"""Isolated install check: a clean standalone install must resolve every
reference its own skill entry files name (R-010)."""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGED_SOURCES = ("install.sh", "skills", "references", "agents", "commands", "THIRD_PARTY_NOTICES.md")
MANIFEST_LINE = 'SHARED_RESOURCES=("references" "THIRD_PARTY_NOTICES.md")'
TRIMMED_MANIFEST_LINE = 'SHARED_RESOURCES=("THIRD_PARTY_NOTICES.md")'

REFERENCE_RE = re.compile(
    r"(?:\$\{CLAUDE_PLUGIN_ROOT\}/|<RESOLVED_PLUGIN_ROOT>/|\.\.\./)?"
    r"((?:skills/[A-Za-z0-9._-]+/)?references/[A-Za-z0-9._-]+\.md)"
)
NOTICE_RE = re.compile(r"\bTHIRD_PARTY_NOTICES\.md\b")


def run_install(script: Path, workdir: Path, *args: str) -> subprocess.CompletedProcess:
    (workdir / ".claude").mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        ["bash", str(script), "--scope", "project", *args],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )


def stage_source(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    for name in STAGED_SOURCES:
        source = REPO_ROOT / name
        if source.is_dir():
            shutil.copytree(source, destination / name)
        else:
            shutil.copy(source, destination / name)
    return destination / "install.sh"


def named_references(skill_md: Path) -> set[str]:
    text = skill_md.read_text(encoding="utf-8")
    names = set(REFERENCE_RE.findall(text))
    if NOTICE_RE.search(text):
        names.add("THIRD_PARTY_NOTICES.md")
    return names


def unresolved_references(install_root: Path) -> list[str]:
    unresolved = []
    for skill_md in sorted(install_root.glob("skills/*/SKILL.md")):
        for name in sorted(named_references(skill_md)):
            candidates = (install_root / name, skill_md.parent / name)
            if not any(candidate.is_file() for candidate in candidates):
                unresolved.append(f"{skill_md.parent.name}: {name}")
    return unresolved


class CleanInstallTest(unittest.TestCase):
    """A single install into an empty target config, inspected several ways."""

    @classmethod
    def setUpClass(cls):
        cls._workdir = tempfile.TemporaryDirectory()
        cls.root = Path(cls._workdir.name) / ".claude"
        cls.result = run_install(REPO_ROOT / "install.sh", Path(cls._workdir.name))

    @classmethod
    def tearDownClass(cls):
        cls._workdir.cleanup()

    def test_install_succeeds(self):
        self.assertEqual(0, self.result.returncode, self.result.stdout + self.result.stderr)

    def test_every_named_reference_resolves(self):
        self.assertEqual([], unresolved_references(self.root))

    def test_shipped_skills_are_installed(self):
        installed = {path.parent.name for path in self.root.glob("skills/*/SKILL.md")}
        shipped = {path.parent.name for path in REPO_ROOT.glob("skills/*/SKILL.md")}
        self.assertEqual(shipped, installed)

    def test_nested_and_shared_trees_are_present(self):
        for relative in (
            "skills/security-liability-audit/references/technical-security.md",
            "skills/security-liability-audit/references/legal-liability.md",
            "skills/session-debug/references/root-cause-tracing.md",
            "references/workflow-overview.md",
            "references/sequence-grammar.md",
            "references/customization-guide.md",
            "THIRD_PARTY_NOTICES.md",
        ):
            with self.subTest(relative=relative):
                self.assertTrue((self.root / relative).is_file())


class InstallOptionsTest(unittest.TestCase):
    def test_skills_only_still_installs_required_helper_files(self):
        with tempfile.TemporaryDirectory() as workdir:
            result = run_install(REPO_ROOT / "install.sh", Path(workdir), "--skills-only")
            root = Path(workdir) / ".claude"
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual([], unresolved_references(root))
            self.assertFalse((root / "agents").exists())
            self.assertFalse((root / "commands").exists())

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as workdir:
            result = run_install(REPO_ROOT / "install.sh", Path(workdir), "--dry-run")
            root = Path(workdir) / ".claude"
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual([], list(root.iterdir()))
            self.assertIn("INSTALL: .claude/references/workflow-overview.md", result.stdout)

    def test_existing_files_are_kept_without_force(self):
        with tempfile.TemporaryDirectory() as workdir:
            root = Path(workdir) / ".claude"
            (root / "references").mkdir(parents=True)
            (root / "references" / "workflow-overview.md").write_text("local edit", encoding="utf-8")
            kept = run_install(REPO_ROOT / "install.sh", Path(workdir))
            self.assertEqual("local edit", (root / "references" / "workflow-overview.md").read_text(encoding="utf-8"))
            overwritten = run_install(REPO_ROOT / "install.sh", Path(workdir), "--force")
            self.assertEqual(0, kept.returncode + overwritten.returncode, kept.stdout + overwritten.stdout)
            self.assertNotEqual("local edit", (root / "references" / "workflow-overview.md").read_text(encoding="utf-8"))


class ManifestRegressionTest(unittest.TestCase):
    """Dropping a resource from the install manifest must make the check fail."""

    def test_reference_removed_from_manifest_is_reported(self):
        with tempfile.TemporaryDirectory() as workdir:
            script = stage_source(Path(workdir) / "source")
            original = script.read_text(encoding="utf-8")
            self.assertIn(MANIFEST_LINE, original)
            script.write_text(original.replace(MANIFEST_LINE, TRIMMED_MANIFEST_LINE), encoding="utf-8")

            target = Path(workdir) / "target"
            result = run_install(script, target)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

            unresolved = unresolved_references(target / ".claude")
            self.assertIn("session-next: references/workflow-overview.md", unresolved)
