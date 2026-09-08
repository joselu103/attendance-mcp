import httpx
import pytest

from attendance_mcp.app import create_app
from attendance_mcp.settings import Settings

HEADERS = {
    "Authorization": "Bearer delegated-token",
    "X-Correlation-ID": "11111111-1111-1111-1111-111111111111",
}


@pytest.fixture
def upstream_requests() -> list[httpx.Request]:
    return []


@pytest.fixture
def app(upstream_requests: list[httpx.Request]):
    async def handler(request: httpx.Request) -> httpx.Response:
        upstream_requests.append(request)
        if request.url.path == "/internal/v1/mcp/session-admissions":
            return httpx.Response(
                204, headers={"X-Attendance-API-Contract-Version": "1.0.0"}
            )
        catalog_payloads: dict[str, object] = {
            "/api/v1/employees": {
                "items": [],
                "limit": 50,
                "offset": 0,
                "next_offset": None,
            },
            "/api/v1/employees/42": {
                "employee_id": 42,
                "first_name": "Ada",
                "last_name": "Lovelace",
                "username": "ada",
                "email": None,
                "active": 1,
            },
            "/api/v1/punch-types": [],
            "/api/v1/locations": [],
        }
        if request.url.path in catalog_payloads:
            return httpx.Response(
                200,
                json=catalog_payloads[request.url.path],
                headers={"X-Attendance-API-Contract-Version": "1.0.0"},
            )
        return httpx.Response(
            200,
            json={"items": [], "limit": 50, "offset": 0, "next_offset": None},
            headers={"X-Attendance-API-Contract-Version": "1.0.0"},
        )

    client = httpx.AsyncClient(
        base_url="https://crmt.example", transport=httpx.MockTransport(handler)
    )
    return create_app(Settings(crmt_base_url="https://crmt.example"), client=client)


@pytest.mark.asyncio
async def test_health_is_public_and_does_not_touch_crmt(app, upstream_requests) -> None:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        response = await client.get("/health")

    assert response.json() == {"status": "ok"}
    assert upstream_requests == []


@pytest.mark.asyncio
async def test_mcp_initialize_admits_session_and_tool_call_maps_to_crmt(
    app, upstream_requests
) -> None:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        initialized = await client.post(
            "/mcp",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        session_headers = {
            **HEADERS,
            "Mcp-Session-Id": initialized.headers["Mcp-Session-Id"],
        }
        await client.post(
            "/mcp",
            headers=session_headers,
            json={
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            },
        )
        response = await client.post(
            "/mcp",
            headers=session_headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "list_my_attendance_events",
                    "arguments": {
                        "start_date": "2026-08-01",
                        "end_date": "2026-08-02",
                    },
                },
            },
        )

    assert initialized.status_code == 200
    assert initialized.headers["X-Attendance-MCP-Contract-Version"] == "1.2.0"
    assert response.json()["result"]["structuredContent"] == {
        "items": [],
        "limit": 50,
        "offset": 0,
        "next_offset": None,
    }
    assert [request.url.path for request in upstream_requests] == [
        "/internal/v1/mcp/session-admissions",
        "/api/v1/me/attendance-events",
    ]
    assert upstream_requests[1].headers["authorization"] == HEADERS["Authorization"]
    assert (
        upstream_requests[1].headers["x-correlation-id"] == HEADERS["X-Correlation-ID"]
    )


@pytest.mark.asyncio
async def test_mcp_rejects_missing_or_malformed_forwarded_headers(app) -> None:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        missing = await client.post("/mcp", json={"method": "initialize"})
        malformed = await client.post(
            "/mcp",
            headers={
                "Authorization": "Bearer delegated-token",
                "X-Correlation-ID": "bad",
            },
            json={"method": "initialize"},
        )

    assert missing.status_code == 401
    assert missing.json()["code"] == "AUTHENTICATION_REQUIRED"
    assert malformed.status_code == 400
    assert malformed.json()["code"] == "CORRELATION_ID_INVALID"


@pytest.mark.asyncio
async def test_administrative_tools_map_legacy_arguments_to_crmt(
    app, upstream_requests
) -> None:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        initialized = await client.post(
            "/mcp",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        session_headers = {
            **HEADERS,
            "Mcp-Session-Id": initialized.headers["Mcp-Session-Id"],
        }
        await client.post(
            "/mcp",
            headers=session_headers,
            json={
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            },
        )
        catalog = await client.post(
            "/mcp",
            headers=session_headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        calls = [
            (
                "list_attendance_events",
                {
                    "employee_id": 42,
                    "start_date": "2026-08-10",
                    "end_date": "2026-08-12",
                    "limit": 20,
                    "offset": 3,
                },
            ),
            ("get_attendance_event", {"attendance_event_id": 100}),
            ("get_daily_attendance", {"employee_id": 42, "day": "2026-08-10"}),
            (
                "get_planned_work",
                {
                    "employee_id": 42,
                    "start_date": "2026-08-10",
                    "end_date": "2026-08-12",
                },
            ),
        ]
        responses = [
            await client.post(
                "/mcp",
                headers=session_headers,
                json={
                    "jsonrpc": "2.0",
                    "id": index + 3,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                },
            )
            for index, (name, arguments) in enumerate(calls)
        ]

    tools = {tool["name"]: tool for tool in catalog.json()["result"]["tools"]}
    assert {name for name, _ in calls}.issubset(tools)
    assert tools["list_my_attendance_events"]["description"] == (
        "List the requesting employee's attendance events over one through 31 "
        "inclusive calendar days. Employee identity is resolved by the server; "
        "limit must be from 1 through 100 and offset must be nonnegative."
    )
    assert tools["list_attendance_events"]["description"] == (
        "List one employee's attendance events in a bounded date range. This MVP "
        "tool is available only to the server-configured admin requester."
    )
    assert all(
        tools[name]["inputSchema"]["properties"][parameter]["format"] == "date"
        for name, parameter in (
            ("list_my_attendance_events", "start_date"),
            ("list_my_attendance_events", "end_date"),
            ("list_attendance_events", "start_date"),
            ("list_attendance_events", "end_date"),
            ("get_daily_attendance", "day"),
            ("get_planned_work", "start_date"),
            ("get_planned_work", "end_date"),
        )
    )
    assert catalog.headers["X-Attendance-MCP-Contract-Version"] == "1.2.0"
    assert all(
        response.json()["result"]["structuredContent"]["items"] == []
        for response in responses
    )
    requests = upstream_requests[1:]
    assert [(request.url.path, dict(request.url.params)) for request in requests] == [
        (
            "/api/v1/employees/42/attendance-events",
            {
                "start_date": "2026-08-10",
                "end_date": "2026-08-12",
                "limit": "20",
                "offset": "3",
            },
        ),
        ("/api/v1/attendance-events/100", {}),
        ("/api/v1/employees/42/daily-attendance", {"day": "2026-08-10"}),
        (
            "/api/v1/employees/42/planned-work",
            {"start_date": "2026-08-10", "end_date": "2026-08-12"},
        ),
    ]
    assert all(
        request.headers["authorization"] == HEADERS["Authorization"]
        for request in requests
    )
    assert all(
        request.headers["x-correlation-id"] == HEADERS["X-Correlation-ID"]
        for request in requests
    )


@pytest.mark.asyncio
async def test_catalog_tools_preserve_legacy_names_defaults_and_rest_mappings(
    app, upstream_requests
) -> None:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        initialized = await client.post(
            "/mcp",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        session_headers = {
            **HEADERS,
            "Mcp-Session-Id": initialized.headers["Mcp-Session-Id"],
        }
        await client.post(
            "/mcp",
            headers=session_headers,
            json={
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            },
        )
        listed = await client.post(
            "/mcp",
            headers=session_headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        tools = {tool["name"]: tool for tool in listed.json()["result"]["tools"]}
        responses = []
        for request_id, name, arguments in [
            (3, "list_employees", {"limit": 50, "offset": 0}),
            (4, "get_employee", {"employee_id": 42}),
            (5, "list_punch_types", {"active_only": False}),
            (6, "list_locations", {}),
        ]:
            responses.append(
                await client.post(
                    "/mcp",
                    headers=session_headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "method": "tools/call",
                        "params": {"name": name, "arguments": arguments},
                    },
                )
            )

    assert {
        "list_employees",
        "get_employee",
        "list_punch_types",
        "list_locations",
    } <= set(tools)
    assert (
        tools["list_employees"]["inputSchema"]["properties"]["limit"]["default"] == 50
    )
    assert (
        tools["list_punch_types"]["inputSchema"]["properties"]["active_only"]["default"]
        is True
    )
    assert all(
        response.json()["result"].get("isError") is not True for response in responses
    )
    assert [request.url.path for request in upstream_requests] == [
        "/internal/v1/mcp/session-admissions",
        "/api/v1/employees",
        "/api/v1/employees/42",
        "/api/v1/punch-types",
        "/api/v1/locations",
    ]
    assert dict(upstream_requests[1].url.params) == {"limit": "50", "offset": "0"}
    assert dict(upstream_requests[3].url.params) == {"active_only": "false"}


@pytest.mark.asyncio
async def test_catalog_includes_read_only_reporting_tools(app) -> None:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        initialized = await client.post(
            "/mcp",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            },
        )
        response = await client.post(
            "/mcp",
            headers={
                **HEADERS,
                "Mcp-Session-Id": initialized.headers["Mcp-Session-Id"],
            },
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )

    names = {tool["name"] for tool in response.json()["result"]["tools"]}
    assert len(names) == 14
    assert {
        "get_current_attendance",
        "get_employee_attendance_analysis",
        "get_employee_attendance_summary",
        "get_exceptions",
        "get_organization_attendance_analysis",
    } <= names
