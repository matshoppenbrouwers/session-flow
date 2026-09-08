# Contributing to session-flow

## Skill Quality Checklist

Before submitting a skill:

- [ ] YAML frontmatter has only `name` and `description`
- [ ] Description includes what it does AND when to trigger
- [ ] SKILL.md is under 500 lines
- [ ] Opens with one sentence saying what it is about to do and what it will produce
- [ ] Cross-references other steps by name, not number
- [ ] No project-specific paths or tool references
- [ ] Uses the path resolution pattern (config → detect → suggest init)

## Agent Quality Checklist

- [ ] YAML frontmatter has `name`, `description`, `tools`, `model: inherit`
- [ ] **Use `model: inherit`** so the agent runs on the user's session model (e.g. a user running Opus 4.7 gets Opus 4.7 subagents automatically). Omitting the field defaults to Sonnet — that is *not* inheritance. Only pin a specific tier (`model: opus` / `sonnet` / `haiku`) when the agent has a hard capability requirement.
- [ ] No project-specific paths or framework assumptions
- [ ] Reads project conventions from CLAUDE.md / AGENTS.md
- [ ] Has a performance budget or scope constraint
- [ ] Output format is structured and actionable

## Testing Changes

Run the suite from the repository root:

```bash
python3 -B -m unittest discover -s tests -v
```

It needs Python 3.9+ and nothing else — no third-party packages, no network. The 356 tests in
`tests/` cover the runtime: its records, store and generated views; the repair and continuation
paths; the packaged standalone installation; end-to-end scenarios against a temporary work root;
and the release metadata, meaning the four version strings and the two shipped descriptions.

**What it does not cover: host invocation.** Nothing in the suite starts Claude Code, loads a
skill through a host, or checks that a skill's prose actually drives an agent the way it reads. A
skill body is exercised only where a test asserts on its text. Run these by hand before submitting
a change to a skill or an agent:

1. Install to a clean `~/.claude/skills/` directory
2. Grep for project-specific paths: `grep -r "pkb/\|_devdocs/\|tauri\|WSL" skills/ agents/`
3. Verify each skill triggers correctly by invoking its slash command
4. Run through the full chain on a sample project

## Pull Request Guidelines

- One skill per PR (unless tightly coupled)
- Include before/after examples if changing behavior
- Update CHANGELOG.md
- Update README.md if adding new skills or changing the chain
