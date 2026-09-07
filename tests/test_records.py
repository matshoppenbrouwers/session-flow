"""Record envelope, identity, and CLI boundary behaviour.

Every rejection here must happen before a write, so the write-sensitive cases run
the real entrypoint against a temporary work root and compare a file snapshot
taken before and after the call.
"""

import importlib.util
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
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "lifecycle" / "records"
NAMESPACE = "6f1d4a02-3c58-4a1e-9b77-0c2f8d5e4411"
OTHER_NAMESPACE = "11111111-2222-3333-4444-555555555555"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import session_flow  # noqa: E402
from session_flow import records  # noqa: E402

COMMAND_FAMILIES = frozenset(
    {
        "doctor",
        "bind-namespace",
        "show",
        "capture",
        "revise",
        "accept",
        "select",
        "claim",
        "record-result",
        "transition",
        "render",
        "import",
        "reconcile",
        "backup",
        "restore",
    }
)
TAXONOMY = frozenset(
    {
        "unsupported-format",
        "stale-revision",
        "root-busy",
        "invalid-identity",
        "missing-authority",
        "inapplicable-evidence",
    }
)
GUARDED_RUN = (
    "import runpy, sys\n"
    "sys.version_info = (3, 6, 9, 'final', 0)\n"
    "sys.argv = [{path!r}, 'doctor']\n"
    "runpy.run_path({path!r}, run_name='__main__')\n"
)


def load_entrypoint():
    spec = importlib.util.spec_from_file_location("session_flow_entrypoint", ENTRYPOINT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CLI = load_entrypoint()


def fixture_text(relative: str) -> str:
    return (FIXTURES / relative).read_text(encoding="utf-8")


def fixture_record(relative: str) -> dict:
    return records.parse_record(fixture_text(relative))


def work_root_with(record_source: str, directory: Path) -> Path:
    item = directory / "_devdocs" / "work" / "seq-001"
    item.mkdir(parents=True)
    shutil.copy(FIXTURES / record_source, item / "intent.md")
    return directory


def snapshot(root: Path) -> dict:
    return {
        str(path.relative_to(root)): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def run_cli(project_root: Path, *arguments: str):
    result = subprocess.run(
        [sys.executable, "-B", str(ENTRYPOINT), *arguments, "--project-root", str(project_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result, json.loads(result.stdout)


class RegionParsingTest(unittest.TestCase):
    """Only the two delimited regions carry machine-owned content."""

    def test_identity_comes_from_the_metadata_fence(self):
        identity = fixture_record("valid/seq-001/intent.md")["identity"]
        self.assertEqual(
            {"format": 1, "namespace": NAMESPACE, "seq": "SEQ-001", "revision": 3},
            {key: identity[key] for key in ("format", "namespace", "seq", "revision")},
        )
        self.assertEqual("session-flow", identity["repositories"][0]["name"])

    def test_scope_is_the_delimited_region_only(self):
        record = fixture_record("valid/seq-001/intent.md")
        self.assertTrue(record["scope"].startswith("A record whose metadata fence"))
        self.assertNotIn("## Scope", record["scope"])
        self.assertNotIn("Parse the two bounded regions", record["scope"])

    def test_captured_markers_survive_as_text(self):
        record = fixture_record("valid/seq-001/intent.md")
        self.assertIn("<!-- session-flow:scope -->", record["body"])
        self.assertEqual(1, fixture_text("valid/seq-001/intent.md").count(records.region_markers("scope")[0]))

    def test_task_record_carries_the_task_identity(self):
        self.assertEqual("A1", fixture_record("valid/seq-001/tasks/A1.md")["identity"]["task"])


class RejectedEnvelopeTest(unittest.TestCase):
    """Malformed, unknown-version, duplicated, and unbounded records are refused."""

    cases = (
        ("invalid/malformed-envelope.md", session_flow.UnsupportedFormatError, "not valid JSON"),
        ("invalid/unknown-format.md", session_flow.UnsupportedFormatError, "format 99 is unknown"),
        ("invalid/duplicate-markers.md", session_flow.UnsupportedFormatError, "exactly one meta region"),
        ("invalid/missing-scope.md", session_flow.UnsupportedFormatError, "exactly one scope region"),
    )

    def test_each_rejection_names_the_format_error(self):
        for source, expected, fragment in self.cases:
            with self.subTest(source=source):
                with self.assertRaises(expected) as raised:
                    records.parse_record(fixture_text(source))
                self.assertIn(fragment, str(raised.exception))
                self.assertEqual("unsupported-format", raised.exception.code)

    def test_identity_fields_are_required(self):
        text = records.render_record(
            {"format": 1, "namespace": NAMESPACE, "seq": "SEQ-009", "revision": 1}, "scope"
        ).replace('"revision": 1,\n  ', "")
        with self.assertRaises(session_flow.InvalidIdentityError) as raised:
            records.parse_record(text)
        self.assertIn("missing revision", str(raised.exception))

    def test_rejection_happens_before_any_write(self):
        for source in ("invalid/malformed-envelope.md", "invalid/unknown-format.md", "invalid/missing-scope.md"):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as workdir:
                root = work_root_with(source, Path(workdir))
                before = snapshot(root)
                result, response = run_cli(root, "show", "--seq", "SEQ-001")
                self.assertEqual(1, result.returncode, result.stdout)
                self.assertEqual("unsupported-format", response["error"]["code"])
                self.assertEqual(before, snapshot(root))

    def test_a_valid_record_is_readable_through_the_same_path(self):
        with tempfile.TemporaryDirectory() as workdir:
            root = work_root_with("valid/seq-001/intent.md", Path(workdir))
            before = snapshot(root)
            result, response = run_cli(root, "show", "--seq", "SEQ-001", "--namespace", NAMESPACE)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("SEQ-001", response["result"]["identity"]["seq"])
            self.assertEqual(before, snapshot(root))

    def test_a_foreign_namespace_is_refused(self):
        with tempfile.TemporaryDirectory() as workdir:
            root = work_root_with("valid/seq-001/intent.md", Path(workdir))
            _, response = run_cli(root, "show", "--seq", "SEQ-001", "--namespace", OTHER_NAMESPACE)
            self.assertEqual("invalid-identity", response["error"]["code"])


class MarkerEscapeTest(unittest.TestCase):
    """Captured source text can never open or close a region."""

    samples = (
        "<!-- session-flow:scope -->",
        "the issue said <!-- session-flow:meta --> then ended -->",
        "an entity already in the text: &#45; and &#45;&#45;",
        "<!--->",
        "plain prose with no markers",
    )

    def test_escaping_round_trips(self):
        for sample in self.samples:
            with self.subTest(sample=sample):
                self.assertEqual(sample, records.unescape_markers(records.escape_markers(sample)))

    def test_escaped_text_contains_no_markers(self):
        for sample in self.samples:
            with self.subTest(sample=sample):
                escaped = records.escape_markers(sample)
                self.assertNotIn("<!--", escaped)
                self.assertNotIn("-->", escaped)

    def test_rendered_record_with_captured_markers_still_parses(self):
        metadata = {"format": 1, "namespace": NAMESPACE, "seq": "SEQ-010", "revision": 1}
        captured = "Original request: <!-- session-flow:scope --> stay out of my regions -->"
        record = records.parse_record(records.render_record(metadata, "the accepted scope", captured))
        self.assertEqual(captured, record["body"])
        self.assertEqual("the accepted scope", record["scope"])


class RevisionTest(unittest.TestCase):
    """Namespace and SEQ are immutable; a changed record increments the revision."""

    def setUp(self):
        self.record = fixture_record("valid/seq-001/intent.md")

    def test_an_unchanged_record_keeps_its_revision(self):
        self.assertEqual(3, records.advance_revision(self.record, fixture_record("valid/seq-001/intent.md")))

    def test_a_changed_record_increments_the_revision(self):
        self.assertEqual(4, records.advance_revision(self.record, fixture_record("revisions/retitled.md")))

    def test_a_scope_edit_increments_the_revision(self):
        edited = fixture_record("valid/seq-001/intent.md")
        edited["scope"] = edited["scope"] + " Delivery is a merged pull request."
        self.assertTrue(records.record_changed(self.record, edited))
        self.assertEqual(4, records.advance_revision(self.record, edited))

    def test_a_seq_mutation_is_refused(self):
        with self.assertRaises(session_flow.InvalidIdentityError) as raised:
            records.advance_revision(self.record, fixture_record("revisions/seq-mutation.md"))
        self.assertIn("`seq` is immutable", str(raised.exception))
        self.assertEqual("seq", raised.exception.detail["field"])

    def test_a_namespace_mutation_is_refused(self):
        moved = fixture_record("valid/seq-001/intent.md")
        moved["metadata"]["namespace"] = OTHER_NAMESPACE
        with self.assertRaises(session_flow.InvalidIdentityError) as raised:
            records.advance_revision(self.record, moved)
        self.assertEqual("namespace", raised.exception.detail["field"])


class PathResolutionTest(unittest.TestCase):
    """Records are addressed by identity, never by a supplied path."""

    def test_identity_resolves_to_the_item_and_task_files(self):
        request = {"work_root": "/w", "seq": "SEQ-042"}
        self.assertEqual(Path("/w/seq-042/intent.md"), records.resolve_record_path(request))
        request["task"] = "A1"
        self.assertEqual(Path("/w/seq-042/tasks/A1.md"), records.resolve_record_path(request))

    def test_a_traversal_identity_is_refused(self):
        for identity in ("../../etc", "SEQ-042/../..", "/etc/passwd", "seq-042"):
            with self.subTest(identity=identity):
                with self.assertRaises(session_flow.InvalidIdentityError):
                    records.resolve_record_path({"work_root": "/w", "seq": identity})

    def test_a_missing_identity_is_refused(self):
        with self.assertRaises(session_flow.InvalidIdentityError):
            records.resolve_record_path({"work_root": "/w"})

    def test_a_path_outside_the_work_root_is_refused(self):
        with self.assertRaises(session_flow.InvalidIdentityError):
            records.ensure_within(Path("/w"), Path("/w/../other/intent.md"))


class CommandBoundaryTest(unittest.TestCase):
    """The dispatch table is complete and every family answers on the protocol."""

    @classmethod
    def setUpClass(cls):
        cls._workdir = tempfile.TemporaryDirectory()
        cls.root = work_root_with("valid/seq-001/intent.md", Path(cls._workdir.name))

    @classmethod
    def tearDownClass(cls):
        cls._workdir.cleanup()

    def test_dispatch_table_holds_every_command_family(self):
        self.assertEqual(COMMAND_FAMILIES, frozenset(CLI.DISPATCH))

    def test_every_family_returns_a_result_or_a_named_error(self):
        for command in sorted(CLI.DISPATCH):
            with self.subTest(command=command):
                arguments = [command, "--seq", "SEQ-001"] if command != "doctor" else [command]
                result, response = run_cli(self.root, *arguments)
                self.assertEqual(CLI.PROTOCOL_VERSION, response["protocol"])
                self.assertNotIn("Traceback", result.stderr)
                if response["ok"]:
                    self.assertIn("result", response)
                    continue
                code = response["error"]["code"]
                self.assertIn(code, session_flow.ERROR_CODES)
                self.assertNotEqual("internal", code)

    def test_an_unlanded_family_names_its_handler(self):
        target = "session_flow.unlanded:show"
        original = dict(CLI.DISPATCH)
        CLI.DISPATCH["show"] = target
        try:
            with self.assertRaises(session_flow.NotImplementedCommandError) as raised:
                CLI.run({"command": "show", "work_root": str(self.root), "seq": "SEQ-001"})
        finally:
            CLI.DISPATCH.clear()
            CLI.DISPATCH.update(original)
        self.assertEqual(target, raised.exception.detail["handler"])

    def test_doctor_reports_an_integer_protocol_version(self):
        _, response = run_cli(self.root, "doctor")
        report = response["result"]
        self.assertIsInstance(report["protocol"], int)
        self.assertNotEqual(report["protocol"], report["plugin_version"])
        self.assertEqual(COMMAND_FAMILIES, frozenset(report["commands"]))
        self.assertTrue(report["commands"]["doctor"]["available"])

    def test_doctor_reports_storage_and_limitations(self):
        _, response = run_cli(self.root, "doctor")
        storage = response["result"]["storage"]
        self.assertEqual(str(self.root / "_devdocs" / "work"), storage["work_root"])
        self.assertTrue(storage["work_root_present"])
        self.assertTrue(any("9p" in limitation for limitation in storage["limitations"]))

    def test_configured_work_path_is_honoured(self):
        with tempfile.TemporaryDirectory() as workdir:
            root = Path(workdir)
            (root / "records").mkdir()
            (root / ".session-flow.json").write_text(
                json.dumps({"paths": {"work": "records", "sequence": "SEQUENCE.md"}}), encoding="utf-8"
            )
            _, response = run_cli(root, "doctor")
            self.assertEqual(str(root / "records"), response["result"]["storage"]["work_root"])

    def test_taxonomy_defines_every_named_error_once(self):
        self.assertTrue(TAXONOMY.issubset(frozenset(session_flow.ERROR_CODES)))
        _, response = run_cli(self.root, "doctor")
        self.assertEqual(session_flow.ERROR_CODES, response["result"]["errors"])

    def test_an_unreadable_input_payload_is_a_named_request_error(self):
        _, response = run_cli(self.root, "capture", "--input", str(self.root / "absent.json"))
        self.assertEqual("invalid-request", response["error"]["code"])


class RuntimeGuardTest(unittest.TestCase):
    """An unsupported interpreter gets an install instruction, not a traceback."""

    def test_the_guard_passes_on_supported_versions(self):
        for version in ((3, 9, 0, "final", 0), (3, 12, 3, "final", 0), (4, 0, 0, "final", 0)):
            with self.subTest(version=version):
                self.assertIsNone(CLI.runtime_error(version))

    def test_the_guard_names_the_install_instruction(self):
        for version in ((2, 7, 18, "final", 0), (3, 6, 9, "final", 0), (3, 8, 10, "final", 0)):
            with self.subTest(version=version):
                error = CLI.runtime_error(version)
                self.assertEqual(session_flow.UnsupportedRuntimeError.code, error["code"])
                self.assertIn("Install Python 3.9 or newer", error["detail"]["install"])
                self.assertIn("3.9", error["detail"]["minimum"])

    def test_an_unsupported_interpreter_answers_on_the_protocol(self):
        result = subprocess.run(
            [sys.executable, "-B", "-c", GUARDED_RUN.format(path=str(ENTRYPOINT))],
            capture_output=True,
            text=True,
            check=False,
        )
        response = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("Install Python 3.9 or newer", result.stderr)
        self.assertEqual("unsupported-runtime", response["error"]["code"])

    def test_the_entrypoint_reports_the_instruction_for_consumers(self):
        with tempfile.TemporaryDirectory() as workdir:
            _, response = run_cli(Path(workdir), "doctor")
            runtime = response["result"]["runtime"]
            self.assertEqual("3.9", runtime["minimum_python"])
            self.assertIn("Install Python 3.9 or newer", runtime["install_instruction"])


ACCEPTED_ITEM = "acceptance/seq-002/intent.md"
ACCEPTED_TASK = "acceptance/seq-002/tasks/A1.md"
REFLOWED = "acceptance/reflowed-scope.md"
WIDENED = "acceptance/widened-scope.md"
AUTHORITY = {"actor": "maintainer", "authority": {"source": "user-request", "revision": "2026-09-07T09:00:00Z"}}
BASE_SCOPE = "Acceptance survives a reflow.\n\n* one item\n* another item\n"


def scope_record(scope: str, **metadata) -> dict:
    fields = {"format": 1, "namespace": NAMESPACE, "seq": "SEQ-100", "revision": 1}
    fields.update(metadata)
    return {
        "metadata": fields,
        "identity": records.validate_identity(fields),
        "scope": scope,
        "body": "",
    }


class ScopeNormalizationTest(unittest.TestCase):
    """A reflowed paragraph must not invalidate acceptance; a reworded one must."""

    equivalents = (
        ("rewrapped lines", "Acceptance survives\na reflow.\n\n* one item\n* another item"),
        ("other list markers", "Acceptance survives a reflow.\n\n- one item\n+ another item\n"),
        ("crlf and trailing space", "Acceptance survives a reflow.  \r\n\r\n* one  item\r\n* another item \r\n"),
        ("tabs and wrapped items", "Acceptance\tsurvives a reflow.\n\n*\tone item\n* another\n  item\n"),
    )

    def fingerprint(self, scope: str) -> str:
        return records.scope_fingerprint(scope_record(scope))

    def test_reflow_and_marker_changes_keep_the_fingerprint(self):
        expected = self.fingerprint(BASE_SCOPE)
        for label, variant in self.equivalents:
            with self.subTest(variant=label):
                self.assertEqual(expected, self.fingerprint(variant))

    def test_ordered_markers_are_unified(self):
        self.assertEqual(self.fingerprint("1) one\n2) two\n"), self.fingerprint("1.  one\n2. two"))

    def test_composed_and_decomposed_text_agree(self):
        self.assertEqual(
            self.fingerprint("Caf\u00e9 acceptance survives."),
            self.fingerprint("Cafe\u0301 acceptance survives."),
        )

    def test_separate_list_items_do_not_merge_into_a_paragraph(self):
        self.assertNotEqual(self.fingerprint("* one item\n* another item"), self.fingerprint("one item another item"))

    def test_a_reworded_scope_changes_the_fingerprint(self):
        widened = BASE_SCOPE + "* a third item\n"
        self.assertNotEqual(self.fingerprint(BASE_SCOPE), self.fingerprint(widened))


class FingerprintFieldGroupTest(unittest.TestCase):
    """The fingerprint covers meaning, and excludes progress, evidence, and ordering."""

    bindings = [{"name": "session-flow", "path": ".", "remote": "git@example.invalid:s/f.git"}]
    references = [{"path": "seq-100/spec.md", "role": "behaviour", "commit": "abc123"}]

    def setUp(self):
        self.record = scope_record(
            BASE_SCOPE,
            repositories=self.bindings,
            delivery={"target": "merged pull request"},
            references=self.references,
        )
        self.fingerprint = records.scope_fingerprint(self.record)

    def variant(self, **metadata) -> str:
        fields = dict(self.record["metadata"])
        fields.update(metadata)
        return records.scope_fingerprint(scope_record(self.record["scope"], **fields))

    def test_excluded_fields_never_change_the_fingerprint(self):
        excluded = {
            "lifecycle": "active",
            "priority": "P0",
            "order": 999,
            "title": "A different title",
            "provenance": {"source": "auto"},
            "evidence": [{"criteria": "anything", "result": "pass"}],
            "scope_checks": [{"kind": "same-meaning"}],
        }
        for field, value in excluded.items():
            with self.subTest(field=field):
                self.assertEqual(self.fingerprint, self.variant(**{field: value}))

    def test_included_fields_change_the_fingerprint(self):
        included = {
            "repositories": [{"name": "session-scribe", "path": "../session-scribe"}],
            "delivery": {"target": "released tag"},
            "references": [{"path": "seq-100/spec.md", "role": "behaviour", "commit": "def456"}],
        }
        for field, value in included.items():
            with self.subTest(field=field):
                self.assertNotEqual(self.fingerprint, self.variant(**{field: value}))

    def test_binding_order_does_not_change_the_fingerprint(self):
        pair = self.bindings + [{"name": "session-ops", "path": "../session-ops"}]
        self.assertEqual(self.variant(repositories=pair), self.variant(repositories=list(reversed(pair))))

    def test_a_reference_without_a_commit_is_refused(self):
        with self.assertRaises(session_flow.InvalidIdentityError) as raised:
            self.variant(references=[{"path": "seq-100/spec.md", "role": "behaviour"}])
        self.assertIn("work-root `commit`", str(raised.exception))


class AcceptanceFixtureTest(unittest.TestCase):
    """Applicability is derived from the stored fingerprint, not from a flag."""

    def test_the_accepted_item_applies_to_its_own_scope(self):
        status = records.acceptance_status(fixture_record(ACCEPTED_ITEM))
        self.assertEqual({"accepted": True, "applies": True}, {key: status[key] for key in ("accepted", "applies")})

    def test_a_whitespace_only_reflow_keeps_the_fingerprint(self):
        item, reflowed = fixture_record(ACCEPTED_ITEM), fixture_record(REFLOWED)
        self.assertNotEqual(item["scope"], reflowed["scope"])
        self.assertEqual(records.scope_fingerprint(item), records.scope_fingerprint(reflowed))
        self.assertTrue(records.acceptance_applies(reflowed))

    def test_a_widened_scope_loses_acceptance_and_evidence(self):
        widened = fixture_record(WIDENED)
        status = records.acceptance_status(widened)
        self.assertTrue(status["accepted"])
        self.assertFalse(status["applies"])
        self.assertIn("scope changed after acceptance", status["reason"])
        self.assertEqual([False], [entry["applies"] for entry in records.evidence_status(widened)])

    def test_a_task_record_carries_its_own_fingerprint(self):
        task = fixture_record(ACCEPTED_TASK)
        self.assertTrue(records.acceptance_applies(task))
        self.assertNotEqual(records.scope_fingerprint(fixture_record(ACCEPTED_ITEM)), records.scope_fingerprint(task))

    def test_an_unaccepted_record_gives_a_reason(self):
        status = records.acceptance_status(fixture_record("valid/seq-001/intent.md"))
        self.assertFalse(status["accepted"])
        self.assertIn("no acceptance", status["reason"])


class AuthorityTest(unittest.TestCase):
    """`[auto]` maps to provenance, never to authority."""

    refused = (
        ("no decision at all", {}),
        ("no actor", {"authority": {"source": "user-request", "revision": "r1"}}),
        ("no authority", {"actor": "maintainer"}),
        ("no authority revision", {"actor": "maintainer", "authority": {"source": "user-request"}}),
        ("blank actor", {"actor": "  ", "authority": {"source": "user-request", "revision": "r1"}}),
        ("auto source", {"actor": "maintainer", "authority": {"source": "auto", "revision": "r1"}}),
        ("marker source", {"actor": "maintainer", "authority": {"source": "[auto]", "revision": "r1"}}),
    )

    def test_a_decision_records_actor_authority_and_scope(self):
        provenance = records.require_authority(dict(AUTHORITY, scope=["implement"]), "accept")
        self.assertEqual("maintainer", provenance["actor"])
        self.assertEqual("user-request", provenance["authority"]["source"])
        self.assertEqual(["implement"], provenance["scope"])
        self.assertTrue(provenance["at"])

    def test_each_incomplete_decision_is_refused(self):
        for label, decision in self.refused:
            with self.subTest(decision=label):
                with self.assertRaises(session_flow.MissingAuthorityError):
                    records.require_authority(decision, "accept")


class LifecycleTest(unittest.TestCase):
    """Seven states, a fixed transition table, and a stable order."""

    def test_the_states_are_exactly_the_seven_named_states(self):
        self.assertEqual(
            ("captured", "accepted", "active", "blocked", "done", "deferred", "cancelled"),
            records.LIFECYCLE_STATES,
        )

    def test_a_legal_path_is_allowed(self):
        for current, target in (("captured", "accepted"), ("accepted", "active"), ("active", "done")):
            with self.subTest(transition=(current, target)):
                self.assertEqual(target, records.check_lifecycle_change(current, target))

    def test_an_illegal_transition_is_refused(self):
        for current, target in (("captured", "done"), ("captured", "active"), ("blocked", "done")):
            with self.subTest(transition=(current, target)):
                with self.assertRaises(session_flow.InvalidRequestError):
                    records.check_lifecycle_change(current, target)

    def test_reopening_closed_work_needs_a_correction(self):
        with self.assertRaises(session_flow.MissingAuthorityError) as raised:
            records.check_lifecycle_change("done", "active")
        self.assertIn("premature", str(raised.exception))
        self.assertEqual("active", records.check_lifecycle_change("done", "active", "closed before delivery"))

    def test_an_unknown_state_is_refused(self):
        with self.assertRaises(session_flow.InvalidRequestError):
            records.check_lifecycle_change("captured", "in-progress")

    def test_the_order_is_priority_then_order_then_identity(self):
        items = [
            scope_record("s", seq="SEQ-005", priority="P2", order=1),
            scope_record("s", seq="SEQ-002", priority="P1", order=5),
            scope_record("s", seq="SEQ-004", priority="P1", order=5),
            scope_record("s", seq="SEQ-003", priority="P1", order=2),
            scope_record("s", seq="SEQ-001"),
        ]
        ordered = [record["identity"]["seq"] for record in sorted(items, key=records.sort_key)]
        self.assertEqual(["SEQ-003", "SEQ-002", "SEQ-004", "SEQ-005", "SEQ-001"], ordered)


class MutationTest(unittest.TestCase):
    """Every write goes through the real entrypoint against a temporary root."""

    def setUp(self):
        workdir = tempfile.TemporaryDirectory()
        self.addCleanup(workdir.cleanup)
        self.base = Path(workdir.name)
        self.root = self.base / "project"
        self.work = self.root / "_devdocs" / "work"
        self.work.mkdir(parents=True)
        shutil.copytree(FIXTURES / "acceptance" / "seq-002", self.work / "seq-002")
        self.payloads = self.base / "payloads"
        self.payloads.mkdir()

    def payload_file(self, data: dict) -> str:
        path = self.payloads / ("payload-%d.json" % len(list(self.payloads.iterdir())))
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def call(self, command: str, data: dict, *identity: str):
        return run_cli(self.root, command, "--input", self.payload_file(data), *(identity or ("--seq", "SEQ-002")))

    def stored(self, relative: str = "seq-002/intent.md") -> dict:
        return records.parse_record((self.work / relative).read_text(encoding="utf-8"))

    def revise(self, **payload):
        payload.setdefault("expected_revision", 4)
        return self.call("revise", payload)


class AcceptanceApplicabilityTest(MutationTest):
    """A scope edit invalidates; a status-only edit and a reflow retain."""

    def test_a_meaning_changing_scope_edit_invalidates_acceptance(self):
        _, response = self.revise(scope=fixture_record(WIDENED)["scope"])
        result = response["result"]
        self.assertFalse(result["acceptance"]["applies"])
        self.assertNotEqual(result["previous_fingerprint"], result["fingerprint"])
        self.assertEqual([False], [entry["applies"] for entry in result["evidence"]])
        self.assertIsNone(result["scope_check"])
        self.assertFalse(records.acceptance_applies(self.stored()))
        self.assertEqual(5, self.stored()["identity"]["revision"])

    def test_a_status_only_edit_retains_acceptance(self):
        _, response = self.revise(metadata={"lifecycle": "active", "priority": "P0", "order": 1})
        result = response["result"]
        self.assertTrue(result["acceptance"]["applies"])
        self.assertEqual(result["previous_fingerprint"], result["fingerprint"])
        self.assertEqual("active", result["lifecycle"])
        self.assertEqual([True], [entry["applies"] for entry in result["evidence"]])
        self.assertTrue(records.acceptance_applies(self.stored()))

    def test_a_whitespace_only_reflow_retains_acceptance(self):
        reflowed = fixture_record(REFLOWED)["scope"]
        _, response = self.revise(scope=reflowed)
        result = response["result"]
        self.assertTrue(result["acceptance"]["applies"])
        self.assertEqual(result["previous_fingerprint"], result["fingerprint"])
        self.assertEqual(5, result["identity"]["revision"])
        self.assertNotEqual(fixture_record(ACCEPTED_ITEM)["scope"], self.stored()["scope"])

    def test_a_same_meaning_decision_records_both_fingerprints(self):
        decision = dict(AUTHORITY, scope=["implement"])
        _, response = self.revise(scope=fixture_record(WIDENED)["scope"], same_meaning=decision)
        check = response["result"]["scope_check"]
        self.assertEqual("same-meaning", check["kind"])
        self.assertTrue(check["previous_fingerprint"] and check["fingerprint"])
        self.assertNotEqual(check["previous_fingerprint"], check["fingerprint"])
        self.assertEqual("maintainer", check["actor"])
        self.assertEqual("user-request", check["authority"]["source"])
        self.assertTrue(response["result"]["acceptance"]["applies"])
        stored = self.stored()
        self.assertTrue(records.acceptance_applies(stored))
        self.assertEqual(
            ["accepted", "same-meaning"], [entry["kind"] for entry in stored["metadata"]["scope_checks"]]
        )

    def test_a_same_meaning_decision_without_authority_is_refused(self):
        before = snapshot(self.work)
        _, response = self.revise(scope="anything else entirely", same_meaning={"actor": "maintainer"})
        self.assertEqual("missing-authority", response["error"]["code"])
        self.assertEqual(before, snapshot(self.work))

    def test_two_scope_decisions_at_once_are_refused(self):
        _, response = self.revise(scope="x", same_meaning=AUTHORITY, preparation=AUTHORITY)
        self.assertEqual("invalid-request", response["error"]["code"])

    def test_a_preparation_change_keeps_acceptance_and_records_the_check(self):
        _, response = self.call(
            "revise",
            {
                "expected_revision": 2,
                "scope": "Collapse whitespace runs and apply NFC before fingerprinting the scope text.",
                "preparation": dict(AUTHORITY, scope=["implement"]),
            },
            "--seq",
            "SEQ-002",
            "--task",
            "A1",
        )
        check = response["result"]["scope_check"]
        self.assertEqual("preparation", check["kind"])
        self.assertTrue(response["result"]["acceptance"]["applies"])
        self.assertTrue(records.acceptance_applies(self.stored("seq-002/tasks/A1.md")))

    def test_a_preparation_change_without_applicable_acceptance_is_refused(self):
        shutil.copy(FIXTURES / WIDENED, self.work / "seq-002" / "intent.md")
        _, response = self.revise(expected_revision=5, scope="narrower still", preparation=AUTHORITY)
        self.assertEqual("missing-authority", response["error"]["code"])
        self.assertIn("applicable acceptance", response["error"]["message"])


class StaleRevisionTest(MutationTest):
    """A mutation carries the revision it expected, and a mismatch writes nothing."""

    def test_a_stale_expected_revision_fails_before_any_write(self):
        before = snapshot(self.work)
        result, response = self.revise(expected_revision=3, metadata={"priority": "P0"})
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertEqual("stale-revision", response["error"]["code"])
        self.assertEqual({"expected": 3, "held": 4}, response["error"]["detail"])
        self.assertEqual(before, snapshot(self.work))

    def test_a_stale_acceptance_fails_before_any_write(self):
        before = snapshot(self.work)
        _, response = self.call("accept", dict(AUTHORITY, expected_revision=1))
        self.assertEqual("stale-revision", response["error"]["code"])
        self.assertEqual(before, snapshot(self.work))

    def test_a_missing_expected_revision_is_a_named_request_error(self):
        before = snapshot(self.work)
        _, response = self.revise(expected_revision=None, metadata={"priority": "P0"})
        self.assertEqual("invalid-request", response["error"]["code"])
        self.assertIn("expected_revision", response["error"]["message"])
        self.assertEqual(before, snapshot(self.work))

    def test_an_unchanged_revision_keeps_the_record_at_its_revision(self):
        _, response = self.revise()
        self.assertEqual(4, response["result"]["identity"]["revision"])


class CaptureAndAcceptTest(MutationTest):
    """Capture grants no acceptance; acceptance needs a decision actor and authority."""

    payload = {
        "scope": "The runtime refuses to reuse an identity that already holds a record.",
        "body": "# SEQ-003\n\n## Original request\n\n\"Never hand me the same SEQ twice.\"",
        "metadata": {
            "title": "Refuse a duplicate capture",
            "lifecycle": "accepted",
            "acceptance": {"fingerprint": "forged", "actor": "nobody"},
            "repositories": [{"name": "session-flow", "path": "."}],
            "delivery": {"target": "merged pull request"},
            "references": [{"path": "seq-003/spec.md", "role": "criteria", "commit": "aa11bb22"}],
        },
    }

    def capture(self, **overrides):
        data = dict(self.payload)
        data.update(overrides)
        return run_cli(
            self.root, "capture", "--seq", "SEQ-003", "--namespace", NAMESPACE, "--input", self.payload_file(data)
        )

    def test_capture_writes_a_captured_record_and_grants_no_acceptance(self):
        _, response = self.capture()
        result = response["result"]
        self.assertEqual("captured", result["lifecycle"])
        self.assertEqual(1, result["identity"]["revision"])
        self.assertFalse(result["acceptance"]["accepted"])
        stored = self.stored("seq-003/intent.md")
        self.assertNotIn("acceptance", stored["metadata"])
        self.assertEqual("captured", stored["metadata"]["lifecycle"])
        self.assertIn("Never hand me the same SEQ twice", stored["body"])

    def test_a_second_capture_of_the_same_identity_is_refused(self):
        self.capture()
        before = snapshot(self.work)
        _, response = self.capture()
        self.assertEqual("invalid-identity", response["error"]["code"])
        self.assertEqual(before, snapshot(self.work))

    def test_an_auto_capture_records_provenance_and_not_authority(self):
        self.capture(auto=True)
        self.assertTrue(self.stored("seq-003/intent.md")["metadata"]["provenance"]["auto"])
        _, response = self.call(
            "accept",
            {"expected_revision": 1, "actor": "session-groom", "authority": {"source": "auto", "revision": "1"}},
            "--seq",
            "SEQ-003",
        )
        self.assertEqual("missing-authority", response["error"]["code"])

    def test_accept_binds_the_current_fingerprint_to_the_authority(self):
        self.capture()
        captured = self.stored("seq-003/intent.md")
        _, response = self.call(
            "accept", dict(AUTHORITY, expected_revision=1, scope=["implement", "create-pr"]), "--seq", "SEQ-003"
        )
        result = response["result"]
        self.assertEqual("accepted", result["lifecycle"])
        self.assertTrue(result["acceptance"]["applies"])
        acceptance = self.stored("seq-003/intent.md")["metadata"]["acceptance"]
        self.assertEqual(records.scope_fingerprint(captured), acceptance["fingerprint"])
        self.assertEqual("maintainer", acceptance["actor"])
        self.assertEqual(["implement", "create-pr"], acceptance["scope"])
        self.assertEqual(2, self.stored("seq-003/intent.md")["identity"]["revision"])

    def test_accept_without_authority_writes_nothing(self):
        self.capture()
        before = snapshot(self.work)
        _, response = self.call("accept", {"expected_revision": 1, "actor": "maintainer"}, "--seq", "SEQ-003")
        self.assertEqual("missing-authority", response["error"]["code"])
        self.assertEqual(before, snapshot(self.work))

    def test_re_acceptance_records_the_superseded_fingerprint(self):
        _, response = self.revise(scope=fixture_record(WIDENED)["scope"])
        superseded = response["result"]["previous_fingerprint"]
        _, response = self.call("accept", dict(AUTHORITY, expected_revision=5))
        self.assertTrue(response["result"]["acceptance"]["applies"])
        checks = self.stored()["metadata"]["scope_checks"]
        self.assertEqual(["accepted", "accepted"], [entry["kind"] for entry in checks])
        self.assertEqual(superseded, checks[-1]["previous_fingerprint"])

    def test_a_mutation_without_a_payload_is_a_named_request_error(self):
        _, response = run_cli(self.root, "revise", "--seq", "SEQ-002")
        self.assertEqual("invalid-request", response["error"]["code"])


if __name__ == "__main__":
    unittest.main()
