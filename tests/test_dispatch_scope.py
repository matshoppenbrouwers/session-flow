"""Static dispatch-scope contract (R-006): a sequence anchor addresses exactly
one task, and neither execution skill keeps a whole-file dispatch branch."""

import re
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEQUENCE = REPO_ROOT / "_devdocs" / "todo" / "SEQUENCE.md"
DISPATCH_SKILLS = (
    REPO_ROOT / "skills" / "session-next" / "SKILL.md",
    REPO_ROOT / "skills" / "session-delegation" / "SKILL.md",
)

ENTRY_RE = re.compile(r"^- \[(?: |x|X|DEFERRED)\] (SEQ-\d+)\b.*? → (\S+)\s*$")

WHOLE_FILE_BRANCHES = (
    (
        "scope disjunction",
        re.compile(r"or\s+anchored\s+task", re.IGNORECASE),
        "the linked phase (or anchored task) is complete",
    ),
    (
        "whole-file dispatch target",
        re.compile(r"against\s+(?:that|the)\s+(?:whole\s+|entire\s+)?(?:todo|phase|plan)?\s*file\b", re.IGNORECASE),
        "invoke `/session-delegation` against that file",
    ),
    (
        "whole-file node construction",
        re.compile(r"(?:every|all|each)\s+tasks?\s+in\s+the\s+(?:todo|phase|plan)\s+file", re.IGNORECASE),
        "every task in the todo file maps to a node in the graph",
    ),
    (
        "whole-file unit of work",
        re.compile(r"(?:whole|entire)\s+(?:todo|phase|plan)\s+file", re.IGNORECASE),
        "dispatch the whole phase file",
    ),
)


def entry_links(sequence_text: str) -> list[tuple[str, str, str | None]]:
    links = []
    for line in sequence_text.splitlines():
        match = ENTRY_RE.match(line)
        if not match:
            continue
        seq_id, target = match.groups()
        path, _, anchor = target.partition("#")
        links.append((seq_id, path, anchor or None))
    return links


def heading_count(task_file: Path, anchor: str) -> int:
    pattern = re.compile(rf"^#{{1,6}} \[{re.escape(anchor)}\]", re.MULTILINE)
    return len(pattern.findall(task_file.read_text(encoding="utf-8")))


def anchor_problems(sequence_text: str, root: Path) -> list[str]:
    problems = []
    for seq_id, path, anchor in entry_links(sequence_text):
        task_file = root / path
        if not task_file.is_file():
            problems.append(f"{seq_id}: missing breakdown {path}")
            continue
        if anchor is None:
            continue
        found = heading_count(task_file, anchor)
        if found != 1:
            problems.append(f"{seq_id}: anchor #{anchor} matched {found} task headings in {path}")
    return problems


def whole_file_branches(skill_text: str) -> list[str]:
    return [label for label, pattern, _ in WHOLE_FILE_BRANCHES if pattern.search(skill_text)]


class AnchorScopeTest(unittest.TestCase):
    """Every anchored entry names one task, so a scope can be resolved from it."""

    def setUp(self):
        self.sequence_text = SEQUENCE.read_text(encoding="utf-8")

    def test_sequence_entries_are_parsed(self):
        self.assertGreater(len(entry_links(self.sequence_text)), 1)

    def test_every_anchor_resolves_to_one_task_heading(self):
        self.assertEqual([], anchor_problems(self.sequence_text, REPO_ROOT))

    def test_unresolvable_anchor_is_reported(self):
        entry = "- [ ] SEQ-900 P1: Invented entry → _devdocs/todo/2026-09-07-astra-phase-1-flow-safeguards.md#9Z-9\n"
        problems = anchor_problems(entry, REPO_ROOT)
        self.assertEqual(1, len(problems), problems)
        self.assertIn("matched 0 task headings", problems[0])

    def test_ambiguous_anchor_is_reported(self):
        with tempfile.TemporaryDirectory() as workdir:
            root = Path(workdir)
            (root / "plan.md").write_text("### [1A-1] first\n\n### [1A-1] second\n", encoding="utf-8")
            entry = "- [ ] SEQ-901 P1: Duplicate → plan.md#1A-1\n"
            problems = anchor_problems(entry, root)
            self.assertEqual(["SEQ-901: anchor #1A-1 matched 2 task headings in plan.md"], problems)

    def test_missing_breakdown_is_reported(self):
        entry = "- [ ] SEQ-902 P1: Dangling → _devdocs/todo/does-not-exist.md#1A-1\n"
        self.assertEqual(["SEQ-902: missing breakdown _devdocs/todo/does-not-exist.md"], anchor_problems(entry, REPO_ROOT))


class DispatchBoundaryTest(unittest.TestCase):
    """Neither skill may dispatch or close out against a whole task plan file."""

    def test_no_whole_file_dispatch_branch_survives(self):
        for skill in DISPATCH_SKILLS:
            with self.subTest(skill=skill.parent.name):
                self.assertEqual([], whole_file_branches(skill.read_text(encoding="utf-8")))

    def test_each_branch_is_detected_when_reintroduced(self):
        base = DISPATCH_SKILLS[0].read_text(encoding="utf-8")
        for label, _, sample in WHOLE_FILE_BRANCHES:
            with self.subTest(branch=label):
                self.assertEqual([label], whole_file_branches(f"{base}\n{sample}\n"))


if __name__ == "__main__":
    unittest.main()
