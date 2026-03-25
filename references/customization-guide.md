# Customization Guide

How to adapt session-flow to your project's structure, tools, and conventions.

---

## Project Configuration

Session-flow reads `.session-flow.json` from your project root. This file is created by `/session-init` but can be edited manually.

### Full schema:

```json
{
  "todoDir": "_devdocs/todo",
  "memoryDir": "_devdocs/memory",
  "architectureDir": "_devdocs/architecture",
  "archiveDir": "_devdocs/memory/archive",
  "reportsDir": "_devdocs/reports"
}
```

All paths are relative to the project root. Every field is optional — skills fall back to auto-detection if a field is missing.

### Minimal config:

```json
{
  "todoDir": "docs/tasks"
}
```

Skills will auto-detect other directories. Only configure what deviates from convention.

---

## Override Agents

Session-flow bundles three agents: `code-reviewer`, `code-sanitizer`, and `code-simplifier`. You can replace any of them with your own.

### Precedence order (highest wins):

1. **Project-level:** `.claude/agents/code-reviewer.md` in your repo
2. **User-level:** `~/.claude/agents/code-reviewer.md` in your home directory
3. **Marketplace plugin:** e.g., `code-simplifier:code-simplifier` (if installed)
4. **Package-bundled:** `session-flow/agents/code-reviewer.md`

### To override:

Create a file at `.claude/agents/code-reviewer.md` (or whichever agent) in your project. Follow the agent format:

```yaml
---
name: code-reviewer
description: Your custom reviewer description.
model: sonnet
tools: Read, Grep, Glob, Bash
---
```

Then write your review instructions below the frontmatter. Post-implementation will automatically pick up your version.

### Marketplace plugins:

If you have a marketplace plugin installed (e.g., `code-simplifier:code-simplifier`), session-post-implementation detects it and uses the plugin instead of the bundled agent. No configuration needed.

---

## Test Runner Integration

Session-post-implementation runs your test suite in Step 5. It finds the test command using this detection order:

### Detection order:

1. **CLAUDE.md instructions** — If your CLAUDE.md contains a `## Testing` section with a command (e.g., `./scripts/run_tests.sh`), that command is used.
2. **Script detection** — Looks for `scripts/run_tests.*`, `scripts/test.*`, or `Makefile` with a `test` target.
3. **Language heuristics:**
   - Python project (`pyproject.toml` or `setup.py`): `pytest`
   - Node project (`package.json`): `npm test`
   - Rust project (`Cargo.toml`): `cargo test`
   - Go project (`go.mod`): `go test ./...`

### To specify explicitly:

Add to your project's `CLAUDE.md`:

```markdown
## Testing

Run tests with:
\`\`\`bash
./scripts/run_tests.sh --quick
\`\`\`
```

Session-post-implementation reads this and uses the exact command.

### Skipping tests:

If your project has no test suite, post-implementation skips Step 5 and notes it in the summary. No configuration needed.

---

## Output Directory Customization

Each skill writes artifacts to a specific directory. To change where artifacts go:

### Option 1: Edit `.session-flow.json`

Change the relevant path:

```json
{
  "todoDir": "project-management/tasks",
  "architectureDir": "docs/arch"
}
```

All skills reading that directory type will use the new path.

### Option 2: Pre-create directories

If the directories exist before you run `/session-init`, the init skill detects them and writes matching paths into `.session-flow.json`. So you can set up your preferred layout first, then run init to formalize it.

### Default directory layout (created by session-init):

```
project-root/
  .session-flow.json
  _devdocs/
    todo/           # Task files from session-task-planning
    memory/         # Session state, decision logs, archives
    architecture/   # Architecture documentation
    reports/        # Research reports from session-research-design
```

---

## Release Tooling

Session-release integrates with your project's versioning and packaging tools.

### Version bump detection order:

1. **`/version-bump` skill** — If your project has `.claude/skills/version-bump/SKILL.md`, session-release invokes it.
2. **Sync scripts** — Looks for `packaging/sync-versions.*` or `scripts/version-bump.*`.
3. **Standard tooling:**
   - Node: updates `version` in `package.json`
   - Python: updates `version` in `pyproject.toml`
   - Rust: updates `version` in `Cargo.toml`

### Release package detection order:

1. **`/release-package` skill** — If your project has `.claude/skills/release-package/SKILL.md`, session-release invokes it.
2. **Standard tooling** — Falls back to `git tag` + changelog update.

### Adding custom release steps:

Create `.claude/skills/version-bump/SKILL.md` in your project with your version bump instructions. Session-release calls it instead of the built-in logic.

Similarly, create `.claude/skills/release-package/SKILL.md` for custom packaging (signing, installer builds, deployment, etc.).

### Satellite content verification:

Session-release checks if your project has satellite directories (docs site, marketing site, etc.) that reference versioned content. It verifies those references are still accurate after the version bump.

Configure satellite paths in `.session-flow.json`:

```json
{
  "satelliteDirs": ["_docs-site", "_website"]
}
```

---

## Task Sizing

Session-task-planning sizes tasks to fit a single Claude Code session. The defaults assume ~30 minutes per task.

### Default thresholds:

| Metric | Default | Meaning |
|--------|---------|---------|
| Files per task | 1-5 | Tasks touching >5 files get split |
| Independent outcomes | 1 | Tasks with multiple outcomes get split |
| Testable | Required | Each task must have a verifiable acceptance criterion |

### Adjusting for longer sessions:

If your sessions typically run longer (1+ hours), you can increase the file count threshold. Add to your CLAUDE.md:

```markdown
## Session-Flow Settings

Task sizing: up to 8 files per task (longer sessions).
```

Session-task-planning reads this and adjusts its splitting heuristic.

### Adjusting for shorter sessions:

For quick iterations (15-minute sessions), tighten the constraints:

```markdown
## Session-Flow Settings

Task sizing: 1-3 files per task (short sessions).
```

### Phase grouping:

Tasks are grouped into phases (`SETUP`, `CORE`, `TEST`, `DOCS`). The phase names come from the implementation plan. To customize phase names, structure your plan with explicit section headers — task-planning preserves them.
