"""Isolated install check: a clean standalone install must resolve every
reference its own skill entry files name (R-010) and must expose an invocable
support package that answers `doctor`."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGED_SOURCES = (
    "install.sh",
    "skills",
    "references",
    "agents",
    "commands",
    "scripts",
    ".claude-plugin",
    "THIRD_PARTY_NOTICES.md",
)
MANIFEST_LINE = 'SUPPORT_PACKAGE=("scripts/session-flow.py" "scripts/session_flow" "references" "THIRD_PARTY_NOTICES.md")'
WITHOUT_REFERENCES = 'SUPPORT_PACKAGE=("scripts/session-flow.py" "scripts/session_flow" "THIRD_PARTY_NOTICES.md")'
WITHOUT_RUNTIME_PACKAGE = 'SUPPORT_PACKAGE=("scripts/session-flow.py" "references" "THIRD_PARTY_NOTICES.md")'

ENTRYPOINT = "scripts/session-flow.py"
DESCRIPTOR = "session-flow-runtime.json"

REFERENCE_RE = re.compile(
    r"(?:\$\{CLAUDE_PLUGIN_ROOT\}/|<RESOLVED_PLUGIN_ROOT>/|\.\.\./)?"
    r"((?:skills/[A-Za-z0-9._-]+/)?references/[A-Za-z0-9._-]+\.md)"
)
NOTICE_RE = re.compile(r"\bTHIRD_PARTY_NOTICES\.md\b")
PROTOCOL_RE = re.compile(r"^PROTOCOL_VERSION\s*=\s*(\d+)", re.MULTILINE)


def run_install(script: Path, workdir: Path, *args: str) -> subprocess.CompletedProcess:
    (workdir / ".claude").mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        ["bash", str(script), "--scope", "project", *args],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )


def run_doctor(install_root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", str(install_root / ENTRYPOINT), "doctor", "--project-root", str(install_root)],
        capture_output=True,
        text=True,
        check=False,
    )


def stage_source(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    for name in STAGED_SOURCES:
        source = REPO_ROOT / name
        if source.is_dir():
            shutil.copytree(source, destination / name, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy(source, destination / name)
    return destination / "install.sh"


def source_package_files() -> list[str]:
    modules = (REPO_ROOT / "scripts" / "session_flow").rglob("*.py")
    return [ENTRYPOINT] + sorted(str(path.relative_to(REPO_ROOT)) for path in modules)


def source_protocol_version() -> int:
    match = PROTOCOL_RE.search((REPO_ROOT / ENTRYPOINT).read_text(encoding="utf-8"))
    assert match is not None, "scripts/session-flow.py must define PROTOCOL_VERSION"
    return int(match.group(1))


def source_package_version() -> str:
    manifest = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    return manifest["version"]


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

    def test_support_package_is_complete(self):
        for relative in source_package_files():
            with self.subTest(relative=relative):
                self.assertTrue((self.root / relative).is_file())

    def test_no_compiled_artifacts_are_copied(self):
        self.assertEqual([], sorted(str(path) for path in self.root.rglob("__pycache__")))

    def test_installed_entrypoint_answers_doctor(self):
        doctor = run_doctor(self.root)
        self.assertEqual(0, doctor.returncode, doctor.stdout + doctor.stderr)
        payload = json.loads(doctor.stdout)
        self.assertTrue(payload["ok"], payload)
        self.assertIsInstance(payload["result"]["protocol"], int)
        self.assertEqual(source_protocol_version(), payload["result"]["protocol"])
        self.assertTrue(payload["result"]["commands"]["doctor"]["available"])

    def test_runtime_descriptors_resolve_the_entrypoint(self):
        descriptors = sorted(self.root.glob(f"skills/*/{DESCRIPTOR}"))
        installed_skills = sorted(self.root.glob("skills/*/SKILL.md"))
        self.assertEqual(len(installed_skills), len(descriptors))
        for descriptor in descriptors:
            with self.subTest(skill=descriptor.parent.name):
                runtime = json.loads(descriptor.read_text(encoding="utf-8"))
                self.assertEqual(source_package_version(), runtime["version"])
                self.assertEqual(source_protocol_version(), runtime["protocol"])
                self.assertEqual("3.9", runtime["python_minimum"])
                resolved = (descriptor.parent / runtime["entrypoint"]).resolve()
                self.assertEqual((self.root / ENTRYPOINT).resolve(), resolved)
                self.assertTrue(resolved.is_file())
                self.assertTrue((descriptor.parent / runtime["references"]).resolve().is_dir())

    def test_python_prerequisite_is_documented(self):
        usage = subprocess.run(
            ["bash", str(REPO_ROOT / "install.sh"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertIn("Python 3.9 or newer", usage.stdout)
        self.assertIn("without Python cannot", usage.stdout)
        self.assertIn("Requires: Python 3.9 or newer", self.result.stdout)


class InstallOptionsTest(unittest.TestCase):
    def test_skills_only_still_installs_required_helper_files(self):
        with tempfile.TemporaryDirectory() as workdir:
            result = run_install(REPO_ROOT / "install.sh", Path(workdir), "--skills-only")
            root = Path(workdir) / ".claude"
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual([], unresolved_references(root))
            for relative in source_package_files():
                self.assertTrue((root / relative).is_file(), relative)
            self.assertTrue((root / "skills" / "session-next" / DESCRIPTOR).is_file())
            self.assertEqual(0, run_doctor(root).returncode)
            self.assertFalse((root / "agents").exists())
            self.assertFalse((root / "commands").exists())

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as workdir:
            result = run_install(REPO_ROOT / "install.sh", Path(workdir), "--dry-run")
            root = Path(workdir) / ".claude"
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual([], list(root.iterdir()))
            self.assertIn("INSTALL: .claude/references/workflow-overview.md", result.stdout)
            self.assertIn(f"INSTALL: .claude/{ENTRYPOINT}", result.stdout)
            self.assertIn(f"INSTALL: .claude/skills/session-next/{DESCRIPTOR}", result.stdout)

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
    """Dropping an asset from the install manifest must make the check fail."""

    def trimmed_install(self, workdir: Path, replacement: str) -> subprocess.CompletedProcess:
        script = stage_source(workdir / "source")
        original = script.read_text(encoding="utf-8")
        self.assertIn(MANIFEST_LINE, original)
        script.write_text(original.replace(MANIFEST_LINE, replacement), encoding="utf-8")
        return run_install(script, workdir / "target")

    def test_reference_removed_from_manifest_is_reported(self):
        with tempfile.TemporaryDirectory() as workdir:
            result = self.trimmed_install(Path(workdir), WITHOUT_REFERENCES)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

            unresolved = unresolved_references(Path(workdir) / "target" / ".claude")
            self.assertIn("session-next: references/workflow-overview.md", unresolved)

    def test_runtime_package_removed_from_manifest_blocks_activation(self):
        with tempfile.TemporaryDirectory() as workdir:
            result = self.trimmed_install(Path(workdir), WITHOUT_RUNTIME_PACKAGE)
            root = Path(workdir) / "target" / ".claude"
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            self.assertIn("did not answer 'doctor'", result.stdout)
            self.assertEqual([], list(root.glob("skills/*/SKILL.md")))
            self.assertFalse((root / "scripts" / "session_flow").exists())
