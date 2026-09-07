"""Local work-item record runtime for session-flow.

Holds the record format version and the one named error taxonomy every module in
this package raises. `scripts/session-flow.py` serializes these errors into the
versioned JSON response; nothing here reads the network or executes a record.
"""

from __future__ import annotations

RECORD_FORMAT_VERSION = 1


class SessionFlowError(Exception):
    """Named runtime error. Subclasses set the wire `code`."""

    code = "internal"

    def __init__(self, message: str, **detail):
        super().__init__(message)
        self.detail = detail

    def as_error(self) -> dict:
        return {"code": self.code, "message": str(self), "detail": self.detail}


class UnsupportedFormatError(SessionFlowError):
    code = "unsupported-format"


class StaleRevisionError(SessionFlowError):
    code = "stale-revision"


class RootBusyError(SessionFlowError):
    code = "root-busy"


class InvalidIdentityError(SessionFlowError):
    code = "invalid-identity"


class MissingAuthorityError(SessionFlowError):
    code = "missing-authority"


class InapplicableEvidenceError(SessionFlowError):
    code = "inapplicable-evidence"


class NotImplementedCommandError(SessionFlowError):
    code = "not-implemented"


class UnsupportedRuntimeError(SessionFlowError):
    """Interpreter below the supported floor.

    The entrypoint's pre-import guard repeats this `code` as a literal, because
    it must answer before any module of this package is imported.
    """

    code = "unsupported-runtime"


class InvalidRequestError(SessionFlowError):
    code = "invalid-request"


ERROR_CODES = {
    UnsupportedFormatError.code: "envelope missing, duplicated, malformed, or of an unknown format version",
    StaleRevisionError.code: "the expected record revision does not match the stored one",
    RootBusyError.code: "the work root is locked by another coordinator or needs reconciliation",
    InvalidIdentityError.code: "identity, immutable field, or resolved path is not valid",
    MissingAuthorityError.code: "the requested change needs authority that was not supplied",
    InapplicableEvidenceError.code: "the evidence does not apply to the accepted scope revision",
    NotImplementedCommandError.code: "the command family is reachable but its handler has not landed",
    UnsupportedRuntimeError.code: "the interpreter is older than the supported floor",
    InvalidRequestError.code: "the request itself is malformed: unknown option, unreadable input file",
    SessionFlowError.code: "unexpected failure; the diagnostic on stderr carries the traceback",
}
