# Adoption Note

What actually happens when you put session-flow on a machine that has never run it, in the order you
meet it. This is the account of the steps, their questions and their output; the reasoning behind the
design is in [work-item-contract.md](work-item-contract.md) and
[runtime-integration.md](runtime-integration.md).

## 1. Python first

Every record is written by `scripts/session-flow.py`, so Python 3.9 or newer must be reachable as
`python3` before anything else. There is no hand-editing path to fall back on.

```bash
python3 --version
```

An interpreter that is too old, or missing, does not produce a traceback: the runtime answers on the
protocol with `error.code` `unsupported-runtime` and `error.detail.install`, which names the package
to install (`sudo apt install python3` on Debian/Ubuntu, `brew install python3` on macOS). A machine
without Python — chiefly native Windows outside WSL — cannot run the plugin at all.

## 2. Install

In Claude Code, register the marketplace and install the plugin:

```
/plugin marketplace add matshoppenbrouwers/session-flow
/plugin install session-flow@session-flow
```

For a standalone copy, `./install.sh` (add `--scope project` for `.claude/` in the current
directory, `--dry-run` to see the file list first). The installer stages the runtime, its Python
package and the `references/` tree, verifies the staged runtime, and only then activates the skill
entry files. A skill installed without its support package would fail on first use, so a failed
verification leaves the previous state alone.

## 3. A new project: `/session-init`

`/session-init` asks three questions and nothing else.

1. **Where the docs root goes** — `_devdocs/` unless you say otherwise.
2. **Whether this repository shares a work root with a parent folder** — answering yes binds this
   repository into that root instead of creating a second namespace.
3. **Whether the work root is versioned, and where** — asked once, acted on, never re-asked.

The third question decides a capability, not only privacy. Tracking the work root in the repository
gives you history, backup and restore from the existing remote, and lets hosted ops read the backlog.
Keeping the work root ignored and giving it its own private repository keeps the records private and
means hosted ops cannot see this backlog: both ops workflow templates read committed files through
`OPS_TODO` and `OPS_SEQUENCE`, and a GitHub Actions job cannot read an ignored directory. Declining
every option is allowed; the work root is then unversioned, backup and restore are unavailable, and
applied transitions report that there was nothing to commit.

Init then binds the namespace and renders. On a fresh project the render writes
`<root>/SEQUENCE.md` with its generated-output header, no entries, and reports `items: 0`.

## 4. An existing repository: `/session-repair`

A repository that already has `todo/SEQUENCE.md`, per-task files and phase files does not run
`/session-init` again. Run `/session-repair`, which surveys, refuses unsafe ground, and stops at a
plan. Nothing is written until you confirm.

The survey also works when the work root or namespace does not exist. It reports unbound item
previews and includes namespace and Git setup in the plan. An absent or empty work root is eligible;
records or runtime state without their namespace require restoration of the original namespace.

The plan lists, per entry, which SEQ becomes which directory, which files are linked, which
identities become tombstones, and which annotations carry across. Identities that survive only in a
historical file appear in that list too, marked `historical`: they are retired, never reallocated.
Read the plan against the sequence you know before you confirm anything.

Repair refuses before the first write when an existing record store has no Git history, when the project
tree or the work root has uncommitted changes, when a prior operation sits unapplied in the journal,
when another coordinator holds the lock, or when the survey met a line it cannot classify. Each
refusal names the condition and the command that clears it. There is no `--force`, so commit or
stash your work and run it again.

An eligible empty work root can acquire Git history during approved setup. Repair reuses enclosing
history when it covers that path. For an ignored work root it creates a separate local repository
on `main`, preserving ignore rules and creating no remote. Git must be installed and the repository
must have a configured commit identity; repair does not invent one.

## 5. What the apply leaves behind

First-time migration calls `bind-namespace` after approval to create the namespace and repository
binding, with a separate setup commit. A setup failure stops before import and reports what remains
to recover. A retry after successful setup preserves its namespace and proceeds to import. Existing
initialized roots need no setup commit.

The import itself is one operation and one commit, `session-flow: import <operation>`. Under the
work root you get `seq-NNN/intent.md` for every entry, `.state/tombstones` holding every identity the
survey saw, and `.state/operations/<id>.json` recording the applied operation. Then the round-trip
check re-derives the sequence from the imported items and compares it with the original entry by
entry; a mismatch fails the run and leaves you a commit to revert.

Repair compares the survey fingerprint before setup and again before import. Apply also checks the
approved fingerprint, so a changed source or discovered identity requires a new review. Verification
reports the compared entry count and both commit IDs when setup was necessary. Local Git history
without a remote does not provide remote backup.

Nothing is deleted or moved. `_devdocs/todo/` becomes the pre-import archive: the historical task and
phase files stay exactly where they are, keep their existing names, and are linked from the new
records rather than rewritten. The pre-import sequence remains an ordinary Git object. Nothing new is
written into the archive after the import.

## 6. The first render

The generated sequence now lives at `paths.sequence` — `_devdocs/SEQUENCE.md` by default, one level
above the archive — and reproduces the pre-import list line for line: same identities, same order,
same ` ⇄ <url>` annotations, same `[auto]` markers, same links and comment lines.

```bash
python3 -B "$ENTRYPOINT" --project-root "$PROJECT_ROOT" render
```

`render` rewrites that file from the work root and reports how many items it wrote. It is generated
output from here on: change the work item through the runtime, then render. Anything typed into the
file is lost at the next render and was never read in between.
