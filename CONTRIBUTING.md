# Contributing to session-flow

## Skill Quality Checklist

Before submitting a skill:

- [ ] YAML frontmatter has only `name` and `description`
- [ ] Description includes what it does AND when to trigger
- [ ] SKILL.md is under 500 lines
- [ ] Has an `**Announce:**` line
- [ ] Has an Anti-Patterns section
- [ ] Has a Workflow Integration section showing its place in the chain
- [ ] No project-specific paths or tool references
- [ ] Uses the path resolution pattern (config → detect → suggest init)

## Agent Quality Checklist

- [ ] YAML frontmatter has `name`, `description`, `model`, `tools`
- [ ] No project-specific paths or framework assumptions
- [ ] Reads project conventions from CLAUDE.md
- [ ] Has a performance budget or scope constraint
- [ ] Output format is structured and actionable

## Testing Changes

1. Install to a clean `~/.claude/skills/` directory
2. Grep for project-specific paths: `grep -r "pkb/\|_devdocs/\|tauri\|WSL" skills/ agents/`
3. Verify each skill triggers correctly by invoking its slash command
4. Run through the full chain on a sample project

## Pull Request Guidelines

- One skill per PR (unless tightly coupled)
- Include before/after examples if changing behavior
- Update CHANGELOG.md
- Update README.md if adding new skills or changing the chain
