"""Shared, safe invocation policy for explicit FastMCP tool registrations."""

import inspect
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import date, datetime
from functools import wraps
from time import perf_counter
from typing import Literal, ParamSpec, TypeVar, get_args, get_origin
from uuid import UUID

import structlog
from fastmcp import Context
from fastmcp.exceptions import ToolError
from starlette.requests import Request

from attendance_mcp.contracts import SafeError
from attendance_mcp.rest_client import (
    AUTHORIZATION_HEADER,
    CORRELATION_ID_HEADER,
    RestFailure,
)

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class HeaderFailure(ValueError):
    """A local, safe rejection before a caller header can be forwarded."""

    def __init__(self, code: str) -> None:
        self.code = code


class ToolCallPolicy:
    """Hide shared tool invocation and value-free lifecycle policy."""

    def instrument(
        self, operation: Callable[P, Awaitable[T]]
    ) -> Callable[P, Awaitable[T]]:
        """Log a tool lifecycle using only facts derived from its interface."""
        handler = operation.__name__
        input_shape = _input_shape(operation)

        @wraps(operation)
        async def instrumented(*args: P.args, **kwargs: P.kwargs) -> T:
            started_at = perf_counter()
            logger.info(
                "mcp_tool_operation_started",
                handler=handler,
                step="invocation",
                input_shape=input_shape,
            )
            try:
                result = await operation(*args, **kwargs)
            except Exception as error:
                logger.warning(
                    "mcp_tool_operation_failed",
                    handler=handler,
                    step="crmt_rest_call",
                    input_shape=input_shape,
                    duration_ms=_duration_ms(started_at),
                    error_type=type(error).__name__,
                )
                raise
            logger.info(
                "mcp_tool_operation_step_completed",
                handler=handler,
                step="crmt_rest_call",
                input_shape=input_shape,
                duration_ms=_duration_ms(started_at),
            )
            logger.info(
                "mcp_tool_operation_succeeded",
                handler=handler,
                step="completed",
                input_shape=input_shape,
                duration_ms=_duration_ms(started_at),
            )
            return result

        return instrumented

    async def call(
        self,
        ctx: Context | None,
        operation: Callable[[Mapping[str, str]], Awaitable[T]],
    ) -> T:
        """Forward admitted headers and translate only safe call failures."""
        try:
            return await operation(forward_headers(_context_request(ctx)))
        except RestFailure as failure:
            raise ToolError(failure.error.model_dump_json()) from None
        except ValueError:
            raise ToolError(
                SafeError.for_code("INTERNAL_ERROR").model_dump_json()
            ) from None


def forward_headers(request: Request) -> dict[str, str]:
    """Return exactly the two valid caller headers allowed to reach CRMT."""
    authorization = request.headers.getlist(AUTHORIZATION_HEADER)
    correlation_id = request.headers.getlist(CORRELATION_ID_HEADER)
    if len(authorization) != 1:
        raise HeaderFailure("AUTHENTICATION_REQUIRED")
    scheme, separator, token = authorization[0].partition(" ")
    if scheme.casefold() != "bearer" or not separator or not token.strip():
        raise HeaderFailure("TOKEN_INVALID")
    if len(correlation_id) != 1:
        raise HeaderFailure("CORRELATION_ID_INVALID")
    if canonical_correlation_id(correlation_id) is None:
        raise HeaderFailure("CORRELATION_ID_INVALID") from None
    return {
        AUTHORIZATION_HEADER: authorization[0],
        CORRELATION_ID_HEADER: correlation_id[0],
    }


def canonical_correlation_id(values: Sequence[str]) -> str | None:
    """Return a logging-safe canonical UUID only for one valid header value."""
    if len(values) != 1:
        return None
    try:
        return str(UUID(values[0]))
    except ValueError:
        return None


def _context_request(ctx: Context | None) -> Request:
    request = ctx.request_context.request if ctx is not None else None
    if request is None:
        raise ValueError("MCP request context is unavailable")
    return request


def _input_shape(operation: Callable[..., object]) -> tuple[str, ...]:
    return tuple(
        f"{parameter.name}:{_annotation_label(parameter.annotation)}"
        f"{'?' if parameter.default is None else ''}"
        for parameter in inspect.signature(operation).parameters.values()
        if parameter.name != "ctx"
    )


def _annotation_label(annotation: object) -> str:
    origin = get_origin(annotation)
    if annotation is date:
        return "date"
    if annotation is datetime:
        return "datetime"
    if annotation is int:
        return "int"
    if annotation is bool:
        return "bool"
    if annotation is str or origin is Literal:
        return "string"
    if origin is list:
        return "list"
    if origin is not None:
        candidates = [
            candidate
            for candidate in get_args(annotation)
            if candidate is not type(None)
        ]
        if len(candidates) == 1:
            return _annotation_label(candidates[0])
    return "object"


def _duration_ms(started_at: float) -> int:
    return round((perf_counter() - started_at) * 1000)
