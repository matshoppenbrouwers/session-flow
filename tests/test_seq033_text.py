"""SEQ-033 acceptance tests for the documentation (tasks A2 to A6).

A2  session-verify and work-item-contract: assess before running, recorded reuse, known-failure baseline
A3  session-task-planning and session-delegation: what a change touches, shared files, actors, widening
A4  session-next and session-init: delivery section, runbook lookup, receipt, `paths.runbook`
A5  session-post-implementation, code-reviewer, README, workflow-overview: simplify opt-in, no `Note`
A6  CHANGELOG: an `## Unreleased` section naming each change

A1 (stale acceptance in the views) is tested in tests/test_views.py.

Each check matches a stable phrase, case-insensitively and with alternatives, so a correct rewording
passes. Nothing here is written to; the files are only read.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS = REPO_ROOT / "skills"
CONTRACT = REPO_ROOT / "references" / "work-item-contract.md"
OVERVIEW = REPO_ROOT / "references" / "workflow-overview.md"
REVIEWER = REPO_ROOT / "agents" / "code-reviewer.md"
README = REPO_ROOT / "README.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
DELIVERY_HEADING = r"When the user asks to commit, push or deploy"
VERIFY_LINE_LIMIT = 400


def skill(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def section(text: str, heading: str) -> str:
    """The text from a heading matching `heading` to the next heading of the same or a higher level."""
    found = re.search(r"^(#+)[ \t]*" + heading + r"[^\n]*\n", text, re.IGNORECASE | re.MULTILINE)
    if found is None:
        return ""
    level = len(found.group(1))
    rest = text[found.end() :]
    following = re.search(r"^#{1,%d}[ \t]+\S" % level, rest, re.MULTILINE)
    return rest[: following.start()] if following else rest


class TextCase(unittest.TestCase):
    def assert_matches(self, pattern: str, text: str, label: str = "") -> None:
        self.assertIsNotNone(
            re.search(pattern, flat(text), re.IGNORECASE),
            "expected text matching /%s/ %s" % (pattern, label),
        )

    def assert_absent(self, pattern: str, text: str, label: str = "") -> None:
        found = re.search(pattern, flat(text), re.IGNORECASE)
        self.assertIsNone(found, "unexpected text %r %s" % (found and found.group(0), label))

    def assert_in_order(self, patterns: tuple, text: str, label: str = "") -> None:
        """Each pattern matches somewhere after the previous one's match."""
        body, position = flat(text), 0
        for pattern in patterns:
            found = re.compile(pattern, re.IGNORECASE).search(body, position)
            self.assertIsNotNone(found, "no text matching /%s/ in order %s" % (pattern, label))
            position = found.end()

    def assert_window_holds(self, anchor: str, patterns: tuple, text: str, size: int = 900, label: str = "") -> None:
        """Some stretch of `size` characters starting at `anchor` matches every pattern."""
        body = flat(text)
        for found in re.finditer(anchor, body, re.IGNORECASE):
            window = body[found.start() : found.start() + size]
            if all(re.search(pattern, window, re.IGNORECASE) for pattern in patterns):
                return
        self.fail("no stretch after /%s/ matches %s %s" % (anchor, ", ".join(patterns), label))


NO_PARALLEL_MUTATION = (
    r"(never|do not|don't|must not)[^.]{0,80}(send|issue|make|run|start)[^.]{0,60}"
    r"(two|more than one|several|concurrent|parallel|overlapping)[^.]{0,60}(mutating|write)[^.]{0,80}"
    r"(call|command|request)s?[^.]{0,120}(same|one|a single) record"
    r"|one mutation per record|one mutating (runtime )?call per record"
    r"|(same|one|a single) record[^.]{0,120}(at once|at the same time|simultaneous\w*|concurrent\w*|in parallel)"
)


# --------------------------------------------------------------------------- A2


class A2VerifyTest(TextCase):
    def verify(self) -> str:
        return skill("session-verify")

    def contract(self) -> str:
        return read(CONTRACT)

    # Behaviour 1: assess before running

    def test_a2_there_is_no_structural_functional_exhaustive_ambition_choice(self):
        self.assert_absent(r"verification ambition", self.verify())
        self.assert_absent(r"\(A\)\s*structural-only|\(C\)\s*exhaustive|default C unless", self.verify())

    def test_a2_the_five_step_procedure_runs_in_order(self):
        self.assert_in_order(
            (
                r"(list|enumerate)\w* (each |all |the )?accepted[^.]{0,30}criteri",
                r"\bmap\w* (the |each )?(existing|applicable)[^.]{0,60}evidence",
                r"run (only )?(the )?checks?[^.]{0,30}(missing|failing)[^.]{0,20}(or )?stale",
                r"full[ -]suite[^.]{0,80}only (when|if)[^.]{0,60}\bno\b[^.]{0,80}\bresult",
                r"record (the|a) (verdict|result)",
            ),
            self.verify(),
            "(assess, then run)",
        )

    def test_a2_an_explicit_exhaustive_request_runs_everything(self):
        self.assert_matches(
            r"(explicit\w*|asks? for|request\w*)[^.]{0,80}exhaustive[^.]{0,160}(runs?|running) (everything|all|every)"
            r"|exhaustive[^.]{0,60}(is |was )?(explicit\w*|request\w*|asked)[^.]{0,120}(runs?|running) (everything|all|every)",
            self.verify(),
            "(exhaustive on request)",
        )

    # Behaviour 2: reuse is a recorded decision

    def test_a2_reused_from_is_documented_with_its_contents(self):
        self.assert_window_holds(
            r"`?reused_from`?",
            (
                r"\bcommit\b",
                r"git status --porcelain|clean",
                r"\bcommand\b",
                r"interpreter",
                r"lock ?file",
                r"environment variables?",
            ),
            self.verify(),
            label="(reused_from contents)",
        )

    def test_a2_only_passing_results_are_reused(self):
        self.assert_window_holds(
            r"`?reused_from`?",
            (r"only[^.]{0,60}pass(ing|ed)?[^.]{0,40}(result|entr)|pass(ing|ed)? (result|entr)\w* (only|alone)",),
            self.verify(),
            label="(passing results only)",
        )

    # Behaviour 3: known failures are a baseline, not a waiver

    def test_a2_the_baseline_file_and_its_columns(self):
        self.assert_matches(r"\{paths\.testing\}/known-failures\.md", self.verify())
        self.assert_window_holds(
            r"known-failures\.md",
            (r"test id", r"reason", r"owner", r"review date"),
            self.verify(),
            label="(baseline columns)",
        )

    def test_a2_a_failure_outside_the_baseline_is_a_fail_entry(self):
        self.assert_window_holds(
            r"known-failures\.md",
            (r"(not in|absent from|outside|missing from|not listed in)[^.]{0,40}(the )?(baseline|file)[^.]{0,120}`?fail`?",),
            self.verify(),
            size=1800,
            label="(new failure is fail)",
        )

    def test_a2_newly_passing_and_overdue_entries_are_reported(self):
        verify = self.verify()
        self.assert_window_holds(
            r"known-failures\.md",
            (
                r"(now pass\w*|newly passing|passes now|started passing)[^.]{0,100}(report\w*|remov\w*)"
                r"|(report\w*|remov\w*)[^.]{0,100}(now pass\w*|newly passing|passes now)",
            ),
            verify,
            size=1800,
            label="(newly passing)",
        )
        self.assert_window_holds(
            r"known-failures\.md",
            (
                r"(past|after|overdue|beyond)[^.]{0,40}review date[^.]{0,100}report\w*"
                r"|report\w*[^.]{0,100}(overdue|past[^.]{0,30}review date)",
            ),
            verify,
            size=1800,
            label="(overdue)",
        )

    def test_a2_a_baseline_is_never_waived_and_never_authorizes_shipping_a_blocker(self):
        self.assert_window_holds(
            r"known-failures\.md",
            (r"never[^.]{0,60}`?waived`?|not[^.]{0,30}recorded as `?waived`?",),
            self.verify(),
            size=1800,
            label="(never waived)",
        )
        self.assert_matches(
            r"(never|does not|doesn't|cannot|no) authori[sz]\w*[^.]{0,60}(ship\w*|releas\w*|deliver\w*)[^.]{0,40}blocker",
            self.verify(),
            "(never authorizes shipping a blocker)",
        )

    def test_a2_the_evidence_entry_cites_the_baseline_with_path_and_commit(self):
        self.assert_window_holds(
            r"`?baseline`?\s*:",
            (r"\bpath\b", r"\bcommit\b"),
            self.verify(),
            size=300,
            label="(baseline: {path, commit})",
        )

    # Behaviour 4: imported history is assessed, not trusted

    def test_a2_imported_items_are_assessed_from_their_provenance_and_never_a_fresh_pass(self):
        self.assert_window_holds(
            r"`?provenance\.imported_from`?",
            (r"history|assess", r"breakdown", r"rerun|re-run|run again"),
            self.verify(),
            size=700,
            label="(imported history is assessed)",
        )
        self.assert_matches(
            r"(historical|imported|legacy)[^.]{0,80}(completion|evidence|done)[^.]{0,80}"
            r"(never|not)[^.]{0,40}(recorded |counted )?as a (fresh )?pass",
            self.verify(),
            "(never a fresh pass)",
        )

    # The delivery pointer and the size cap

    def test_a2_verify_points_to_the_delivery_section_in_session_next(self):
        self.assert_matches(DELIVERY_HEADING, self.verify(), "(pointer to session-next)")
        self.assert_matches(r"session-next", self.verify())

    def test_a2_the_skill_stays_under_the_line_limit(self):
        self.assertLess(len(self.verify().splitlines()), VERIFY_LINE_LIMIT)

    # references/work-item-contract.md

    def test_a2_the_contract_has_an_evidence_entry_field_table(self):
        rows = [row for row in self.contract().splitlines() if row.lstrip().startswith("|")]
        table = "\n".join(rows)
        for field in ("criteria", "fingerprint", "result", "revision", "environment", "limitations", "reused_from", "baseline"):
            self.assertRegex(table, r"`%s`" % field, "the evidence-entry table lacks `%s`" % field)

    def test_a2_the_contract_gives_the_baseline_file_format(self):
        self.assert_matches(r"known-failures\.md", self.contract())
        self.assert_matches(
            r"\|\s*Test id\s*\|\s*Reason\s*\|\s*Owner\s*\|\s*Review date\s*\|", self.contract(), "(baseline header)"
        )
        self.assert_matches(r"ISO|YYYY-MM-DD", self.contract(), "(date form)")


# --------------------------------------------------------------------------- A3


class A3PlanningTest(TextCase):
    def planning(self) -> str:
        return skill("session-task-planning")

    def delegation(self) -> str:
        return skill("session-delegation")

    # session-task-planning

    def test_a3_planning_finds_the_tests_baselines_and_docs_a_changed_symbol_touches(self):
        self.assert_window_holds(
            r"(each|every) symbol[^.]{0,40}(task|change)",
            (r"search|grep|find", r"\btests?\b", r"schema baselines?", r"\bdocs?\b|documentation", r"boundary|allowed_paths"),
            self.planning(),
            size=700,
            label="(find what a change touches)",
        )

    def test_a3_acceptance_tests_go_to_the_test_author(self):
        self.assert_matches(
            r"acceptance tests?[^.]{0,100}test[ -]author|test[ -]author[^.]{0,100}acceptance tests?",
            self.planning(),
            "(acceptance tests go to the test author)",
        )

    def test_a3_shared_files_stay_out_of_write_scopes(self):
        self.assert_matches(
            r"shared[^.]{0,120}(not|never|stay out|out of|outside)[^.]{0,100}(allowed_paths|write scope|boundary)",
            self.planning(),
            "(shared files out of allowed_paths)",
        )
        self.assert_matches(
            r"(item'?s own record|own record|per-item content)", self.planning(), "(per-item content goes in the record)"
        )

    def test_a3_the_checklist_has_a_line_for_each_rule(self):
        checklist = section(self.planning(), "Validation Checklist")
        lines = [line for line in checklist.splitlines() if line.lstrip().startswith("- [ ]")]
        text = "\n".join(lines)
        self.assertRegex(text, r"(?i)(tests?|schema baselines?|docs?)[^\n]{0,120}(touch|referenc|search|found|listed)|(touch|referenc|search)\w*[^\n]{0,120}(tests?|docs?)")
        self.assertRegex(text, r"(?i)shared[^\n]{0,120}(allowed_paths|write scope|boundary|scope)")

    # session-delegation

    def test_a3_each_task_gets_its_own_actor_named_from_its_identity(self):
        self.assert_matches(r"agent:<task ?id>", self.delegation(), "(actor agent:<task ID>)")
        self.assert_matches(
            r"(never|do not|don't|must not)[^.]{0,60}reus\w*[^.]{0,80}actor|one actor per task|actor[^.]{0,60}(never|not)[^.]{0,40}(shared|reused)[^.]{0,40}(across|between)",
            self.delegation(),
            "(no actor reuse across tasks)",
        )

    def test_a3_no_two_mutating_runtime_calls_for_one_record_at_once(self):
        self.assert_matches(NO_PARALLEL_MUTATION, self.delegation(), "(one mutation per record)")

    def test_a3_widening_follows_approval_revise_then_a_full_reclaim(self):
        self.assert_window_holds(
            r"widen\w*[^.]{0,40}(boundary|allowed_paths|write boundary|paths)",
            (
                r"approv\w+",
                r"\brevise\b",
                r"allowed_paths",
                r"re-?claim|claims? (it |the task )?again|same actor",
                r"full (new )?(list|set)|whole (new )?list|entire (new )?list|complete (new )?list",
            ),
            self.delegation(),
            size=1400,
            label="(widening sequence)",
        )
        self.assert_in_order(
            (r"widen\w*[^.]{0,40}(boundary|allowed_paths|paths)", r"approv\w+", r"\brevise\b", r"re-?claim|claims? (it |the task )?again|same actor"),
            self.delegation(),
            "(approval, revise, re-claim)",
        )

    def test_a3_the_reclaim_replaces_the_previous_claim_so_the_list_is_complete(self):
        self.assert_matches(
            r"(claim|re-?claim)[^.]{0,80}replaces?[^.]{0,60}(previous|earlier|prior)[^.]{0,40}(claim|paths)"
            r"|replaces? (the )?(previous|earlier|prior) claim",
            self.delegation(),
            "(a claim replaces the previous claim's paths)",
        )

    def test_a3_the_final_suite_run_is_recorded_as_reusable_evidence(self):
        self.assert_window_holds(
            r"run the project'?s full test suite",
            (r"evidence", r"\bcommand\b", r"environment", r"reus\w*|reused_from"),
            self.delegation(),
            size=700,
            label="(Step 7.1 records reusable evidence)",
        )


# --------------------------------------------------------------------------- A4


class A4DeliveryTest(TextCase):
    def next_skill(self) -> str:
        return skill("session-next")

    def delivery(self) -> str:
        return section(self.next_skill(), DELIVERY_HEADING)

    def test_a4_session_next_has_the_delivery_section(self):
        self.assertNotEqual(self.delivery().strip(), "", "no section titled %r" % DELIVERY_HEADING)

    def test_a4_the_runbook_is_found_through_paths_then_project_instructions_then_the_user(self):
        self.assert_in_order(
            (r"paths\.runbook", r"CLAUDE\.md|AGENTS\.md", r"\bask\w*\b[^.]{0,40}(the )?user|\bask\b"),
            self.delivery(),
            "(runbook lookup order)",
        )
        self.assert_matches(r"(offer|propos|suggest)\w*[^.]{0,80}record[^.]{0,80}paths\.runbook", self.delivery(), "(offer to record)")

    def test_a4_the_steps_run_in_order_and_end_with_a_receipt(self):
        self.assert_in_order(
            (
                r"commit\w*[^.]{0,60}only[^.]{0,40}(item'?s?|its|the item'?s?)[^.]{0,20}paths|only[^.]{0,40}(item'?s?|its)[^.]{0,20}paths",
                r"hooks?[^.]{0,80}(present|exist\w*)[^.]{0,60}executable|executable[^.]{0,60}hooks?",
                r"\bpush\w*\b",
                r"deployed (revision|commit|version)",
                r"\bhealth\b",
                r"delivery\.receipt",
            ),
            self.delivery(),
            "(commit item paths, hooks, push, deployed revision, health, receipt)",
        )

    def test_a4_the_receipt_records_revision_target_and_health_result(self):
        self.assert_window_holds(
            r"delivery\.receipt",
            (r"\brevision\b", r"\btarget\b", r"health"),
            self.delivery(),
            size=400,
            label="(receipt fields)",
        )

    def test_a4_authorized_verification_is_never_cancelled(self):
        self.assert_matches(
            r"(already )?authori[sz]ed[^.]{0,80}verif\w*[^.]{0,160}(never|not)[^.]{0,40}(silently )?cancel\w*"
            r"|never[^.]{0,40}cancel\w*[^.]{0,80}(authori[sz]ed )?verif\w*"
            r"|verif\w*[^.]{0,120}(never|not)[^.]{0,30}(silently )?cancel\w*",
            self.delivery(),
            "(authorized verification continues)",
        )

    def test_a4_delivery_authority_exists_only_where_the_user_granted_it(self):
        self.assert_matches(
            r"delivery authority[^.]{0,100}(only|exists)[^.]{0,100}grant\w*|only where the user (has )?granted",
            self.delivery(),
            "(delivery authority)",
        )

    def test_a4_step_4_points_at_the_widening_sequence(self):
        step = section(self.next_skill(), r"Step 4[^\n]*")
        self.assert_matches(
            r"widening sequence|\brevise\b[^.]{0,160}allowed_paths|allowed_paths[^.]{0,160}\brevise\b",
            step,
            "(widening reference in Step 4)",
        )
        self.assert_matches(r"session-delegation", step)

    def test_a4_session_next_forbids_two_mutating_calls_for_one_record(self):
        self.assert_matches(NO_PARALLEL_MUTATION, self.next_skill(), "(one mutation per record)")

    def test_a4_session_init_documents_paths_runbook_as_optional(self):
        self.assert_window_holds(
            r"`?paths\.runbook`?",
            (r"optional",),
            skill("session-init"),
            size=400,
            label="(paths.runbook is optional)",
        )


# --------------------------------------------------------------------------- A5


class A5ReviewTest(TextCase):
    def post(self) -> str:
        return skill("session-post-implementation")

    def table_rows(self, path: Path, needle: str) -> list:
        return [row for row in read(path).splitlines() if row.lstrip().startswith("|") and re.search(needle, row, re.I)]

    def test_a5_simplify_is_off_in_every_column_of_the_mode_table(self):
        rows = [row for row in self.post().splitlines() if re.match(r"\s*\|\s*\d+\.\s*Simplify", row, re.I)]
        self.assertEqual(len(rows), 1, "expected one Simplify row in the mode table")
        cells = [cell.strip().lower() for cell in rows[0].strip().strip("|").split("|")[1:]]
        self.assertEqual(len(cells), 3, rows[0])
        self.assertNotIn("yes", cells, "Simplify is on in a preset: %s" % rows[0])

    def test_a5_preset_descriptions_no_longer_list_simplify(self):
        presets = [
            line
            for line in self.post().splitlines()
            if re.search(r'label:\s*"(Full pipeline|Standard|Quick)', line)
        ]
        self.assertEqual(len(presets), 3, presets)
        for line in presets:
            self.assert_absent(r"simplif", line, "(preset description)")

    def test_a5_simplify_is_offered_as_an_add_on(self):
        question = self.post().split("**Question 2", 1)[-1].split("**Question 3", 1)[0]
        self.assert_matches(r"\"?simplify\"?|simplifier", question, "(Question 2 offers Simplify)")

    def test_a5_simplify_runs_only_when_chosen(self):
        step = section(self.post(), r"Step 1: Simplify")
        self.assertNotEqual(step.strip(), "")
        self.assert_matches(
            r"run when:?\*{0,2}\s*1 is in the resolved step set|only (when|if)[^.]{0,80}(chosen|selected|add-on|added|opted)",
            step,
            "(Step 1 is conditional)",
        )

    def test_a5_the_reviewer_prompt_is_limited_to_correctness_or_accepted_requirements(self):
        found = re.search(r'subagent_type="code-reviewer"\s*\n\s*prompt:\s*"([^"]*)"', self.post())
        self.assertIsNotNone(found, "no code-reviewer prompt found")
        prompt = found.group(1)
        self.assert_matches(r"correctness", prompt, "(reviewer prompt)")
        self.assert_matches(r"requirement", prompt, "(reviewer prompt)")
        self.assert_absent(r"code quality", prompt, "(reviewer prompt)")

    def test_a5_the_reviewer_has_no_note_severity(self):
        reviewer = read(REVIEWER)
        self.assertNotRegex(reviewer, r"(?m)^#+\s*Note\b")
        self.assertNotRegex(reviewer, r"(?m)^\|\s*Note\s*\|")
        self.assertNotRegex(reviewer, r"\[SEVERITY\]\s*\[confidence\][^\n]*\bNote\b")

    def test_a5_the_verdict_counts_critical_and_warning_only(self):
        verdict = re.search(r"\*\*Verdict:\*\*[^\n]*", read(REVIEWER))
        self.assertIsNotNone(verdict)
        self.assert_matches(r"critical", verdict.group(0), "(verdict)")
        self.assert_matches(r"warning", verdict.group(0), "(verdict)")
        self.assert_absent(r"\bnotes?\b", verdict.group(0), "(verdict)")
        summary = re.search(r"\| Severity \| Count \|.*?(?=\n\n)", read(REVIEWER), re.S)
        self.assertIsNotNone(summary)
        self.assertRegex(summary.group(0), r"Critical")
        self.assertRegex(summary.group(0), r"Warning")
        self.assertNotRegex(summary.group(0), r"Note")

    def test_a5_summary_rows_no_longer_list_simplify_as_a_default_step(self):
        for path in (README, OVERVIEW):
            rows = self.table_rows(path, r"post-implementation")
            self.assertTrue(rows, "no post-implementation summary rows in %s" % path.name)
            for row in rows:
                with self.subTest(path=path.name, row=row[:60]):
                    self.assert_absent(r"simplif", row)


# --------------------------------------------------------------------------- A6


class A6ChangelogTest(TextCase):
    def text(self) -> str:
        return read(CHANGELOG)

    def unreleased(self) -> str:
        return section(self.text(), r"(?:\[?Unreleased\]?|3\.1\.0\b)")

    def bullets(self) -> list:
        return [flat(part) for part in re.split(r"\n\s*[-*]\s+", self.unreleased())[1:]]

    def assert_a_bullet_matches(self, pattern: str, label: str) -> None:
        self.assertTrue(
            any(re.search(pattern, bullet, re.IGNORECASE) for bullet in self.bullets()),
            "no Unreleased bullet matches /%s/ %s" % (pattern, label),
        )

    def test_a6_unreleased_sits_above_the_3_0_0_entry(self):
        unreleased = re.search(r"(?m)^##\s+(?:\[?Unreleased\]?|3\.1\.0\b)", self.text())
        released = re.search(r"(?m)^##\s+\[?3\.0\.0\b", self.text())
        self.assertIsNotNone(unreleased, "no `## Unreleased` section")
        self.assertIsNotNone(released)
        self.assertLess(unreleased.start(), released.start())

    def test_a6_verify_has_no_modes_and_reuses_applicable_results(self):
        self.assert_a_bullet_matches(
            r"verif\w*[^.]{0,200}(no (\w+ )?modes?|without (\w+ )?modes?|assess\w*[^.]{0,40}(before|first))"
            r"[^.]{0,300}reus\w*|verif\w*[^.]{0,200}reus\w*[^.]{0,100}(applicable|passing)",
            "(verify has no modes and reuses applicable results)",
        )

    def test_a6_the_known_failure_baseline_file_is_named(self):
        self.assert_a_bullet_matches(r"known-failures\.md", "(baseline file)")

    def test_a6_the_simplifier_is_off_by_default(self):
        self.assert_a_bullet_matches(
            r"simplif\w*[^.]{0,120}(off by default|opt-in|no longer (runs|a default)|add-on)", "(simplifier)"
        )

    def test_a6_the_note_severity_is_removed(self):
        self.assert_a_bullet_matches(
            r"`?note`?[^.]{0,80}severity[^.]{0,80}(removed|gone|dropped)|(removed|dropped|no longer)[^.]{0,80}`?note`?[^.]{0,40}severity",
            "(Note severity)",
        )

    def test_a6_the_acceptance_stale_token_is_named(self):
        self.assert_a_bullet_matches(r"\(acceptance stale\)", "(stale token)")

    def test_a6_paths_runbook_is_named_as_optional(self):
        self.assert_a_bullet_matches(r"paths\.runbook[^.]{0,200}optional|optional[^.]{0,120}paths\.runbook", "(runbook)")


if __name__ == "__main__":
    unittest.main()
