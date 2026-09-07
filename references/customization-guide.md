# Customization Guide

How to adapt session-flow to your project's structure, tools, and conventions.

---

## Project Configuration

Session-flow reads `.session-flow.json` from your project root. This file is created by `/session-init` but can be edited manually.

### Full schema:

```json
{
  "root": "_devdocs",
  "paths": {
    "research": "_devdocs/research",
    "plans": "_devdocs/plans",
    "work": "_devdocs/work",
    "sequence": "_devdocs/SEQUENCE.md",
    "testing": "_devdocs/testing",
    "architecture": "_devdocs/architecture",
    "direction": "_devdocs/PRD.md",
    "conventions": "_devdocs/conventions.md",
    "lessons": "_devdocs/lessons.md"
  }
}
```

All paths are relative to the project root and live under the nested `paths` object. `paths.sequence`, `paths.direction`, `paths.conventions`, and `paths.lessons` point at files; the rest are directories. Auto-detection covers a missing documentation directory, but not the two the runtime needs: `paths.work` and `paths.sequence` fall back to `_devdocs/work` and `_devdocs/SEQUENCE.md`, so set them explicitly whenever the docs root is not `_devdocs`.

| Key | Purpose |
|-----|---------|
| `work` | The work root: one directory per work item, plus `namespace.json`. Every record the runtime writes lives here |
| `sequence` | The generated backlog view of that work root. Read-only output — `render` writes it, nothing edits it by hand |
| `direction` | Product-direction doc grounding `/session-gatekeeper` triage |
| `conventions` | House rules read by `session-research-design` at design time and enforced by `code-reviewer` |
| `lessons` | Conclusions from past work, read as a one-line index by `session-research-design` and `session-delegation` |

`todo` and `tasks` are not written for a new project. A repository that used the earlier layout keeps them, pointing at its existing `todo/` directory so those historical files stay findable; nothing new is written there.

### Sharing one work root

A path may leave the repo, for example `"work": "../work"`, resolved relative to the repo root. Write it that way when several repos in one parent folder share a backlog: point `work` and `sequence` at the shared locations and leave the rest inside the repo.

The shared root keeps one `namespace.json`, and each participating repository is one entry in its `repositories` list — `{"name": ..., "path": ...}`, the path relative to the work root. Every mutation validates those bindings, so a binding that no longer resolves to a directory fails with `invalid-identity` rather than writing. Never give a second repository its own namespace inside a shared root: identity is allocated per root, and a second namespace splits the sequence in two.

`/session-init` asks once whether the work root is tracked in the repository or lives in its own private repository, and acts on the answer. That decision belongs to the root, not to each repository that binds to it — a repository joining a shared root inherits it. See [work-item-contract.md](work-item-contract.md) for the record format and [runtime-integration.md](runtime-integration.md) for how a skill reaches the runtime.

### Conventions and lessons format

Both files are one rule per line, `rule — reason`, ~140 characters. The reason is mandatory — without it, design either treats the rule as gospel or ignores it. Anything that needs more than one line is an architecture decision and belongs in `architecture/decisions.md` instead.

```markdown
Repository access goes through the store layer — direct SQL in handlers made schema changes unshippable.
No global mutable config — the 2025 rollout bug traced to a request handler mutating it mid-flight.
```

Conventions are rules to design and review against; lessons are conclusions drawn after the fact. Neither is required: when a key is unset or the file is missing, the consuming skills say so and fall back to `CLAUDE.md` plus observed patterns rather than inventing a house style. The highest-value conventions entries are the negatives — what was tried and rejected — because that evidence is gone from the codebase and nothing else records it.

### Minimal config:

```json
{
  "root": "docs",
  "paths": { "work": "docs/work", "sequence": "docs/SEQUENCE.md" }
}
```

Skills auto-detect the other documentation directories. Configure what deviates from convention, and always configure the two the runtime writes.

---

## Override Agents

Session-flow bundles six agents: `code-reviewer`, `code-simplifier`, `codebase-researcher`, `external-researcher`, `security-auditor`, and `test-author`. You can replace any of them with your own.

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
tools: Read, Grep, Glob, Bash
---
```

Then write your review instructions below the frontmatter. Post-implementation will automatically pick up your version.

### Marketplace plugins:

If you have a marketplace plugin installed (e.g., `code-simplifier:code-simplifier`), session-post-implementation detects it and uses the plugin instead of the bundled agent. No configuration needed.

---

## Model Selection

Bundled agents (`code-reviewer`, `code-simplifier`, `security-auditor`) declare **`model: inherit`** in their frontmatter. They run on the parent session's model. So:

- A user running Claude Code on Opus 4.7 gets Opus 4.7 subagents automatically.
- A user running Sonnet gets Sonnet subagents.
- A user on Haiku gets Haiku subagents (may be underpowered for heavy review — override if so).

> **Note:** `model: inherit` is the magic value. *Omitting* the `model` field entirely does **not** inherit — Claude Code falls back to Sonnet. If you want the user's session tier, write `model: inherit` explicitly.

### Why inherit-by-default?

Pinning a specific tier in a bundled agent is hostile to users who upgrade their main model: their code review stays stuck at the pinned tier even though they paid for more capability. `inherit` respects the user's choice.

### When to override

If a specific agent genuinely needs a different tier than the session default:

1. **Project-level override** — create `.claude/agents/code-reviewer.md` in your repo with `model: opus` (or whatever) in the frontmatter.
2. **User-level override** — create `~/.claude/agents/code-reviewer.md` for all your projects.

The precedence rules above apply: project wins over user wins over bundle.

### Custom agents you write

For your own custom agents, **use `model: inherit`** unless the agent has a task-specific reason to pin a tier (e.g. heavy reasoning that always warrants Opus regardless of session model). Do not omit the field — that silently falls back to Sonnet.

---

## Test Runner Integration

Session-post-implementation runs your test suite in its test-suite step. It finds the test command using this detection order:

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

If your project has no test suite, post-implementation skips the test-suite step and notes it in the summary. No configuration needed.

---

## Output Directory Customization

Each skill writes artifacts to a specific directory. To change where artifacts go:

### Option 1: Edit `.session-flow.json`

Change the relevant path:

```json
{
  "paths": {
    "work": "project-management/work",
    "architecture": "docs/arch"
  }
}
```

All skills reading that directory type will use the new path.

### Option 2: Pre-create directories

If the directories exist before you run `/session-init`, the init skill detects them and writes matching paths into `.session-flow.json`. So you can set up your preferred layout first, then run init to formalize it.

### Default directory layout (created by session-init):

```
project-root/
  .session-flow.json
  CLAUDE.md / AGENTS.md   # session-flow:sequence block wired in by init
  _devdocs/
    research/       # Research documents from session-research-design
    plans/          # Implementation plans from session-research-design
    work/           # Work root: one directory per work item, plus namespace.json
    SEQUENCE.md     # Generated backlog view of the work root -- never edited by hand
    testing/        # Manual test plans and results from session-post-implementation
    architecture/   # Architecture documentation
    PRD.md          # Product direction doc (optional; used by session-gatekeeper)
    conventions.md  # House rules (optional; used by session-research-design and code-reviewer)
    lessons.md      # Conclusions from past work (optional; one-line index)
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
