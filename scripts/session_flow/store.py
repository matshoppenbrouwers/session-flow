"""Work-root store: root lock, ID reservation, tombstones, operation journal.

One coordinator mutates one work root at a time. The lock is an exclusively
created directory, the reservation index is `tombstones`, and every mutation is
written to `.state/operations/<id>.json` before the canonical records are
replaced, so an interrupted run leaves a reconcilable operation rather than a
half-known root. The journal is a recovery record, not a history store: Git owns
history, and an applied operation ends in a commit of the work root.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from session_flow import (
    RECORD_FORMAT_VERSION,
    InvalidIdentityError,
    InvalidRequestError,
    MissingAuthorityError,
    RootBusyError,
    SessionFlowError,
    StaleRevisionError,
    UnsupportedFormatError,
)
from session_flow import records

STATE_DIRECTORY = ".state"
LOCK_DIRECTORY = "lock"
OWNER_FILE = "owner.json"
OPERATIONS_DIRECTORY = "operations"
TOMBSTONES_FILE = "tombstones"
NAMESPACE_FILE = "namespace.json"

TEMPORARY_PREFIX = ".session-flow-"
ITEM_DIRECTORY_RE = re.compile(r"^seq-([0-9]{3,6})$")
OPERATION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
DEFAULT_COORDINATOR = "session-flow"
IMPORT_COMMAND = "import"
CLAIM_FIELD = "claim"
RESULT_FIELD = "result"
CLAIM_EXEMPT_TRANSITIONS = ((records.LIFECYCLE_CAPTURED, records.LIFECYCLE_ACCEPTED),)
RESULT_OUTCOMES = ("passed", "failed", "blocked", "unknown")
APPLIED = "applied"
PREPARED = "prepared"
PENDING = "pending"
DIVERGED = "diverged"
RESOLVED = "resolved"
BLOCKED = "blocked"
GIT_TIMEOUT = 60
DEFAULT_REMOTE = "origin"
REMOTE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
REVISION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@^~-]{0,199}$")


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_directory(work_root: Path) -> Path:
    return Path(work_root) / STATE_DIRECTORY


def lock_directory(work_root: Path) -> Path:
    return state_directory(work_root) / LOCK_DIRECTORY


def owner_path(work_root: Path) -> Path:
    return lock_directory(work_root) / OWNER_FILE


def operations_directory(work_root: Path) -> Path:
    return state_directory(work_root) / OPERATIONS_DIRECTORY


def tombstones_path(work_root: Path) -> Path:
    return state_directory(work_root) / TOMBSTONES_FILE


def namespace_path(work_root: Path) -> Path:
    return Path(work_root) / NAMESPACE_FILE


def sync_directory(directory: Path) -> None:
    try:
        handle = os.open(str(directory), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(handle)
    except OSError:
        pass
    finally:
        os.close(handle)


def write_atomic(path: Path, text: str) -> None:
    """Replace `path` through a temporary on the target's own filesystem."""
    directory = Path(path).parent
    directory.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=str(directory), prefix=TEMPORARY_PREFIX, delete=False
    )
    try:
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, str(path))
    except OSError:
        Path(handle.name).unlink(missing_ok=True)
        raise
    sync_directory(directory)


def write_json(path: Path, document: dict) -> None:
    write_atomic(path, json.dumps(document, indent=2, sort_keys=True) + "\n")


def read_json(path: Path, description: str, error=InvalidRequestError) -> dict:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as failure:
        raise error(
            f"cannot read the {description} at {path} ({failure.strerror}); "
            "check the work root's permissions",
            path=str(path),
        ) from failure
    except ValueError as failure:
        raise error(
            f"the {description} at {path} is not valid JSON ({failure}); repair the file before writing",
            path=str(path),
        ) from failure
    if not isinstance(payload, dict):
        raise error(f"the {description} at {path} must hold a JSON object", path=str(path))
    return payload


def ensure_plain_path(work_root: Path, candidate: Path) -> Path:
    """Reject a symlink or a non-regular file anywhere between the root and the target."""
    root = Path(work_root)
    try:
        relative = Path(candidate).relative_to(root)
    except ValueError as failure:
        raise InvalidIdentityError(
            f"{candidate} is not inside the work root {root}; address records by identity, not by path",
            path=str(candidate),
        ) from failure
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise InvalidIdentityError(
                f"{current} is a symbolic link; the work root holds plain files only, "
                "so replace the link with the real record",
                path=str(current),
            )
        if current.exists() and not (current.is_file() or current.is_dir()):
            raise InvalidIdentityError(
                f"{current} is not a regular file or directory; remove the special file "
                "before mutating this work item",
                path=str(current),
            )
    return Path(candidate)


def resolved_work_root(request: dict) -> Path:
    work_root = Path(request["work_root"]).resolve()
    if not work_root.is_dir():
        raise InvalidIdentityError(
            f"no work root at {work_root}; run /session-init to create it before mutating records",
            work_root=str(work_root),
        )
    return work_root


def record_path(work_root: Path, seq: str, task=None) -> Path:
    directory = Path(work_root) / records.item_directory(seq)
    if task is None:
        candidate = directory / records.INTENT_FILE
    else:
        candidate = directory / records.TASKS_DIRECTORY / (records.parse_task_id(task) + ".md")
    ensure_plain_path(work_root, candidate)
    records.ensure_within(work_root, candidate)
    return candidate


def read_namespace(work_root: Path) -> dict:
    path = namespace_path(work_root)
    if not path.is_file():
        raise InvalidIdentityError(
            f"the work root at {work_root} has no {NAMESPACE_FILE}; run /session-init to bind "
            "the namespace and repositories before mutating records",
            work_root=str(work_root),
        )
    document = read_json(path, NAMESPACE_FILE, UnsupportedFormatError)
    version = document.get("format")
    if type(version) is not int:
        raise UnsupportedFormatError(
            f"{path} has no integer `format` field; add \"format\": {RECORD_FORMAT_VERSION}",
            path=str(path),
        )
    if version != RECORD_FORMAT_VERSION:
        raise UnsupportedFormatError(
            f"{NAMESPACE_FILE} declares format {version} and this runtime reads "
            f"{RECORD_FORMAT_VERSION}; upgrade session-flow instead of editing the root",
            format=version,
        )
    return {
        "format": version,
        "namespace": records.parse_namespace(document.get("namespace")),
        "repositories": records.parse_repositories(document.get("repositories", [])),
    }


def validate_bindings(work_root: Path, bindings: list) -> list:
    """Check each shared-root repository binding resolves to a plain directory."""
    for binding in bindings:
        raw = Path(work_root) / binding["path"]
        if raw.is_symlink():
            raise InvalidIdentityError(
                f"repository binding {binding['name']} points at the symbolic link {raw}; "
                f"record the real path in {NAMESPACE_FILE}",
                binding=binding["name"],
            )
        if not raw.resolve().is_dir():
            raise InvalidIdentityError(
                f"repository binding {binding['name']} resolves to {raw.resolve()}, which is not a "
                f"directory; correct the binding in {NAMESPACE_FILE}",
                binding=binding["name"],
            )
    return list(bindings)


def current_host() -> str:
    return socket.gethostname()


def process_alive(pid) -> bool:
    if type(pid) is not int or pid <= 0:
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def owner_liveness(owner) -> str:
    """Classify the recorded owner. A timestamp is never part of this decision."""
    if not isinstance(owner, dict):
        return "unrecorded"
    if owner.get("host") != current_host():
        return "unknown"
    return "alive" if process_alive(owner.get("pid")) else "gone"


def read_owner(work_root: Path):
    path = owner_path(work_root)
    if not path.is_file():
        return None
    try:
        owner = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return owner if isinstance(owner, dict) else None


def describe_owner(owner) -> str:
    if not isinstance(owner, dict):
        return "an unrecorded coordinator"
    return "%s on %s (pid %s)" % (
        owner.get("coordinator", "an unnamed coordinator"),
        owner.get("host", "an unnamed host"),
        owner.get("pid", "unknown"),
    )


def ownership_document(coordinator: str) -> dict:
    return {
        "host": current_host(),
        "coordinator": coordinator,
        "pid": os.getpid(),
        "token": uuid.uuid4().hex,
        "acquired_at": now_stamp(),
    }


def busy_error(work_root: Path) -> RootBusyError:
    owner = read_owner(work_root)
    liveness = owner_liveness(owner)
    pending = [document["operation"] for document in pending_operations(work_root)]
    return RootBusyError(
        f"the work root is held by {describe_owner(owner)}, whose process is {liveness}; "
        "an expired timestamp never releases the lock, so wait for that coordinator, run "
        "reconcile, or take the lock over explicitly once its owner is gone",
        owner=owner,
        liveness=liveness,
        pending_operations=pending,
    )


def take_over_lock(work_root: Path, coordinator: str, takeover: dict, allow_pending=False) -> dict:
    owner = read_owner(work_root)
    liveness = owner_liveness(owner)
    if liveness not in ("gone", "unrecorded"):
        raise busy_error(work_root)
    pending = [document["operation"] for document in pending_operations(work_root)]
    if pending and not allow_pending:
        raise RootBusyError(
            f"the previous coordinator left {len(pending)} prepared operation(s) in the work root; "
            "run reconcile before taking the lock over",
            owner=owner,
            liveness=liveness,
            pending_operations=pending,
        )
    ownership = ownership_document(coordinator)
    ownership["took_over_from"] = owner
    ownership["takeover_reason"] = takeover.get("reason", "the previous owner is gone")
    write_json(owner_path(work_root), ownership)
    return ownership


def acquire_lock(work_root: Path, coordinator: str, takeover=None, allow_pending=False) -> dict:
    directory = lock_directory(work_root)
    directory.parent.mkdir(parents=True, exist_ok=True)
    try:
        directory.mkdir()
    except FileExistsError:
        if takeover is None:
            raise busy_error(work_root)
        return take_over_lock(work_root, coordinator, takeover, allow_pending)
    ownership = ownership_document(coordinator)
    write_json(owner_path(work_root), ownership)
    return ownership


def release_lock(work_root: Path, ownership: dict) -> None:
    held = read_owner(work_root)
    if held is not None and held.get("token") != ownership.get("token"):
        raise RootBusyError(
            f"the root lock is held by {describe_owner(held)}, not by this coordinator; "
            "only the matching lock may be released",
            owner=held,
        )
    owner_path(work_root).unlink(missing_ok=True)
    try:
        lock_directory(work_root).rmdir()
    except FileNotFoundError:
        return
    except OSError as failure:
        raise RootBusyError(
            f"cannot release the root lock at {lock_directory(work_root)} ({failure.strerror}); "
            "remove the unexpected content inside it and re-run",
            path=str(lock_directory(work_root)),
        ) from failure


@contextmanager
def root_lock(work_root: Path, coordinator: str, takeover=None, allow_pending=False):
    ownership = acquire_lock(work_root, coordinator, takeover, allow_pending)
    try:
        yield ownership
    finally:
        release_lock(work_root, ownership)


def read_tombstones(work_root: Path) -> dict:
    path = tombstones_path(work_root)
    if not path.is_file():
        return {"format": RECORD_FORMAT_VERSION, "entries": []}
    document = read_json(path, TOMBSTONES_FILE, UnsupportedFormatError)
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise UnsupportedFormatError(
            f"{path} must hold an `entries` list of retired and reserved identities; "
            "repair the allocation index before reserving",
            path=str(path),
        )
    return {"format": document.get("format", RECORD_FORMAT_VERSION), "entries": entries}


def entry_ids(entry) -> list:
    if not isinstance(entry, dict):
        return []
    aliases = entry.get("aliases") if isinstance(entry.get("aliases"), list) else []
    return [value for value in [entry.get("seq")] + list(aliases) if isinstance(value, str)]


def retained_ids(work_root: Path) -> set:
    return {
        "SEQ-" + ITEM_DIRECTORY_RE.match(child.name).group(1)
        for child in Path(work_root).iterdir()
        if child.is_dir() and ITEM_DIRECTORY_RE.match(child.name)
    }


def taken_ids(work_root: Path) -> set:
    taken = retained_ids(work_root)
    for entry in read_tombstones(work_root)["entries"]:
        taken.update(entry_ids(entry))
    return taken


def item_number(value: str):
    match = records.ITEM_ID_RE.match(value)
    return int(match.group(1)) if match else None


def next_item_id(work_root: Path) -> str:
    numbers = [number for number in map(item_number, taken_ids(work_root)) if number is not None]
    return "SEQ-%03d" % ((max(numbers) if numbers else 0) + 1)


def reserve_item_id(work_root: Path, operation_id: str) -> str:
    """Take the next identity durably. A crashed reservation stays taken."""
    document = read_tombstones(work_root)
    item_id = next_item_id(work_root)
    document["entries"].append(
        {"seq": item_id, "state": "reserved", "operation": operation_id, "at": now_stamp()}
    )
    write_json(tombstones_path(work_root), document)
    return item_id


def parse_operation_id(value) -> str:
    if not isinstance(value, str) or not OPERATION_ID_RE.match(value):
        raise InvalidIdentityError(
            f"{value!r} is not an operation identity; supply `operation` as up to 64 characters of "
            "letters, digits, dot, hyphen, or underscore",
            operation=value,
        )
    return value


def operation_path(work_root: Path, operation_id: str) -> Path:
    return operations_directory(work_root) / (parse_operation_id(operation_id) + ".json")


def load_operation(work_root: Path, operation_id: str):
    path = operation_path(work_root, operation_id)
    if not path.is_file():
        return None
    return read_json(path, "operation journal entry", RootBusyError)


def pending_operations(work_root: Path) -> list:
    directory = operations_directory(work_root)
    if not directory.is_dir():
        return []
    pending = []
    for path in sorted(directory.glob("*.json")):
        document = read_json(path, "operation journal entry", RootBusyError)
        if document.get("state") != APPLIED:
            pending.append(document)
    return pending


def replayed_result(work_root: Path, operation_id: str, fingerprint: str):
    """Return the prior result for a retried operation, or raise on a conflicting reuse."""
    document = load_operation(work_root, operation_id)
    if document is None:
        return None
    if document.get("payload_fingerprint") != fingerprint:
        raise InvalidIdentityError(
            f"operation {operation_id} already exists with a different payload; issue a new "
            "operation identity instead of reusing this one",
            operation=operation_id,
            state=document.get("state"),
        )
    if document.get("state") != APPLIED:
        raise RootBusyError(
            f"operation {operation_id} is prepared but not applied; run reconcile to finish or "
            "abandon it before retrying",
            operation=operation_id,
            state=document.get("state"),
        )
    result = dict(document.get("result") or {})
    result["replayed"] = True
    return result


def block_on_pending(work_root: Path, operation_id: str) -> None:
    blocking = [
        document["operation"]
        for document in pending_operations(work_root)
        if document.get("operation") != operation_id
    ]
    if blocking:
        raise RootBusyError(
            f"the work root has {len(blocking)} prepared operation(s) awaiting recovery "
            f"({', '.join(blocking)}); run reconcile before applying another operation",
            pending_operations=blocking,
        )


def require_payload(request: dict) -> dict:
    payload = request.get("input")
    if not isinstance(payload, dict):
        raise InvalidRequestError(
            f"the {request['command']} command needs --input <file> holding a JSON object with "
            "`operation` and its requested changes",
            command=request["command"],
        )
    return payload


def coordinator_name(payload: dict) -> str:
    coordinator = payload.get("coordinator", DEFAULT_COORDINATOR)
    if not isinstance(coordinator, str) or not coordinator:
        raise InvalidRequestError("`coordinator` must be a non-empty string naming the caller")
    return coordinator


def expected_revision(change: dict, seq: str) -> int:
    value = change.get("expect_revision")
    if type(value) is not int:
        raise InvalidRequestError(
            f"the change to {seq} carries no integer `expect_revision`; read the record and send "
            "the revision this operation was built against",
            seq=seq,
        )
    return value


def patch_metadata(metadata: dict, patch) -> dict:
    if patch is None:
        return dict(metadata)
    if not isinstance(patch, dict):
        raise InvalidRequestError("`metadata` must be an object patched over the stored metadata")
    merged = dict(metadata)
    for key, value in patch.items():
        if value is None:
            merged.pop(key, None)
        else:
            merged[key] = value
    return merged


def acting_identity(payload: dict) -> str:
    """Who a change acts as: the payload's `actor`, or the coordinator that sent it."""
    actor = payload.get("actor")
    return actor if isinstance(actor, str) and actor else coordinator_name(payload)


def change_authority(payload: dict, command: str) -> dict:
    """What every planned change is judged against, whichever command carries it."""
    return {
        "command": command,
        "actor": acting_identity(payload),
        "correction": payload.get("correction"),
    }


def require_claim_holder(current: dict, held: str, target: str, authority: dict) -> None:
    """Only the actor holding the claim moves a record between lifecycle states."""
    identity = current["identity"]
    name = records.record_name(identity)
    claim = current["metadata"].get(CLAIM_FIELD)
    if not isinstance(claim, dict):
        raise MissingAuthorityError(
            f"{name} carries no claim, so {authority['command']} cannot move it from {held} to "
            f"{target}; take the assignment with the `claim` command, naming the actor that does "
            "the work, before changing its lifecycle",
            seq=identity["seq"],
            lifecycle=held,
            requested=target,
        )
    if claim.get("actor") != authority["actor"]:
        raise MissingAuthorityError(
            f"{name} is claimed by {claim.get('actor')}, not by {authority['actor']}; only the "
            f"claiming actor moves it from {held} to {target}, so act as that actor or reassign "
            "the claim with `claim` and a `takeover_claim` authority",
            seq=identity["seq"],
            actor=claim.get("actor"),
            lifecycle=held,
            requested=target,
        )


def check_lifecycle_authority(work_root: Path, current: dict, patch, authority: dict) -> None:
    """Refuse a lifecycle change the contract forbids, one no claim covers, or an unearned `done`.

    Every existing-record mutation passes here, whichever command planned it, so the
    transition table in `records` governs `transition` as it already governs `revise`.
    A patch that sets no `lifecycle` moves nothing, and `captured` to `accepted` is the
    one state change that legitimately precedes a claim.
    """
    if not isinstance(patch, dict) or "lifecycle" not in patch:
        return
    held = records.lifecycle_of(current)
    target = records.validate_lifecycle(patch["lifecycle"])
    try:
        records.check_lifecycle_change(held, target, authority["correction"])
    except InvalidRequestError as illegal:
        raise InvalidIdentityError(
            f"{records.record_name(current['identity'])}: {illegal}",
            seq=current["identity"]["seq"],
            **illegal.detail,
        ) from illegal
    if target == held or (held, target) in CLAIM_EXEMPT_TRANSITIONS:
        return
    require_claim_holder(current, held, target, authority)
    if target == records.LIFECYCLE_DONE:
        records.check_completion(work_root, current)


def plan_existing_record(work_root: Path, namespace: dict, change: dict, authority: dict) -> dict:
    seq = records.parse_item_id(change.get("seq"))
    path = record_path(work_root, seq, change.get("task"))
    current = records.read_record(path)
    records.check_namespace(current["identity"], namespace["namespace"])
    held = current["identity"]["revision"]
    expected = expected_revision(change, seq)
    if held != expected:
        raise StaleRevisionError(
            f"record {seq} is at revision {held} and this operation expected {expected}; "
            "re-read the record and rebuild the change",
            seq=seq,
            held=held,
            expected=expected,
        )
    check_lifecycle_authority(work_root, current, change.get("metadata"), authority)
    updated = {
        "metadata": patch_metadata(current["metadata"], change.get("metadata")),
        "scope": change.get("scope", current["scope"]),
        "body": change.get("body", current["body"]),
    }
    updated["metadata"]["revision"] = records.advance_revision(current, updated)
    text = records.render_record(updated["metadata"], updated["scope"], updated["body"])
    return {
        "seq": seq,
        "task": change.get("task"),
        "path": path,
        "revision": updated["metadata"]["revision"],
        "before": records.digest(Path(path).read_text(encoding="utf-8")),
        "after": records.digest(text),
        "content": text,
    }


def plan_new_record(work_root: Path, namespace: dict, change: dict, operation_id: str) -> dict:
    scope = change.get("scope")
    if not isinstance(scope, str) or not scope.strip():
        raise InvalidRequestError("a new record needs non-empty `scope` text to bind acceptance to")
    seq = reserve_item_id(work_root, operation_id)
    metadata = patch_metadata({}, change.get("metadata"))
    metadata.update(
        {
            "format": RECORD_FORMAT_VERSION,
            "namespace": namespace["namespace"],
            "seq": seq,
            "revision": 1,
        }
    )
    path = record_path(work_root, seq, change.get("task"))
    if path.exists():
        raise InvalidIdentityError(
            f"{path} already exists although {seq} was just reserved; reconcile the work root",
            seq=seq,
        )
    text = records.render_record(metadata, scope, change.get("body", ""))
    return {
        "seq": seq,
        "task": change.get("task"),
        "path": path,
        "revision": 1,
        "reserved": seq,
        "before": None,
        "after": records.digest(text),
        "content": text,
    }


def plan_change(work_root: Path, namespace: dict, change, operation_id: str, authority: dict) -> dict:
    if not isinstance(change, dict):
        raise InvalidRequestError("each entry of `changes` must be an object")
    if change.get("new"):
        return plan_new_record(work_root, namespace, change, operation_id)
    return plan_existing_record(work_root, namespace, change, authority)


def plan_changes(work_root: Path, namespace: dict, changes, operation_id: str, authority: dict) -> list:
    if not isinstance(changes, list) or not changes:
        raise InvalidRequestError(
            "`changes` must be a non-empty list; an operation that changes nothing is not a transition"
        )
    plan = [plan_change(work_root, namespace, change, operation_id, authority) for change in changes]
    addressed = [str(entry["path"]) for entry in plan]
    if len(set(addressed)) != len(addressed):
        raise InvalidRequestError(
            "two changes address the same record; combine them into one change before applying"
        )
    return plan


def journal_entry(entry: dict) -> dict:
    return {
        "seq": entry["seq"],
        "task": entry["task"],
        "path": str(entry["path"]),
        "revision": entry["revision"],
        "before": entry["before"],
        "after": entry["after"],
        "content": entry["content"],
    }


def write_prepared_operation(work_root, command, operation_id, fingerprint, payload, ownership, plan):
    document = {
        "format": RECORD_FORMAT_VERSION,
        "operation": operation_id,
        "command": command,
        "state": PREPARED,
        "payload_fingerprint": fingerprint,
        "provenance": payload.get("provenance"),
        "owner": ownership,
        "prepared_at": now_stamp(),
        "reserved": [entry["reserved"] for entry in plan if entry.get("reserved")],
        "changes": [journal_entry(entry) for entry in plan],
    }
    write_json(operation_path(work_root, operation_id), document)
    return document


def apply_planned_changes(plan: list) -> None:
    for entry in plan:
        Path(entry["path"]).parent.mkdir(parents=True, exist_ok=True)
        write_atomic(Path(entry["path"]), entry["content"])


def operation_result(operation_id: str, namespace: dict, plan: list) -> dict:
    return {
        "operation": operation_id,
        "state": APPLIED,
        "replayed": False,
        "namespace": namespace["namespace"],
        "reserved": [entry["reserved"] for entry in plan if entry.get("reserved")],
        "records": [
            {
                "seq": entry["seq"],
                "task": entry["task"],
                "path": str(entry["path"]),
                "revision": entry["revision"],
                "before": entry["before"],
                "after": entry["after"],
            }
            for entry in plan
        ],
    }


def mark_operation_applied(work_root: Path, document: dict, result: dict) -> dict:
    document["state"] = APPLIED
    document["applied_at"] = now_stamp()
    document["result"] = result
    write_json(operation_path(work_root, document["operation"]), document)
    return document


def regenerate_views(request: dict) -> dict:
    """Refresh generated views. They are replaceable output, never an authority."""
    try:
        from session_flow import views
    except ImportError:
        return {"refreshed": False, "reason": "the views module is not installed in this build"}
    render = getattr(views, "render", None)
    if render is None:
        return {"refreshed": False, "reason": "the views module provides no render handler"}
    try:
        return {"refreshed": True, "render": render(request)}
    except SessionFlowError as failure:
        return {"refreshed": False, "reason": str(failure), "error": failure.as_error()}


def run_git(work_root: Path, arguments: list):
    try:
        return subprocess.run(
            ["git", "-C", str(work_root)] + arguments,
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_TIMEOUT,
        )
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return None


def git_failure(reason: str) -> dict:
    return {"committed": False, "reason": reason}


def commit_work_root(work_root: Path, message: str) -> dict:
    """Commit the work root's own paths. History belongs to Git, not to this runtime."""
    reason = unversioned_reason(work_root, git_toplevel(work_root))
    if reason is not None:
        return git_failure(
            f"the work root {reason}, so this transition is not versioned and backup and "
            "restore are unavailable"
        )
    staged = run_git(work_root, ["add", "-A", "--", "."])
    if staged is None or staged.returncode != 0:
        return git_failure("git add failed: " + first_line(staged))
    staged_diff = run_git(work_root, ["diff", "--cached", "--quiet", "--", "."])
    if staged_diff is None:
        return git_failure("git diff failed: " + first_line(staged_diff))
    if staged_diff.returncode == 0:
        return git_failure("the applied records match the committed ones, so there was nothing to commit")
    committed = run_git(work_root, ["-c", "commit.gpgsign=false", "commit", "-m", message, "--", "."])
    if committed is None or committed.returncode != 0:
        return git_failure("git commit failed: " + first_line(committed))
    head = run_git(work_root, ["rev-parse", "HEAD"])
    return {"committed": True, "commit": head.stdout.strip() if head else None}


def first_line(completed) -> str:
    if completed is None:
        return "git is not installed or did not answer in time"
    text = (completed.stderr or completed.stdout or "").strip().splitlines()
    return text[0] if text else "no diagnostic"


def commit_operation(request, work_root: Path, namespace: dict, command: str, document, plan) -> dict:
    """Replace the records, mark the operation applied, refresh the views, commit the root."""
    operation_id = document["operation"]
    apply_planned_changes(plan)
    result = operation_result(operation_id, namespace, plan)
    mark_operation_applied(work_root, document, result)
    result["views"] = regenerate_views(request)
    result["commit"] = commit_work_root(work_root, f"session-flow: {command} {operation_id}")
    document["views"], document["commit"] = result["views"], result["commit"]
    write_json(operation_path(work_root, operation_id), document)
    return result


def run_operation(request, payload, command, operation_id, fingerprint, changes, ownership):
    work_root = resolved_work_root(request)
    namespace = read_namespace(work_root)
    validate_bindings(work_root, namespace["repositories"])
    replayed = replayed_result(work_root, operation_id, fingerprint)
    if replayed is not None:
        return replayed
    block_on_pending(work_root, operation_id)
    plan = plan_changes(
        work_root, namespace, changes, operation_id, change_authority(payload, command)
    )
    document = write_prepared_operation(
        work_root, command, operation_id, fingerprint, payload, ownership, plan
    )
    return commit_operation(request, work_root, namespace, command, document, plan)


def requested_takeover(payload: dict):
    takeover = payload.get("takeover")
    if takeover is None or isinstance(takeover, dict):
        return takeover
    raise InvalidRequestError(
        "`takeover` must be an object naming the `reason` the previous coordinator is gone"
    )


def apply_operation(request: dict, payload: dict, command: str, changes=None) -> dict:
    """Run one mutation in the documented order, under the root lock."""
    work_root = resolved_work_root(request)
    operation_id = parse_operation_id(payload.get("operation"))
    fingerprint = records.digest(payload)
    replayed = replayed_result(work_root, operation_id, fingerprint)
    if replayed is not None:
        return replayed
    requested = payload.get("changes") if changes is None else changes
    with root_lock(work_root, coordinator_name(payload), requested_takeover(payload)) as ownership:
        return run_operation(
            request, payload, command, operation_id, fingerprint, requested, ownership
        )


def transition(request: dict) -> dict:
    payload = require_payload(request)
    return apply_operation(request, payload, "transition")


def record_target(request: dict, payload: dict) -> dict:
    seq = payload.get("seq", request.get("seq"))
    task = payload.get("task", request.get("task"))
    return {"seq": records.parse_item_id(seq), "task": task}


def claimed_actor(payload: dict) -> str:
    actor = payload.get("actor")
    if not isinstance(actor, str) or not actor:
        raise InvalidRequestError("`actor` must name the agent or session taking this assignment")
    return actor


def claim_change(current: dict, payload: dict, target: dict, coordinator: str) -> dict:
    actor = claimed_actor(payload)
    held = current["metadata"].get(CLAIM_FIELD)
    if isinstance(held, dict) and held.get("actor") != actor and not payload.get("takeover_claim"):
        raise MissingAuthorityError(
            f"{target['seq']} is claimed by {held.get('actor')}; record that claim's result, or "
            "supply `takeover_claim` with the authority that reassigns it",
            actor=held.get("actor"),
        )
    claim = {
        "actor": actor,
        "coordinator": coordinator,
        "host": current_host(),
        "claimed_at": payload.get("claimed_at", now_stamp()),
        "allowed_paths": payload.get("allowed_paths", []),
    }
    if payload.get("takeover_claim"):
        claim["reassigned_from"] = held.get("actor") if isinstance(held, dict) else None
    return dict(target, expect_revision=payload.get("expect_revision"), metadata={CLAIM_FIELD: claim})


def claim(request: dict) -> dict:
    """Record a bounded assignment. It starts nothing and schedules nothing."""
    payload = require_payload(request)
    work_root = resolved_work_root(request)
    target = record_target(request, payload)
    current = records.read_record(record_path(work_root, target["seq"], target["task"]))
    change = claim_change(current, payload, target, coordinator_name(payload))
    return apply_operation(request, payload, "claim", [change])


def validate_outcome(result) -> dict:
    if not isinstance(result, dict):
        raise InvalidRequestError("`result` must be an object naming the outcome of the claimed work")
    outcome = result.get("outcome")
    if outcome not in RESULT_OUTCOMES:
        raise InvalidRequestError(
            f"{outcome!r} is not a task outcome; use one of {', '.join(RESULT_OUTCOMES)}",
            outcome=outcome,
        )
    return dict(result, recorded_at=result.get("recorded_at", now_stamp()))


def record_result(request: dict) -> dict:
    """Record a claimed task's own result. Judging its evidence is not this command's work."""
    payload = require_payload(request)
    work_root = resolved_work_root(request)
    target = record_target(request, payload)
    current = records.read_record(record_path(work_root, target["seq"], target["task"]))
    held = current["metadata"].get(CLAIM_FIELD)
    if not isinstance(held, dict):
        raise MissingAuthorityError(
            f"{target['seq']} carries no claim; claim the assignment before recording its result",
            seq=target["seq"],
        )
    actor = claimed_actor(payload)
    if held.get("actor") != actor:
        raise MissingAuthorityError(
            f"{target['seq']} is claimed by {held.get('actor')}, not by {actor}; only the claiming "
            "actor records its result",
            actor=held.get("actor"),
        )
    change = dict(
        target,
        expect_revision=payload.get("expect_revision"),
        metadata={RESULT_FIELD: validate_outcome(payload.get("result"))},
    )
    return apply_operation(request, payload, "record-result", [change])


def current_digest(path) -> str | None:
    candidate = Path(path)
    if not candidate.is_file():
        return None
    return records.digest(candidate.read_text(encoding="utf-8"))


def change_state(change: dict) -> dict:
    """Classify one journalled change against the file that is on disk now."""
    held = current_digest(change.get("path"))
    report = {"path": change.get("path"), "seq": change.get("seq"), "task": change.get("task")}
    if held == change.get("after"):
        return dict(report, state=APPLIED)
    if held != change.get("before"):
        return dict(
            report,
            state=DIVERGED,
            reason="the file matches neither the recorded before nor the recorded after content, "
            "so something outside this runtime changed it; compare it with the journal by hand",
            expected=change.get("before"),
            found=held,
        )
    if not isinstance(change.get("content"), str):
        return dict(
            report,
            state=DIVERGED,
            reason="the journal entry carries no rendered content to finish this change with; "
            "rebuild the operation instead of recovering it",
            expected=change.get("before"),
            found=held,
        )
    return dict(report, state=PENDING)


def finish_change(change: dict) -> None:
    Path(change["path"]).parent.mkdir(parents=True, exist_ok=True)
    write_atomic(Path(change["path"]), change["content"])


def recovered_result(document: dict, namespace: dict) -> dict:
    changes = document.get("changes") or []
    return {
        "operation": document.get("operation"),
        "state": APPLIED,
        "replayed": False,
        "recovered": True,
        "namespace": namespace["namespace"],
        "reserved": document.get("reserved", []),
        "records": [
            {field: change.get(field) for field in ("seq", "task", "path", "revision", "before", "after")}
            for change in changes
        ],
    }


def reconcile_operation(work_root: Path, namespace: dict, document: dict) -> dict:
    """Finish one prepared operation, or leave it untouched and explicitly blocked."""
    operation_id = document.get("operation")
    changes = document.get("changes") or []
    states = [change_state(change) for change in changes]
    if any(state["state"] == DIVERGED for state in states):
        return {"operation": operation_id, "state": BLOCKED, "changes": states}
    for change, state in zip(changes, states):
        if state["state"] == PENDING:
            finish_change(change)
    result = recovered_result(document, namespace)
    mark_operation_applied(work_root, document, result)
    return {"operation": operation_id, "state": RESOLVED, "changes": states, "result": result}


def unwritten_reservations(work_root: Path) -> list:
    """Identities that were reserved but whose record was never written. They stay taken."""
    retained = retained_ids(work_root)
    return sorted(
        {
            entry["seq"]
            for entry in read_tombstones(work_root)["entries"]
            if isinstance(entry, dict)
            and entry.get("state") == "reserved"
            and isinstance(entry.get("seq"), str)
            and entry["seq"] not in retained
        }
    )


def reconcile(request: dict) -> dict:
    """Finish or explicitly block each prepared operation. It repeats no external effect."""
    payload = request.get("input") if isinstance(request.get("input"), dict) else {}
    work_root = resolved_work_root(request)
    namespace = read_namespace(work_root)
    validate_bindings(work_root, namespace["repositories"])
    takeover = requested_takeover(payload) or {"reason": "recovering prepared operations"}
    with root_lock(work_root, coordinator_name(payload), takeover, allow_pending=True):
        operations = [
            reconcile_operation(work_root, namespace, document)
            for document in pending_operations(work_root)
        ]
        blocked = [entry["operation"] for entry in operations if entry["state"] == BLOCKED]
        views = regenerate_views(request)
        commit = (
            git_failure(
                "reconciliation is blocked on unexplained divergence, so nothing was committed; "
                "resolve the named files and run reconcile again"
            )
            if blocked
            else commit_work_root(work_root, f"session-flow: reconcile {len(operations)} operation(s)")
        )
        return {
            "state": BLOCKED if blocked else RESOLVED,
            "operations": operations,
            "resolved": [entry["operation"] for entry in operations if entry["state"] == RESOLVED],
            "blocked": blocked,
            "reserved": unwritten_reservations(work_root),
            "views": views,
            "commit": commit,
        }


def git_toplevel(work_root: Path):
    completed = run_git(work_root, ["rev-parse", "--show-toplevel"])
    if completed is None or completed.returncode != 0:
        return None
    return completed.stdout.strip()


def git_value(work_root: Path, arguments: list):
    completed = run_git(work_root, arguments)
    if completed is None or completed.returncode != 0:
        return None
    return completed.stdout.strip()


def unversioned_reason(work_root: Path, toplevel) -> str | None:
    """Why the work root has no history of its own, or None when something versions it.

    `git rev-parse --show-toplevel` answers for the nearest enclosing repository, so a
    gitignored root nested in a tracked one would otherwise read as versioned and send
    every Git operation to a repository that holds none of the records.
    """
    if toplevel is None:
        return "is not a Git repository"
    if os.path.realpath(toplevel) == os.path.realpath(str(work_root)):
        return None
    if not ignored_by_enclosing(work_root):
        return None
    return f"is ignored by the enclosing repository at {toplevel}, which tracks nothing in it"


def require_versioned_root(work_root: Path, command: str) -> str:
    toplevel = git_toplevel(work_root)
    reason = unversioned_reason(work_root, toplevel)
    if reason is not None:
        raise InvalidIdentityError(
            f"the work root at {work_root} {reason}, so {command} is unavailable; "
            f"run `git -C {work_root} init -b main` and commit the records, or restore the root "
            "from the repository that already holds them",
            work_root=str(work_root),
        )
    return toplevel


def parse_remote_name(value) -> str:
    if value is None:
        return DEFAULT_REMOTE
    if not isinstance(value, str) or not REMOTE_NAME_RE.match(value):
        raise InvalidRequestError(
            f"{value!r} is not a Git remote name; pass `remote` as the configured remote, "
            f"or omit it to use {DEFAULT_REMOTE}",
            remote=value,
        )
    return value


def remote_url(work_root: Path, remote: str) -> str:
    url = git_value(work_root, ["remote", "get-url", remote])
    if url is None:
        raise InvalidIdentityError(
            f"the work root at {work_root} has no Git remote named {remote}; add it with "
            f"`git -C {work_root} remote add {remote} <url>` before backing up",
            remote=remote,
        )
    return url


def uncommitted_paths(work_root: Path) -> list:
    completed = run_git(work_root, ["status", "--porcelain", "--", "."])
    if completed is None or completed.returncode != 0:
        raise InvalidIdentityError(
            f"cannot read the Git status of {work_root} ({first_line(completed)}); repair the "
            "repository before backing it up",
            work_root=str(work_root),
        )
    return [line[3:] for line in completed.stdout.splitlines() if line.strip()]


def backup_reason(pushed, outstanding: list):
    if pushed is None or pushed.returncode != 0:
        return "git push failed: " + first_line(pushed)
    if outstanding:
        return (
            f"{len(outstanding)} path(s) are not committed, so this backup does not carry them; "
            "apply them through a transition and back up again"
        )
    return None


def backup(request: dict) -> dict:
    """Verify the configured remote and push. It defines no archive format of its own."""
    payload = request.get("input") if isinstance(request.get("input"), dict) else {}
    work_root = resolved_work_root(request)
    require_versioned_root(work_root, "backup")
    remote = parse_remote_name(payload.get("remote"))
    url = remote_url(work_root, remote)
    branch = git_value(work_root, ["symbolic-ref", "--quiet", "--short", "HEAD"])
    if not branch:
        raise InvalidIdentityError(
            f"the work root at {work_root} has a detached HEAD, so there is no branch to push; "
            "check out the branch that holds the records and run backup again",
            work_root=str(work_root),
        )
    outstanding = uncommitted_paths(work_root)
    pushed = run_git(work_root, ["push", remote, branch])
    succeeded = pushed is not None and pushed.returncode == 0
    return {
        "pushed": succeeded,
        "complete": succeeded and not outstanding,
        "remote": remote,
        "url": url,
        "branch": branch,
        "commit": git_value(work_root, ["rev-parse", "HEAD"]),
        "uncommitted": outstanding,
        "reason": backup_reason(pushed, outstanding),
    }


def parse_source(payload: dict) -> str:
    source = payload.get("source")
    if not isinstance(source, str) or not source.strip() or source.startswith("-"):
        raise InvalidRequestError(
            "`source` must name the Git repository that holds the work records, as a path or a "
            "URL; restore clones it rather than unpacking an archive of its own",
            source=source,
        )
    return source


def parse_restore_revision(payload: dict):
    revision = payload.get("revision")
    if revision is None:
        return None
    if not isinstance(revision, str) or not REVISION_RE.match(revision):
        raise InvalidRequestError(
            f"{revision!r} is not a revision; pass `revision` as the commit, tag, or branch to "
            "check out, or omit it to restore the default branch",
            revision=revision,
        )
    return revision


def empty_target(work_root: Path) -> Path:
    if work_root.exists() and (not work_root.is_dir() or any(work_root.iterdir())):
        raise InvalidIdentityError(
            f"{work_root} already holds records; restore into an empty work root so nothing is "
            "overwritten, then compare the two roots yourself",
            work_root=str(work_root),
        )
    return work_root


def clone_work_root(source: str, work_root: Path) -> None:
    work_root.parent.mkdir(parents=True, exist_ok=True)
    completed = run_git(work_root.parent, ["clone", "--", source, str(work_root)])
    if completed is None or completed.returncode != 0:
        raise InvalidIdentityError(
            f"cannot clone {source} into {work_root} ({first_line(completed)}); check that the "
            "source repository is reachable and that git is installed",
            source=source,
        )


def checkout_revision(work_root: Path, revision: str) -> None:
    completed = run_git(work_root, ["checkout", "--detach", revision])
    if completed is None or completed.returncode != 0:
        raise InvalidIdentityError(
            f"cannot check out {revision} in {work_root} ({first_line(completed)}); name a commit, "
            "tag, or branch that the restored repository carries",
            revision=revision,
        )


def restore(request: dict) -> dict:
    """Check the work records out of the repository that holds them. It unpacks no archive."""
    payload = require_payload(request)
    source = parse_source(payload)
    revision = parse_restore_revision(payload)
    work_root = empty_target(Path(request["work_root"]))
    clone_work_root(source, work_root)
    if revision is not None:
        checkout_revision(work_root, revision)
    namespace = read_namespace(work_root)
    return {
        "restored": True,
        "source": source,
        "revision": revision,
        "work_root": str(work_root),
        "commit": git_value(work_root, ["rev-parse", "HEAD"]),
        "namespace": namespace["namespace"],
        "identities": sorted(retained_ids(work_root)),
        "reserved": unwritten_reservations(work_root),
        "pending_operations": [document.get("operation") for document in pending_operations(work_root)],
    }


def imported_record_change(work_root: Path, item: dict) -> dict | None:
    """Plan one imported record, or None when that exact record is already stored."""
    seq = records.parse_item_id(item["metadata"]["seq"])
    path = record_path(work_root, seq)
    after = records.digest(item["text"])
    held = current_digest(path)
    if held == after:
        return None
    if held is not None:
        raise InvalidIdentityError(
            f"{path} already holds a different record for {seq}; import never overwrites a stored "
            "record, so reconcile the two by hand before importing again",
            seq=seq,
            path=str(path),
        )
    return {
        "seq": seq,
        "task": None,
        "path": path,
        "revision": item["metadata"].get("revision", 1),
        "before": None,
        "after": after,
        "content": item["text"],
    }


def tombstone_change(work_root: Path, entries: list, operation_id: str) -> dict | None:
    """Plan the allocation-index write that retires every identity the survey saw."""
    document = read_tombstones(work_root)
    known = {value for entry in document["entries"] for value in entry_ids(entry)}
    added = [entry for entry in entries if entry["seq"] not in known]
    if not added:
        return None
    stamp = now_stamp()
    document["entries"].extend(
        {"seq": entry["seq"], "state": entry["state"], "operation": operation_id, "at": stamp}
        for entry in added
    )
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    path = tombstones_path(work_root)
    return {
        "seq": None,
        "task": None,
        "path": path,
        "revision": None,
        "before": current_digest(path),
        "after": records.digest(text),
        "content": text,
    }


def plan_import_changes(work_root: Path, plan: dict, operation_id: str) -> list:
    """The allocation index first, then every record the import still has to write."""
    changes = [tombstone_change(work_root, plan["tombstones"], operation_id)]
    changes += [imported_record_change(work_root, item) for item in plan["items"]]
    return [change for change in changes if change is not None]


def refuse_unversioned_root(work_root: Path) -> None:
    reason = unversioned_reason(work_root, git_toplevel(work_root))
    if reason is None:
        return
    raise InvalidIdentityError(
        f"the work root at {work_root} {reason}, so an import could not be reverted; run "
        f"`git -C {work_root} init -b main`, commit the current records, and re-run",
        work_root=str(work_root),
    )


def uncommitted_under(root: Path, ignored: list) -> list:
    """Uncommitted paths of `root`'s repository, dropping everything under an ignored path.

    Porcelain status names each path from the repository top, not from `root`.
    """
    toplevel = git_toplevel(root)
    if toplevel is None:
        return []
    excluded = [Path(path).resolve() for path in ignored]
    outstanding = []
    for entry in uncommitted_paths(root):
        candidate = (Path(toplevel) / entry).resolve()
        if any(candidate == path or path in candidate.parents for path in excluded):
            continue
        outstanding.append(entry)
    return outstanding


def record_changes(work_root: Path) -> list:
    """Uncommitted records, ignoring the `.state` journal and lock that recovery owns."""
    return uncommitted_under(work_root, [state_directory(work_root)])


def project_changes(request: dict, work_root: Path) -> list:
    """Uncommitted project paths, excluding the work root and the generated sequence."""
    return uncommitted_under(
        Path(request["project_root"]), [work_root, Path(request["sequence_path"])]
    )


def refuse_uncommitted(root: Path, outstanding: list, description: str) -> None:
    if not outstanding:
        return
    raise InvalidIdentityError(
        f"the {description} at {root} has {len(outstanding)} uncommitted change(s), including "
        f"{', '.join(outstanding[:3])}; an import must stay revertable on its own, so commit or "
        f"stash them (`git -C {root} status`) and re-run",
        path=str(root),
        uncommitted=outstanding,
    )


def refuse_unsafe_ground(request: dict, work_root: Path) -> None:
    """Stop before the first write when the ground cannot carry an undo. There is no force."""
    refuse_unversioned_root(work_root)
    refuse_uncommitted(work_root, record_changes(work_root), "work root")
    refuse_uncommitted(
        Path(request["project_root"]), project_changes(request, work_root), "project tree"
    )


def prior_operation(work_root: Path, operation_id: str, fingerprint: str):
    """The journal entry for this operation identity, refusing a reuse with another payload."""
    document = load_operation(work_root, operation_id)
    if document is None:
        return None
    if document.get("payload_fingerprint") != fingerprint:
        raise InvalidIdentityError(
            f"operation {operation_id} already exists with a different payload; issue a new "
            "operation identity instead of reusing this one",
            operation=operation_id,
            state=document.get("state"),
        )
    return document


def resume_operation(request: dict, work_root: Path, namespace: dict, document: dict) -> dict:
    """Finish an interrupted operation from its journal instead of planning it again."""
    operation_id = document["operation"]
    resumed = reconcile_operation(work_root, namespace, document)
    if resumed["state"] == BLOCKED:
        raise RootBusyError(
            f"operation {operation_id} cannot be resumed: a file matches neither the recorded "
            "before nor the recorded after content, so compare the named paths with the journal "
            "by hand before running reconcile",
            operation=operation_id,
            changes=resumed["changes"],
        )
    result = dict(resumed["result"], resumed=True, changed=True)
    result["views"] = regenerate_views(request)
    result["commit"] = commit_work_root(work_root, f"session-flow: {IMPORT_COMMAND} {operation_id}")
    return result


def unchanged_import(operation_id: str, namespace: dict) -> dict:
    return {
        "operation": operation_id,
        "state": APPLIED,
        "replayed": False,
        "changed": False,
        "namespace": namespace["namespace"],
        "reserved": [],
        "records": [],
        "reason": "every identity is already recorded and already retired in the allocation "
        "index, so this run wrote nothing",
    }


def apply_import(request: dict, payload: dict, plan: dict) -> dict:
    """Apply one import as a single journalled operation under the root lock."""
    work_root = resolved_work_root(request)
    operation_id = parse_operation_id(payload.get("operation"))
    fingerprint = records.digest(payload)
    refuse_unsafe_ground(request, work_root)
    coordinator = coordinator_name(payload)
    with root_lock(work_root, coordinator, requested_takeover(payload), True) as ownership:
        namespace = read_namespace(work_root)
        validate_bindings(work_root, namespace["repositories"])
        document = prior_operation(work_root, operation_id, fingerprint)
        if document is not None and document.get("state") == APPLIED:
            return dict(document.get("result") or {}, replayed=True, changed=False)
        if document is not None:
            return resume_operation(request, work_root, namespace, document)
        block_on_pending(work_root, operation_id)
        changes = plan_import_changes(work_root, plan, operation_id)
        if not changes:
            return unchanged_import(operation_id, namespace)
        prepared = write_prepared_operation(
            work_root, IMPORT_COMMAND, operation_id, fingerprint, payload, ownership, changes
        )
        applied = commit_operation(request, work_root, namespace, IMPORT_COMMAND, prepared, changes)
        return dict(applied, changed=True)


def parse_binding(payload: dict):
    """Return the repository binding to record, or None when the payload names none."""
    binding = payload.get("repository")
    if binding is None:
        return None
    if not isinstance(binding, dict):
        raise InvalidRequestError(
            "`repository` must be an object; pass {\"repository\": {\"name\": \"<repo>\", "
            "\"path\": \"<path to it, relative to the work root>\"}}",
            repository=binding,
        )
    return records.parse_repositories([binding])[0]


def bound_repositories(existing: list, binding) -> list:
    """Add the binding once. A name already bound elsewhere is a conflict, not an overwrite."""
    if binding is None:
        return existing
    for current in existing:
        if current["name"] != binding["name"]:
            continue
        if current["path"] == binding["path"]:
            return existing
        raise InvalidIdentityError(
            f"repository {binding['name']} is already bound to {current['path']} in "
            f"{NAMESPACE_FILE}; rename the binding or correct its path rather than rebinding it",
            binding=binding["name"],
        )
    return existing + [binding]


def bind_namespace(request: dict) -> dict:
    """Create the work root's namespace.json, or bind one more repository into it.

    The namespace UUID is allocated once and never rewritten: a second one orphans
    every record already under the root.
    """
    payload = request.get("input") or {}
    if not isinstance(payload, dict):
        raise InvalidRequestError(
            "the bind-namespace payload must be a JSON object carrying an optional `repository` "
            "binding and `coordinator`; omit --input to create the namespace alone"
        )
    binding = parse_binding(payload)
    work_root = Path(request["work_root"])
    if work_root.exists() and not work_root.is_dir():
        raise InvalidIdentityError(
            f"{work_root} is configured as the work root but is not a directory; correct "
            "`paths.work` in .session-flow.json or move the file out of the way",
            work_root=str(work_root),
        )
    work_root.mkdir(parents=True, exist_ok=True)
    with root_lock(work_root, coordinator_name(payload)):
        created = not namespace_path(work_root).is_file()
        document = (
            {"format": RECORD_FORMAT_VERSION, "namespace": str(uuid.uuid4()), "repositories": []}
            if created
            else read_namespace(work_root)
        )
        repositories = validate_bindings(work_root, bound_repositories(document["repositories"], binding))
        changed = created or repositories != document["repositories"]
        document["repositories"] = repositories
        if changed:
            write_json(namespace_path(work_root), document)
        return dict(
            document,
            created=created,
            changed=changed,
            path=str(namespace_path(work_root)),
            commit=(
                commit_work_root(work_root, "session-flow: bind namespace")
                if changed
                else git_failure("the namespace was already bound, so there was nothing to commit")
            ),
        )


def namespace_report(work_root: Path) -> dict:
    try:
        return {"namespace": read_namespace(work_root)["namespace"]}
    except SessionFlowError as failure:
        return {
            "namespace": None,
            "namespace_error": failure.as_error(),
            "limitations": [
                f"the work root at {work_root} has no readable {NAMESPACE_FILE}: every mutation "
                "fails until /session-init binds the namespace and repositories"
            ],
        }


def journal_report(work_root: Path) -> dict:
    try:
        return {
            "pending_operations": [document.get("operation") for document in pending_operations(work_root)],
            "reserved": unwritten_reservations(work_root),
        }
    except SessionFlowError as failure:
        return {
            "pending_operations": None,
            "journal_error": failure.as_error(),
            "limitations": [
                f"the operation journal under {operations_directory(work_root)} cannot be read, so "
                "recovery state is unknown: repair the named file before mutating this root"
            ],
        }


def unversioned_limitation(work_root: Path, enclosing) -> str:
    nested = (
        f" It is ignored by the enclosing repository at {enclosing}, which therefore versions "
        "nothing under it."
        if enclosing
        else ""
    )
    return (
        f"the work root at {work_root} is not a Git repository: backup and restore are "
        f"unavailable and applied transitions keep no history.{nested} Run "
        f"`git -C {work_root} init -b main` and commit the records to enable them."
    )


def ignored_by_enclosing(work_root: Path) -> bool:
    """True when the enclosing repository ignores the work root, so it tracks nothing in it."""
    completed = run_git(work_root, ["check-ignore", "-q", "."])
    return completed is not None and completed.returncode == 0


def versioning_report(work_root: Path) -> dict:
    """Report what actually versions the work root: its own repository, an enclosing one, or nothing."""
    toplevel = git_toplevel(work_root)
    own = toplevel is not None and os.path.realpath(toplevel) == os.path.realpath(str(work_root))
    if unversioned_reason(work_root, toplevel) is not None:
        report = {"versioned": False, "limitations": [unversioned_limitation(work_root, toplevel)]}
        if toplevel is not None:
            report["enclosing_repository"] = toplevel
        return report
    remotes = git_value(work_root, ["remote"])
    report = {
        "versioned": True,
        "repository": toplevel,
        "own_repository": own,
        "branch": git_value(work_root, ["symbolic-ref", "--quiet", "--short", "HEAD"]),
        "commit": git_value(work_root, ["rev-parse", "HEAD"]),
        "remotes": remotes.split() if remotes else [],
    }
    if not report["remotes"]:
        report["limitations"] = [
            f"the work root at {work_root} has no Git remote: backup has nowhere to push. Add one "
            f"with `git -C {work_root} remote add {DEFAULT_REMOTE} <url>`."
        ]
    return report


def work_root_report(request: dict) -> dict:
    """doctor's storage section. It mutates nothing and reports rather than raising."""
    work_root = Path(request["work_root"])
    if not work_root.is_dir():
        return {
            "versioned": False,
            "limitations": [
                f"there is no work root at {work_root}: run /session-init before recording work"
            ],
        }
    report = {"locked": lock_directory(work_root).is_dir()}
    limitations = []
    for section in (namespace_report(work_root), journal_report(work_root), versioning_report(work_root)):
        limitations.extend(section.pop("limitations", []))
        report.update(section)
    report["limitations"] = limitations
    return report
