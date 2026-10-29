"""Initialize review guidance without changing work records or existing policy."""

import argparse
import json
import os
import stat
import sys
import tempfile
from pathlib import Path


START = b"<!-- session-flow:review -->"
END = b"<!-- /session-flow:review -->"
BRIDGE = b"""<!-- session-flow:review -->
## Code review

When reviewing code, read the repository-root `REVIEW.md` and any `REVIEW.md`
in parent directories of the reviewed files. Apply that guidance alongside
project instructions and configured conventions. If a policy file is absent,
say so; do not invent project rules. Review policy guides findings; it does not
authorize edits, publication, or completion of work.
For a session-flow report-only review, leave edits and full-suite execution to
the coordinating workflow. Identify the review policy files used in the handoff.
<!-- /session-flow:review -->"""


def snapshot(path):
    """Reject links and special files rather than editing their destinations."""
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(mode):
        raise ValueError("not a regular file: " + str(path))
    return path.read_bytes()


def instruction_content(original):
    content = original or b""
    newline = b"\r\n" if b"\r\n" in content else b"\n"
    bridge = BRIDGE.replace(b"\n", newline)
    if START in content or END in content:
        if content.count(START) != 1 or content.count(END) != 1:
            raise ValueError("malformed session-flow:review markers")
        start, end = content.index(START), content.index(END)
        if end < start:
            raise ValueError("malformed session-flow:review markers")
        return content[:start] + bridge + content[end + len(END):]
    separator = (b"" if content.endswith(b"\n") else newline) + newline if content else b""
    return content + separator + bridge + newline


def initialize(project_root):
    root = Path(project_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("project root must be an existing directory")
    template = Path(__file__).resolve().parents[2] / "references" / "review-policy-template.md"
    policy = template.read_bytes()
    plan = []
    # Preflight every destination before creating anything.
    for name in ("REVIEW.md", "CLAUDE.md", "AGENTS.md"):
        path = root / name
        before = snapshot(path)
        after = (policy if before is None else before) if name == "REVIEW.md" else instruction_content(before)
        plan.append((path, before, after))
    results = {}
    for path, before, after in plan:
        if before == after:
            results[path.name] = "preserved"
            continue
        if snapshot(path) != before:
            raise ValueError("file changed during initialization: " + str(path))
        if before is None:
            with path.open("xb") as stream:
                stream.write(after)
            results[path.name] = "created"
        else:
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=root, prefix=".session-flow-review-", delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(after)
                os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
                os.replace(temporary, path)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            results[path.name] = "updated"
    return {"project_root": str(root), "files": results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = initialize(args.project_root)
    except (OSError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
