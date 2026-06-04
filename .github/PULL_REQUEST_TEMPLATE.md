## What & why

Briefly describe the change and the motivation.

## Type

- [ ] New skill
- [ ] New agent
- [ ] Fix / improvement to an existing skill or agent
- [ ] Docs only

## Checklist

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full quality checklists.

- [ ] One skill per PR (unless tightly coupled)
- [ ] Skill YAML frontmatter has only `name` and `description`; agents use `model: inherit`
- [ ] No project-specific paths or tool references
- [ ] Updated `CHANGELOG.md`
- [ ] Updated `README.md` if adding skills or changing the chain
- [ ] Tested by installing to a clean `~/.claude/skills/` and invoking the relevant command
