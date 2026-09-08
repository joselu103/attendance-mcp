"""ASGI composition for Attendance MCP's public, stateless HTTP surface."""

import json
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

import httpx
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from attendance_mcp.contracts import SafeError
from attendance_mcp.rest_client import (
    AUTHORIZATION_HEADER,
    CORRELATION_ID_HEADER,
    CrmtRestClient,
    RestFailure,
)
from attendance_mcp.settings import Settings

MCP_CONTRACT_VERSION = "1.2.0"


def create_app(
    settings: Settings | None = None, *, client: httpx.AsyncClient | None = None
) -> Starlette:
    """Create the public health route and the mounted Streamable HTTP server."""
    runtime_settings = settings or Settings()
    owns_client = client is None
    rest_client = CrmtRestClient(
        client=client
        or httpx.AsyncClient(
            base_url=str(runtime_settings.crmt_base_url),
            timeout=runtime_settings.request_timeout_seconds,
        )
    )
    mcp = FastMCP("Attendance MCP", version=MCP_CONTRACT_VERSION)

    @mcp.tool(
        name="list_my_attendance_events",
        description="List the authenticated requester's attendance events.",
        annotations={"readOnlyHint": True},
    )
    async def list_my_attendance_events(
        start_date: str,
        end_date: str,
        limit: int = 50,
        offset: int = 0,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        """Map the frozen legacy MCP request directly to its CRMT REST operation."""
        try:
            headers = _forward_headers(_context_request(ctx))
            return await rest_client.list_my_attendance_events(
                headers=headers,
                params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit,
                    "offset": offset,
                },
            )
        except RestFailure as failure:
            raise ToolError(failure.error.model_dump_json()) from None
        except ValueError:
            raise ToolError(
                SafeError.for_code("INTERNAL_ERROR").model_dump_json()
            ) from None

    mcp_app = mcp.http_app(path="/mcp", transport="streamable-http", json_response=True)

    @asynccontextmanager
    async def lifespan(_: Starlette):
        try:
            async with mcp_app.lifespan(mcp_app):
                yield
        finally:
            if owns_client:
                await rest_client.aclose()

    app = Starlette(
        routes=[
            Route("/health", _health, methods=["GET"]),
            Mount("/", app=mcp_app),
        ],
        lifespan=lifespan,
    )
    app.add_middleware(_AdmissionMiddleware, rest_client=rest_client)
    return app


async def _health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def _context_request(ctx: Context | None) -> Request:
    request = ctx.request_context.request if ctx is not None else None
    if request is None:
        raise ValueError("MCP request context is unavailable")
    return request


def _forward_headers(request: Request) -> dict[str, str]:
    authorization = request.headers.getlist(AUTHORIZATION_HEADER)
    correlation_id = request.headers.getlist(CORRELATION_ID_HEADER)
    if len(authorization) != 1:
        raise HeaderFailure("AUTHENTICATION_REQUIRED")
    scheme, separator, token = authorization[0].partition(" ")
    if scheme.casefold() != "bearer" or not separator or not token.strip():
        raise HeaderFailure("TOKEN_INVALID")
    if len(correlation_id) != 1:
        raise HeaderFailure("CORRELATION_ID_INVALID")
    try:
        UUID(correlation_id[0])
    except ValueError:
        raise HeaderFailure("CORRELATION_ID_INVALID") from None
    return {
        AUTHORIZATION_HEADER: authorization[0],
        CORRELATION_ID_HEADER: correlation_id[0],
    }


class _AdmissionMiddleware:
    """Validate inbound headers and admit only MCP initialize requests through CRMT."""

    def __init__(self, app: ASGIApp, rest_client: CrmtRestClient) -> None:
        self._app = app
        self._rest_client = rest_client

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] != "/mcp":
            await self._app(scope, receive, send)
            return
        request = Request(scope, receive=receive)
        try:
            headers = _forward_headers(request)
        except HeaderFailure as failure:
            status_code = (
                401
                if failure.code in {"AUTHENTICATION_REQUIRED", "TOKEN_INVALID"}
                else 400
            )
            await _send_safe_error(
                scope, send, SafeError.for_code(failure.code), status_code
            )
            return

        body = await request.body()
        if len(body) > 65536:
            await _send_safe_error(
                scope, send, SafeError.for_code("INVALID_ARGUMENT"), 400
            )
            return
        if _is_initialize(body):
            try:
                await self._rest_client.admit_session(headers)
            except RestFailure as failure:
                await _send_safe_error(scope, send, failure.error, failure.status_code)
                return

        sent = False

        async def replay() -> Message:
            nonlocal sent
            if sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self._app(scope, replay, send)


def _is_initialize(body: bytes) -> bool:
    try:
        value: Any = json.loads(body)
    except (TypeError, ValueError):
        return False
    return isinstance(value, dict) and value.get("method") == "initialize"


async def _send_safe_error(
    scope: Scope, send: Send, error: SafeError, status_code: int
) -> None:
    response = JSONResponse(error.model_dump(), status_code=status_code)
    await response(scope, _empty_receive, send)


async def _empty_receive() -> Message:
    return {"type": "http.disconnect"}


class HeaderFailure(ValueError):
    """A local, safe rejection before a caller header can be forwarded."""

    def __init__(self, code: str) -> None:
        self.code = code
