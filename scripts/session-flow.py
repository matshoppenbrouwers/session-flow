#!/usr/bin/env python3
"""session-flow local record runtime: CLI and versioned request/response boundary.

Written without f-strings, annotations, or other post-3.5 syntax so that an
unsupported interpreter reaches the runtime guard below and receives an install
instruction instead of a SyntaxError. Package modules are imported only after
that guard passes.

Free text reaches the runtime through --input <file> as JSON. No option takes
interpolated issue text, no argument is passed to a shell, and no record content
is executed.
"""

import argparse
import json
import os
import sys

PROTOCOL_VERSION = 1
MINIMUM_PYTHON = (3, 9)
INSTALL_INSTRUCTION = (
    "Install Python 3.9 or newer and expose it as python3 (Debian/Ubuntu: "
    "'sudo apt install python3'; macOS: 'brew install python3'), then re-run this command. "
    "Machines without Python cannot run session-flow."
)

PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_ROOT = os.path.join(PACKAGE_ROOT, "scripts")
CONFIG_FILE = ".session-flow.json"
DEFAULT_WORK_ROOT = "_devdocs/work"
DEFAULT_SEQUENCE = "_devdocs/SEQUENCE.md"
PLUGIN_MANIFEST = os.path.join(PACKAGE_ROOT, ".claude-plugin", "plugin.json")

BUILTIN = "builtin"
DISPATCH = {
    "doctor": BUILTIN,
    "bind-namespace": "session_flow.store:bind_namespace",
    "show": "session_flow.records:show",
    "capture": "session_flow.records:capture",
    "revise": "session_flow.records:revise",
    "accept": "session_flow.records:accept",
    "select": "session_flow.views:select",
    "claim": "session_flow.store:claim",
    "record-result": "session_flow.store:record_result",
    "transition": "session_flow.store:transition",
    "render": "session_flow.views:render",
    "import": "session_flow.views:import_sequence",
    "reconcile": "session_flow.store:reconcile",
    "backup": "session_flow.store:backup",
    "restore": "session_flow.store:restore",
}
STORAGE_REPORT_HOOK = "session_flow.store:work_root_report"

RUNTIME_LIMITATIONS = (
    "9p and DrvFs write caching can lose recently written records on hard power loss.",
    "No POSIX lock coordinates with a Windows-side process editing the same files.",
    "Network and cloud-synchronized work roots are unsupported.",
    "Simultaneous editing from another operating system and multi-host mutation are unsupported.",
)


def version_string(version_info):
    return "%d.%d.%d" % (version_info[0], version_info[1], version_info[2])


def runtime_error(version_info):
    """Return the named error for an unsupported interpreter, or None."""
    if tuple(version_info[:2]) >= MINIMUM_PYTHON:
        return None
    return {
        "code": "unsupported-runtime",
        "message": "session-flow needs Python %d.%d or newer; this interpreter reports %s"
        % (MINIMUM_PYTHON[0], MINIMUM_PYTHON[1], version_string(version_info)),
        "detail": {
            "minimum": "%d.%d" % MINIMUM_PYTHON,
            "found": version_string(version_info),
            "install": INSTALL_INSTRUCTION,
        },
    }


def emit(command, payload, exit_code=0, diagnostic=None):
    body = {"protocol": PROTOCOL_VERSION, "command": command}
    body.update(payload)
    sys.stdout.write(json.dumps(body, indent=2, sort_keys=True) + "\n")
    if diagnostic:
        sys.stderr.write(diagnostic.rstrip("\n") + "\n")
    return exit_code


def build_parser():
    parser = argparse.ArgumentParser(
        prog="session-flow.py",
        description="Deterministic local operations on work-item records.",
        epilog="Mutations read their payload from --input <file>; no option accepts free text.",
    )
    parser.add_argument("command", choices=sorted(DISPATCH))
    parser.add_argument("--project-root", default=".", help="repository whose .session-flow.json resolves the paths")
    parser.add_argument("--namespace", help="namespace UUID the addressed records must belong to")
    parser.add_argument("--seq", help="work-item identity, SEQ-NNN")
    parser.add_argument("--task", help="task identity within the work item, such as A1")
    parser.add_argument("--input", help="path to the JSON payload for a mutation")
    return parser


def read_json(path, description):
    from session_flow import InvalidRequestError

    try:
        with open(path, "r") as handle:
            return json.load(handle)
    except OSError as error:
        raise InvalidRequestError(
            "cannot read the %s at %s (%s); pass a readable file" % (description, path, error.strerror),
            path=path,
        )
    except ValueError as error:
        raise InvalidRequestError(
            "the %s at %s is not valid JSON (%s); correct the file and re-run" % (description, path, error),
            path=path,
        )


def load_config(project_root):
    path = os.path.join(project_root, CONFIG_FILE)
    if not os.path.isfile(path):
        return {}
    config = read_json(path, "project configuration")
    if not isinstance(config, dict):
        from session_flow import InvalidRequestError

        raise InvalidRequestError("%s must hold a JSON object; restore it from the reference" % path)
    return config


def configured_path(project_root, config, key, default):
    paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    value = paths.get(key) if isinstance(paths.get(key), str) else default
    return os.path.abspath(os.path.join(project_root, value))


def build_request(args):
    project_root = os.path.abspath(args.project_root)
    config = load_config(project_root)
    payload = read_json(args.input, "input payload") if args.input else None
    return {
        "protocol": PROTOCOL_VERSION,
        "command": args.command,
        "project_root": project_root,
        "work_root": configured_path(project_root, config, "work", DEFAULT_WORK_ROOT),
        "sequence_path": configured_path(project_root, config, "sequence", DEFAULT_SEQUENCE),
        "namespace": args.namespace,
        "seq": args.seq,
        "task": args.task,
        "input": payload,
        "config": config,
    }


def resolve_handler(target):
    """Return the module function for a dispatch target, or None when it has not landed."""
    import importlib

    module_name, _, function_name = target.partition(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        if getattr(error, "name", None) != module_name:
            raise
        return None
    return getattr(module, function_name, None)


def command_availability():
    report = {}
    for command in sorted(DISPATCH):
        target = DISPATCH[command]
        available = target == BUILTIN or resolve_handler(target) is not None
        report[command] = {"handler": target, "available": available}
    return report


def plugin_version():
    if not os.path.isfile(PLUGIN_MANIFEST):
        return None
    manifest = read_json(PLUGIN_MANIFEST, "plugin manifest")
    return manifest.get("version") if isinstance(manifest, dict) else None


def storage_report(request):
    report = {
        "work_root": request["work_root"],
        "work_root_present": os.path.isdir(request["work_root"]),
        "sequence_path": request["sequence_path"],
        "limitations": list(RUNTIME_LIMITATIONS),
    }
    hook = resolve_handler(STORAGE_REPORT_HOOK)
    if hook is None:
        return report
    extra = dict(hook(request))
    report["limitations"].extend(extra.pop("limitations", []))
    report.update(extra)
    return report


def doctor(request):
    from session_flow import ERROR_CODES, RECORD_FORMAT_VERSION

    return {
        "protocol": PROTOCOL_VERSION,
        "plugin_version": plugin_version(),
        "record_format": RECORD_FORMAT_VERSION,
        "runtime": {
            "python": version_string(sys.version_info),
            "minimum_python": "%d.%d" % MINIMUM_PYTHON,
            "executable": sys.executable,
            "package_root": PACKAGE_ROOT,
            "install_instruction": INSTALL_INSTRUCTION,
        },
        "storage": storage_report(request),
        "commands": command_availability(),
        "errors": dict(ERROR_CODES),
    }


def run(request):
    from session_flow import NotImplementedCommandError

    command = request["command"]
    if command == "doctor":
        return doctor(request)
    target = DISPATCH[command]
    handler = resolve_handler(target)
    if handler is None:
        raise NotImplementedCommandError(
            "the %s command is not implemented in this build; its handler is %s" % (command, target),
            command=command,
            handler=target,
        )
    return handler(request)


def main(argv=None):
    guard = runtime_error(sys.version_info)
    if guard is not None:
        return emit(None, {"ok": False, "error": guard}, 1, INSTALL_INSTRUCTION)
    if SCRIPTS_ROOT not in sys.path:
        sys.path.insert(0, SCRIPTS_ROOT)

    from session_flow import SessionFlowError

    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return emit(args.command, {"ok": True, "result": run(build_request(args))})
    except SessionFlowError as error:
        return emit(args.command, {"ok": False, "error": error.as_error()}, 1, str(error))
    except Exception as error:
        # Consumers parse stdout, so an unexpected failure still answers on the protocol.
        import traceback

        detail = {"code": "internal", "message": "%s: %s" % (type(error).__name__, error), "detail": {}}
        return emit(args.command, {"ok": False, "error": detail}, 1, traceback.format_exc())


if __name__ == "__main__":
    sys.exit(main())
