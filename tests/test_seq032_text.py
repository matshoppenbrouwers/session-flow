"""SEQ-032 acceptance tests for the documentation (tasks A5 and A6).

A5  runtime-integration.md, session-delegation, session-next and the changelog describe the new runtime
A6  the other five skills keep at most one payload example and point to `schema <command>`

Each check matches a stable phrase, case-insensitively and with alternatives, so a correct rewording
passes. Nothing here is written to; the files are only read.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS = REPO_ROOT / "skills"
REFERENCE = REPO_ROOT / "references" / "runtime-integration.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
SEQ030_TEXT_TESTS = REPO_ROOT / "tests" / "test_seq030_text.py"
FENCE = re.compile(r"```json\n(.*?)```", re.DOTALL)
LIST_SCOPE = re.compile(r'"scope"\s*:\s*\[')
SCHEMA_POINTER = r"\bschema\s+(<[\w-]+>|capture|accept|revise|transition|claim|record-result)"
NUMBERED_TRANSITION_STEP = (
    r"(\d\.|[-*])\s*(a\s+|the\s+)?(second\s+)?`?transition`?\s+(it\s+|the task\s+)?to\s+`?(active|done)`?"
)
TRANSITION_AFTER_CLAIM = r"after\s+(claiming|the claim|a claim)[^.]{0,120}`?transition`?[^.]{0,60}`?active`?"
TRANSITION_AFTER_PASS = (
    r"(after|once|when)[^.]{0,80}(passing|passed)[^.]{0,80}result[^.]{0,120}`?transition`?[^.]{0,60}`?done`?"
)
SHOW_FIELDS = ("body", "fingerprint", "acceptance", "evidence")


def skill(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def json_blocks(text: str) -> list:
    return FENCE.findall(text)


def unreleased_sections() -> dict:
    text = CHANGELOG.read_text(encoding="utf-8")
    match = re.search(
        r"^##\s+\[?Unreleased\]?[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.IGNORECASE | re.DOTALL | re.MULTILINE
    )
    if match is None:
        return {}
    parts = re.split(r"^###\s+", match.group(1), flags=re.MULTILINE)[1:]
    return {part.split("\n", 1)[0].strip().lower(): flat(part) for part in parts}


class TextCase(unittest.TestCase):
    def assert_matches(self, pattern: str, text: str, label: str = "") -> None:
        self.assertIsNotNone(
            re.search(pattern, flat(text), re.IGNORECASE),
            "expected text matching /%s/ %s" % (pattern, label),
        )

    def assert_absent(self, pattern: str, text: str, label: str = "") -> None:
        found = re.search(pattern, flat(text), re.IGNORECASE)
        self.assertIsNone(found, "unexpected text %r %s" % (found and found.group(0), label))

    def assert_window_holds(self, anchor: str, words: tuple, text: str, size: int = 900, label: str = "") -> None:
        """Some stretch of `size` characters starting at `anchor` names every word."""
        body = flat(text)
        for found in re.finditer(anchor, body, re.IGNORECASE):
            window = body[found.start() : found.start() + size]
            if all(re.search(r"\b%s\b" % re.escape(word), window, re.IGNORECASE) for word in words):
                return
        self.fail("no stretch after /%s/ names %s %s" % (anchor, ", ".join(words), label))

    def assert_at_most_one_example(self, name: str) -> None:
        self.assertLessEqual(len(json_blocks(skill(name))), 1, "%s keeps more than one json payload example" % name)

    def assert_points_to_schema(self, name: str) -> None:
        self.assert_matches(SCHEMA_POINTER, skill(name), "(%s points to `schema <command>`)" % name)

    def assert_no_manual_task_transitions(self, text: str, label: str = "") -> None:
        for pattern in (NUMBERED_TRANSITION_STEP, TRANSITION_AFTER_CLAIM, TRANSITION_AFTER_PASS):
            self.assert_absent(pattern, text, label)


# --------------------------------------------------------------------------- A5


class A5RuntimeDocsTest(TextCase):
    CLOSE_OUT_SKILLS = ("session-delegation", "session-next")

    def reference(self) -> str:
        return REFERENCE.read_text(encoding="utf-8")

    # references/runtime-integration.md

    def test_a5_the_reference_documents_the_schema_command(self):
        self.assert_matches(SCHEMA_POINTER, self.reference(), "(`schema <command>`)")
        self.assert_matches(r"required[^.]{0,120}optional|optional[^.]{0,120}required", self.reference(), "(fields)")
        self.assert_matches(r"\bexample\b", self.reference(), "(example payload)")

    def test_a5_the_reference_documents_the_new_show_fields(self):
        self.assert_window_holds(r"`?show`?", SHOW_FIELDS, self.reference(), label="(show fields)")

    def test_a5_the_reference_documents_generated_operation_ids(self):
        self.assert_matches(
            r"(generat\w+|creates?|assigns?|inserts?|adds?)[^.]{0,120}`?operation`?|`?operation`?[^.]{0,120}(generat\w+|optional|omit\w*)",
            self.reference(),
            "(generated operation ids)",
        )
        self.assertIn("op-", self.reference())

    def test_a5_the_reference_says_to_retry_with_the_returned_id(self):
        self.assert_matches(
            r"(retr\w+|re-?send\w*|replay\w*)[^.]{0,200}(returned|generated|same)[^.]{0,40}(operation|id)|(returned|generated)[^.]{0,40}(operation )?(id|identifier)[^.]{0,160}(retr\w+|re-?send\w*|replay\w*)",
            self.reference(),
            "(retry with the returned id)",
        )

    def test_a5_the_reference_says_claim_moves_accepted_to_active(self):
        self.assert_matches(
            r"`?claim`?[^.]{0,200}`?accepted`?[^.]{0,120}`?active`?",
            self.reference(),
            "(claim moves accepted to active)",
        )

    def test_a5_the_reference_says_record_result_closes_a_task_on_passed(self):
        text = self.reference()
        self.assert_matches(r"`?record-result`?[^.]{0,300}`?passed`?[^.]{0,300}`?done`?", text, "(closes on passed)")
        self.assert_matches(r"evidence (entry|entries)|`?evidence`?[^.]{0,60}entry", text, "(evidence entry)")
        self.assertIn("not_closed", text)

    def test_a5_the_reference_says_record_result_blocks_a_task_on_blocked(self):
        self.assert_matches(r"`?blocked`?[^.]{0,200}`?blocked`?", self.reference(), "(blocked outcome blocks the task)")

    def test_a5_the_reference_says_a_result_never_closes_an_item(self):
        self.assert_matches(
            r"(never|not|cannot|does not|do not)[^.]{0,100}(clos\w+|complet\w+|finish\w*|mov\w+)[^.]{0,80}\bitems?\b|\bitems?\b[^.]{0,120}(never|not|unchanged)[^.]{0,80}(clos\w+|complet\w+|done|lifecycle)",
            self.reference(),
            "(results never close an item)",
        )

    # session-delegation and session-next

    def test_a5_close_out_skills_keep_at_most_one_payload_example(self):
        for name in self.CLOSE_OUT_SKILLS:
            with self.subTest(skill=name):
                self.assert_at_most_one_example(name)

    def test_a5_close_out_skills_point_to_schema_for_the_other_payloads(self):
        for name in self.CLOSE_OUT_SKILLS:
            with self.subTest(skill=name):
                self.assert_points_to_schema(name)

    def test_a5_close_out_skills_say_a_claim_starts_the_work(self):
        for name in self.CLOSE_OUT_SKILLS:
            with self.subTest(skill=name):
                self.assert_matches(
                    r"`?claim`?[^.]{0,200}(starts?|moves?|leaves?|makes?|sets?|puts?)[^.]{0,100}`?active`?|`?active`?[^.]{0,100}`?claim`?",
                    skill(name),
                    "(a claim starts the work)",
                )

    def test_a5_close_out_skills_say_a_passing_result_closes_the_task(self):
        for name in self.CLOSE_OUT_SKILLS:
            with self.subTest(skill=name):
                self.assert_matches(
                    r"`?record-result`?[^.]{0,300}`?passed`?[^.]{0,300}`?done`?|`?passed`?[^.]{0,200}(closes?|moves?|leaves?)[^.]{0,100}`?done`?",
                    skill(name),
                    "(a passing result closes the task)",
                )

    def test_a5_close_out_skills_do_not_send_the_task_transitions_by_hand(self):
        for name in self.CLOSE_OUT_SKILLS:
            with self.subTest(skill=name):
                self.assert_no_manual_task_transitions(skill(name), "(in %s)" % name)

    def test_a5_delegation_lists_the_close_out_as_claim_then_record_result(self):
        text = flat(skill("session-delegation"))
        start = re.search(r"close[- ]?out", text, re.IGNORECASE)
        self.assertIsNotNone(start, "no close-out section")
        window = text[start.start() : start.start() + 3000]
        self.assertRegex(window, r"(?is)`?claim`?.*?`?record-result`?")
        self.assertRegex(window, r"(?i)`?done`?")
        self.assert_no_manual_task_transitions(window, "(in the close-out)")

    def test_a5_next_describes_claim_then_record_result(self):
        text = flat(skill("session-next"))
        self.assertRegex(text, r"(?is)`claim`.*?`record-result`")

    def test_a5_the_seq030_close_out_test_asserts_claim_then_record_result(self):
        text = SEQ030_TEXT_TESTS.read_text(encoding="utf-8")
        self.assertNotIn("record-result.*?transition.*?`?active`?.*?evidence.*?transition.*?`?done`?", text)
        start = text.index("def test_a6_the_close_out_order_is_listed")
        body = text[start : start + 900]
        self.assertRegex(body, r"claim")
        self.assertRegex(body, r"record-result")
        self.assertLess(body.index("claim"), body.index("record-result"))

    # CHANGELOG.md

    def section(self, prefix: str) -> str:
        found = [text for heading, text in unreleased_sections().items() if heading.startswith(prefix)]
        self.assertTrue(found, "no '### %s...' heading under '## Unreleased'" % prefix.title())
        return found[0]

    def test_a5_breaking_changes_list_that_claim_starts_work(self):
        self.assert_matches(
            r"`?claim`?[^.]{0,160}(starts?|moves?|leaves?|makes?)[^.]{0,100}(work|active)",
            self.section("breaking"),
            "(claim starts work)",
        )

    def test_a5_breaking_changes_list_that_record_result_can_close_or_block_a_task(self):
        text = self.section("breaking")
        self.assert_matches(r"`?record-result`?[^.]{0,200}(clos\w+|`?done`?)", text, "(closes a task)")
        self.assert_matches(r"`?record-result`?[^.]{0,200}block\w*", text, "(blocks a task)")

    def test_a5_changes_list_the_schema_command(self):
        self.assert_matches(r"`?schema`?[^.]{0,120}(command|<command>|payload)|schema command", self.section("chang"))

    def test_a5_changes_list_the_show_fields(self):
        self.assert_window_holds(r"`?show`?", SHOW_FIELDS, self.section("chang"), size=400, label="(show fields)")

    def test_a5_changes_list_generated_operation_ids(self):
        self.assert_matches(
            r"generat\w+[^.]{0,80}(operation|ids?)|operation (ids?|identifiers?)[^.]{0,100}(generat\w+|optional|omit\w*)",
            self.section("chang"),
        )


# --------------------------------------------------------------------------- A6


class A6SkillTrimTest(TextCase):
    TRIMMED = (
        "session-verify",
        "session-groom",
        "session-research-design",
        "session-task-planning",
        "session-add-task",
    )
    DECISION_SKILLS = ("session-research-design", "session-task-planning")

    def test_a6_each_skill_keeps_at_most_one_json_payload_example(self):
        for name in self.TRIMMED:
            with self.subTest(skill=name):
                self.assert_at_most_one_example(name)

    def test_a6_each_skill_points_to_schema_for_the_other_payloads(self):
        for name in self.TRIMMED:
            with self.subTest(skill=name):
                self.assert_points_to_schema(name)

    def test_a6_decision_skills_keep_a_decision_example(self):
        for name in self.DECISION_SKILLS:
            with self.subTest(skill=name):
                blocks = json_blocks(skill(name))
                self.assertEqual(1, len(blocks), "%s keeps exactly one json example" % name)
                self.assertIn('"authority"', blocks[0])
                self.assertRegex(blocks[0], LIST_SCOPE, "the decision scope is a list of strings")
                self.assertIn("expect_revision", blocks[0])

    def test_a6_no_skill_sends_a_transition_to_active_after_claiming_or_to_done_after_a_pass(self):
        for name in self.TRIMMED:
            with self.subTest(skill=name):
                self.assert_no_manual_task_transitions(skill(name), "(in %s)" % name)


if __name__ == "__main__":
    unittest.main()
