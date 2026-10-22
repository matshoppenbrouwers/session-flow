"""Describe the payload each mutating command reads.

The valid key sets stay with the commands that validate them; this module imports
them and adds only what they cannot say, the required fields and one minimal example,
so validation and description cannot drift.
"""

from __future__ import annotations

from . import InvalidRequestError, records, store

VALID_KEYS = {
    "capture": records.CAPTURE_KEYS,
    "accept": records.ACCEPT_KEYS,
    "revise": records.REVISE_KEYS,
    "transition": store.TRANSITION_KEYS,
    "claim": store.CLAIM_KEYS,
    "record-result": store.RESULT_KEYS,
}

REQUIRED = {
    "capture": ("scope",),
    "accept": ("actor", "authority", "expect_revision"),
    "revise": ("expect_revision",),
    "transition": ("actor", "changes"),
    "claim": ("seq", "actor", "expect_revision"),
    "record-result": ("seq", "actor", "expect_revision", "result"),
}

EXAMPLES = {
    "capture": {
        "scope": "What the work must deliver, in the words the decision will bind.",
        "body": "",
        "metadata": {
            "title": "A short name for the task",
            "parent": "SEQ-001",
            "priority": "P2",
            "order": 10,
            "depends_on": ["SEQ-001/A0"],
            "allowed_paths": ["scripts/example.py"],
        },
    },
    "accept": {
        "actor": "user:name",
        "authority": {"source": "the user's own words approving this scope", "revision": "2026-01-01T00:00:00Z"},
        "scope": ["implement", "verify"],
        "expect_revision": 1,
    },
    "revise": {"expect_revision": 1, "body": "The revised record body."},
    "transition": {
        "actor": "agent:name",
        "changes": [{"seq": "SEQ-001", "task": "A1", "expect_revision": 1, "metadata": {"lifecycle": "accepted"}}],
    },
    "claim": {
        "seq": "SEQ-001",
        "task": "A1",
        "actor": "agent:A1",
        "expect_revision": 1,
        "allowed_paths": ["scripts/example.py"],
    },
    "record-result": {
        "seq": "SEQ-001",
        "task": "A1",
        "actor": "agent:A1",
        "expect_revision": 2,
        "result": {
            "outcome": "passed",
            "summary": "What was done and how it was checked.",
            "evidence": {
                "criteria": "The acceptance criteria this evidence supports.",
                "revision": "The commit or revision it was observed on.",
                "environment": "Where it was run.",
                "limitations": "What the check did not cover.",
            },
        },
    },
}


def describe(command: str | None) -> dict:
    """Return a command's required fields, optional fields and one minimal example payload."""
    if command not in VALID_KEYS:
        raise InvalidRequestError(
            f"schema needs one command name, one of {', '.join(sorted(VALID_KEYS))}; "
            f"got {command!r}. Run `schema <command>` with one of them",
            commands=sorted(VALID_KEYS),
        )
    required = list(REQUIRED[command])
    return {
        "required": required,
        "optional": sorted(VALID_KEYS[command] - set(required)),
        "example": EXAMPLES[command],
    }
