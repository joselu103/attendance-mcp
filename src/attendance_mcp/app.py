"""ASGI composition for Attendance MCP's public, stateless HTTP surface."""

import json
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

import httpx
import structlog
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
MCP_CONTRACT_VERSION_HEADER = "X-Attendance-MCP-Contract-Version"
logger = structlog.get_logger(__name__)


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
        description=(
            "List the requesting employee's attendance events over one through 31 "
            "inclusive calendar days. Employee identity is resolved by the server; "
            "limit must be from 1 through 100 and offset must be nonnegative."
        ),
    )
    async def list_my_attendance_events(
        start_date: date,
        end_date: date,
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

    @mcp.tool(
        name="list_employees",
        description=(
            "List active employees for attendance lookups. Inactive employee "
            "records are excluded. Results use bounded limit/offset pagination."
        ),
    )
    async def list_employees(
        limit: int = 50, offset: int = 0, ctx: Context | None = None
    ) -> dict[str, object]:
        """Map the legacy active-employee page to CRMT REST."""
        try:
            return await rest_client.list_employees(
                headers=_forward_headers(_context_request(ctx)),
                params={"limit": limit, "offset": offset},
            )
        except RestFailure as failure:
            raise ToolError(failure.error.model_dump_json()) from None
        except ValueError:
            raise ToolError(
                SafeError.for_code("INTERNAL_ERROR").model_dump_json()
            ) from None

    @mcp.tool(
        name="get_employee",
        description="Return one employee's directory-safe metadata by ID.",
    )
    async def get_employee(
        employee_id: int, ctx: Context | None = None
    ) -> dict[str, object]:
        """Map the legacy employee lookup to CRMT REST."""
        try:
            return await rest_client.get_employee(
                headers=_forward_headers(_context_request(ctx)), employee_id=employee_id
            )
        except RestFailure as failure:
            raise ToolError(failure.error.model_dump_json()) from None
        except ValueError:
            raise ToolError(
                SafeError.for_code("INTERNAL_ERROR").model_dump_json()
            ) from None

    @mcp.tool(
        name="list_punch_types",
        description=(
            "List configured punch types and their server-derived attendance locations. "
            "Locations are reference data, not caller-selected input."
        ),
    )
    async def list_punch_types(
        active_only: bool = True, ctx: Context | None = None
    ) -> list[object]:
        """Map the legacy punch-type lookup to CRMT REST."""
        try:
            return await rest_client.list_punch_types(
                headers=_forward_headers(_context_request(ctx)), active_only=active_only
            )
        except RestFailure as failure:
            raise ToolError(failure.error.model_dump_json()) from None
        except ValueError:
            raise ToolError(
                SafeError.for_code("INTERNAL_ERROR").model_dump_json()
            ) from None

    @mcp.tool(
        name="list_locations",
        description="List attendance-event location reference data.",
    )
    async def list_locations(ctx: Context | None = None) -> list[object]:
        """Map the legacy location lookup to CRMT REST."""
        try:
            return await rest_client.list_locations(
                headers=_forward_headers(_context_request(ctx))
            )
        except RestFailure as failure:
            raise ToolError(failure.error.model_dump_json()) from None
        except ValueError:
            raise ToolError(
                SafeError.for_code("INTERNAL_ERROR").model_dump_json()
            ) from None

    @mcp.tool(
        name="list_attendance_events",
        description=(
            "List one employee's attendance events in a bounded date range. "
            "This MVP tool is available only to the server-configured admin requester."
        ),
    )
    async def list_attendance_events(
        employee_id: int,
        start_date: date,
        end_date: date,
        limit: int = 50,
        offset: int = 0,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        """Map the legacy administrator event list directly to CRMT REST."""
        try:
            return await rest_client.list_attendance_events(
                employee_id=employee_id,
                headers=_forward_headers(_context_request(ctx)),
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

    @mcp.tool(
        name="get_attendance_event",
        description="Return one attendance event, including recorded audit metadata.",
    )
    async def get_attendance_event(
        attendance_event_id: int, ctx: Context | None = None
    ) -> dict[str, object]:
        """Map the legacy administrator event detail directly to CRMT REST."""
        try:
            return await rest_client.get_attendance_event(
                attendance_event_id=attendance_event_id,
                headers=_forward_headers(_context_request(ctx)),
            )
        except RestFailure as failure:
            raise ToolError(failure.error.model_dump_json()) from None
        except ValueError:
            raise ToolError(
                SafeError.for_code("INTERNAL_ERROR").model_dump_json()
            ) from None

    @mcp.tool(
        name="get_daily_attendance",
        description=(
            "Return one employee's local-calendar daily attendance events and "
            "calculated planned-versus-logged outcome."
        ),
    )
    async def get_daily_attendance(
        employee_id: int, day: date, ctx: Context | None = None
    ) -> dict[str, object]:
        """Map the legacy daily administrator view directly to CRMT REST."""
        try:
            return await rest_client.get_daily_attendance(
                employee_id=employee_id,
                headers=_forward_headers(_context_request(ctx)),
                params={"day": day},
            )
        except RestFailure as failure:
            raise ToolError(failure.error.model_dump_json()) from None
        except ValueError:
            raise ToolError(
                SafeError.for_code("INTERNAL_ERROR").model_dump_json()
            ) from None

    @mcp.tool(
        name="get_planned_work",
        description=(
            "Return recorded daily planned-work hours for one employee over an "
            "inclusive Europe/Ljubljana range of up to 31 calendar days."
        ),
    )
    async def get_planned_work(
        employee_id: int,
        start_date: date,
        end_date: date,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        """Map the legacy planned-work administrator view directly to CRMT REST."""
        try:
            return await rest_client.get_planned_work(
                employee_id=employee_id,
                headers=_forward_headers(_context_request(ctx)),
                params={"start_date": start_date, "end_date": end_date},
            )
        except RestFailure as failure:
            raise ToolError(failure.error.model_dump_json()) from None
        except ValueError:
            raise ToolError(
                SafeError.for_code("INTERNAL_ERROR").model_dump_json()
            ) from None

    @mcp.tool(name="get_current_attendance", annotations={"readOnlyHint": True})
    async def get_current_attendance(
        as_of: datetime | None = None,
        status: Literal[
            "office",
            "remote",
            "customer_site",
            "break",
            "absence",
            "no_status",
            "unknown",
        ]
        | None = None,
        limit: int = 50,
        offset: int = 0,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        return await _reporting_call(
            ctx,
            lambda headers: rest_client.get_current_attendance(
                headers=headers,
                params=_defined_params(
                    as_of=as_of.isoformat() if as_of else None,
                    status=status,
                    limit=limit,
                    offset=offset,
                ),
            ),
        )

    @mcp.tool(
        name="get_employee_attendance_analysis", annotations={"readOnlyHint": True}
    )
    async def get_employee_attendance_analysis(
        employee_id: int, start_date: date, end_date: date, ctx: Context | None = None
    ) -> dict[str, object]:
        return await _reporting_call(
            ctx,
            lambda headers: rest_client.get_employee_attendance_analysis(
                employee_id=employee_id,
                headers=headers,
                params={"start_date": start_date, "end_date": end_date},
            ),
        )

    @mcp.tool(
        name="get_employee_attendance_summary", annotations={"readOnlyHint": True}
    )
    async def get_employee_attendance_summary(
        employee_id: int, start_date: date, end_date: date, ctx: Context | None = None
    ) -> dict[str, object]:
        return await _reporting_call(
            ctx,
            lambda headers: rest_client.get_employee_attendance_summary(
                employee_id=employee_id,
                headers=headers,
                params={"start_date": start_date, "end_date": end_date},
            ),
        )

    @mcp.tool(name="get_exceptions", annotations={"readOnlyHint": True})
    async def get_exceptions(
        start_date: date,
        end_date: date,
        employee_ids: list[int] | None = None,
        limit: int = 50,
        offset: int = 0,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        return await _reporting_call(
            ctx,
            lambda headers: rest_client.get_exceptions(
                headers=headers,
                params=_defined_params(
                    start_date=start_date,
                    end_date=end_date,
                    employee_ids=employee_ids,
                    limit=limit,
                    offset=offset,
                ),
            ),
        )

    @mcp.tool(
        name="get_organization_attendance_analysis", annotations={"readOnlyHint": True}
    )
    async def get_organization_attendance_analysis(
        start_date: date,
        end_date: date,
        limit: int = 50,
        offset: int = 0,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        return await _reporting_call(
            ctx,
            lambda headers: rest_client.get_organization_attendance_analysis(
                headers=headers,
                params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit,
                    "offset": offset,
                },
            ),
        )

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
    app.add_middleware(_McpContractVersionMiddleware)
    app.add_middleware(_RequestLoggingMiddleware)
    return app


async def _health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def _context_request(ctx: Context | None) -> Request:
    request = ctx.request_context.request if ctx is not None else None
    if request is None:
        raise ValueError("MCP request context is unavailable")
    return request


async def _reporting_call(ctx: Context | None, operation: Any) -> dict[str, object]:
    try:
        return await operation(_forward_headers(_context_request(ctx)))
    except RestFailure as failure:
        raise ToolError(failure.error.model_dump_json()) from None
    except ValueError:
        raise ToolError(
            SafeError.for_code("INTERNAL_ERROR").model_dump_json()
        ) from None


def _defined_params(**params: object) -> dict[str, object]:
    return {name: value for name, value in params.items() if value is not None}


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


class _RequestLoggingMiddleware:
    """Bind only a valid correlation ID while an HTTP request is in flight."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        structlog.contextvars.clear_contextvars()
        correlation_id = _request_correlation_id(scope)
        if correlation_id is not None:
            structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        status_code: int | None = None

        async def send_with_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self._app(scope, receive, send_with_status)
            logger.info("http_request_completed", status_code=status_code)
        except Exception:
            logger.exception("http_request_failed")
            raise
        finally:
            structlog.contextvars.clear_contextvars()


def _request_correlation_id(scope: Scope) -> str | None:
    values = [
        value.decode("latin-1")
        for name, value in scope.get("headers", [])
        if name.lower() == CORRELATION_ID_HEADER.lower().encode()
    ]
    if len(values) != 1:
        return None
    try:
        return str(UUID(values[0]))
    except ValueError:
        return None


class _McpContractVersionMiddleware:
    """Publish the frozen MCP contract version on every MCP HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] != "/mcp":
            await self._app(scope, receive, send)
            return

        async def send_with_contract_version(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != MCP_CONTRACT_VERSION_HEADER.lower().encode()
                ]
                headers.append(
                    (
                        MCP_CONTRACT_VERSION_HEADER.lower().encode(),
                        MCP_CONTRACT_VERSION.encode(),
                    )
                )
                message["headers"] = headers
            await send(message)

        await self._app(scope, receive, send_with_contract_version)


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
