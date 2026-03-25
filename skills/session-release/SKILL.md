---
name: session-release
description: End-to-end release workflow that bumps version, packages artifacts, and verifies satellite content (docs sites, marketing sites, changelogs) is up-to-date. Combines project-specific release skills with a generic release surface scan. Triggers on "/session-release" or when user says "prepare the release", "do a release", or "release workflow".
---

# Session Release

Orchestrate a full release cycle: version bump, artifact packaging, and satellite content verification.

**Announce:** "Using session-release to run the full release workflow."

## Core Principle

A release is more than a version bump. Code ships alongside documentation, websites, changelogs, and download pages. This skill ensures nothing is forgotten by:

1. Running the project's own release skills (if they exist)
2. Scanning for satellite content that may need updating
3. Confirming with the user before proceeding at each gate

## Prerequisites

- All tests pass (run `/session-post-implementation` or the test suite first)
- Working tree is clean or changes are committed
- User knows the target version (or will provide it)

## Workflow

### Step 1: Pre-flight checks

Verify readiness:

1. **Git status**: Check for uncommitted changes. Warn if dirty.
2. **Test status**: Ask the user to confirm tests pass (or offer to run them).
3. **Target version**: If not provided as argument, ask the user. Validate semver format.

### Step 2: Version bump

Look for a project-specific version bump mechanism:

**Detection order:**
1. Project skill: `/version-bump` (check `.claude/skills/version-bump/SKILL.md`)
2. Version sync script: `packaging/sync-versions.py`, `scripts/bump-version.*`
3. Standard tooling: `npm version`, `cargo set-version`, `bumpversion`, `tbump`
4. Manual: Search for version strings across config files

**If a project skill exists:** Invoke `/version-bump <version>` and follow its workflow.

**If no skill exists:** Identify all files containing the current version and update them. Common locations:
- `package.json` / `Cargo.toml` / `pyproject.toml` / `setup.cfg`
- `version.py` / `__init__.py` / `_version.py`
- `tauri.conf.json` / `Info.plist` / `build.gradle`

After bumping, verify consistency by grepping for the old version -- nothing should remain except changelogs and historical references.

### Step 3: User gate -- build

The build step often requires the user's environment (signing keys, native toolchains, CI pipelines). Present the build instructions and **wait for the user to confirm the build is complete** before proceeding.

**If a project skill exists** (`/release-package`): it will contain build instructions -- reference them.

**If no skill exists:** Check for common build commands:
- `npm run build` / `pnpm build`
- `cargo build --release`
- `python -m build` / `poetry build`
- CI/CD trigger instructions

Print the build command(s) and ask: "Run the build and let me know when it's done."

**Do NOT run builds automatically** -- they often need environment setup, signing keys, or manual oversight.

### Step 4: Package release artifacts

Look for a project-specific packaging mechanism:

**Detection order:**
1. Project skill: `/release-package` (check `.claude/skills/release-package/SKILL.md`)
2. Release scripts: `scripts/release.*`, `packaging/release.*`
3. Standard tooling: `gh release create`, `cargo publish`, `npm publish`

**If a project skill exists:** Invoke `/release-package` and follow its workflow.

**If no skill exists:** Identify artifacts and provide manual instructions.

### Step 5: Satellite content scan

This is the key differentiator. Scan the repository for content that often needs updating alongside a release but is easy to forget.

**Scan for these categories:**

#### 5a. Documentation sites

Search for documentation site directories:
```
Glob patterns: **/docusaurus.config.*, **/mkdocs.yml, **/docs/conf.py, **/.vitepress/config.*, **/astro.config.*, **/book.toml
Common dirs: docs-site/, _docs-site/, docs/, documentation/, website/docs/
```

**If found:** Check for version references, outdated screenshots, feature docs that should mention new capabilities.

#### 5b. Marketing / landing pages

Search for website directories:
```
Glob patterns: **/index.html (in website-like dirs), _website/, website/, landing/, www/
Package.json with vite/next/gatsby in non-app directories
```

**If found:** Check for version badges, download links, feature lists, changelog sections.

#### 5c. Changelogs and release notes

Search for:
```
CHANGELOG.md, CHANGES.md, HISTORY.md, RELEASES.md, NEWS.md
```

**If found:** Check if the new version has an entry. If not, draft one from recent git history.

#### 5d. README and badges

Check root `README.md` for:
- Version badges (shields.io, badgen, etc.)
- Installation instructions referencing specific versions
- Feature lists that may be outdated

#### 5e. Download / distribution files

Search for:
```
Glob patterns: **/downloads/*, **/dist/*, **/releases/*, latest.json, **/DownloadModal.*, **/download*.tsx
```

**If found:** Check if they reference the new version.

#### 5f. API documentation

Search for:
```
**/openapi.*, **/swagger.*, **/api-docs/
```

### Step 6: User gate -- satellite updates

Present findings as a checklist:

```markdown
## Release Surface Scan for v{VERSION}

### Needs attention:
- [ ] {item}: {what needs updating} ({file path})
- [ ] {item}: {what needs updating} ({file path})

### Looks current:
- [x] {item}: already up-to-date ({file path})

### Not found (skip):
- {category}: no {type} detected in this repo
```

**Ask the user:** "Which of these should we update now? (Enter numbers, 'all', or 'skip')"

Apply the updates the user approves. For each update:
- Make the minimal change needed (version string, link, date)
- Show the diff before applying if the change is non-trivial
- For changelog entries, draft from `git log` since the last tag

### Step 7: Final verification

Run a final check:

1. **Version grep**: Search for the OLD version across the repo. Flag any remaining references (excluding changelogs, git history, lock files).
2. **Build artifacts**: Verify expected release artifacts exist (if applicable).
3. **Satellite content**: Spot-check that updated files are consistent.

### Step 8: Release commit

If changes were made in steps 5-6, commit them:

```
release: prepare v{VERSION} for distribution
```

### Step 9: Release instructions

Print a summary of what's ready and what the user needs to do next:

```markdown
## Release v{VERSION} Ready

### Completed:
- Version bumped across {N} files
- {Artifacts packaged / listed}
- {Satellite content updated}

### Next steps:
1. {Push / tag / create GitHub release / publish -- project-specific}
2. {Deploy docs site -- if applicable}
3. {Deploy website -- if applicable}
4. {Announce -- if applicable}
```

## Execution Notes

- Steps 3 and 6 are **user gates** -- always wait for confirmation before proceeding
- The satellite scan (Step 5) is intentionally broad -- it's better to flag something unnecessary than to miss something important
- Lock files (`package-lock.json`, `Cargo.lock`, `pnpm-lock.yaml`) should be regenerated by the build, not manually edited
- Exclude from old-version grep: `CHANGELOG.md`, `*.lock`, `node_modules/`, `.git/`, `target/`, `build/`, `dist/`

## Anti-Patterns

**Skipping the satellite scan:**
- BAD: Bump version, package, ship -- forget the docs site still says v0.1.0
- GOOD: Always scan, even if you think nothing needs updating

**Auto-running builds:**
- BAD: Run build commands without checking for signing keys or environment setup
- GOOD: Print build instructions, wait for user to confirm completion

**Updating lock files manually:**
- BAD: Edit `package-lock.json` to change version strings
- GOOD: Let the build toolchain regenerate lock files

**Grepping too aggressively:**
- BAD: Flag every occurrence of "0.2.0" including in unrelated constants
- GOOD: Focus on config files, docs, and distribution -- skip test fixtures and historical references

## Workflow Integration

This skill is the final step in the session workflow chain:

```
/session-init  -->  /session-research-design  -->  /session-task-planning  -->  /session-delegation  -->  /session-post-implementation  -->  /session-release
  (bootstrap)       (research & design)             (break into tasks)          (execute tasks)           (refine and test)                  (this skill)
```

It can also be used standalone when the code is already tested and ready to ship.
