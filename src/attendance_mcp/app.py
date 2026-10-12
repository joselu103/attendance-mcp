"""ASGI composition for Attendance MCP's public, stateless HTTP surface."""

from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Annotated, Literal

import httpx
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from attendance_mcp.contracts import SafeError
from attendance_mcp.http_lifecycle import MCP_CONTRACT_VERSION, _McpHttpLifecycle
from attendance_mcp.rest_client import CrmtRestClient
from attendance_mcp.settings import Settings
from attendance_mcp.tool_policy import ToolCallPolicy

EmployeeId = Annotated[
    int, Field(description="Employee numeric identifier.", examples=[42])
]
OptionalEmployeeId = Annotated[
    int | None, Field(description="Employee numeric identifier.", examples=[42])
]
AttendanceEventId = Annotated[
    int, Field(description="Attendance event numeric identifier.", examples=[101])
]
StartDate = Annotated[
    date,
    Field(
        description="Inclusive Europe/Ljubljana calendar start date (YYYY-MM-DD).",
        examples=["2026-08-01"],
    ),
]
EndDate = Annotated[
    date,
    Field(
        description="Inclusive Europe/Ljubljana calendar end date (YYYY-MM-DD).",
        examples=["2026-08-31"],
    ),
]
Day = Annotated[
    date,
    Field(
        description="Europe/Ljubljana calendar day (YYYY-MM-DD).",
        examples=["2026-08-10"],
    ),
]
AsOf = Annotated[
    datetime | None,
    Field(
        description="Optional ISO 8601 timestamp for the detailed administrator view.",
        examples=["2026-08-10T08:30:00"],
    ),
]
Limit = Annotated[
    int,
    Field(
        description="Page size; defaults to 50. REST validates the allowed range.",
        examples=[25],
    ),
]
Offset = Annotated[
    int,
    Field(description="Zero-based page offset; defaults to 0.", examples=[0]),
]
Username = Annotated[
    str | None, Field(description="Employee username selector.", examples=["ana.novak"])
]
Email = Annotated[
    str | None,
    Field(description="Employee email selector.", examples=["ana.novak@example.com"]),
]
ActiveOnly = Annotated[
    bool,
    Field(description="When true, return only active punch types.", examples=[True]),
]
EmployeeIds = Annotated[
    list[int] | None,
    Field(
        description="Optional employee numeric identifiers to filter exceptions.",
        examples=[[42, 43]],
    ),
]
Statuses = Annotated[
    list[Literal["office", "remote", "customer_site", "break", "absence", "no_status"]]
    | None,
    Field(
        description="Optional unique status categories; omit for all recognized categories.",
        examples=[["office", "remote"]],
    ),
]


def _tool_metadata(
    *, english: dict[str, object], slovene: dict[str, object]
) -> dict[str, object]:
    """Expose bilingual, schema-valid argument examples with the MCP tool metadata."""
    return {
        "examples": [
            {"language": "en", "arguments": english},
            {"language": "sl", "arguments": slovene},
        ]
    }


def create_app(
    settings: Settings | None = None, *, client: httpx.AsyncClient | None = None
) -> Starlette:
    """Build the public health endpoint and Streamable HTTP MCP server.

    Args:
        settings: Runtime configuration. Loads from the environment when omitted.
        client: Attendance REST API client to use. A supplied client remains owned
            by the caller; the app closes a client it creates during shutdown.
    """
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
            "List the requesting employee's attendance events for explicit inclusive "
            "Europe/Ljubljana start and end dates with no maximum span; future "
            "end dates are allowed. Page the complete period using limit (default "
            "50, from 1 through 100), offset (default 0, nonnegative), and the "
            "returned next_offset. End must not precede start. Employee identity "
            "is resolved by the server."
        ),
        meta=_tool_metadata(
            english={"start_date": "2026-08-01", "end_date": "2026-08-31"},
            slovene={"start_date": "2026-08-01", "end_date": "2026-08-31"},
        ),
    )
    @tool_call_policy.instrument
    async def list_my_attendance_events(
        start_date: StartDate,
        end_date: EndDate,
        limit: Limit = 50,
        offset: Offset = 0,
        ctx: Context | None = None,
    ) -> dict[str, object]:
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
        meta=_tool_metadata(
            english={"limit": 25, "offset": 0},
            slovene={"limit": 25, "offset": 0},
        ),
    )
    @tool_call_policy.instrument
    async def list_employees(
        limit: Limit = 50, offset: Offset = 0, ctx: Context | None = None
    ) -> dict[str, object]:
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
        meta=_tool_metadata(english={"employee_id": 42}, slovene={"employee_id": 42}),
    )
    @tool_call_policy.instrument
    async def get_employee(
        employee_id: EmployeeId, ctx: Context | None = None
    ) -> dict[str, object]:
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.get_employee(
                headers=headers, employee_id=employee_id
            ),
        )

    @mcp.tool(
        name="resolve_employee",
        annotations={"readOnlyHint": True},
        description=(
            "Resolve one employee's directory-safe metadata by exactly one employee "
            "ID, username, or email. Authorization remains enforced by the server."
        ),
        meta=_tool_metadata(
            english={"username": "ana.novak"}, slovene={"username": "ana.novak"}
        ),
    )
    @tool_call_policy.instrument
    async def resolve_employee(
        employee_id: OptionalEmployeeId = None,
        username: Username = None,
        email: Email = None,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        selectors = _defined_params(
            employee_id=employee_id, username=username, email=email
        )
        if len(selectors) != 1:
            raise ToolError(SafeError.for_code("INVALID_ARGUMENT").model_dump_json())
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.resolve_employee(
                headers=headers, params=selectors
            ),
        )

    @mcp.tool(
        name="list_punch_types",
        annotations={"readOnlyHint": True},
        description=(
            "List configured punch types and their server-derived attendance locations. "
            "Locations are reference data, not caller-selected input."
        ),
        meta=_tool_metadata(
            english={"active_only": True}, slovene={"active_only": True}
        ),
    )
    @tool_call_policy.instrument
    async def list_punch_types(
        active_only: ActiveOnly = True, ctx: Context | None = None
    ) -> list[object]:
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
        meta=_tool_metadata(english={}, slovene={}),
    )
    @tool_call_policy.instrument
    async def list_locations(ctx: Context | None = None) -> list[object]:
        return await tool_call_policy.call(
            ctx, lambda headers: rest_client.list_locations(headers=headers)
        )

    @mcp.tool(
        name="list_attendance_events",
        annotations={"readOnlyHint": True},
        description=(
            "List one employee's attendance events for explicit inclusive "
            "Europe/Ljubljana start and end dates with no maximum span; future "
            "end dates are allowed. Page the complete period using limit (default "
            "50, from 1 through 100), offset (default 0, nonnegative), and the "
            "returned next_offset. End must not precede start. Available only "
            "to an administrator authorized by the REST API."
        ),
        meta=_tool_metadata(
            english={
                "employee_id": 42,
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
            },
            slovene={
                "employee_id": 42,
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
            },
        ),
    )
    @tool_call_policy.instrument
    async def list_attendance_events(
        employee_id: EmployeeId,
        start_date: StartDate,
        end_date: EndDate,
        limit: Limit = 50,
        offset: Offset = 0,
        ctx: Context | None = None,
    ) -> dict[str, object]:
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
        meta=_tool_metadata(
            english={"attendance_event_id": 101}, slovene={"attendance_event_id": 101}
        ),
    )
    @tool_call_policy.instrument
    async def get_attendance_event(
        attendance_event_id: AttendanceEventId, ctx: Context | None = None
    ) -> dict[str, object]:
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
        meta=_tool_metadata(
            english={"employee_id": 42, "day": "2026-08-10"},
            slovene={"employee_id": 42, "day": "2026-08-10"},
        ),
    )
    @tool_call_policy.instrument
    async def get_daily_attendance(
        employee_id: EmployeeId, day: Day, ctx: Context | None = None
    ) -> dict[str, object]:
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
        meta=_tool_metadata(
            english={
                "employee_id": 42,
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
            },
            slovene={
                "employee_id": 42,
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
            },
        ),
    )
    @tool_call_policy.instrument
    async def get_planned_work(
        employee_id: EmployeeId,
        start_date: StartDate,
        end_date: EndDate,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.get_planned_work(
                employee_id=employee_id,
                headers=headers,
                params={"start_date": start_date, "end_date": end_date},
            ),
        )

    @mcp.tool(
        name="get_current_work_status",
        description=(
            "List today's current workforce status categories at server-derived "
            "Europe/Ljubljana time for any mapped delegated employee. Results contain "
            "only first_name, last_name, status, and pagination; no event details."
        ),
        annotations={"readOnlyHint": True},
        meta=_tool_metadata(
            english={"statuses": ["office", "remote"], "limit": 25, "offset": 0},
            slovene={"statuses": ["office", "remote"], "limit": 25, "offset": 0},
        ),
    )
    @tool_call_policy.instrument
    async def get_current_work_status(
        statuses: Statuses = None,
        limit: Limit = 50,
        offset: Offset = 0,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        if statuses is not None and (
            not statuses or len(set(statuses)) != len(statuses)
        ):
            raise ToolError(SafeError.for_code("INVALID_ARGUMENT").model_dump_json())
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.get_current_work_status(
                headers=headers,
                params=_defined_params(status=statuses, limit=limit, offset=offset),
            ),
        )

    @mcp.tool(
        name="get_current_attendance",
        description=(
            "Administrator-only detailed current attendance states as of an "
            "optional timestamp with bounded pagination. Other employees should "
            "use get_current_work_status."
        ),
        annotations={"readOnlyHint": True},
        meta=_tool_metadata(
            english={
                "as_of": "2026-08-10T08:30:00",
                "statuses": ["office"],
                "limit": 25,
                "offset": 0,
            },
            slovene={
                "as_of": "2026-08-10T08:30:00",
                "statuses": ["office"],
                "limit": 25,
                "offset": 0,
            },
        ),
    )
    @tool_call_policy.instrument
    async def get_current_attendance(
        as_of: AsOf = None,
        statuses: Statuses = None,
        limit: Limit = 50,
        offset: Offset = 0,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        if statuses is not None and (
            not statuses or len(set(statuses)) != len(statuses)
        ):
            raise ToolError(SafeError.for_code("INVALID_ARGUMENT").model_dump_json())
        return await tool_call_policy.call(
            ctx,
            lambda headers: rest_client.get_current_attendance(
                headers=headers,
                params=_defined_params(
                    as_of=as_of.isoformat() if as_of else None,
                    status=statuses,
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
        meta=_tool_metadata(
            english={
                "employee_id": 42,
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
            },
            slovene={
                "employee_id": 42,
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
            },
        ),
    )
    @tool_call_policy.instrument
    async def get_employee_attendance_analysis(
        employee_id: EmployeeId,
        start_date: StartDate,
        end_date: EndDate,
        ctx: Context | None = None,
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
        meta=_tool_metadata(
            english={
                "employee_id": 42,
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
            },
            slovene={
                "employee_id": 42,
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
            },
        ),
    )
    @tool_call_policy.instrument
    async def get_employee_attendance_summary(
        employee_id: EmployeeId,
        start_date: StartDate,
        end_date: EndDate,
        ctx: Context | None = None,
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
        meta=_tool_metadata(
            english={
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
                "employee_ids": [42, 43],
                "limit": 25,
                "offset": 0,
            },
            slovene={
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
                "employee_ids": [42, 43],
                "limit": 25,
                "offset": 0,
            },
        ),
    )
    @tool_call_policy.instrument
    async def get_exceptions(
        start_date: StartDate,
        end_date: EndDate,
        employee_ids: EmployeeIds = None,
        limit: Limit = 50,
        offset: Offset = 0,
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
        meta=_tool_metadata(
            english={
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
                "limit": 25,
                "offset": 0,
            },
            slovene={
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
                "limit": 25,
                "offset": 0,
            },
        ),
    )
    @tool_call_policy.instrument
    async def get_organization_attendance_analysis(
        start_date: StartDate,
        end_date: EndDate,
        limit: Limit = 50,
        offset: Offset = 0,
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
    app.add_middleware(_McpHttpLifecycle)
    return app


async def _health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def _defined_params(**params: object) -> dict[str, object]:
    return {name: value for name, value in params.items() if value is not None}
