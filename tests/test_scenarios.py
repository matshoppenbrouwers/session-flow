"""Phase 4 lifecycle scenarios: bounded dispatch, dependency guards, resumed claims,
and a task result kept apart from a delivered outcome.

Two kinds of check live here, and the difference matters when one fails.

*Runtime checks* drive the real entrypoint against a copy of a scenario work root and
assert what the runtime answers: which candidate `select` returns, which record a claim
touches, which error a stale claim or a missing prerequisite raises, and whether
acceptance and evidence still apply after a scope edit.

*Contract checks* read the stop and gate tables out of the skills that instruct the
coordinating agent. A cycle, an overlapping write scope and an undelivered outcome are
decided by that agent from the records it loaded: the runtime supplies the records and
the error vocabulary, not the decision. Every code those tables name is checked against
the runtime's own `ERROR_CODES`, so an invented error fails, and each scenario fixture
is checked to really exhibit the condition its manifest claims.
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
SCENARIOS = REPO_ROOT / "tests" / "fixtures" / "lifecycle" / "scenarios"
SKILLS = REPO_ROOT / "skills"
DELEGATION_SKILL = SKILLS / "session-delegation" / "SKILL.md"
VERIFY_SKILL = SKILLS / "session-verify" / "SKILL.md"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from session_flow import ERROR_CODES, records  # noqa: E402

STOP_HEADER = "Stop condition"
GATE_HEADER = "Completion is refused when"


def manifest(scenario: str) -> dict:
    return json.loads((SCENARIOS / scenario / "scenario.json").read_text(encoding="utf-8"))


def manifests(key: str) -> list:
    documents = [manifest(path.parent.name) for path in sorted(SCENARIOS.glob("*/scenario.json"))]
    return [document for document in documents if key in document]


def task_records(work_root: Path, seq: str) -> dict:
    directory = work_root / records.item_directory(seq) / records.TASKS_DIRECTORY
    return {
        path.stem: records.read_record(path)["metadata"]
        for path in sorted(directory.glob("*.md"))
        if not path.name.startswith("_")
    }


def dependency_cycles(work_root: Path, seq: str) -> list:
    """Every dependency chain among an item's tasks that closes on itself."""
    metadata = task_records(work_root, seq)
    edges = {f"{seq}/{task}": list(fields.get("depends_on") or []) for task, fields in metadata.items()}
    found = []

    def walk(node: str, chain: list) -> None:
        if node in chain:
            found.append(chain[chain.index(node):] + [node])
            return
        for prerequisite in edges.get(node, []):
            walk(prerequisite, chain + [node])

    for identity in edges:
        walk(identity, [])
    return found


def overlapping_scopes(work_root: Path, seq: str) -> list:
    """Every pair of tasks that declare a shared allowed path."""
    metadata = task_records(work_root, seq)
    identities = sorted(metadata)
    overlaps = []
    for index, first in enumerate(identities):
        for second in identities[index + 1:]:
            shared = sorted(
                set(metadata[first].get("allowed_paths") or [])
                & set(metadata[second].get("allowed_paths") or [])
            )
            if shared:
                overlaps.append((f"{seq}/{first}", f"{seq}/{second}", shared))
    return overlaps


def table_rows(text: str, header: str) -> list:
    """The cells of every row of the one Markdown table whose header names `header`."""
    rows, inside = [], False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            inside = False
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if header in cells:
            inside = True
            continue
        if inside and set(cells[0]) <= set("-: "):
            continue
        if inside:
            rows.append(cells)
    return rows


def named_error(cell: str) -> str:
    return cell.strip().strip("`")


def instructed_stop(text: str, header: str, match: str) -> str | None:
    """The named error the table gives for the condition containing `match`, if any."""
    for cells in table_rows(text, header):
        if match.lower() in cells[0].lower():
            return named_error(cells[1])
    return None


def snapshot(root: Path) -> dict:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*.md"))
        if path.is_file()
    }


class ScenarioCase(unittest.TestCase):
    """A disposable project holding one scenario's work root."""

    scenario = ""

    def setUp(self):
        directory = tempfile.mkdtemp(prefix="session-flow-scenario-")
        self.addCleanup(shutil.rmtree, directory, True)
        self.project = Path(directory)
        self.root = self.project / "_devdocs" / "work"
        self.root.parent.mkdir(parents=True)
        shutil.copytree(SCENARIOS / self.scenario / "work", self.root)
        self.manifest = manifest(self.scenario)

    def run_cli(self, command: str, *arguments, payload=None) -> dict:
        call = [sys.executable, "-B", str(ENTRYPOINT), command, "--project-root", str(self.project)]
        if payload is not None:
            path = self.project / f"payload-{len(list(self.project.glob('payload-*.json')))}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            call += ["--input", str(path)]
        completed = subprocess.run(call + list(arguments), capture_output=True, text=True, check=False)
        return json.loads(completed.stdout)

    def result(self, command: str, *arguments, payload=None) -> dict:
        answer = self.run_cli(command, *arguments, payload=payload)
        self.assertTrue(answer["ok"], answer.get("error"))
        return answer["result"]

    def error(self, command: str, *arguments, payload=None) -> dict:
        answer = self.run_cli(command, *arguments, payload=payload)
        self.assertFalse(answer["ok"], answer.get("result"))
        return answer["error"]

    def metadata(self, seq: str, task=None) -> dict:
        arguments = ["--seq", seq] + (["--task", task] if task else [])
        return self.result("show", *arguments)["metadata"]


class BoundedSelectionTest(ScenarioCase):
    """`select` answers with one candidate, and a named identity cannot widen to another."""

    scenario = "bounded"

    def test_one_candidate_is_returned_with_reasons_for_the_rest(self):
        answer = self.result("select")
        self.assertEqual("SEQ-101", answer["candidate"]["seq"])
        self.assertEqual(3, len(answer["considered"]))
        self.assertEqual(2, answer["eligible"])

    def test_a_named_identity_answers_about_that_identity_only(self):
        answer = self.result("select", "--seq", "SEQ-102")
        self.assertEqual("SEQ-102", answer["candidate"]["seq"])
        self.assertEqual(["SEQ-102"], [entry["seq"] for entry in answer["considered"]])

    def test_captured_work_outranks_nothing(self):
        answer = self.result("select", "--seq", "SEQ-103")
        self.assertIsNone(answer["candidate"])
        reasons = answer["considered"][0]["reasons"]
        self.assertTrue(any("captured" in reason for reason in reasons), reasons)


class BoundedClaimTest(ScenarioCase):
    """A dispatch request naming one task claims that task and leaves the rest alone."""

    scenario = "bounded"

    def claim_payload(self, task: str, actor: str, operation: str, revision=2) -> dict:
        return {
            "operation": operation,
            "coordinator": "session-delegation",
            "actor": actor,
            "seq": "SEQ-101",
            "task": task,
            "expect_revision": revision,
            "allowed_paths": ["scripts/session_flow/store.py", "tests/test_store.py"],
        }

    def test_a_claim_touches_only_the_named_record(self):
        before = snapshot(self.root)
        answer = self.result(
            "claim", "--seq", "SEQ-101", "--task", "A1",
            payload=self.claim_payload("A1", "agent:store", "dispatch-0001"),
        )
        self.assertEqual(["A1"], [entry["task"] for entry in answer["records"]])
        after = snapshot(self.root)
        self.assertEqual(
            ["seq-101/tasks/A1.md"],
            sorted(name for name in before if before[name] != after.get(name)),
        )
        self.assertEqual(sorted(before), sorted(name for name in after if name in before))

    def test_the_dispatch_set_does_not_reach_the_dependent_task(self):
        self.result(
            "claim", "--seq", "SEQ-101", "--task", "A1",
            payload=self.claim_payload("A1", "agent:store", "dispatch-0002"),
        )
        self.assertIn("claim", self.metadata("SEQ-101", "A1"))
        self.assertNotIn("claim", self.metadata("SEQ-101", "A2"))

    def test_a_stale_claim_stops_the_second_actor(self):
        self.result(
            "claim", "--seq", "SEQ-101", "--task", "A1",
            payload=self.claim_payload("A1", "agent:store", "dispatch-0003"),
        )
        error = self.error(
            "claim", "--seq", "SEQ-101", "--task", "A1",
            payload=self.claim_payload("A1", "agent:other", "dispatch-0004", revision=3),
        )
        stop = self.manifest["stop"]
        self.assertEqual(stop["code"], error["code"])
        self.assertEqual("agent:store", error["detail"]["actor"])
        self.assertEqual("agent:store", self.metadata("SEQ-101", "A1")["claim"]["actor"])
        self.assertEqual(
            stop["code"],
            instructed_stop(DELEGATION_SKILL.read_text(encoding="utf-8"), STOP_HEADER, stop["match"]),
        )

    def test_only_the_claiming_actor_records_the_result(self):
        self.result(
            "claim", "--seq", "SEQ-101", "--task", "A1",
            payload=self.claim_payload("A1", "agent:store", "dispatch-0005"),
        )
        error = self.error(
            "record-result", "--seq", "SEQ-101", "--task", "A1",
            payload={
                "operation": "result-0001",
                "actor": "agent:other",
                "seq": "SEQ-101",
                "task": "A1",
                "expect_revision": 3,
                "result": {"outcome": "passed"},
            },
        )
        self.assertEqual("missing-authority", error["code"])


class ResumedClaimTest(ScenarioCase):
    """An interrupted coordinator resumes its assignment; it does not take a second one."""

    scenario = "bounded"
    PAYLOAD = {
        "operation": "dispatch-resumed",
        "coordinator": "session-delegation",
        "actor": "agent:store",
        "seq": "SEQ-101",
        "task": "A1",
        "expect_revision": 2,
        "allowed_paths": ["scripts/session_flow/store.py"],
    }

    def test_the_same_operation_recovers_the_bounded_assignment(self):
        first = self.result("claim", "--seq", "SEQ-101", "--task", "A1", payload=dict(self.PAYLOAD))
        resumed = self.result("claim", "--seq", "SEQ-101", "--task", "A1", payload=dict(self.PAYLOAD))
        self.assertFalse(first["replayed"])
        self.assertTrue(resumed["replayed"])
        self.assertEqual(
            [entry["revision"] for entry in first["records"]],
            [entry["revision"] for entry in resumed["records"]],
        )
        claim = self.metadata("SEQ-101", "A1")["claim"]
        self.assertEqual("agent:store", claim["actor"])
        self.assertEqual(["scripts/session_flow/store.py"], claim["allowed_paths"])
        self.assertEqual(3, self.metadata("SEQ-101", "A1")["revision"])

    def test_the_same_operation_cannot_carry_another_assignment(self):
        self.result("claim", "--seq", "SEQ-101", "--task", "A1", payload=dict(self.PAYLOAD))
        error = self.error(
            "claim", "--seq", "SEQ-101", "--task", "A2",
            payload=dict(self.PAYLOAD, task="A2", expect_revision=2),
        )
        self.assertEqual("invalid-identity", error["code"])
        self.assertNotIn("claim", self.metadata("SEQ-101", "A2"))


class UnknownPrerequisiteTest(ScenarioCase):
    """A `depends_on` entry naming no record stops dispatch with the runtime's own error."""

    scenario = "unknown-prerequisite"

    def test_the_prerequisite_is_named_by_the_task(self):
        self.assertEqual(["SEQ-201/A9"], self.metadata("SEQ-201", "A1")["depends_on"])

    def test_the_named_prerequisite_has_no_record(self):
        error = self.error("show", "--seq", "SEQ-201", "--task", "A9")
        self.assertEqual(self.manifest["stop"]["code"], error["code"])

    def test_the_stop_is_instructed_with_that_error(self):
        stop = self.manifest["stop"]
        self.assertEqual(
            stop["code"],
            instructed_stop(DELEGATION_SKILL.read_text(encoding="utf-8"), STOP_HEADER, stop["match"]),
        )


class DependencyGraphTest(unittest.TestCase):
    """The cycle and write-scope conditions are decided by the coordinating agent from the
    task records. These checks prove the fixtures really carry the condition, and that the
    clean scenario carries neither."""

    def test_the_cycle_scenario_closes_on_itself(self):
        found = dependency_cycles(SCENARIOS / "dependency-cycle" / "work", "SEQ-301")
        self.assertTrue(found, "the fixture no longer contains a dependency cycle")
        self.assertEqual({"SEQ-301/A1", "SEQ-301/A2"}, set(found[0]))

    def test_the_overlap_scenario_shares_a_path(self):
        found = overlapping_scopes(SCENARIOS / "overlapping-scope" / "work", "SEQ-401")
        self.assertEqual(
            [("SEQ-401/A1", "SEQ-401/A2", ["scripts/session_flow/records.py"])], found
        )

    def test_the_bounded_scenario_carries_neither_condition(self):
        work = SCENARIOS / "bounded" / "work"
        self.assertEqual([], dependency_cycles(work, "SEQ-101"))
        self.assertEqual([], overlapping_scopes(work, "SEQ-101"))


class StopContractTest(unittest.TestCase):
    """Every scenario stop is instructed, and every instructed error is a real runtime code."""

    def setUp(self):
        self.text = DELEGATION_SKILL.read_text(encoding="utf-8")

    def test_every_scenario_stop_is_instructed(self):
        for document in manifests("stop"):
            with self.subTest(scenario=document["scenario"]):
                stop = document["stop"]
                self.assertEqual(stop["code"], instructed_stop(self.text, STOP_HEADER, stop["match"]))

    def test_the_five_dispatch_stops_are_present(self):
        rows = table_rows(self.text, STOP_HEADER)
        self.assertEqual(5, len(rows), [row[0] for row in rows])

    def test_every_instructed_error_is_a_runtime_code(self):
        for cells in table_rows(self.text, STOP_HEADER):
            with self.subTest(condition=cells[0]):
                self.assertIn(named_error(cells[1]), ERROR_CODES)

    def test_a_removed_stop_is_detected(self):
        stop = manifest("dependency-cycle")["stop"]
        without = "\n".join(
            line for line in self.text.splitlines() if stop["match"] not in line
        )
        self.assertIsNone(instructed_stop(without, STOP_HEADER, stop["match"]))

    def test_an_invented_error_is_detected(self):
        invented = self.text.replace("| `invalid-request` |", "| `overlapping-scope` |")
        codes = [named_error(cells[1]) for cells in table_rows(invented, STOP_HEADER)]
        self.assertNotIn("overlapping-scope", ERROR_CODES)
        self.assertIn("overlapping-scope", codes)


class UnmergedDeliveryTest(ScenarioCase):
    """Every task passed; the accepted outcome still needs its delivery target."""

    scenario = "unmerged-delivery"

    def test_every_task_passed(self):
        for task in ("A1", "A2"):
            with self.subTest(task=task):
                metadata = self.metadata("SEQ-501", task)
                self.assertEqual("done", metadata["lifecycle"])
                self.assertEqual("passed", metadata["result"]["outcome"])

    def test_the_parent_is_not_done_and_holds_no_delivery_evidence(self):
        metadata = self.metadata("SEQ-501")
        self.assertEqual("active", metadata["lifecycle"])
        self.assertEqual("merged pull request", metadata["delivery"]["target"])
        self.assertNotIn("evidence", metadata)

    def test_the_parent_stays_out_of_the_done_count(self):
        answer = self.result("select", "--seq", "SEQ-501")
        self.assertEqual({"total": 2, "done": 2}, answer["candidate"]["task_counts"])
        self.assertEqual("active", answer["candidate"]["lifecycle"])

    def test_the_refusing_gate_is_instructed(self):
        gate = self.manifest["completion_gate"]
        self.assertEqual(
            gate["code"],
            instructed_stop(VERIFY_SKILL.read_text(encoding="utf-8"), GATE_HEADER, gate["match"]),
        )


class StaleEvidenceTest(ScenarioCase):
    """Evidence applies to the fingerprint it was gathered against, and to no other."""

    scenario = "stale-evidence"
    REFLOWED = (
        "A stored verdict is evidence about the revision it was recorded against: "
        "release compares the recorded revision with the candidate and refuses to infer coverage.\n"
    )
    WIDENED = (
        "A stored verdict is evidence about the revision it was recorded against: release compares\n"
        "the recorded revision with the candidate and refuses to infer coverage. Release also blocks\n"
        "the candidate when any satellite site still names the previous version.\n"
    )

    def revise(self, scope: str) -> dict:
        return self.result(
            "revise", "--seq", "SEQ-601", payload={"expected_revision": 3, "scope": scope}
        )

    def test_reflowing_the_scope_keeps_acceptance_and_evidence_applicable(self):
        answer = self.revise(self.REFLOWED)
        self.assertEqual(answer["previous_fingerprint"], answer["fingerprint"])
        self.assertTrue(answer["acceptance"]["applies"], answer["acceptance"])
        self.assertEqual([True], [entry["applies"] for entry in answer["evidence"]])

    def test_a_meaning_change_makes_acceptance_and_evidence_inapplicable(self):
        answer = self.revise(self.WIDENED)
        self.assertNotEqual(answer["previous_fingerprint"], answer["fingerprint"])
        self.assertTrue(answer["acceptance"]["accepted"])
        self.assertFalse(answer["acceptance"]["applies"], answer["acceptance"])
        self.assertEqual([False], [entry["applies"] for entry in answer["evidence"]])

    def test_stale_scope_stops_selection_with_a_reason(self):
        self.revise(self.WIDENED)
        answer = self.result("select", "--seq", "SEQ-601")
        self.assertIsNone(answer["candidate"])
        reasons = answer["considered"][0]["reasons"]
        self.assertTrue(any("scope is now" in reason for reason in reasons), reasons)

    def test_the_refusing_gate_is_instructed(self):
        gate = self.manifest["completion_gate"]
        self.assertEqual(
            gate["code"],
            instructed_stop(VERIFY_SKILL.read_text(encoding="utf-8"), GATE_HEADER, gate["match"]),
        )


class UnknownOutcomeTest(ScenarioCase):
    """An outcome nobody observed is recorded as unknown, and stays unknown."""

    scenario = "bounded"
    CLAIM = {
        "operation": "dispatch-unknown",
        "coordinator": "session-delegation",
        "actor": "agent:store",
        "seq": "SEQ-101",
        "task": "A1",
        "expect_revision": 2,
        "allowed_paths": ["scripts/session_flow/store.py"],
    }

    def setUp(self):
        super().setUp()
        self.result("claim", "--seq", "SEQ-101", "--task", "A1", payload=dict(self.CLAIM))

    def record(self, outcome: str) -> dict:
        return {
            "operation": f"result-{outcome}",
            "actor": "agent:store",
            "seq": "SEQ-101",
            "task": "A1",
            "expect_revision": 3,
            "result": {"outcome": outcome, "checks": [{"command": "pytest", "observed": "not run"}]},
        }

    def test_an_unknown_outcome_is_stored_as_unknown(self):
        self.result("record-result", "--seq", "SEQ-101", "--task", "A1", payload=self.record("unknown"))
        metadata = self.metadata("SEQ-101", "A1")
        self.assertEqual("unknown", metadata["result"]["outcome"])
        self.assertEqual("accepted", metadata["lifecycle"])

    def test_the_refusing_gate_is_instructed(self):
        gate = self.manifest["completion_gate"]
        self.assertEqual(
            gate["code"],
            instructed_stop(VERIFY_SKILL.read_text(encoding="utf-8"), GATE_HEADER, gate["match"]),
        )

    def test_an_outcome_outside_the_vocabulary_is_refused(self):
        error = self.error(
            "record-result", "--seq", "SEQ-101", "--task", "A1", payload=self.record("ok")
        )
        self.assertEqual("invalid-request", error["code"])
        self.assertNotIn("result", self.metadata("SEQ-101", "A1"))


class ReopeningTest(ScenarioCase):
    """A premature closure reopens under the same identity, with a correction."""

    scenario = "unmerged-delivery"

    def reopen(self, correction=None) -> dict:
        payload = {
            "expected_revision": 2,
            "actor": "agent:installer",
            "metadata": {"lifecycle": "active"},
        }
        if correction is not None:
            payload["correction"] = correction
        return payload

    def test_reopening_without_a_correction_is_refused(self):
        error = self.error("revise", "--seq", "SEQ-501", "--task", "A1", payload=self.reopen())
        self.assertEqual("missing-authority", error["code"])
        self.assertEqual("done", self.metadata("SEQ-501", "A1")["lifecycle"])

    def test_reopening_with_a_correction_keeps_the_identity(self):
        correction = {"reason": "the installer never copied the audit references", "actor": "maintainer"}
        answer = self.result(
            "revise", "--seq", "SEQ-501", "--task", "A1", payload=self.reopen(correction)
        )
        self.assertEqual("active", answer["lifecycle"])
        self.assertEqual("SEQ-501", answer["identity"]["seq"])
        self.assertEqual([correction], self.metadata("SEQ-501", "A1")["corrections"])


class CompletionGateContractTest(unittest.TestCase):
    """Every scenario gate is instructed, and every instructed error is a real runtime code."""

    def setUp(self):
        self.text = VERIFY_SKILL.read_text(encoding="utf-8")

    def test_every_scenario_gate_is_instructed(self):
        for document in manifests("completion_gate"):
            with self.subTest(scenario=document["scenario"]):
                gate = document["completion_gate"]
                self.assertEqual(gate["code"], instructed_stop(self.text, GATE_HEADER, gate["match"]))

    def test_the_five_completion_gates_are_present(self):
        rows = table_rows(self.text, GATE_HEADER)
        self.assertEqual(5, len(rows), [row[0] for row in rows])

    def test_every_instructed_error_is_a_runtime_code(self):
        for cells in table_rows(self.text, GATE_HEADER):
            with self.subTest(refusal=cells[0]):
                self.assertIn(named_error(cells[1]), ERROR_CODES)

    def test_a_removed_gate_is_detected(self):
        gate = manifest("unmerged-delivery")["completion_gate"]
        without = "\n".join(line for line in self.text.splitlines() if gate["match"] not in line)
        self.assertIsNone(instructed_stop(without, GATE_HEADER, gate["match"]))


if __name__ == "__main__":
    unittest.main()
