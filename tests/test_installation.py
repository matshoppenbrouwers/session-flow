"""Installed-package checks.

A clean standalone install must resolve every reference its own skill entry files
name (R-010) and expose an invocable support package that answers `doctor`. Beyond
that: the source, native-plugin, and standalone layouts must run the same fixtures
through both local invocation routes; packaging must never touch the work root; a
restore into an empty root must reproduce it; and a missing or too-old interpreter
must answer with an install instruction rather than a traceback."""

import json
import os
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
DESCRIPTOR_SKILL = "session-next"

REFERENCE_RE = re.compile(
    r"(?:\$\{CLAUDE_PLUGIN_ROOT\}/|<RESOLVED_PLUGIN_ROOT>/|\.\.\./)?"
    r"((?:skills/[A-Za-z0-9._-]+/)?references/[A-Za-z0-9._-]+\.md)"
)
NOTICE_RE = re.compile(r"\bTHIRD_PARTY_NOTICES\.md\b")
PROTOCOL_RE = re.compile(r"^PROTOCOL_VERSION\s*=\s*(\d+)", re.MULTILINE)

CORE_FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "lifecycle" / "store" / "root"
CORE_ITEM = "SEQ-001"
CORE_RESERVED = "SEQ-002"
SPACED_PREFIX = "session flow installed "
GIT = shutil.which("git")
NEEDS_GIT = "git is required to version the work root"
SHELL_TOOLS = ("bash", "cp", "mkdir", "find", "sed", "head", "basename", "dirname", "cat", "rm")
COMMIT_RE = re.compile(r"\b[0-9a-f]{40}\b")
UPGRADE_VERSION = "99.0.0"
VERSION_RE = re.compile(r'("version"\s*:\s*)"[^"]*"')

# Where each supported layout resolves the entrypoint from. The source row is the
# checkout itself; the other two are the documented local invocation routes.
ROUTES = {
    "source": "the package-relative path inside the checkout",
    "native-plugin": "${CLAUDE_PLUGIN_ROOT}/" + ENTRYPOINT,
    "standalone": "the entrypoint named by skills/*/" + DESCRIPTOR,
}
INSTALLED_ROUTES = ("native-plugin", "standalone")

ACCEPTANCE_PAYLOAD = {
    "expected_revision": 1,
    "actor": "maintainer",
    "authority": {"source": "maintainer decision", "revision": "2026-09-07T12:30:00Z"},
    "scope": ["implement", "record"],
    "decided_at": "2026-09-07T12:30:00Z",
}
# A lifecycle change needs the claim that covers it, so the fixture run takes the
# assignment before moving the item. `claimed_at` is literal because a defaulted
# timestamp differs between the three layout runs and they must reproduce each other.
CLAIM_PAYLOAD = {
    "operation": "op-installed-claim",
    "coordinator": "tests.test_installation",
    "actor": "tests.test_installation",
    "seq": CORE_ITEM,
    "expect_revision": 2,
    "claimed_at": "2026-09-07T13:00:00Z",
    "allowed_paths": [],
}
TRANSITION_PAYLOAD = {
    "operation": "op-installed-layout",
    "coordinator": "tests.test_installation",
    "provenance": {"actor": "maintainer", "source": "fixture run"},
    "changes": [{"seq": CORE_ITEM, "expect_revision": 3, "metadata": {"lifecycle": "active"}}],
}
PENDING_OPERATION = {
    "format": 1,
    "operation": "op-interrupted-before-restore",
    "command": "transition",
    "state": "prepared",
    "payload_fingerprint": "sha256:fixture",
    "prepared_at": "2026-09-07T13:00:00Z",
    "reserved": [],
    "changes": [],
}
# Runs the shipped entrypoint under an interpreter that reports 3.8, so the runtime
# guard rather than a real old Python is what the missing-interpreter checks exercise.
OLD_INTERPRETER = (
    "import runpy, sys\n"
    "sys.version_info = (3, 8, 10, 'final', 0)\n"
    "arguments = list(sys.argv[1:])\n"
    "while arguments and arguments[0].startswith('-'):\n"
    "    arguments.pop(0)\n"
    "sys.argv = arguments\n"
    "sys.exit(runpy.run_path(arguments[0])['main']())\n"
)


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


def temporary_root(register) -> Path:
    """A disposable root whose name contains a space, so every path below it is spaced."""
    directory = tempfile.mkdtemp(prefix=SPACED_PREFIX)
    register(shutil.rmtree, directory, True)
    return Path(directory)


def git(root: Path, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([GIT, "-C", str(root), *arguments], capture_output=True, text=True, check=False)


def core_fixture_project(parent: Path) -> Path:
    """A project holding the shared core work-root fixture, versioned by Git."""
    project = parent / "project"
    work_root = project / "_devdocs" / "work"
    shutil.copytree(CORE_FIXTURE_ROOT, work_root)
    git(work_root, "init", "-b", "main")
    git(work_root, "config", "user.email", "fixture@example.invalid")
    git(work_root, "config", "user.name", "Fixture Coordinator")
    git(work_root, "add", "-A")
    git(work_root, "-c", "commit.gpgsign=false", "commit", "-m", "Initialize synthetic work records")
    return project


def write_payload(directory: Path, name: str, document: dict) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return str(path)


def snapshot(root: Path) -> dict:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def run_entrypoint(
    entrypoint: Path, project: Path, command: str, *arguments: str, environment=None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", str(entrypoint), command, "--project-root", str(project), *arguments],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


def invoke(entrypoint: Path, project: Path, command: str, *arguments: str, environment=None) -> dict:
    """Parse the one JSON object stdout carries. A call that answers otherwise is a failure."""
    completed = run_entrypoint(entrypoint, project, command, *arguments, environment=environment)
    try:
        payload = json.loads(completed.stdout)
    except ValueError:
        payload = {"ok": False, "stdout": completed.stdout, "stderr": completed.stderr}
    payload["exit_code"] = completed.returncode
    return payload


def normalized(document, project: Path) -> dict:
    """Absolute paths and commit ids differ between layouts; nothing else may."""
    text = json.dumps(document, sort_keys=True)
    text = text.replace(json.dumps(str(project))[1:-1], "<project>")
    return json.loads(COMMIT_RE.sub("<commit>", text))


def core_fixture_run(entrypoint: Path, project: Path, payloads: dict, environment=None) -> dict:
    """The one fixture run every supported installed layout must reproduce."""
    doctor = invoke(entrypoint, project, "doctor", environment=environment)
    for varying in ("runtime", "plugin_version"):
        doctor.get("result", {}).pop(varying, None)
    steps = {
        "doctor": doctor,
        "show": invoke(entrypoint, project, "show", "--seq", CORE_ITEM, environment=environment),
        "accept": invoke(
            entrypoint, project, "accept", "--seq", CORE_ITEM, "--input", payloads["accept"],
            environment=environment,
        ),
        "claim": invoke(
            entrypoint, project, "claim", "--seq", CORE_ITEM, "--input", payloads["claim"],
            environment=environment,
        ),
        "transition": invoke(
            entrypoint, project, "transition", "--input", payloads["transition"], environment=environment
        ),
        "select": invoke(entrypoint, project, "select", environment=environment),
        "render": invoke(entrypoint, project, "render", environment=environment),
    }
    sequence = project / "_devdocs" / "SEQUENCE.md"
    steps["sequence"] = sequence.read_text(encoding="utf-8") if sequence.is_file() else None
    return normalized(steps, project)


def plugin_layout(parent: Path) -> tuple:
    """Native plugin: the host unpacks the package and names its root in the environment."""
    plugin_root = parent / "host plugin cache" / "session-flow"
    stage_source(plugin_root)
    environment = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(plugin_root))
    return Path(environment["CLAUDE_PLUGIN_ROOT"]) / ENTRYPOINT, environment


def descriptor_entrypoint(install_root: Path) -> Path:
    """Standalone copy: the entrypoint is read from the descriptor beside the entry file."""
    descriptor = install_root / "skills" / DESCRIPTOR_SKILL / DESCRIPTOR
    runtime = json.loads(descriptor.read_text(encoding="utf-8"))
    return (descriptor.parent / runtime["entrypoint"]).resolve()


def standalone_layout(parent: Path) -> tuple:
    """Standalone: what install.sh leaves behind under the selected target."""
    workdir = parent / "standalone host"
    workdir.mkdir(parents=True, exist_ok=True)
    result = run_install(REPO_ROOT / "install.sh", workdir)
    install_root = workdir / ".claude"
    return descriptor_entrypoint(install_root), install_root, result


@unittest.skipUnless(GIT, NEEDS_GIT)
class InstalledLayoutTest(unittest.TestCase):
    """Source, native-plugin, and standalone must run the same fixtures identically."""

    @classmethod
    def setUpClass(cls):
        cls.root = temporary_root(cls.addClassCleanup)
        cls.payloads = {
            "accept": write_payload(cls.root / "payloads", "accept.json", ACCEPTANCE_PAYLOAD),
            "claim": write_payload(cls.root / "payloads", "claim.json", CLAIM_PAYLOAD),
            "transition": write_payload(cls.root / "payloads", "transition.json", TRANSITION_PAYLOAD),
        }
        plugin_entrypoint, cls.plugin_environment = plugin_layout(cls.root)
        standalone_entrypoint, cls.install_root, cls.install_result = standalone_layout(cls.root)
        cls.entrypoints = {
            "source": REPO_ROOT / ENTRYPOINT,
            "native-plugin": plugin_entrypoint,
            "standalone": standalone_entrypoint,
        }
        cls.runs = {}
        for layout, entrypoint in cls.entrypoints.items():
            project = core_fixture_project(cls.root / layout)
            environment = cls.plugin_environment if layout == "native-plugin" else None
            cls.runs[layout] = core_fixture_run(entrypoint, project, cls.payloads, environment)

    def test_the_standalone_install_succeeded(self):
        result = self.install_result
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_every_layout_resolves_a_real_entrypoint(self):
        for layout, entrypoint in self.entrypoints.items():
            with self.subTest(layout=layout, route=ROUTES[layout]):
                self.assertTrue(entrypoint.is_file(), f"{layout} resolves no entrypoint via {ROUTES[layout]}")

    def test_both_installed_routes_are_exercised(self):
        for layout in INSTALLED_ROUTES:
            with self.subTest(layout=layout, route=ROUTES[layout]):
                self.assertIn(layout, self.runs)
        self.assertNotEqual(self.entrypoints["native-plugin"], self.entrypoints["standalone"])

    def test_every_step_of_the_fixture_run_succeeded(self):
        for layout, run in self.runs.items():
            for step, payload in run.items():
                if step == "sequence":
                    continue
                with self.subTest(layout=layout, step=step):
                    self.assertTrue(payload["ok"], payload)
                    self.assertEqual(0, payload["exit_code"])

    def test_installed_layouts_reproduce_the_source_run(self):
        for layout in INSTALLED_ROUTES:
            with self.subTest(layout=layout, route=ROUTES[layout]):
                self.assertEqual(self.runs["source"], self.runs[layout])

    def test_the_fixture_run_actually_changed_the_records(self):
        run = self.runs["source"]
        self.assertTrue(run["accept"]["result"]["acceptance"]["applies"])
        self.assertEqual("applied", run["transition"]["result"]["state"])
        self.assertTrue(run["transition"]["result"]["commit"]["committed"])
        self.assertEqual(CORE_ITEM, run["select"]["result"]["candidate"]["seq"])
        self.assertIn(CORE_ITEM, run["sequence"])

    def test_every_path_under_test_contains_a_space(self):
        for layout in INSTALLED_ROUTES:
            with self.subTest(layout=layout):
                self.assertIn(" ", str(self.entrypoints[layout]))

    def test_the_release_number_is_reported_where_each_layout_carries_it(self):
        """`plugin_version` is reporting-only; a standalone copy carries it in the descriptor."""
        plugin_doctor = invoke(
            self.entrypoints["native-plugin"], self.root, "doctor", environment=self.plugin_environment
        )
        self.assertTrue(plugin_doctor["ok"], plugin_doctor)
        self.assertEqual(source_package_version(), plugin_doctor["result"]["plugin_version"])
        descriptor = json.loads(
            (self.install_root / "skills" / DESCRIPTOR_SKILL / DESCRIPTOR).read_text(encoding="utf-8")
        )
        self.assertEqual(source_package_version(), descriptor["version"])
        self.assertEqual(source_protocol_version(), descriptor["protocol"])


@unittest.skipUnless(GIT, NEEDS_GIT)
class WorkRootSurvivalTest(unittest.TestCase):
    """Packaging owns replaceable code; the work root is authoritative storage."""

    def setUp(self):
        self.root = temporary_root(self.addCleanup)
        self.source = self.root / "package source"
        stage_source(self.source)
        self.workdir = self.root / "standalone host"
        self.workdir.mkdir(parents=True)
        self.install_root = self.workdir / ".claude"
        self.assertEqual(0, run_install(self.source / "install.sh", self.workdir).returncode)
        self.project = core_fixture_project(self.root)
        self.work_root = self.project / "_devdocs" / "work"
        self.before = snapshot(self.work_root)

    def upgrade(self) -> subprocess.CompletedProcess:
        manifest = self.source / ".claude-plugin" / "plugin.json"
        manifest.write_text(
            VERSION_RE.sub(r'\1"%s"' % UPGRADE_VERSION, manifest.read_text(encoding="utf-8"), count=1),
            encoding="utf-8",
        )
        return run_install(self.source / "install.sh", self.workdir, "--force")

    def test_the_install_target_and_the_work_root_are_disjoint(self):
        installed = {path.resolve() for path in self.install_root.rglob("*")}
        self.assertFalse([path for path in installed if self.work_root.resolve() in path.parents])
        self.assertEqual([], [path for path in self.work_root.rglob("*") if path.name == DESCRIPTOR])

    def test_an_upgrade_replaces_the_package_and_leaves_the_work_root(self):
        result = self.upgrade()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        descriptor = json.loads(
            (self.install_root / "skills" / DESCRIPTOR_SKILL / DESCRIPTOR).read_text(encoding="utf-8")
        )
        self.assertEqual(UPGRADE_VERSION, descriptor["version"])
        self.assertEqual(self.before, snapshot(self.work_root))

    def test_an_uninstall_leaves_the_work_root_and_a_reinstall_reads_it(self):
        shutil.rmtree(self.install_root)
        shutil.rmtree(self.source)
        self.assertEqual(self.before, snapshot(self.work_root))

        stage_source(self.source)
        self.assertEqual(0, run_install(self.source / "install.sh", self.workdir).returncode)
        shown = invoke(descriptor_entrypoint(self.install_root), self.project, "show", "--seq", CORE_ITEM)
        self.assertTrue(shown["ok"], shown)
        self.assertEqual(CORE_ITEM, shown["result"]["identity"]["seq"])
        self.assertEqual(self.before, snapshot(self.work_root))


@unittest.skipUnless(GIT, NEEDS_GIT)
class RestoreTest(unittest.TestCase):
    """Restore is a checkout: an empty root reproduces identities, acceptance, and pending work."""

    def setUp(self):
        self.root = temporary_root(self.addCleanup)
        entrypoint, self.install_root, result = standalone_layout(self.root)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.entrypoint = entrypoint
        self.project = core_fixture_project(self.root)
        self.work_root = self.project / "_devdocs" / "work"
        accepted = invoke(
            self.entrypoint,
            self.project,
            "accept",
            "--seq",
            CORE_ITEM,
            "--input",
            write_payload(self.root / "payloads", "accept.json", ACCEPTANCE_PAYLOAD),
        )
        self.assertTrue(accepted["ok"], accepted)
        write_payload(
            self.work_root / ".state" / "operations",
            PENDING_OPERATION["operation"] + ".json",
            PENDING_OPERATION,
        )
        git(self.work_root, "add", "-A")
        git(self.work_root, "-c", "commit.gpgsign=false", "commit", "-m", "Accepted item, interrupted operation")

    def test_restore_into_an_empty_root_reproduces_the_work_root(self):
        target = self.root / "restored project"
        target.mkdir()
        restored = invoke(
            self.entrypoint,
            target,
            "restore",
            "--input",
            write_payload(self.root / "payloads", "restore.json", {"source": str(self.work_root)}),
        )
        self.assertTrue(restored["ok"], restored)
        result = restored["result"]
        self.assertEqual([CORE_ITEM], result["identities"])
        self.assertEqual([CORE_RESERVED], result["reserved"])
        self.assertEqual([PENDING_OPERATION["operation"]], result["pending_operations"])

        restored_root = Path(result["work_root"])
        self.assertEqual(
            (self.work_root / "seq-001" / "intent.md").read_text(encoding="utf-8"),
            (restored_root / "seq-001" / "intent.md").read_text(encoding="utf-8"),
        )
        shown = invoke(self.entrypoint, target, "show", "--seq", CORE_ITEM)
        acceptance = shown["result"]["metadata"]["acceptance"]
        self.assertEqual("maintainer", acceptance["actor"])
        self.assertEqual("2026-09-07T12:30:00Z", acceptance["accepted_at"])
        self.assertEqual(1, len(shown["result"]["metadata"]["scope_checks"]))


class MissingInterpreterTest(unittest.TestCase):
    """No Python, or too old a Python, must produce an install instruction, not a traceback."""

    def setUp(self):
        self.root = temporary_root(self.addCleanup)

    def shell_only_path(self) -> Path:
        """A PATH holding the installer's shell tools and deliberately no python3."""
        binaries = self.root / "bin"
        binaries.mkdir(parents=True, exist_ok=True)
        for tool in SHELL_TOOLS:
            resolved = shutil.which(tool)
            if resolved is None:
                self.skipTest(f"{tool} is required to run install.sh without python3")
            (binaries / tool).symlink_to(resolved)
        self.assertIsNone(shutil.which("python3", path=str(binaries)))
        return binaries

    def test_install_without_python3_names_how_to_install_it(self):
        binaries = self.shell_only_path()
        workdir = self.root / "no interpreter"
        (workdir / ".claude").mkdir(parents=True)
        result = subprocess.run(
            ["bash", str(REPO_ROOT / "install.sh"), "--scope", "project"],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=False,
            env={"PATH": str(binaries), "HOME": str(self.root)},
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)
        self.assertIn("python3 is not on PATH", result.stdout)
        self.assertIn("apt install python3", result.stdout)
        self.assertIn("brew install python3", result.stdout)
        self.assertTrue((workdir / ".claude" / ENTRYPOINT).is_file())

    def old_interpreter(self) -> Path:
        """A python3 that answers as 3.8 so the shipped runtime guard is the thing under test."""
        binaries = self.root / "old"
        binaries.mkdir(parents=True, exist_ok=True)
        stub = binaries / "python3"
        stub.write_text("#!%s\n%s" % (sys.executable, OLD_INTERPRETER), encoding="utf-8")
        stub.chmod(0o755)
        return binaries

    def test_the_shipped_entrypoint_refuses_an_old_interpreter(self):
        for layout, entrypoint in (
            ("source", REPO_ROOT / ENTRYPOINT),
            ("standalone", standalone_layout(self.root)[0]),
        ):
            with self.subTest(layout=layout):
                completed = subprocess.run(
                    [sys.executable, "-B", "-c", OLD_INTERPRETER, str(entrypoint), "doctor"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
                self.assertNotIn("Traceback", completed.stderr)
                payload = json.loads(completed.stdout)
                self.assertFalse(payload["ok"])
                self.assertEqual("unsupported-runtime", payload["error"]["code"])
                self.assertIn("apt install python3", payload["error"]["detail"]["install"])

    def test_install_reports_an_old_interpreter_as_an_interpreter_problem(self):
        binaries = self.old_interpreter()
        workdir = self.root / "old interpreter"
        (workdir / ".claude").mkdir(parents=True)
        result = subprocess.run(
            ["bash", str(REPO_ROOT / "install.sh"), "--scope", "project"],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=False,
            env=dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ["PATH"]),
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)
        self.assertIn("older than 3.9", result.stdout)
        self.assertIn("apt install python3", result.stdout)
        self.assertNotIn("complete session-flow checkout", result.stdout)
        self.assertEqual([], list((workdir / ".claude").glob("skills/*/SKILL.md")))
