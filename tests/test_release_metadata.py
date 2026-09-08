"""Release-metadata consistency checks.

The release number lives in four places — `plugin.json`, both slots in
`marketplace.json`, and `CITATION.cff` — and those four have drifted apart before.
These checks defend their mutual agreement, that the agreed number is semver at the
2.x major this release moves to, and that `CITATION.cff` carries a real release date
beside it. They also pin the two shipped descriptions to the true skill count and the
Python runtime prerequisite, and pin `README.md` against a stale skill count anywhere
in its body.

`tests/test_installation.py` already reads `plugin.json`'s version dynamically and
asserts the installed layouts report it; nothing here duplicates that. The subject
here is the cross-file agreement that check cannot see."""

import json
import re
import unittest
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_MANIFEST = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_MANIFEST = REPO_ROOT / ".claude-plugin" / "marketplace.json"
CITATION = REPO_ROOT / "CITATION.cff"
README = REPO_ROOT / "README.md"

MINIMUM_MAJOR = 2
SHIPPED_SKILL_COUNT = 16
PYTHON_MINIMUM = "3.9"

SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
CFF_VERSION_RE = re.compile(r"^version:\s*[\"']?([^\"'\s#]+)", re.MULTILINE)
CFF_DATE_RE = re.compile(r"^date-released:\s*[\"']?([^\"'\s#]+)", re.MULTILINE)
PYTHON_PREREQUISITE_RE = re.compile(r"python\s*" + re.escape(PYTHON_MINIMUM), re.IGNORECASE)

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}
DIGITS = r"(\d+)"
ANY_COUNT = r"(\d+|" + "|".join(sorted(NUMBER_WORDS)) + r")"


def count_patterns(token: str) -> tuple:
    """Both shapes a skill count is written in, given what counts as a number token.

    Before: "15 skills", "16-skill chain", "15 skill metadata". The lookbehind drops a
    count that is the tail of a range — "1-2 skills are loaded at a time" claims no
    total and is legitimate prose — and a count welded to a word or identifier.
    After: the badge and label forms, "Skills-15-green" and "Skills: 15".
    """
    return (
        re.compile(r"(?<![\w./\-–—])" + token + r"[\s\-–]?\s*skills?\b", re.IGNORECASE),
        re.compile(r"\bskills?\s*[:=-]\s*" + token, re.IGNORECASE),
    )


# Prose counts a subset in words — "Two skills are derived from superpowers" — and that
# is not a total-count claim, so the README scan reads digits only. A description is one
# sentence whose only skill count is the total, so it accepts either spelling.
DIGIT_PATTERNS = count_patterns(DIGITS)
ANY_PATTERNS = count_patterns(ANY_COUNT)


def read_json(path: Path) -> dict:
    assert path.is_file(), f"{path} must exist"
    return json.loads(path.read_text(encoding="utf-8"))


def declared_versions() -> dict[str, str]:
    """Every place the release number is written, keyed by where a drift would be fixed."""
    plugin = read_json(PLUGIN_MANIFEST)
    marketplace = read_json(MARKETPLACE_MANIFEST)
    plugins = marketplace.get("plugins") or []
    assert plugins, "marketplace.json must list at least one plugin"
    citation = CFF_VERSION_RE.findall(CITATION.read_text(encoding="utf-8"))
    assert len(citation) == 1, f"CITATION.cff must declare exactly one top-level version, found {citation}"
    return {
        ".claude-plugin/plugin.json:version": plugin.get("version"),
        ".claude-plugin/marketplace.json:metadata.version": marketplace.get("metadata", {}).get("version"),
        ".claude-plugin/marketplace.json:plugins[0].version": plugins[0].get("version"),
        "CITATION.cff:version": citation[0],
    }


def shipped_descriptions() -> dict[str, str]:
    plugins = read_json(MARKETPLACE_MANIFEST).get("plugins") or []
    assert plugins, "marketplace.json must list at least one plugin"
    return {
        ".claude-plugin/plugin.json:description": read_json(PLUGIN_MANIFEST).get("description"),
        ".claude-plugin/marketplace.json:plugins[0].description": plugins[0].get("description"),
    }


def as_number(token: str) -> int:
    return NUMBER_WORDS[token.lower()] if token.lower() in NUMBER_WORDS else int(token)


def skill_counts(text: str, patterns=ANY_PATTERNS) -> list[int]:
    """Every skill count the text claims, as integers, in no particular order."""
    before, after = patterns
    return [as_number(token) for token in before.findall(text) + after.findall(text)]


def lines_claiming(path: Path, counts: set[int]) -> list[str]:
    """Every line of the file that claims one of the given skill counts, with its number."""
    return [
        f"{path.name}:{number}: {line.strip()}"
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if counts.intersection(skill_counts(line, DIGIT_PATTERNS))
    ]


def lines_containing(path: Path, needle: str) -> list[str]:
    return [
        f"{path.name}:{number}: {line.strip()}"
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if needle in line
    ]


class VersionAgreementTest(unittest.TestCase):
    """The four version strings move together or the release is mislabelled somewhere."""

    def setUp(self):
        self.versions = declared_versions()

    def test_all_four_version_strings_agree(self):
        self.assertEqual(4, len(self.versions))
        for where, value in self.versions.items():
            with self.subTest(where=where):
                self.assertIsNotNone(value, f"{where} declares no version")
        self.assertEqual(1, len(set(self.versions.values())), self.versions)

    def test_the_agreed_version_is_semver(self):
        for where, value in self.versions.items():
            with self.subTest(where=where):
                self.assertIsNotNone(value, f"{where} declares no version")
                self.assertRegex(str(value), SEMVER_RE, f"{where} is not a semantic version")

    def test_the_release_is_at_least_major_two(self):
        for where, value in self.versions.items():
            with self.subTest(where=where):
                match = SEMVER_RE.match(str(value))
                self.assertIsNotNone(match, f"{where} is not a semantic version: {value}")
                self.assertGreaterEqual(
                    int(match.group("major")),
                    MINIMUM_MAJOR,
                    f"{where} reads {value}; the breaking release is {MINIMUM_MAJOR}.0.0 or later",
                )

    def test_citation_records_a_release_date(self):
        found = CFF_DATE_RE.findall(CITATION.read_text(encoding="utf-8"))
        self.assertEqual(1, len(found), f"CITATION.cff must declare exactly one date-released, found {found}")
        try:
            released = date.fromisoformat(found[0])
        except ValueError as error:
            self.fail(f"CITATION.cff date-released {found[0]!r} is not an ISO date: {error}")
        self.assertIsInstance(released, date)


class ShippedDescriptionTest(unittest.TestCase):
    """Both descriptions are the plugin's shop window: the count and the prerequisite."""

    def setUp(self):
        self.descriptions = shipped_descriptions()

    def test_both_descriptions_state_the_shipped_skill_count(self):
        for where, description in self.descriptions.items():
            with self.subTest(where=where):
                self.assertIsNotNone(description, f"{where} is missing")
                counts = skill_counts(description)
                self.assertTrue(counts, f"{where} states no skill count")
                self.assertEqual(
                    {SHIPPED_SKILL_COUNT},
                    set(counts),
                    f"{where} states skill counts {sorted(set(counts))}; the shipped count is {SHIPPED_SKILL_COUNT}",
                )

    def test_both_descriptions_name_the_python_runtime_prerequisite(self):
        for where, description in self.descriptions.items():
            with self.subTest(where=where):
                self.assertIsNotNone(description, f"{where} is missing")
                self.assertRegex(
                    description,
                    PYTHON_PREREQUISITE_RE,
                    f"{where} does not name the Python {PYTHON_MINIMUM} runtime prerequisite",
                )


class ReadmeSkillCountTest(unittest.TestCase):
    """README claimed 15 skills after the sixteenth shipped; no stale count may remain."""

    def test_readme_never_says_fifteen_skills(self):
        self.assertEqual([], lines_containing(README, "15 skills"))

    def test_readme_claims_no_skill_count_other_than_the_shipped_one(self):
        stale = {count for count in range(1, 100) if count != SHIPPED_SKILL_COUNT}
        self.assertMultiLineEqual("", "\n".join(lines_claiming(README, stale)))


if __name__ == "__main__":
    unittest.main()
