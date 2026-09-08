"""Small, adapter-owned representations of CRMT's safe public boundary."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

SafeErrorCode = Literal[
    "AUTHENTICATION_REQUIRED",
    "TOKEN_INVALID",
    "CORRELATION_ID_INVALID",
    "IDENTITY_UNMAPPED",
    "IDENTITY_AMBIGUOUS",
    "INVALID_ARGUMENT",
    "FORBIDDEN",
    "NOT_FOUND",
    "BACKEND_UNAVAILABLE",
    "INTERNAL_ERROR",
]

SAFE_MESSAGES: dict[SafeErrorCode, str] = {
    "AUTHENTICATION_REQUIRED": "Please sign in to use Attendance.",
    "TOKEN_INVALID": "Your sign-in could not be verified. Please try again.",
    "CORRELATION_ID_INVALID": "The request correlation ID is missing or invalid.",
    "IDENTITY_UNMAPPED": (
        "Your Teams account is not linked to an active attendance employee. "
        "Contact an administrator."
    ),
    "IDENTITY_AMBIGUOUS": "Your Teams account cannot be linked safely. Contact an administrator.",
    "INVALID_ARGUMENT": "Check the attendance date range and pagination values and try again.",
    "FORBIDDEN": "You do not have permission to do that.",
    "NOT_FOUND": "The requested attendance record was not found.",
    "BACKEND_UNAVAILABLE": "Attendance is temporarily unavailable. Please try again shortly.",
    "INTERNAL_ERROR": "Attendance could not complete that request.",
}


class SafeError(BaseModel):
    """A validated CRMT envelope; nothing else crosses the adapter boundary."""

    model_config = ConfigDict(extra="forbid")

    code: SafeErrorCode
    message: str

    @classmethod
    def for_code(cls, code: SafeErrorCode) -> "SafeError":
        return cls(code=code, message=SAFE_MESSAGES[code])

    @classmethod
    def from_upstream(cls, value: object) -> "SafeError | None":
        if not isinstance(value, dict):
            return None
        try:
            error = cls.model_validate(value)
        except ValueError:
            return None
        return error if error.message == SAFE_MESSAGES[error.code] else None
