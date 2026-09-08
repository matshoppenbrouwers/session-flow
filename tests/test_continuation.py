"""Phase 6 continuation scenarios: what bounds a run that spans several units.

`ContinuationRun` is the scenario runner. It performs the loop `/session-next`
instructs — re-resolve the standing policy, select, resolve one unit, claim,
record — against a copy of a scenario project and the real entrypoint, and it
records where the loop stopped and why. Each scenario's `scenario.json` names the
outcomes to record, the units that should run, and the stop the run should reach,
so a runner that continues past a bound disagrees with the manifest.

A task with a recorded result is finished as far as continuation is concerned:
`record-result` writes the result, and moving the record to `done` is a separate
transition the coordinator makes later.

The contract checks read the stop table out of `/session-next` and the
continuation rules out of `/session-delegation`. Those stops are decided by the
coordinating agent from what the runtime answered, so the instruction is where
they live; every error the table names is checked against the runtime's own
`ERROR_CODES`, and every reason a manifest expects is checked against the table.
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
SCENARIOS = REPO_ROOT / "tests" / "fixtures" / "lifecycle" / "continuation"
NEXT_SKILL = REPO_ROOT / "skills" / "session-next" / "SKILL.md"
DELEGATION_SKILL = REPO_ROOT / "skills" / "session-delegation" / "SKILL.md"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from session_flow import ERROR_CODES, records  # noqa: E402

CONFIG_FILE = ".session-flow.json"
POLICY_KEY = "continuation"
POLICY_KEYS = ("authority", "capacity", "scope", "stop_conditions")
CONDITIONS = ("result-not-passed", "delivery-outstanding")
CAPACITY_SPENT = "capacity-exhausted"
CONDITION_MET = "stop-condition-met"
NO_CANDIDATE = "no-candidate"
NO_AUTHORITY = "missing-authority"
COORDINATOR_REASONS = (CAPACITY_SPENT, CONDITION_MET, NO_CANDIDATE)
STOP_HEADER = "Continuation stop"
MAX_ROUNDS = 12


def manifest(scenario: str) -> dict:
    return json.loads((SCENARIOS / scenario / "scenario.json").read_text(encoding="utf-8"))


def manifests() -> list:
    return [manifest(path.parent.name) for path in sorted(SCENARIOS.glob("*/scenario.json"))]


def read_config(project: Path) -> dict:
    return json.loads((project / CONFIG_FILE).read_text(encoding="utf-8"))


def write_config(project: Path, config: dict) -> None:
    (project / CONFIG_FILE).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def standing_policy(project: Path) -> dict | None:
    """The policy in force right now, or None when nothing authorizes continuation.

    Read from disk on every call: a policy withdrawn or edited mid-run is gone
    from the next round, and a malformed one authorizes nothing.
    """
    policy = read_config(project).get(POLICY_KEY)
    if not isinstance(policy, dict) or any(key not in policy for key in POLICY_KEYS):
        return None
    source = (policy["authority"] or {}).get("source")
    if not isinstance(source, str) or source.strip().lower() in records.PROVENANCE_SOURCES:
        return None
    if type((policy["capacity"] or {}).get("units")) is not int:
        return None
    if any(token not in CONDITIONS for token in policy["stop_conditions"]):
        return None
    return policy


def policy_covers(policy: dict, seq: str, action: str) -> bool:
    scope = policy.get("scope") or {}
    return seq in (scope.get("seq") or []) and action in (scope.get("actions") or [])


class ContinuationRun:
    """One continuation loop, driven against the entrypoint. Holds the run's state."""

    def __init__(self, project: Path, scenario: dict, action="implement"):
        self.project = project
        self.scenario = scenario
        self.action = action
        self.units = []
        self.stop = None

    def call(self, command: str, *arguments, payload=None) -> dict:
        call = [sys.executable, "-B", str(ENTRYPOINT), command, "--project-root", str(self.project)]
        if payload is not None:
            path = self.project / f"payload-{len(list(self.project.glob('payload-*.json')))}.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            call += ["--input", str(path)]
        completed = subprocess.run(call + list(arguments), capture_output=True, text=True, check=False)
        return json.loads(completed.stdout)

    def metadata(self, seq: str, task=None) -> dict:
        arguments = ["--seq", seq] + (["--task", task] if task else [])
        body = self.call("show", *arguments)
        return body["result"]["metadata"]

    def stopped(self, reason: str, detail: str, condition=None) -> None:
        self.stop = {"reason": reason, "detail": detail, "condition": condition}

    def run(self) -> "ContinuationRun":
        for _ in range(MAX_ROUNDS):
            if self.stop is not None:
                return self
            self.round()
        raise AssertionError("the continuation loop ran past its bound without stopping")

    def round(self) -> None:
        policy = standing_policy(self.project)
        if policy is None:
            return self.stopped(NO_AUTHORITY, "no standing policy is in force")
        if len(self.units) >= policy["capacity"]["units"]:
            return self.stopped(CAPACITY_SPENT, f"{len(self.units)} of {policy['capacity']['units']} units run")
        candidate = self.call("select")["result"]["candidate"]
        if candidate is None:
            return self.stopped(NO_CANDIDATE, "select returned no eligible item")
        if not policy_covers(policy, candidate["seq"], self.action):
            return self.stopped(NO_AUTHORITY, f"the policy does not cover {candidate['seq']}/{self.action}")
        unit = self.next_unit(candidate)
        if unit is None:
            return self.stopped(NO_CANDIDATE, f"{candidate['seq']} has no unit left to run")
        self.execute(policy, candidate, unit)

    def next_unit(self, candidate: dict) -> dict | None:
        """The first task carrying no result whose prerequisites are satisfied."""
        for entry in candidate["tasks"]:
            unit = self.metadata(candidate["seq"], entry["task"])
            if unit.get("result") is None and self.prerequisites_met(unit):
                return unit
        return None

    def prerequisites_met(self, unit: dict) -> bool:
        for identity in unit.get("depends_on") or []:
            seq, _, task = identity.partition("/")
            prerequisite = self.metadata(seq, task or None)
            outcome = (prerequisite.get("result") or {}).get("outcome")
            if outcome != "passed" and prerequisite.get("lifecycle") != "done":
                return False
        return True

    def execute(self, policy: dict, candidate: dict, unit: dict) -> None:
        seq, task = unit["seq"], unit["task"]
        claimed = self.claim(unit)
        if not claimed["ok"]:
            return self.stopped(claimed["error"]["code"], claimed["error"]["message"])
        self.apply_revocation(len(self.units) + 1)
        outcome = self.scenario["outcomes"][task]
        self.record(unit, outcome)
        self.units.append(f"{seq}/{task}")
        condition = self.condition_met(policy, candidate, outcome)
        if condition is not None:
            self.stopped(CONDITION_MET, f"{seq}/{task} met {condition}", condition)

    def claim(self, unit: dict) -> dict:
        payload = {
            "operation": f"continue-{len(self.units):04d}",
            "coordinator": "session-next",
            "actor": f"agent:{unit['task']}",
            "seq": unit["seq"],
            "task": unit["task"],
            "expect_revision": unit["revision"],
            "allowed_paths": unit.get("allowed_paths") or [],
        }
        return self.call("claim", "--seq", unit["seq"], "--task", unit["task"], payload=payload)

    def record(self, unit: dict, outcome: str) -> dict:
        """A claimed unit's result is recorded even when authority was withdrawn while it ran."""
        held = self.metadata(unit["seq"], unit["task"])
        payload = {
            "operation": f"result-{len(self.units):04d}",
            "coordinator": "session-next",
            "actor": f"agent:{unit['task']}",
            "seq": unit["seq"],
            "task": unit["task"],
            "expect_revision": held["revision"],
            "result": {
                "outcome": outcome,
                "checks": [{"command": "python3 -B -m unittest", "observed": outcome}],
            },
        }
        return self.call(
            "record-result", "--seq", unit["seq"], "--task", unit["task"], payload=payload
        )

    def apply_revocation(self, unit_number: int) -> None:
        if self.scenario.get("revoke_after_claim") != unit_number:
            return
        config = read_config(self.project)
        config.pop(POLICY_KEY, None)
        write_config(self.project, config)

    def condition_met(self, policy: dict, candidate: dict, outcome: str) -> str | None:
        conditions = policy["stop_conditions"]
        if "result-not-passed" in conditions and outcome != "passed":
            return "result-not-passed"
        if "delivery-outstanding" in conditions and delivery_outstanding(candidate["path"]):
            return "delivery-outstanding"
        return None


def delivery_outstanding(path) -> bool:
    """The item owes a delivery target and holds no evidence that applies to its scope."""
    record = records.read_record(Path(path))
    if not record["metadata"].get("delivery"):
        return False
    applicable = [entry for entry in records.evidence_status(record) if entry["applies"]]
    return records.lifecycle_of(record) != "done" and not applicable


class ContinuationCase(unittest.TestCase):
    """A disposable copy of one scenario's project."""

    scenario = ""

    def setUp(self):
        directory = tempfile.mkdtemp(prefix="session-flow-continuation-")
        self.addCleanup(shutil.rmtree, directory, True)
        self.project = Path(directory) / "project"
        shutil.copytree(SCENARIOS / self.scenario / "project", self.project)
        self.manifest = manifest(self.scenario)
        self.expected = self.manifest["expected"]

    def continuation(self) -> ContinuationRun:
        return ContinuationRun(self.project, self.manifest).run()

    def untouched(self, run: ContinuationRun) -> None:
        for task in self.manifest["untouched"]:
            with self.subTest(task=task):
                metadata = run.metadata(self.manifest["seq"], task)
                self.assertNotIn("claim", metadata)
                self.assertNotIn("result", metadata)

    def assert_stop(self, run: ContinuationRun) -> None:
        self.assertEqual(self.expected["units"], run.units)
        self.assertEqual(self.expected["reason"], run.stop["reason"])
        self.assertEqual(self.expected["condition"], run.stop["condition"])


class CapacityTest(ContinuationCase):
    """Three eligible units, capacity for two: the run stops at the bound it was given."""

    scenario = "capacity"

    def test_the_run_stops_when_the_capacity_is_spent(self):
        run = self.continuation()
        self.assert_stop(run)
        self.assertIn("2 of 2 units run", run.stop["detail"])

    def test_the_unit_beyond_the_capacity_is_never_claimed(self):
        self.untouched(self.continuation())

    def test_the_units_that_ran_recorded_their_results(self):
        run = self.continuation()
        for identity in run.units:
            with self.subTest(identity=identity):
                seq, _, task = identity.partition("/")
                self.assertEqual("passed", run.metadata(seq, task)["result"]["outcome"])

    def test_a_wider_capacity_would_have_reached_the_third_unit(self):
        config = read_config(self.project)
        config[POLICY_KEY]["capacity"]["units"] = 4
        write_config(self.project, config)
        run = self.continuation()
        self.assertEqual(["SEQ-701/A1", "SEQ-701/A2", "SEQ-701/A3"], run.units)
        self.assertEqual(NO_CANDIDATE, run.stop["reason"])


class StopConditionTest(ContinuationCase):
    """Capacity is ample; the configured condition ends the run instead."""

    scenario = "stop-condition"

    def test_the_run_stops_on_the_configured_condition(self):
        run = self.continuation()
        self.assert_stop(run)
        self.assertEqual("failed", run.metadata("SEQ-702", "A2")["result"]["outcome"])

    def test_the_unit_after_the_condition_is_never_claimed(self):
        self.untouched(self.continuation())

    def test_without_the_condition_the_failure_does_not_stop_the_run(self):
        config = read_config(self.project)
        config[POLICY_KEY]["stop_conditions"] = []
        write_config(self.project, config)
        run = self.continuation()
        self.assertEqual(["SEQ-702/A1", "SEQ-702/A2", "SEQ-702/A3"], run.units)


class DeliveryOutstandingTest(ContinuationCase):
    """The unit passed and the accepted outcome still owes its delivery target."""

    scenario = "delivery-outstanding"

    def test_the_run_stops_while_the_delivery_is_outstanding(self):
        run = self.continuation()
        self.assert_stop(run)

    def test_the_remaining_unit_is_never_claimed(self):
        self.untouched(self.continuation())

    def test_the_condition_reads_the_item_rather_than_the_task(self):
        item = SCENARIOS / self.scenario / "project" / "_devdocs" / "work" / "seq-703" / "intent.md"
        self.assertTrue(delivery_outstanding(item))


class RevokedAuthorityTest(ContinuationCase):
    """Authority is withdrawn while the first unit runs."""

    scenario = "revoked-authority"

    def test_the_next_dispatch_is_refused(self):
        run = self.continuation()
        self.assert_stop(run)
        self.assertIsNone(standing_policy(self.project))

    def test_the_effect_that_already_happened_stays_recorded(self):
        run = self.continuation()
        metadata = run.metadata("SEQ-704", "A1")
        self.assertEqual("agent:A1", metadata["claim"]["actor"])
        self.assertEqual("passed", metadata["result"]["outcome"])

    def test_the_unit_after_the_revocation_is_never_claimed(self):
        self.untouched(self.continuation())


class OpsRequestTest(ContinuationCase):
    """A bounded request from ops is a candidate, and nothing stands behind it."""

    scenario = "ops-request"

    def setUp(self):
        super().setUp()
        self.request = json.loads(
            (SCENARIOS / self.scenario / self.manifest["request"]).read_text(encoding="utf-8")
        )

    def test_the_request_names_an_item_that_is_otherwise_eligible(self):
        run = ContinuationRun(self.project, self.manifest)
        answer = run.call("select", "--seq", self.request["seq"])["result"]
        self.assertEqual(self.request["seq"], answer["candidate"]["seq"])
        self.assertEqual([], answer["considered"][0]["reasons"])

    def test_the_request_starts_no_work(self):
        run = self.continuation()
        self.assert_stop(run)
        self.untouched(run)

    def test_the_requests_own_authority_field_is_not_authority(self):
        self.assertEqual("session-ops", self.request["authority"]["source"])
        self.assertIsNone(standing_policy(self.project))


class MalformedPolicyTest(ContinuationCase):
    """A policy that is not complete and well formed authorizes nothing."""

    scenario = "capacity"

    def refuse(self, change) -> None:
        config = read_config(self.project)
        change(config[POLICY_KEY])
        write_config(self.project, config)
        self.assertIsNone(standing_policy(self.project))
        run = self.continuation()
        self.assertEqual([], run.units)
        self.assertEqual(NO_AUTHORITY, run.stop["reason"])

    def test_a_policy_missing_its_capacity_authorizes_nothing(self):
        self.refuse(lambda policy: policy.pop("capacity"))

    def test_a_capacity_that_is_not_a_number_of_units_authorizes_nothing(self):
        self.refuse(lambda policy: policy["capacity"].update(units="all of them"))

    def test_an_undefined_stop_condition_authorizes_nothing(self):
        self.refuse(lambda policy: policy["stop_conditions"].append("when-it-feels-right"))

    def test_provenance_is_not_an_authority_source(self):
        self.refuse(lambda policy: policy["authority"].update(source="[auto]"))

    def test_an_identity_outside_the_policy_scope_starts_nothing(self):
        config = read_config(self.project)
        config[POLICY_KEY]["scope"]["seq"] = ["SEQ-999"]
        write_config(self.project, config)
        run = self.continuation()
        self.assertEqual([], run.units)
        self.assertEqual(NO_AUTHORITY, run.stop["reason"])

    def test_an_action_outside_the_policy_scope_starts_nothing(self):
        run = ContinuationRun(self.project, self.manifest, action="deploy").run()
        self.assertEqual([], run.units)
        self.assertEqual(NO_AUTHORITY, run.stop["reason"])


def table_rows(text: str, header: str) -> list:
    """The cells of every row of the Markdown table whose header names `header`."""
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


def reported_reasons(text: str) -> list:
    return [cells[1].strip("` ") for cells in table_rows(text, STOP_HEADER)]


class StopContractTest(unittest.TestCase):
    """The stops the runner reaches are the stops `/session-next` instructs."""

    def setUp(self):
        self.text = NEXT_SKILL.read_text(encoding="utf-8")

    def test_every_scenario_stop_is_instructed(self):
        for document in manifests():
            with self.subTest(scenario=document["scenario"]):
                self.assertIn(document["expected"]["reason"], reported_reasons(self.text))

    def test_the_six_continuation_stops_are_present(self):
        rows = table_rows(self.text, STOP_HEADER)
        self.assertEqual(6, len(rows), [row[0] for row in rows])

    def test_every_reported_reason_is_a_runtime_code_or_a_coordinator_reason(self):
        for reason in reported_reasons(self.text):
            with self.subTest(reason=reason):
                self.assertIn(reason, tuple(ERROR_CODES) + COORDINATOR_REASONS)

    def test_a_removed_stop_is_detected(self):
        without = "\n".join(
            line for line in self.text.splitlines() if "capacity is spent" not in line
        )
        self.assertNotIn(CAPACITY_SPENT, reported_reasons(without))

    def test_both_configured_conditions_are_defined(self):
        for condition in CONDITIONS:
            with self.subTest(condition=condition):
                self.assertIn(f"`{condition}`", self.text)


class ContinuationRuleTest(unittest.TestCase):
    """Both execution skills carry the rules the runner enforces."""

    def setUp(self):
        self.next_text = NEXT_SKILL.read_text(encoding="utf-8")
        self.delegation_text = DELEGATION_SKILL.read_text(encoding="utf-8")

    def test_the_policy_names_capacity_scope_and_stop_conditions(self):
        for key in POLICY_KEYS:
            with self.subTest(key=key):
                self.assertIn(f'"{key}"', self.next_text)

    def test_authority_is_re_resolved_before_each_dispatch(self):
        self.assertIn("Re-read the policy from `.session-flow.json`", self.next_text)
        self.assertIn(
            "re-resolve the authority before each dispatch and before each consequential effect",
            self.delegation_text,
        )

    def test_a_completed_effect_survives_a_revocation(self):
        self.assertIn("Revocation blocks the next dispatch", self.next_text)
        self.assertIn("tasks already dispatched finish, and their results are recorded", self.delegation_text)

    def test_an_ops_request_is_a_candidate_and_not_an_assignment(self):
        self.assertIn("Ops produces requests, not assignments.", self.next_text)
        self.assertIn("the request starts nothing", self.next_text)
        self.assertIn("candidate for a named set, never the set itself", self.delegation_text)


if __name__ == "__main__":
    unittest.main()
