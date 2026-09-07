# Runtime Integration

How a skill, a command, or a companion plugin reaches the session-flow record runtime: where the
package lives on each host, the versioned request/response protocol, the named errors, and the
limitations the runtime does not defend against. Record fields and lifecycle rules are in
[work-item-contract.md](work-item-contract.md).

The runtime is a hard requirement, not an optional layer. There is no hand-editing path and no
legacy mode: when the helper or its interpreter is missing, mutation fails closed.

## Resolving the package

The entrypoint is `<package-root>/scripts/session-flow.py`, invoked with an absolute path by an
absolute interpreter path. Three host cases, one rule each — and no fourth:

| Host | Resolution |
|------|------------|
| Native Claude plugin | Use the plugin root the host supplies in `${CLAUDE_PLUGIN_ROOT}`. |
| Codex | Use the discovered installed skill and package location for the installed entry file. |
| Standalone copy | Read the runtime descriptor the installer wrote beside the entry file. |

The descriptor is `session-flow-runtime.json`, written into each installed skill directory next to
its `SKILL.md`. Its paths are relative to that directory, so a moved installation still resolves:

```json
{
  "package": "session-flow",
  "version": "2.0.0",
  "protocol": 1,
  "python_minimum": "3.9",
  "entrypoint": "../../scripts/session-flow.py",
  "package_root": "../..",
  "references": "../../references"
}
```

Resolve `entrypoint` and `references` against the descriptor's own directory and use the absolute
results. It is generated output, rewritten on every install, so never edit it and never treat its
`version` as authoritative — ask `doctor` for `protocol`.

**Never scan the filesystem for an installed copy.** A found-by-search package may be any version,
and picking one silently is how two protocols end up mixed in one session.

When the descriptor, the entrypoint, or a named support file is missing, fail with what is missing
and where it was expected. Do not fall back to a different copy, a bundled snippet, or hand-editing.

## Invoking a command

```bash
python3 /abs/path/to/scripts/session-flow.py doctor --project-root /abs/path/to/repo
python3 /abs/path/to/scripts/session-flow.py revise --project-root /abs/path/to/repo \
  --seq SEQ-042 --input /abs/path/to/payload.json
```

| Option | Meaning |
|--------|---------|
| `--project-root` | The repository whose `.session-flow.json` resolves `paths.work` and `paths.sequence`. Defaults to the working directory. |
| `--namespace` | The namespace UUID the addressed records must belong to. A mismatch is `invalid-identity`. |
| `--seq` | Work-item identity, `SEQ-NNN`. |
| `--task` | Task identity within that item, such as `A1`. |
| `--input` | Path to the JSON payload of a mutation. |

Every mutation payload carries an operation ID, the expected record revisions, the requested changes,
and provenance. **No option accepts interpolated issue text or a shell fragment**, no argument is
passed to a shell, and no record content is executed by any command. Free text reaches the runtime
only as JSON through `--input`.

Paths resolve from `.session-flow.json`: `paths.work` (default `_devdocs/work`) and `paths.sequence`
(default `_devdocs/SEQUENCE.md`).

## Request and response protocol

stdout carries exactly one JSON object; diagnostics go to stderr. Parse stdout, never stderr.

Success, exit code 0:

```json
{
  "protocol": 1,
  "command": "show",
  "ok": true,
  "result": {}
}
```

Failure, exit code 1:

```json
{
  "protocol": 1,
  "command": "revise",
  "ok": false,
  "error": {
    "code": "stale-revision",
    "message": "record SEQ-042 holds revision 5; the request expected 4",
    "detail": {"seq": "SEQ-042"}
  }
}
```

`protocol`, `command`, and `ok` are always present. `result` and `error` are mutually exclusive.
`error.detail` is an object whose keys depend on the code; treat unknown keys as informational.
An unsupported interpreter answers on the same protocol with `command: null` — the guard runs before
any package module is imported, so a too-old interpreter receives JSON and an install instruction
rather than a `SyntaxError`.

### The `protocol` version

`protocol` is a single integer, reported by `doctor` and echoed in every response. It is
**independent of the plugin's semantic version**: the release number moves with every shipped
change, the protocol only when this contract changes.

Consumers check `protocol`, never the release number. Each companion declares the minimum and
maximum protocol it accepts in its own configuration, alongside its explicit path to the flow
installation. When flow is absent or the protocol falls outside that range, the lifecycle-dependent
commands refuse and name what to install, while the companion's standalone features — session
logging, Notion capture, portfolio rendering — keep working. Nothing degrades to editing records by
hand.

### Command families

| Command | Effect |
|---------|--------|
| `doctor` | Report runtime, protocol, storage, command availability, and error codes. Never mutates. |
| `show` | Return one record's identity, metadata, and scope. |
| `capture` | Create a work item in `captured`. |
| `revise` | Change a record under an expected revision. `--same-meaning` records both fingerprints. |
| `accept` | Bind an acceptance record to the current fingerprint and authority. |
| `select` | Return one candidate and its eligibility reasons. It never starts execution. |
| `claim` | Record a bounded assignment. It does not run or schedule that assignment. |
| `record-result` | Record a scoped task result. |
| `transition` | Apply a lifecycle transition. |
| `render` | Regenerate the sequence view and task views. Output is read-only, never an authority. |
| `import` | One-way transformation of an existing `SEQUENCE.md` into work items. There is no dual-format mutation path. |
| `reconcile` | Finish known partial operations; stop on unexplained divergence. |
| `backup` | Verify the configured work-root remote and push. |
| `restore` | Check the work root out from that remote. |

`backup` and `restore` are thin wrappers over Git and define no archive format. The work root is an
ordinary Git repository: it owns history, and each applied transition ends in a commit there.

A command whose handler has not landed in this build is still reachable and answers
`not-implemented` naming its handler. `doctor`'s `commands` map reports each family's handler and
whether it is available, so a consumer can check before invoking rather than after failing.

## Named errors

| Code | Meaning |
|------|---------|
| `unsupported-format` | Envelope missing, duplicated, malformed, or of an unknown format version. |
| `stale-revision` | The expected record revision does not match the stored one. |
| `root-busy` | The work root is locked by another coordinator or needs reconciliation. |
| `invalid-identity` | Identity, immutable field, illegal transition, or resolved path is not valid. |
| `missing-authority` | The requested change needs authority that was not supplied. |
| `inapplicable-evidence` | The evidence does not apply to the accepted scope revision. |
| `not-implemented` | The command family is reachable but its handler has not landed. |
| `unsupported-runtime` | The interpreter is older than the supported floor. |
| `invalid-request` | The request itself is malformed: unknown option, unreadable input file. |
| `internal` | Unexpected failure; the diagnostic on stderr carries the traceback. |

Every rejection happens before any file is written. Dispatch on `error.code`, never on the message
text, which is written for a person and may be reworded.

## `doctor`

`doctor` is the one command a consumer may call before it trusts anything else. Its result carries:

- `protocol` — the integer above.
- `plugin_version` — the semantic release, for reporting only.
- `record_format` — the record format version this build reads.
- `runtime` — `python`, `minimum_python`, `executable`, `package_root`, `install_instruction`.
- `storage` — `work_root`, `work_root_present`, `sequence_path`, and `limitations`.
- `commands` — per family, its handler and whether it is available.
- `errors` — the code-to-description map above.

The runtime floor is **Python 3.9 with the standard library only**. Below it, `doctor` returns
`unsupported-runtime` with an explicit install instruction rather than a traceback. Machines without
Python — chiefly native Windows outside WSL — cannot run the plugin, and that is the whole
compatibility story.

An unversioned work root appears in `storage.limitations` as a named limitation stating that backup
and restore are unavailable.

## Limitations

These are limitations of the runtime, not guarantees it makes. They were measured on 2026-09-07 on
the primary development path (`/mnt/c`, a 9p/DrvFs mount) and on native ext4; what held is stated as
holding, and what did not is stated as a limit rather than engineered around.

- **9p and DrvFs write caching can lose recently written records on a hard power loss.** Replacement
  itself is sound: 3000 concurrent reads during repeated replacement produced no torn read on either
  filesystem, and directory `fsync` and hardlink exclusivity both work on both. Durability after
  power loss on a 9p mount is what is not promised.
- **No POSIX lock coordinates with a Windows-side process editing the same files.** The root lock
  serializes participating local writers only. It cannot stop another permitted tool, or an editor
  on the Windows side, from writing into the work root.
- **Multiple replacements are not collectively atomic.** Each individual `os.replace` is atomic; a
  transition that rewrites several records is made recoverable by the operation journal, not by the
  filesystem.
- **Enforcement stops at the CLI boundary.** The runtime rejects invalid calls and detects unexpected
  revisions. It cannot constrain other permitted tools. Host permissions must constrain external
  actions; no acceptance field and no model-generated policy is a credential.
- **Host plugin storage is not authoritative.** Records live in the configured work root only.
  Host plugin caches and host-managed plugin data are replaceable, and a documented uninstall can
  remove the latter; never keep state there.
- **Local recovery has no external effects.** A crash leaves a reconcilable operation, never an
  instruction to repeat its effects. `reconcile` stops on unexplained divergence instead of
  overwriting it, and never performs an external side effect.

### Unsupported configurations

Outside the coordination guarantee. These are documented as **unsupported** rather than defended
against, and a report from one of them is not a defect:

- Network or cloud-synchronized work roots.
- Simultaneous editing of one work root from another operating system.
- Mutation of one work root from more than one host.
- More than one coordinator at a time. Several agents may execute independent tasks, but state
  transitions are serialized through the root lock.

Linux/WSL and macOS are the tested runtimes. Native Windows is out of scope while Python is a hard
requirement.
