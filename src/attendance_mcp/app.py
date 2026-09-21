"""ASGI composition for Attendance MCP's public, stateless HTTP surface."""

from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Literal

import httpx
from fastmcp import Context, FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from attendance_mcp.http_lifecycle import MCP_CONTRACT_VERSION, _McpHttpLifecycle
from attendance_mcp.rest_client import CrmtRestClient
from attendance_mcp.settings import Settings
from attendance_mcp.tool_policy import ToolCallPolicy


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
    tool_call_policy = ToolCallPolicy()

    @mcp.tool(
        name="list_my_attendance_events",
        annotations={"readOnlyHint": True},
        description=(
            "List the requesting employee's attendance events over one through 31 "
            "inclusive calendar days. Employee identity is resolved by the server; "
            "limit must be from 1 through 100 and offset must be nonnegative."
        ),
    )
    @tool_call_policy.instrument
    async def list_my_attendance_events(
        start_date: date,
        end_date: date,
        limit: int = 50,
        offset: int = 0,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        """Map the frozen legacy MCP request directly to its CRMT REST operation."""
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.list_my_attendance_events(
                headers=headers,
                params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit,
                    "offset": offset,
                },
            ),
        )

    @mcp.tool(
        name="list_employees",
        annotations={"readOnlyHint": True},
        description=(
            "List active employees for attendance lookups. Inactive employee "
            "records are excluded. Results use bounded limit/offset pagination."
        ),
    )
    @tool_call_policy.instrument
    async def list_employees(
        limit: int = 50, offset: int = 0, ctx: Context | None = None
    ) -> dict[str, object]:
        """Map the legacy active-employee page to CRMT REST."""
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.list_employees(
                headers=headers,
                params={"limit": limit, "offset": offset},
            ),
        )

    @mcp.tool(
        name="get_employee",
        annotations={"readOnlyHint": True},
        description="Return one employee's directory-safe metadata by ID.",
    )
    @tool_call_policy.instrument
    async def get_employee(
        employee_id: int, ctx: Context | None = None
    ) -> dict[str, object]:
        """Map the legacy employee lookup to CRMT REST."""
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.get_employee(
                headers=headers, employee_id=employee_id
            ),
        )

    @mcp.tool(
        name="list_punch_types",
        annotations={"readOnlyHint": True},
        description=(
            "List configured punch types and their server-derived attendance locations. "
            "Locations are reference data, not caller-selected input."
        ),
    )
    @tool_call_policy.instrument
    async def list_punch_types(
        active_only: bool = True, ctx: Context | None = None
    ) -> list[object]:
        """Map the legacy punch-type lookup to CRMT REST."""
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.list_punch_types(
                headers=headers, active_only=active_only
            ),
        )

    @mcp.tool(
        name="list_locations",
        annotations={"readOnlyHint": True},
        description="List attendance-event location reference data.",
    )
    @tool_call_policy.instrument
    async def list_locations(ctx: Context | None = None) -> list[object]:
        """Map the legacy location lookup to CRMT REST."""
        return await tool_call_policy.call(
            ctx, lambda headers: rest_client.list_locations(headers=headers)
        )

    @mcp.tool(
        name="list_attendance_events",
        annotations={"readOnlyHint": True},
        description=(
            "List one employee's attendance events in a bounded date range. "
            "This MVP tool is available only to the server-configured admin requester."
        ),
    )
    @tool_call_policy.instrument
    async def list_attendance_events(
        employee_id: int,
        start_date: date,
        end_date: date,
        limit: int = 50,
        offset: int = 0,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        """Map the legacy administrator event list directly to CRMT REST."""
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.list_attendance_events(
                employee_id=employee_id,
                headers=headers,
                params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit,
                    "offset": offset,
                },
            ),
        )

    @mcp.tool(
        name="get_attendance_event",
        annotations={"readOnlyHint": True},
        description="Return one attendance event, including recorded audit metadata.",
    )
    @tool_call_policy.instrument
    async def get_attendance_event(
        attendance_event_id: int, ctx: Context | None = None
    ) -> dict[str, object]:
        """Map the legacy administrator event detail directly to CRMT REST."""
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.get_attendance_event(
                attendance_event_id=attendance_event_id,
                headers=headers,
            ),
        )

    @mcp.tool(
        name="get_daily_attendance",
        annotations={"readOnlyHint": True},
        description=(
            "Return one employee's local-calendar daily attendance events and "
            "calculated planned-versus-logged outcome."
        ),
    )
    @tool_call_policy.instrument
    async def get_daily_attendance(
        employee_id: int, day: date, ctx: Context | None = None
    ) -> dict[str, object]:
        """Map the legacy daily administrator view directly to CRMT REST."""
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.get_daily_attendance(
                employee_id=employee_id,
                headers=headers,
                params={"day": day},
            ),
        )

    @mcp.tool(
        name="get_planned_work",
        annotations={"readOnlyHint": True},
        description=(
            "Return recorded daily planned-work hours for one employee over an "
            "inclusive Europe/Ljubljana range of up to 31 calendar days."
        ),
    )
    @tool_call_policy.instrument
    async def get_planned_work(
        employee_id: int,
        start_date: date,
        end_date: date,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        """Map the legacy planned-work administrator view directly to CRMT REST."""
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.get_planned_work(
                employee_id=employee_id,
                headers=headers,
                params={"start_date": start_date, "end_date": end_date},
            ),
        )

    @mcp.tool(
        name="get_current_attendance",
        description=(
            "List current attendance states as of an optional timestamp with bounded "
            "pagination."
        ),
        annotations={"readOnlyHint": True},
    )
    @tool_call_policy.instrument
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
        return await tool_call_policy.call(
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
        name="get_employee_attendance_analysis",
        description=(
            "Return attendance analysis for one employee over an inclusive date range."
        ),
        annotations={"readOnlyHint": True},
    )
    @tool_call_policy.instrument
    async def get_employee_attendance_analysis(
        employee_id: int, start_date: date, end_date: date, ctx: Context | None = None
    ) -> dict[str, object]:
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.get_employee_attendance_analysis(
                employee_id=employee_id,
                headers=headers,
                params={"start_date": start_date, "end_date": end_date},
            ),
        )

    @mcp.tool(
        name="get_employee_attendance_summary",
        description=(
            "Return an attendance summary for one employee over an inclusive date range."
        ),
        annotations={"readOnlyHint": True},
    )
    @tool_call_policy.instrument
    async def get_employee_attendance_summary(
        employee_id: int, start_date: date, end_date: date, ctx: Context | None = None
    ) -> dict[str, object]:
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.get_employee_attendance_summary(
                employee_id=employee_id,
                headers=headers,
                params={"start_date": start_date, "end_date": end_date},
            ),
        )

    @mcp.tool(
        name="get_exceptions",
        description=(
            "List attendance exceptions over an inclusive date range with bounded "
            "pagination."
        ),
        annotations={"readOnlyHint": True},
    )
    @tool_call_policy.instrument
    async def get_exceptions(
        start_date: date,
        end_date: date,
        employee_ids: list[int] | None = None,
        limit: int = 50,
        offset: int = 0,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        return await tool_call_policy.call(
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
        name="get_organization_attendance_analysis",
        description=(
            "Return organization attendance analysis over an inclusive date range "
            "with bounded pagination."
        ),
        annotations={"readOnlyHint": True},
    )
    @tool_call_policy.instrument
    async def get_organization_attendance_analysis(
        start_date: date,
        end_date: date,
        limit: int = 50,
        offset: int = 0,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        return await tool_call_policy.call(
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

    mcp_app = mcp.http_app(
        path="/mcp",
        transport="streamable-http",
        json_response=True,
        stateless_http=True,
    )

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
    app.add_middleware(_McpHttpLifecycle, rest_client=rest_client)
    return app


async def _health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def _defined_params(**params: object) -> dict[str, object]:
    return {name: value for name, value in params.items() if value is not None}
