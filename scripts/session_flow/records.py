"""Record envelopes: bounded regions, identity, fingerprints, and acceptance.

Two regions carry machine-owned content: one JSON metadata fence and one scope
region holding the acceptance-bearing text. Nothing outside those regions is
read as a field, and no record content is ever executed.

Acceptance names a normalized fingerprint of the scope text, the repository
bindings, the required delivery target, and the work-root commits of the
referenced behaviour and criteria documents. Applicability is therefore derived
by comparison and never stored as a flag: a status change or a reflowed
paragraph leaves the fingerprint untouched, while a meaning-changing edit
invalidates dependent acceptance and evidence unless the reviser declares a
same-meaning or preparation decision. Those decisions travel in the mutation's
`--input` payload as `same_meaning` and `preparation`, because no option of the
entrypoint accepts free text.

Every handler here writes at most one record. Collective atomicity across
records, root locking, and the work-root commit belong to the transition
protocol, not to a record-level edit.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

from session_flow import (
    RECORD_FORMAT_VERSION,
    InapplicableEvidenceError,
    InvalidIdentityError,
    InvalidRequestError,
    MissingAuthorityError,
    StaleRevisionError,
    UnsupportedFormatError,
)

META_REGION = "meta"
SCOPE_REGION = "scope"
SUPPORTED_FORMATS = (RECORD_FORMAT_VERSION,)
REQUIRED_FIELDS = ("format", "namespace", "seq", "revision")
IMMUTABLE_FIELDS = ("format", "namespace", "seq")
INTENT_FILE = "intent.md"
TASKS_DIRECTORY = "tasks"
JSON_FENCE_OPEN = "```json"
FENCE_CLOSE = "```"

ITEM_ID_RE = re.compile(r"^SEQ-([0-9]{3,6})$")
TASK_ID_RE = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")
NAMESPACE_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

MARKER_ESCAPES = (("&#45;", "&amp;#45;"), ("<!--", "<!&#45;&#45;"), ("-->", "&#45;&#45;>"))


def region_markers(name: str) -> tuple[str, str]:
    return f"<!-- session-flow:{name} -->", f"<!-- /session-flow:{name} -->"


def escape_markers(text: str) -> str:
    """Neutralize region markers in captured source text, reversibly."""
    for raw, escaped in MARKER_ESCAPES:
        text = text.replace(raw, escaped)
    return text


def unescape_markers(text: str) -> str:
    for raw, escaped in reversed(MARKER_ESCAPES):
        text = text.replace(escaped, raw)
    return text


def find_region(text: str, name: str) -> str:
    opener, closer = region_markers(name)
    opened, closed = text.count(opener), text.count(closer)
    if opened != 1 or closed != 1:
        raise UnsupportedFormatError(
            f"record needs exactly one {name} region, found {opened} opening and {closed} closing "
            f"markers; keep one {opener} ... {closer} pair and re-run",
            region=name,
            opened=opened,
            closed=closed,
        )
    start = text.index(opener) + len(opener)
    end = text.index(closer)
    if end < start:
        raise UnsupportedFormatError(
            f"the {name} region closes before it opens; put {opener} above {closer}", region=name
        )
    return text[start:end]


def strip_json_fence(block: str) -> str:
    lines = block.strip().splitlines()
    if len(lines) < 2 or lines[0].strip() != JSON_FENCE_OPEN or lines[-1].strip() != FENCE_CLOSE:
        raise UnsupportedFormatError(
            f"the metadata region must hold one {JSON_FENCE_OPEN} fence closed by {FENCE_CLOSE}; "
            "rewrite the envelope before writing"
        )
    return "\n".join(lines[1:-1])


def parse_metadata(text: str) -> dict:
    payload = strip_json_fence(find_region(text, META_REGION))
    try:
        metadata = json.loads(payload)
    except json.JSONDecodeError as error:
        raise UnsupportedFormatError(
            f"the metadata fence is not valid JSON ({error.msg} on line {error.lineno}); "
            "fix the fence before writing"
        ) from error
    if not isinstance(metadata, dict):
        raise UnsupportedFormatError("the metadata fence must hold a JSON object, not a bare value")
    return metadata


def validate_format(metadata: dict) -> int:
    version = metadata.get("format")
    if type(version) is not int:
        raise UnsupportedFormatError(
            "the record has no integer `format` field; add \"format\": "
            f"{RECORD_FORMAT_VERSION} to the metadata fence"
        )
    if version not in SUPPORTED_FORMATS:
        raise UnsupportedFormatError(
            f"record format {version} is unknown to this runtime, which reads "
            f"{list(SUPPORTED_FORMATS)}; upgrade session-flow instead of editing the record",
            format=version,
        )
    return version


def parse_item_id(value) -> str:
    if not isinstance(value, str) or not ITEM_ID_RE.match(value):
        raise InvalidIdentityError(
            f"{value!r} is not a work-item identity; use SEQ-NNN with three to six digits", seq=value
        )
    return value


def parse_task_id(value) -> str:
    if not isinstance(value, str) or not TASK_ID_RE.match(value):
        raise InvalidIdentityError(
            f"{value!r} is not a task identity; use alphanumeric segments joined by hyphens, such as A1",
            task=value,
        )
    return value


def parse_namespace(value) -> str:
    if not isinstance(value, str) or not NAMESPACE_RE.match(value):
        raise InvalidIdentityError(
            f"{value!r} is not a namespace UUID; copy the `namespace` value from the work root's "
            "namespace.json",
            namespace=value,
        )
    return value


def parse_revision(value) -> int:
    if type(value) is not int or value < 1:
        raise InvalidIdentityError(
            f"{value!r} is not a record revision; use a positive integer starting at 1", revision=value
        )
    return value


def valid_binding(entry) -> bool:
    return (
        isinstance(entry, dict)
        and isinstance(entry.get("name"), str)
        and isinstance(entry.get("path"), str)
    )


def parse_repositories(value) -> list[dict]:
    if not isinstance(value, list):
        raise InvalidIdentityError("`repositories` must be a list of bindings; wrap the binding in a list")
    for entry in value:
        if not valid_binding(entry):
            raise InvalidIdentityError(
                "each repository binding needs a string `name` and `path`; correct the metadata fence",
                binding=entry,
            )
    return [dict(entry) for entry in value]


def validate_identity(metadata: dict) -> dict:
    validate_format(metadata)
    missing = [field for field in REQUIRED_FIELDS if field not in metadata]
    if missing:
        raise InvalidIdentityError(
            f"the metadata fence is missing {', '.join(missing)}; add the identity fields before writing",
            missing=missing,
        )
    identity = {
        "format": metadata["format"],
        "namespace": parse_namespace(metadata["namespace"]),
        "seq": parse_item_id(metadata["seq"]),
        "revision": parse_revision(metadata["revision"]),
        "repositories": parse_repositories(metadata.get("repositories", [])),
    }
    if "task" in metadata:
        identity["task"] = parse_task_id(metadata["task"])
    return identity


def body_text(text: str) -> str:
    for name in (META_REGION, SCOPE_REGION):
        opener, closer = region_markers(name)
        start, end = text.find(opener), text.find(closer)
        if start < 0 or end < start:
            continue
        text = text[:start] + text[end + len(closer):]
    return text.strip("\n")


def parse_record(text: str) -> dict:
    """Parse one record. Raises before any caller can write on every rejection."""
    metadata = parse_metadata(text)
    identity = validate_identity(metadata)
    scope = find_region(text, SCOPE_REGION)
    return {
        "metadata": metadata,
        "identity": identity,
        "scope": unescape_markers(scope).strip("\n"),
        "body": unescape_markers(body_text(text)),
    }


def render_record(metadata: dict, scope: str, body: str = "") -> str:
    """Serialize a record in canonical order: metadata fence, body, scope region."""
    validate_identity(metadata)
    meta_open, meta_close = region_markers(META_REGION)
    scope_open, scope_close = region_markers(SCOPE_REGION)
    fence = json.dumps(metadata, indent=2, sort_keys=True)
    sections = [
        f"{meta_open}\n{JSON_FENCE_OPEN}\n{fence}\n{FENCE_CLOSE}\n{meta_close}",
        escape_markers(body).strip("\n"),
        f"{scope_open}\n{escape_markers(scope).strip()}\n{scope_close}",
    ]
    return "\n\n".join(section for section in sections if section) + "\n"


def comparable_content(record: dict) -> tuple:
    metadata = {key: value for key, value in record["metadata"].items() if key != "revision"}
    return json.dumps(metadata, sort_keys=True), record["scope"], record["body"]


def record_changed(previous: dict, updated: dict) -> bool:
    return comparable_content(previous) != comparable_content(updated)


def advance_revision(previous: dict, updated: dict) -> int:
    """Return the revision the updated record must carry. Immutable fields must match."""
    revision = validate_identity(previous["metadata"])["revision"]
    validate_identity(updated["metadata"])
    for field in IMMUTABLE_FIELDS:
        held, offered = previous["metadata"].get(field), updated["metadata"].get(field)
        if held != offered:
            raise InvalidIdentityError(
                f"`{field}` is immutable: the record holds {held!r} and the update carries {offered!r}; "
                "capture a new work item instead of renaming this one",
                field=field,
            )
    return revision + 1 if record_changed(previous, updated) else revision


def ensure_within(root: Path, candidate: Path) -> Path:
    root, candidate = Path(root).resolve(), Path(candidate).resolve()
    if root != candidate and root not in candidate.parents:
        raise InvalidIdentityError(
            f"{candidate} lies outside the work root {root}; address records by identity, not by path",
            path=str(candidate),
        )
    return candidate


def item_directory(item_id: str) -> str:
    return parse_item_id(item_id).lower()


def resolve_record_path(request: dict) -> Path:
    work_root = Path(request["work_root"])
    if not request.get("seq"):
        raise InvalidIdentityError("this command needs --seq SEQ-NNN to address a work item")
    directory = work_root / item_directory(request["seq"])
    task = request.get("task")
    relative = directory / INTENT_FILE if task is None else directory / TASKS_DIRECTORY / f"{parse_task_id(task)}.md"
    return ensure_within(work_root, relative)


def read_record(path: Path) -> dict:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise InvalidIdentityError(
            f"no record at {path}; capture the work item before addressing it", path=str(path)
        ) from error
    except OSError as error:
        raise InvalidIdentityError(
            f"cannot read {path} ({error.strerror}); check the work root's permissions", path=str(path)
        ) from error
    return parse_record(text)


def check_namespace(identity: dict, expected: str | None) -> None:
    if expected is None:
        return
    if identity["namespace"] != parse_namespace(expected):
        raise InvalidIdentityError(
            f"record {identity['seq']} belongs to namespace {identity['namespace']}, not {expected}; "
            "point --namespace at the work root that owns it",
            namespace=identity["namespace"],
        )


WHITESPACE_RUN_RE = re.compile(r"[^\S\n]+")
BULLET_RE = re.compile(r"^[-*+][ \t]+")
ORDERED_RE = re.compile(r"^([0-9]+)[.)][ \t]+")
NORMALIZED_ITEM_RE = re.compile(r"^(?:- |[0-9]+\. )")

BINDING_FIELDS = ("name", "path", "remote")

ACCEPTANCE_KEY = "acceptance"
SCOPE_CHECKS_KEY = "scope_checks"
EVIDENCE_KEY = "evidence"
DELIVERY_KEY = "delivery"
DELIVERY_REQUIREMENT_KEYS = ("repository", "required", "target")
DELIVERY_RECEIPT_KEY = "delivered_at"
RESERVED_METADATA = (ACCEPTANCE_KEY, SCOPE_CHECKS_KEY, "format", "namespace", "seq", "revision")
PROVENANCE_SOURCES = ("auto", "provenance", "[auto]")

LIFECYCLE_CAPTURED = "captured"
LIFECYCLE_ACCEPTED = "accepted"
LIFECYCLE_DONE = "done"
LIFECYCLE_CANCELLED = "cancelled"
CLOSED_LIFECYCLES = (LIFECYCLE_DONE, LIFECYCLE_CANCELLED)
TASK_VIEW_PREFIX = "_"
LIFECYCLE_STATES = ("captured", "accepted", "active", "blocked", "done", "deferred", "cancelled")
LEGAL_TRANSITIONS = {
    "captured": ("accepted", "deferred", "cancelled"),
    "accepted": ("active", "blocked", "deferred", "cancelled"),
    "active": ("blocked", "done", "deferred", "cancelled"),
    "blocked": ("active", "deferred", "cancelled"),
    "done": ("active",),
    "deferred": ("captured", "accepted", "cancelled"),
    "cancelled": ("captured",),
}
REOPENING_TRANSITIONS = (("done", "active"), ("cancelled", "captured"))

PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
DEFAULT_PRIORITY = "P2"
DEFAULT_ORDER = 10 ** 6
FIRST_REVISION = 1

SAME_MEANING = "same-meaning"
PREPARATION = "preparation"
ACCEPTED_CHECK = "accepted"
SCOPE_DECISIONS = {"same_meaning": SAME_MEANING, "preparation": PREPARATION}


def normalize_line(line: str) -> str:
    collapsed = WHITESPACE_RUN_RE.sub(" ", line).strip()
    bullet = BULLET_RE.match(collapsed)
    if bullet:
        return "- " + collapsed[bullet.end():]
    ordered = ORDERED_RE.match(collapsed)
    if ordered:
        return ordered.group(1) + ". " + collapsed[ordered.end():]
    return collapsed


def group_blocks(lines: list[str]) -> list[str]:
    """Join each paragraph and each list item onto one line, so reflow is invisible."""
    blocks, current = [], []
    for line in lines:
        if current and (not line or NORMALIZED_ITEM_RE.match(line)):
            blocks.append(" ".join(current))
            current = []
        if line:
            current.append(line)
    if current:
        blocks.append(" ".join(current))
    return blocks


def normalize_scope(text: str) -> str:
    """Return the reflow-insensitive normal form of acceptance-bearing text."""
    unified = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(group_blocks([normalize_line(line) for line in unified.split("\n")]))


def digest(payload) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def canonical_binding(entry) -> dict:
    if not valid_binding(entry):
        raise InvalidIdentityError(
            "each repository binding needs a string `name` and `path`; correct the metadata fence",
            binding=entry,
        )
    return {field: entry.get(field) for field in BINDING_FIELDS}


def canonical_reference(entry) -> dict:
    """A referenced behaviour or criteria document, identified by work-root commit."""
    commit = entry.get("commit") if isinstance(entry, dict) else None
    path = entry.get("path") if isinstance(entry, dict) else None
    if not isinstance(path, str) or not isinstance(commit, str) or not commit.strip():
        raise InvalidIdentityError(
            "each entry in `references` needs a `path` and the work-root `commit` it was read at; "
            "a filename alone cannot identify the revision that was accepted",
            reference=entry,
        )
    return {"path": path, "commit": commit.strip(), "role": entry.get("role")}


def delivery_requirement(delivery):
    """What delivery the accepted scope requires, without the receipt that records it.

    Only the named keys are the requirement. Projecting them, rather than deleting
    the receipt fields known today, keeps a receipt field added later outside the
    fingerprint by construction.
    """
    if not isinstance(delivery, dict):
        return delivery
    return {key: delivery[key] for key in DELIVERY_REQUIREMENT_KEYS if key in delivery}


def fingerprint_inputs(record: dict) -> dict:
    """The accepted meaning of a record: scope, bindings, delivery target, references.

    Progress, evidence, and ordering fields are absent by construction, so a
    status change, a reprioritization, or a recorded delivery receipt can never
    invalidate acceptance.
    """
    metadata = record["metadata"]
    references = metadata.get("references") or []
    if not isinstance(references, list):
        raise InvalidIdentityError("`references` must be a list of referenced documents; wrap it in a list")
    return {
        "scope": normalize_scope(record["scope"]),
        "repositories": sorted(
            (canonical_binding(entry) for entry in metadata.get("repositories") or []),
            key=lambda binding: (binding["name"], binding["path"]),
        ),
        "delivery": delivery_requirement(metadata.get(DELIVERY_KEY)),
        "references": sorted(
            (canonical_reference(entry) for entry in references),
            key=lambda entry: (entry["path"], entry["commit"]),
        ),
    }


def scope_fingerprint(record: dict) -> str:
    return digest(fingerprint_inputs(record))


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_authority(decision, action: str) -> dict:
    """Return the trusted provenance for a decision, or refuse the decision."""
    decision = decision if isinstance(decision, dict) else {}
    actor = decision.get("actor")
    authority = decision.get("authority") if isinstance(decision.get("authority"), dict) else {}
    source, revision = authority.get("source"), authority.get("revision")
    if not (isinstance(actor, str) and actor.strip() and isinstance(source, str) and source.strip() and revision):
        raise MissingAuthorityError(
            f"{action} needs `actor` and an `authority` naming a `source` and its `revision` in the "
            "input payload; a record's own provenance is never authority",
            action=action,
        )
    if source.strip().lower() in PROVENANCE_SOURCES:
        raise MissingAuthorityError(
            f"`{source}` is provenance, not authority; {action} needs a decision actor and a trusted "
            "authority source",
            action=action,
            source=source,
        )
    return {
        "actor": actor.strip(),
        "authority": {"source": source.strip(), "revision": revision},
        "scope": list(decision.get("scope") or []),
        "at": decision.get("decided_at") if isinstance(decision.get("decided_at"), str) else timestamp(),
    }


def acceptance_of(record: dict) -> dict | None:
    acceptance = record["metadata"].get(ACCEPTANCE_KEY)
    return acceptance if isinstance(acceptance, dict) else None


def acceptance_applies(record: dict) -> bool:
    acceptance = acceptance_of(record)
    return acceptance is not None and acceptance.get("fingerprint") == scope_fingerprint(record)


def acceptance_status(record: dict) -> dict:
    """Applicability is derived from the fingerprint, never stored as a flag."""
    fingerprint = scope_fingerprint(record)
    acceptance = acceptance_of(record)
    if acceptance is None:
        return {
            "accepted": False,
            "applies": False,
            "fingerprint": fingerprint,
            "reason": "the record carries no acceptance; accept it before dependent work",
        }
    if acceptance.get("fingerprint") == fingerprint:
        return {
            "accepted": True,
            "applies": True,
            "fingerprint": fingerprint,
            "reason": "acceptance names the current scope fingerprint",
        }
    return {
        "accepted": True,
        "applies": False,
        "fingerprint": fingerprint,
        "accepted_fingerprint": acceptance.get("fingerprint"),
        "reason": "the scope changed after acceptance; re-accept it or record a same-meaning decision",
    }


def evidence_status(record: dict) -> list[dict]:
    """Evidence applies only to the fingerprint it was gathered against."""
    fingerprint = scope_fingerprint(record)
    entries = record["metadata"].get(EVIDENCE_KEY) or []
    return [
        {
            "criteria": entry.get("criteria") if isinstance(entry, dict) else None,
            "fingerprint": entry.get("fingerprint") if isinstance(entry, dict) else None,
            "applies": isinstance(entry, dict) and entry.get("fingerprint") == fingerprint,
        }
        for entry in entries
    ]


def record_name(identity: dict) -> str:
    task = identity.get("task")
    return f"{identity['seq']}/{task}" if task else identity["seq"]


def stale_evidence(record: dict) -> list:
    """Evidence entries gathered against a fingerprint the record no longer carries."""
    return [entry for entry in evidence_status(record) if not entry["applies"]]


def check_evidence_applies(record: dict, name: str) -> None:
    stale = stale_evidence(record)
    if not stale:
        return
    criteria = ", ".join(str(entry["criteria"]) for entry in stale)
    raise InapplicableEvidenceError(
        f"{name} carries {len(stale)} evidence entry(ies) gathered against another scope "
        f"fingerprint ({criteria}), so they say nothing about the accepted outcome; re-run those "
        "checks against the current fingerprint and append the results, or record a same-meaning "
        "decision with `revise --same-meaning`, before completing it",
        seq=record["identity"]["seq"],
        fingerprint=scope_fingerprint(record),
        evidence=stale,
    )


def check_delivery_recorded(record: dict, name: str) -> None:
    delivery = record["metadata"].get(DELIVERY_KEY)
    if not isinstance(delivery, dict) or delivery.get("required") is not True:
        return
    if delivery.get(DELIVERY_RECEIPT_KEY):
        return
    target = delivery.get("target") or "the delivery its accepted scope requires"
    raise InapplicableEvidenceError(
        f"{name} requires {target} and carries no delivery receipt, so the accepted outcome is "
        f"not delivered however many tasks passed; deliver it and record "
        f"`delivery.{DELIVERY_RECEIPT_KEY}` before completing it",
        seq=record["identity"]["seq"],
        delivery=delivery,
    )


def open_tasks(work_root: Path, identity: dict) -> list:
    """The item's tasks that are neither `done` nor `cancelled`.

    A record that is itself a task owns no tasks, and an item with no `tasks/`
    directory is not a parent, so both answer with nothing outstanding. A leading
    underscore marks a generated view rather than a record, as it does for the views.
    """
    if identity.get("task"):
        return []
    directory = Path(work_root) / item_directory(identity["seq"]) / TASKS_DIRECTORY
    if not directory.is_dir():
        return []
    return sorted(
        path.stem
        for path in directory.glob("*.md")
        if not path.name.startswith(TASK_VIEW_PREFIX)
        and lifecycle_of(read_record(path)) not in CLOSED_LIFECYCLES
    )


def check_tasks_closed(work_root: Path, record: dict, name: str) -> None:
    outstanding = open_tasks(work_root, record["identity"])
    if not outstanding:
        return
    raise InapplicableEvidenceError(
        f"{name} still has {len(outstanding)} task(s) that are neither done nor cancelled "
        f"({', '.join(outstanding)}); finish or cancel each of them before completing the item "
        "they belong to",
        seq=record["identity"]["seq"],
        open_tasks=outstanding,
    )


def check_completion(work_root: Path, record: dict) -> None:
    """Refuse `done` while the record's own evidence, delivery, or tasks contradict it.

    The stored record is what is judged: evidence, a delivery receipt and a task's
    own closure are each recorded before the item that rests on them is completed.
    """
    name = record_name(record["identity"])
    check_evidence_applies(record, name)
    check_delivery_recorded(record, name)
    check_tasks_closed(work_root, record, name)


def check_completed_record(request: dict, current: dict, updated: dict) -> None:
    """The gate for the record-level handlers, which write without the store's plan."""
    if lifecycle_of(updated) != LIFECYCLE_DONE or lifecycle_of(current) == LIFECYCLE_DONE:
        return
    check_completion(Path(request["work_root"]), current)


def lifecycle_of(record: dict) -> str:
    return validate_lifecycle(record["metadata"].get("lifecycle", LIFECYCLE_CAPTURED))


def validate_lifecycle(state) -> str:
    if state not in LIFECYCLE_STATES:
        raise InvalidRequestError(
            f"{state!r} is not a lifecycle state; use one of {', '.join(LIFECYCLE_STATES)}",
            lifecycle=state,
        )
    return state


def check_lifecycle_change(current, target, correction=None) -> str:
    """Return the target state, or refuse an illegal or unaccounted-for change."""
    current, target = validate_lifecycle(current), validate_lifecycle(target)
    if current == target:
        return target
    if target not in LEGAL_TRANSITIONS[current]:
        raise InvalidRequestError(
            f"{current} work cannot become {target}; its legal next states are "
            f"{', '.join(LEGAL_TRANSITIONS[current])}",
            lifecycle=current,
            requested=target,
        )
    if (current, target) in REOPENING_TRANSITIONS and not correction:
        raise MissingAuthorityError(
            f"reopening {current} work as {target} needs a `correction` in the payload saying why the "
            "closure was premature; a successor work item covers anything found after valid delivery",
            lifecycle=current,
            requested=target,
        )
    return target


def sort_key(record: dict) -> tuple:
    """Stable order: priority, then order, then identity."""
    metadata, identity = record["metadata"], record["identity"]
    order = metadata.get("order")
    return (
        PRIORITY_RANK.get(metadata.get("priority"), len(PRIORITY_RANK)),
        order if type(order) is int else DEFAULT_ORDER,
        identity["seq"],
        identity.get("task") or "",
    )


def as_record(metadata: dict, scope: str, body: str) -> dict:
    return {"metadata": metadata, "identity": validate_identity(metadata), "scope": scope, "body": body}


def write_record_file(path: Path, text: str) -> None:
    """Replace one record through a temporary file on the same filesystem."""
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as error:
        if temporary.exists():
            temporary.unlink()
        raise InvalidIdentityError(
            f"cannot write {path} ({error.strerror}); check the work root's permissions", path=str(path)
        ) from error


def require_payload(request: dict, command: str) -> dict:
    payload = request.get("input")
    if not isinstance(payload, dict):
        raise InvalidRequestError(
            f"{command} needs --input <file> holding a JSON object; no option accepts free text",
            command=command,
        )
    return payload


def check_expected_revision(record: dict, payload: dict, command: str) -> int:
    expected = payload.get("expected_revision")
    if type(expected) is not int:
        raise InvalidRequestError(
            f"{command} needs an integer `expected_revision` in its payload; read the current one with "
            "`show` and send it back",
            command=command,
        )
    held = record["identity"]["revision"]
    if expected != held:
        raise StaleRevisionError(
            f"the record stands at revision {held} and this request expected {expected}; re-read it with "
            "`show`, re-apply the change, and send the current revision",
            expected=expected,
            held=held,
        )
    return held


def scope_decision(payload: dict) -> tuple[str, dict] | None:
    """Return the one declared scope decision and its authority, or None."""
    declared = [key for key in SCOPE_DECISIONS if key in payload]
    if not declared:
        return None
    if len(declared) > 1:
        raise InvalidRequestError(
            "a revision carries at most one scope decision; send either `same_meaning` or `preparation`",
            keys=declared,
        )
    kind = SCOPE_DECISIONS[declared[0]]
    return kind, require_authority(payload[declared[0]], f"a {kind} decision")


def record_scope_check(metadata: dict, kind: str, previous: str | None, fingerprint: str, provenance: dict) -> dict:
    """Append the check and return it. Both fingerprints are recorded in one step."""
    check = {
        "kind": kind,
        "previous_fingerprint": previous,
        "fingerprint": fingerprint,
        "actor": provenance["actor"],
        "authority": provenance["authority"],
        "scope": provenance["scope"],
        "at": provenance["at"],
    }
    metadata[SCOPE_CHECKS_KEY] = list(metadata.get(SCOPE_CHECKS_KEY) or []) + [check]
    return check


def settle_scope(current: dict, updated: dict, decision) -> dict | None:
    """Carry acceptance across a declared same-meaning or preparation edit.

    Without a decision nothing is carried: acceptance keeps naming the old
    fingerprint, so a meaning-changing edit invalidates it by derivation.
    """
    if decision is None:
        return None
    kind, provenance = decision
    if kind == PREPARATION and not acceptance_applies(current):
        raise MissingAuthorityError(
            "a preparation change needs an applicable acceptance or standing authority on the record; "
            "accept the outcome before preparing work under it",
            kind=kind,
        )
    metadata = updated["metadata"]
    fingerprint = scope_fingerprint(updated)
    check = record_scope_check(metadata, kind, scope_fingerprint(current), fingerprint, provenance)
    acceptance = acceptance_of(current)
    if acceptance is not None:
        metadata[ACCEPTANCE_KEY] = dict(acceptance, fingerprint=fingerprint, rebound_at=check["at"])
    return check


def show(request: dict) -> dict:
    """Read one record and return its parsed identity, metadata, and scope."""
    path = resolve_record_path(request)
    record = read_record(path)
    check_namespace(record["identity"], request.get("namespace"))
    return {
        "path": str(path),
        "identity": record["identity"],
        "metadata": record["metadata"],
        "scope": record["scope"],
    }


def capture_namespace(request: dict, metadata: dict) -> str:
    supplied = request.get("namespace") or metadata.get("namespace")
    if supplied is None:
        raise InvalidIdentityError(
            "capture needs --namespace, the UUID in the work root's namespace.json, so the new record "
            "declares the identity scope it belongs to"
        )
    return parse_namespace(supplied)


def build_capture_metadata(request: dict, payload: dict) -> dict:
    """Capture fills identity, title, provenance, bindings, captured state, and ordering."""
    supplied = payload.get("metadata")
    if supplied is not None and not isinstance(supplied, dict):
        raise InvalidRequestError("`metadata` must be a JSON object of envelope fields")
    metadata = {key: value for key, value in dict(supplied or {}).items() if key not in RESERVED_METADATA}
    provenance = dict(metadata.get("provenance") or {})
    if payload.get("auto"):
        provenance["auto"] = True
    if provenance:
        metadata["provenance"] = provenance
    metadata.setdefault("priority", DEFAULT_PRIORITY)
    metadata.update(
        {
            "format": RECORD_FORMAT_VERSION,
            "namespace": capture_namespace(request, dict(supplied or {})),
            "seq": parse_item_id(request.get("seq")),
            "revision": FIRST_REVISION,
            "lifecycle": LIFECYCLE_CAPTURED,
        }
    )
    if request.get("task") is not None:
        metadata["task"] = parse_task_id(request["task"])
    return metadata


def capture(request: dict) -> dict:
    """Write a new record in the captured state. Capture grants no acceptance."""
    payload = require_payload(request, "capture")
    path = resolve_record_path(request)
    if path.exists():
        raise InvalidIdentityError(
            f"a record already stands at {path}; revise it instead of capturing the identity twice",
            path=str(path),
        )
    metadata = build_capture_metadata(request, payload)
    scope = payload.get("scope")
    if not isinstance(scope, str) or not scope.strip():
        raise InvalidRequestError("capture needs the acceptance-bearing `scope` text in its payload")
    text = render_record(metadata, scope, payload.get("body") or "")
    record = parse_record(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_record_file(path, text)
    return {
        "path": str(path),
        "identity": record["identity"],
        "lifecycle": lifecycle_of(record),
        "fingerprint": scope_fingerprint(record),
        "acceptance": acceptance_status(record),
    }


def apply_revision_edits(current: dict, payload: dict) -> dict:
    """Merge the requested edits onto the current record without touching identity."""
    edits = payload.get("metadata")
    if edits is not None and not isinstance(edits, dict):
        raise InvalidRequestError("`metadata` must be a JSON object of envelope fields")
    edits = dict(edits or {})
    metadata = dict(current["metadata"])
    metadata.update({key: value for key, value in edits.items() if key not in RESERVED_METADATA})
    if "lifecycle" in edits:
        metadata["lifecycle"] = check_lifecycle_change(
            lifecycle_of(current), edits["lifecycle"], payload.get("correction")
        )
    if payload.get("correction"):
        metadata["corrections"] = list(metadata.get("corrections") or []) + [payload["correction"]]
    return as_record(
        metadata,
        payload["scope"] if isinstance(payload.get("scope"), str) else current["scope"],
        payload["body"] if isinstance(payload.get("body"), str) else current["body"],
    )


def load_for_mutation(request: dict, command: str) -> tuple[Path, dict, dict]:
    payload = require_payload(request, command)
    path = resolve_record_path(request)
    current = read_record(path)
    check_namespace(current["identity"], request.get("namespace"))
    check_expected_revision(current, payload, command)
    return path, current, payload


def revise(request: dict) -> dict:
    """Edit a record. A declared same-meaning decision carries acceptance across."""
    path, current, payload = load_for_mutation(request, "revise")
    updated = apply_revision_edits(current, payload)
    check_completed_record(request, current, updated)
    check = settle_scope(current, updated, scope_decision(payload))
    updated["metadata"]["revision"] = advance_revision(current, updated)
    text = render_record(updated["metadata"], updated["scope"], updated["body"])
    written = parse_record(text)
    write_record_file(path, text)
    return {
        "path": str(path),
        "identity": written["identity"],
        "previous_fingerprint": scope_fingerprint(current),
        "fingerprint": scope_fingerprint(written),
        "lifecycle": lifecycle_of(written),
        "acceptance": acceptance_status(written),
        "evidence": evidence_status(written),
        "scope_check": check,
    }


def accept(request: dict) -> dict:
    """Bind the current fingerprint to a decision actor and a trusted authority."""
    path, current, payload = load_for_mutation(request, "accept")
    provenance = require_authority(payload, "accept")
    fingerprint = scope_fingerprint(current)
    previous = acceptance_of(current)
    metadata = dict(current["metadata"])
    metadata["lifecycle"] = check_lifecycle_change(
        lifecycle_of(current), payload.get("lifecycle", LIFECYCLE_ACCEPTED), payload.get("correction")
    )
    metadata[ACCEPTANCE_KEY] = {
        "fingerprint": fingerprint,
        "actor": provenance["actor"],
        "authority": provenance["authority"],
        "scope": provenance["scope"],
        "accepted_at": provenance["at"],
    }
    record_scope_check(
        metadata,
        ACCEPTED_CHECK,
        previous.get("fingerprint") if previous else None,
        fingerprint,
        provenance,
    )
    updated = as_record(metadata, current["scope"], current["body"])
    check_completed_record(request, current, updated)
    metadata["revision"] = advance_revision(current, updated)
    text = render_record(metadata, current["scope"], current["body"])
    written = parse_record(text)
    write_record_file(path, text)
    return {
        "path": str(path),
        "identity": written["identity"],
        "lifecycle": lifecycle_of(written),
        "acceptance": acceptance_status(written),
        "evidence": evidence_status(written),
    }
