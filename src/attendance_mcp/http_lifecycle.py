"""One private ASGI lifecycle boundary for public Attendance MCP HTTP requests."""

from time import perf_counter
from uuid import uuid4

import structlog
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from attendance_mcp.contracts import SafeError
from attendance_mcp.rest_client import (
    CORRELATION_ID_HEADER,
)
from attendance_mcp.tool_policy import (
    HeaderFailure,
    canonical_correlation_id,
    forward_headers,
)

MCP_CONTRACT_VERSION = "1.3.0"
MCP_CONTRACT_VERSION_HEADER = "X-Attendance-MCP-Contract-Version"
_MAX_MCP_BODY_BYTES = 65_536
logger = structlog.get_logger(__name__)


class _McpHttpLifecycle:
    """Apply the HTTP contract before FastMCP handles an MCP request.

    Every MCP request receives trace logging and contract-version publication.
    MCP requests require admitted headers and a bounded body. Other ASGI traffic
    passes through unchanged apart from lifecycle logging.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        trace_id = _trace_id(scope)
        route = scope.get("path", "")
        started_at = perf_counter()
        status_code: int | None = None
        outcome: dict[str, str] = {"result_state": "completed"}
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
        logger.info("http_request_received", route=route, trace_id=trace_id)

        async def send_response(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                if route == "/mcp":
                    _publish_contract_version(message)
            await send(message)

        try:
            if route == "/mcp":
                await self._handle_mcp(scope, receive, send_response, outcome)
            else:
                await self._app(scope, receive, send_response)
            event_data: dict[str, object] = {
                "route": route,
                "trace_id": trace_id,
                "status_code": status_code,
                "duration_ms": _duration_ms(started_at),
                **outcome,
            }
            if outcome["result_state"] == "completed":
                logger.info("http_request_completed", **event_data)
            else:
                _log_response_failure(event_data)
        except Exception:
            logger.exception(
                "http_request_failed",
                route=route,
                trace_id=trace_id,
                result_state="failed",
                status_code=status_code,
                duration_ms=_duration_ms(started_at),
            )
            raise
        finally:
            structlog.contextvars.clear_contextvars()

    async def _handle_mcp(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        outcome: dict[str, str],
    ) -> None:
        request = Request(scope, receive=receive)
        try:
            forward_headers(request)
        except HeaderFailure as failure:
            outcome.update(
                result_state="header_rejected",
                header_admission="rejected",
                safe_error_code=failure.code,
            )
            status_code = (
                401
                if failure.code in {"AUTHENTICATION_REQUIRED", "TOKEN_INVALID"}
                else 400
            )
            await _send_safe_error(
                scope, send, SafeError.for_code(failure.code), status_code
            )
            return

        outcome["header_admission"] = "accepted"
        body = await request.body()
        if len(body) > _MAX_MCP_BODY_BYTES:
            outcome.update(
                result_state="request_rejected", safe_error_code="INVALID_ARGUMENT"
            )
            await _send_safe_error(
                scope, send, SafeError.for_code("INVALID_ARGUMENT"), 400
            )
            return
        await self._app(scope, _replay_body(body), send)


def _trace_id(scope: Scope) -> str:
    values = [
        value.decode("latin-1")
        for name, value in scope.get("headers", [])
        if name.lower() == CORRELATION_ID_HEADER.lower().encode()
    ]
    return canonical_correlation_id(values) or str(uuid4())


def _publish_contract_version(message: Message) -> None:
    headers = [
        (name, value)
        for name, value in message.get("headers", [])
        if name.lower() != MCP_CONTRACT_VERSION_HEADER.lower().encode()
    ]
    headers.append(
        (MCP_CONTRACT_VERSION_HEADER.lower().encode(), MCP_CONTRACT_VERSION.encode())
    )
    message["headers"] = headers


def _replay_body(body: bytes) -> Receive:
    sent = False

    async def replay() -> Message:
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return replay


async def _send_safe_error(
    scope: Scope, send: Send, error: SafeError, status_code: int
) -> None:
    response = JSONResponse(error.model_dump(), status_code=status_code)
    await response(scope, _empty_receive, send)


async def _empty_receive() -> Message:
    return {"type": "http.disconnect"}


def _duration_ms(started_at: float) -> int:
    return round((perf_counter() - started_at) * 1000)


def _log_response_failure(event_data: dict[str, object]) -> None:
    status_code = event_data["status_code"]
    if isinstance(status_code, int) and status_code >= 500:
        logger.error("http_request_failed", **event_data)
    else:
        logger.warning("http_request_failed", **event_data)
