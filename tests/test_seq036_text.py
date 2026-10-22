"""SEQ-036 acceptance tests for the documentation (task B4).

B4  the reference, the work-item contract, session-delegation, session-next, session-verify and the
    changelog describe the SEQ-036 runtime: what leaving out `result.evidence` does, which fields only
    their own command writes, append-only evidence, refused identity edits, claim's acceptance check and
    JSON argument errors; no file mentions a `--same-meaning` flag

Each check looks for case-insensitive keywords that co-occur in one paragraph or list item, so a correct
rewording passes. Nothing here is written to; the files are only read.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE = REPO_ROOT / "references" / "runtime-integration.md"
CONTRACT = REPO_ROOT / "references" / "work-item-contract.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
SKILLS = REPO_ROOT / "skills"
LIST_ITEM = re.compile(r"^\s*([-*]|\d+\.)\s")

LEAVE_OUT = r"\b(leav(e|es|ing)|omit(s|ted|ting)?|without|left out|absent)\b"
EVIDENCE_LEFT_OUT = (
    r"evidence",
    LEAVE_OUT,
    r"\bapplicable\b|\bapplies\b",
    r"\bclos(e|es|ed|ing)\b",
    r"already|existing|earlier|previous|stored|recorded",
)
OLD_LEAVE_OUT_SENTENCE = r"leave\s+`?evidence`?\s+out\s+to\s+record\s+a\s+result\s+that\s+will\s+not\s+close"
HELPER_OWNED = (r"\bclaim\b", r"\bresult\b", r"\bcorrections\b", r"\bonly\b", r"record-result")
EVIDENCE_APPEND_ONLY = (
    r"evidence",
    r"append[- ]only|only (be )?append(ed|s)?\b|stored entries|existing entries",
    r"\brevise\b",
    r"\btransition\b",
)
IDENTITY_REFUSED = (r"\bformat\b", r"\bnamespace\b", r"\bseq\b", r"\btask\b", r"refus|reject", r"acceptance")
CLAIM_NEEDS_ACCEPTANCE = (r"\bclaim\b", r"accept", r"missing-authority", r"fingerprint|applicable|applies")
ARGUMENT_ERRORS_IN_JSON = (r"argument", r"json", r"\bexit\w*\b[^.]{0,30}\b2\b", r"invalid-request")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def skill(name: str) -> str:
    return read(SKILLS / name / "SKILL.md")


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def paragraphs(text: str) -> list:
    return [flat(block) for block in re.split(r"\n\s*\n", text) if block.strip()]


def list_items(text: str) -> list:
    items, current = [], []
    for line in text.splitlines():
        if LIST_ITEM.match(line) or not line.strip():
            if current:
                items.append(flat(" ".join(current)))
            current = [line] if line.strip() else []
        elif current:
            current.append(line)
    if current:
        items.append(flat(" ".join(current)))
    return items


def units(text: str) -> list:
    """Every paragraph and every list item: the stretches a keyword group may co-occur in."""
    return paragraphs(text) + list_items(text)


def unreleased_breaking_changes() -> str:
    text = read(CHANGELOG)
    section = re.search(
        r"^##\s+\[?Unreleased\]?[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.IGNORECASE | re.DOTALL | re.MULTILINE
    )
    if section is None:
        return ""
    parts = re.split(r"^###\s+", section.group(1), flags=re.MULTILINE)[1:]
    for part in parts:
        if part.split("\n", 1)[0].strip().lower() == "breaking changes":
            return part.split("\n", 1)[1] if "\n" in part else ""
    return ""


class TextCase(unittest.TestCase):
    def assert_unit_holds(self, text: str, patterns: tuple, label: str) -> None:
        """Some paragraph or list item matches every pattern."""
        for unit in units(text):
            if all(re.search(pattern, unit, re.IGNORECASE) for pattern in patterns):
                return
        self.fail("no paragraph or list item in %s matches all of: %s" % (label, "; ".join(patterns)))

    def assert_absent(self, pattern: str, text: str, label: str) -> None:
        found = re.search(pattern, flat(text), re.IGNORECASE)
        self.assertIsNone(found, "%s still says %r" % (label, found and found.group(0)))


class B4DocsTest(TextCase):
    """The docs follow the code: field ownership, refused edits, claim's check, JSON argument errors."""

    # the --same-meaning flag does not exist

    def test_b4_no_reference_or_skill_mentions_a_same_meaning_flag(self):
        files = sorted((REPO_ROOT / "references").rglob("*")) + sorted(SKILLS.rglob("*"))
        checked = 0
        for path in files:
            if not path.is_file() or path.suffix not in (".md", ".json", ".txt", ""):
                continue
            checked += 1
            self.assertNotIn("--same-meaning", read(path), "%s mentions a --same-meaning flag" % path.relative_to(REPO_ROOT))
        self.assertGreater(checked, 5)

    # leaving result.evidence out

    def test_b4_the_reference_says_leaving_evidence_out_closes_only_with_an_applicable_entry_recorded(self):
        text = read(REFERENCE)
        self.assert_unit_holds(text, EVIDENCE_LEFT_OUT, "runtime-integration.md")
        self.assert_absent(OLD_LEAVE_OUT_SENTENCE, text, "runtime-integration.md")

    def test_b4_session_delegation_says_leaving_evidence_out_closes_only_with_an_applicable_entry_recorded(self):
        text = skill("session-delegation")
        self.assert_unit_holds(text, EVIDENCE_LEFT_OUT, "session-delegation/SKILL.md")
        self.assert_absent(OLD_LEAVE_OUT_SENTENCE, text, "session-delegation/SKILL.md")

    def test_b4_session_next_says_leaving_evidence_out_closes_only_with_an_applicable_entry_recorded(self):
        text = skill("session-next")
        self.assert_unit_holds(text, EVIDENCE_LEFT_OUT, "session-next/SKILL.md")
        self.assert_absent(OLD_LEAVE_OUT_SENTENCE, text, "session-next/SKILL.md")

    def test_b4_the_changelog_says_leaving_evidence_out_closes_only_with_an_applicable_entry_recorded(self):
        text = unreleased_breaking_changes()
        self.assertTrue(text.strip(), "CHANGELOG.md has no Unreleased breaking changes section")
        self.assert_unit_holds(text, EVIDENCE_LEFT_OUT, "CHANGELOG.md Unreleased breaking changes")
        self.assert_absent(OLD_LEAVE_OUT_SENTENCE, text, "CHANGELOG.md")

    # the reference and the work-item contract

    RULES = {
        "claim, result and corrections are written only by their commands": HELPER_OWNED,
        "evidence is append-only in revise and transition": EVIDENCE_APPEND_ONLY,
        "identity and acceptance fields refuse a change": IDENTITY_REFUSED,
        "claim needs applicable acceptance": CLAIM_NEEDS_ACCEPTANCE,
        "argument errors answer in JSON with exit 2": ARGUMENT_ERRORS_IN_JSON,
    }

    def assert_runtime_rules(self, text: str, name: str) -> None:
        for rule, patterns in self.RULES.items():
            with self.subTest(rule=rule):
                self.assert_unit_holds(text, patterns, "%s (%s)" % (name, rule))

    def test_b4_the_reference_states_the_field_ownership_and_argument_error_rules(self):
        self.assert_runtime_rules(read(REFERENCE), "runtime-integration.md")

    def test_b4_the_work_item_contract_states_the_field_ownership_and_argument_error_rules(self):
        self.assert_runtime_rules(read(CONTRACT), "work-item-contract.md")

    def test_b4_the_reference_no_longer_says_patches_can_still_write_helper_owned_fields(self):
        self.assert_absent(
            r"(revise|transition)[^.]{0,80}metadata patches can still write\s+`?claim`?",
            read(REFERENCE),
            "runtime-integration.md",
        )

    def test_b4_neither_reference_says_metadata_evidence_replaces_the_whole_list(self):
        for path in (REFERENCE, CONTRACT):
            with self.subTest(path=path.name):
                self.assert_absent(r"evidence`?\s+replaces the whole list", read(path), path.name)

    # session-verify

    def test_b4_session_verify_says_stored_evidence_entries_come_first_and_stay_unchanged(self):
        text = skill("session-verify")
        self.assert_unit_holds(
            text,
            (r"evidence", r"stored|existing", r"\bfirst\b", r"unchanged|in order|same order", r"refus|reject|append[- ]only"),
            "session-verify/SKILL.md",
        )
        self.assert_absent(r"evidence`?\s+replaces the whole list", text, "session-verify/SKILL.md")

    # the changelog

    def test_b4_the_changelog_lists_the_field_ownership_and_argument_error_changes_as_breaking(self):
        text = unreleased_breaking_changes()
        self.assertTrue(text.strip(), "CHANGELOG.md has no Unreleased breaking changes section")
        for rule, patterns in self.RULES.items():
            with self.subTest(rule=rule):
                self.assert_unit_holds(text, patterns, "CHANGELOG.md Unreleased breaking changes (%s)" % rule)


if __name__ == "__main__":
    unittest.main()
