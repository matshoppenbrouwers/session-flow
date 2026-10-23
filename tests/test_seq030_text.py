"""SEQ-030 acceptance tests for the skill text and changelog (tasks A5, A6, A7).

Each check matches a stable phrase, case-insensitively and with alternatives, so a correct
rewording passes. Nothing here is written to; the files are only read.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS = REPO_ROOT / "skills"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
FENCE = re.compile(r"```json\n(.*?)```", re.DOTALL)
STRING_SCOPE = re.compile(r'"scope"\s*:\s*"')
LIST_SCOPE = re.compile(r'"scope"\s*:\s*\[')
SCOPE_VALUE = re.compile(r'"scope"\s*:\s*(\S)')
LINE_RANGE = re.compile(r"\.\w+:\d+(?:-\d+)?")


def skill(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


class TextCase(unittest.TestCase):
    def assert_matches(self, pattern: str, text: str, label: str = "") -> None:
        self.assertIsNotNone(
            re.search(pattern, flat(text), re.IGNORECASE),
            "expected text matching /%s/ %s" % (pattern, label),
        )

    def assert_absent(self, pattern: str, text: str, label: str = "") -> None:
        found = re.search(pattern, flat(text), re.IGNORECASE)
        self.assertIsNone(found, "unexpected text %r %s" % (found and found.group(0), label))


class A5PlanningSkillsTest(TextCase):
    SKILLS = ("session-research-design", "session-task-planning")

    def test_a5_no_deprecated_revision_key_remains(self):
        for name in self.SKILLS:
            with self.subTest(skill=name):
                self.assertNotIn("expected_revision", skill(name))

    def test_a5_payload_examples_use_expect_revision(self):
        for name in self.SKILLS:
            with self.subTest(skill=name):
                self.assertIn("expect_revision", skill(name))

    def test_a5_decision_scope_examples_are_lists_of_strings(self):
        for name in self.SKILLS:
            with self.subTest(skill=name):
                decisions = [block for block in FENCE.findall(skill(name)) if '"authority"' in block]
                values = [value for block in decisions for value in SCOPE_VALUE.findall(block)]
                self.assertTrue(values, "no decision example with a scope in %s" % name)
                self.assertEqual(["["] * len(values), values)
                self.assertTrue(all(LIST_SCOPE.search(block) for block in decisions if '"scope"' in block))
                self.assertFalse(
                    any(STRING_SCOPE.search(block) for block in decisions), "a decision scope is still a string"
                )

    def test_a5_task_planning_offers_no_line_range_boundaries(self):
        self.assertIsNone(LINE_RANGE.search(skill("session-task-planning")))

    def test_a5_task_planning_says_boundaries_are_whole_paths_or_directory_globs(self):
        text = skill("session-task-planning")
        self.assert_matches(r"whole[ -](file )?paths?|whole files?|entire files?", text, "(whole paths)")
        self.assert_matches(r"director(y|ies)[ -]globs?", text, "(directory globs)")


class A6DelegationTest(TextCase):
    def test_a6_recording_a_result_no_longer_claims_to_unblock_dependents(self):
        self.assert_absent(r"recording a result\s+unblocks", skill("session-delegation"))

    def test_a6_a_dependent_unblocks_when_its_prerequisite_is_done(self):
        self.assert_matches(
            r"unblock\w*[^.]{0,160}`?done`?|`?done`?[^.]{0,160}unblock\w*|(claimable|can be claimed|may be claimed)[^.]{0,120}`?done`?",
            skill("session-delegation"),
        )

    def test_a6_the_close_out_order_is_listed(self):
        text = flat(skill("session-delegation"))
        start = re.search(r"close[- ]?out", text, re.IGNORECASE)
        self.assertIsNotNone(start, "no close-out section")
        self.assertRegex(
            text[start.start() : start.start() + 3000],
            r"(?is)`?claim`?.*?`?record-result`?",
        )


class A6NextTest(TextCase):
    def test_a6_a_direct_user_instruction_has_an_acceptance_step(self):
        text = skill("session-next")
        self.assert_matches(
            r"direct (user )?instruction|user (directly )?(names|asks for|tells you)|named (work )?item|names? a (specific |particular )?item",
            text,
            "(direct instruction)",
        )
        self.assert_matches(r"\baccept\b[^#]{0,600}quot\w+|quot\w+[^#]{0,600}\baccept\b", text, "(quoted authority)")
        self.assertRegex(text, LIST_SCOPE, "the acceptance example passes scope as a list")


class A6PostImplementationTest(TextCase):
    def test_a6_the_review_cap_is_one_review_plus_two_fix_rounds(self):
        text = skill("session-post-implementation")
        self.assert_matches(r"\b(one|a single|1) (initial )?review", text, "(one review)")
        self.assert_matches(
            r"(at most|up to|no more than|maximum of|max(imum)?) (of )?(two|2)\b[^.]{0,80}(fix|round|re-review)",
            text,
            "(at most two rounds)",
        )

    def test_a6_open_findings_at_the_cap_are_recorded_as_blockers(self):
        self.assert_matches(
            r"(open|unresolved|remaining) (review )?findings?[^.]{0,200}blockers?|blockers?[^.]{0,200}(open|unresolved|remaining) (review )?findings?",
            skill("session-post-implementation"),
        )

    def test_a6_the_older_conflicting_re_run_rules_are_gone(self):
        text = skill("session-post-implementation")
        self.assert_absent(r"loop until the reviewer passes", text)
        self.assert_absent(r"re-run the reviewer once on the fixes", text)


def unreleased_sections() -> dict:
    text = CHANGELOG.read_text(encoding="utf-8")
    match = re.search(r"^##\s+3\.0\.0\b[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
    if match is None:
        return {}
    parts = re.split(r"^###\s+", match.group(1), flags=re.MULTILINE)[1:]
    return {part.split("\n", 1)[0].strip().lower(): flat(part) for part in parts}


class A7ChangelogTest(TextCase):
    def section(self, prefix: str) -> str:
        found = [text for heading, text in unreleased_sections().items() if heading.startswith(prefix)]
        self.assertTrue(found, "no '### %s...' heading under '## Unreleased'" % prefix.title())
        return found[0]

    def test_a7_breaking_changes_list_strict_validation_and_the_tighter_gate(self):
        text = self.section("breaking")
        self.assert_matches(r"decision `?scope`?|scope[^.]{0,80}(list|string)", text, "(decision scope)")
        self.assert_matches(r"unknown[^.]{0,60}(key|field)s?", text, "(unknown keys)")
        self.assert_matches(r"completion (gate|check)|completing|completion", text, "(completion gate)")

    def test_a7_changes_list_the_revision_key_unification_with_the_alias(self):
        text = self.section("chang")
        self.assertIn("expect_revision", text)
        self.assertIn("expected_revision", text)
        self.assert_matches(r"deprecated|alias", text)

    def test_a7_changes_list_latest_evidence_supersession(self):
        self.assert_matches(
            r"latest[^.]{0,80}evidence|evidence[^.]{0,120}(latest|supersed)|supersed\w+[^.]{0,80}evidence",
            self.section("chang"),
        )

    def test_a7_changes_list_reclaim_clearing_results(self):
        self.assert_matches(
            r"reclaim\w*[^.]{0,120}result|claim\w*[^.]{0,80}clears?[^.]{0,40}result|result[^.]{0,80}cleared",
            self.section("chang"),
        )

    def test_a7_changes_list_the_line_range_removal(self):
        self.assert_matches(r"line[- ]ranges?", self.section("chang"))

    def test_a7_changes_list_the_review_cap(self):
        self.assert_matches(
            r"review[^.]{0,120}(cap|two|2|round)|(cap|two|2|round)[^.]{0,120}review", self.section("chang")
        )


if __name__ == "__main__":
    unittest.main()
