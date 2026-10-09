import httpx
import pytest

from attendance_mcp.app import create_app
from attendance_mcp.settings import Settings

HEADERS = {
    "Authorization": "Bearer delegated-token",
    "X-Correlation-ID": "11111111-1111-1111-1111-111111111111",
    "Accept": "application/json, text/event-stream",
}


@pytest.fixture
def upstream_requests() -> list[httpx.Request]:
    return []


@pytest.fixture
def app(upstream_requests: list[httpx.Request]):
    async def handler(request: httpx.Request) -> httpx.Response:
        upstream_requests.append(request)
        catalog_payloads: dict[str, object] = {
            "/api/v1/employees/resolve": {
                "employee_id": 42,
                "first_name": "Ada",
                "last_name": "Lovelace",
                "username": "ada",
                "email": None,
                "active": 1,
            },
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
async def test_mcp_initialize_without_upstream_call_and_tool_call_maps_to_crmt(
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
        session_headers = HEADERS
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
    assert initialized.headers["X-Attendance-MCP-Contract-Version"] == "1.3.0"
    assert response.json()["result"]["structuredContent"] == {
        "items": [],
        "limit": 50,
        "offset": 0,
        "next_offset": None,
    }
    assert [request.url.path for request in upstream_requests] == [
        "/api/v1/me/attendance-events"
    ]
    assert upstream_requests[0].headers["authorization"] == HEADERS["Authorization"]
    assert (
        upstream_requests[0].headers["x-correlation-id"] == HEADERS["X-Correlation-ID"]
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
    assert missing.headers["X-Attendance-MCP-Contract-Version"] == "1.3.0"
    assert malformed.status_code == 400
    assert malformed.json()["code"] == "CORRELATION_ID_INVALID"
    assert malformed.headers["X-Attendance-MCP-Contract-Version"] == "1.3.0"


@pytest.mark.asyncio
async def test_mcp_rejects_duplicate_correlation_and_oversized_bodies_safely(
    app, upstream_requests, monkeypatch
) -> None:
    events: list[tuple[str, str, dict[str, object]]] = []

    class CapturingLogger:
        def info(self, event: str, **values: object) -> None:
            events.append(("info", event, values))

        def warning(self, event: str, **values: object) -> None:
            events.append(("warning", event, values))

        def error(self, event: str, **values: object) -> None:
            events.append(("error", event, values))

        def exception(self, event: str, **values: object) -> None:
            events.append(("exception", event, values))

    monkeypatch.setattr("attendance_mcp.http_lifecycle.logger", CapturingLogger())
    duplicate_correlation = "33333333-3333-3333-3333-333333333333"
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        duplicate = await client.post(
            "/mcp",
            headers=[
                ("Authorization", "Bearer delegated-token"),
                ("X-Correlation-ID", duplicate_correlation),
                ("X-Correlation-ID", duplicate_correlation),
            ],
            json={"method": "initialize"},
        )
        oversized = await client.post("/mcp", headers=HEADERS, content=b"x" * 65_537)

    assert duplicate.status_code == 400
    assert duplicate.json()["code"] == "CORRELATION_ID_INVALID"
    assert duplicate.headers["X-Attendance-MCP-Contract-Version"] == "1.3.0"
    assert oversized.status_code == 400
    assert oversized.json()["code"] == "INVALID_ARGUMENT"
    assert oversized.headers["X-Attendance-MCP-Contract-Version"] == "1.3.0"
    assert upstream_requests == []
    received = [
        values for _, event, values in events if event == "http_request_received"
    ]
    assert received[0]["trace_id"] != duplicate_correlation


@pytest.mark.asyncio
async def test_catalog_admits_every_read_only_tool_for_the_teams_bot(
    app,
) -> None:
    """Exercise the SDK server catalog against the bot's safe admission contract."""
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        await client.post(
            "/mcp",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "teams-bot-compatible-test", "version": "1"},
                },
            },
        )
        catalog = await client.post(
            "/mcp",
            headers=HEADERS,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )

    tools = catalog.json()["result"]["tools"]
    requester = next(
        tool for tool in tools if tool["name"] == "list_my_attendance_events"
    )
    assert len(tools) == 16
    assert all(
        isinstance(tool["description"], str) and len(tool["description"]) <= 4_096
        for tool in tools
    )
    assert all(tool["annotations"] == {"readOnlyHint": True} for tool in tools)
    assert requester["inputSchema"]["type"] == "object"
    assert requester["inputSchema"]["required"] == ["start_date", "end_date"]
    assert set(requester["inputSchema"]["properties"]) == {
        "start_date",
        "end_date",
        "limit",
        "offset",
    }


@pytest.mark.asyncio
async def test_request_lifecycle_records_only_safe_header_outcomes(
    monkeypatch,
) -> None:
    events: list[tuple[str, str, dict[str, object]]] = []

    class CapturingLogger:
        def info(self, event: str, **values: object) -> None:
            events.append(("info", event, values))

        def warning(self, event: str, **values: object) -> None:
            events.append(("warning", event, values))

        def error(self, event: str, **values: object) -> None:
            events.append(("error", event, values))

        def exception(self, event: str, **values: object) -> None:
            events.append(("exception", event, values))

    monkeypatch.setattr("attendance_mcp.http_lifecycle.logger", CapturingLogger())

    async def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("initialize must not call the Attendance REST API")

    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        },
    }
    async with httpx.AsyncClient(
        base_url="https://crmt.example", transport=httpx.MockTransport(handler)
    ) as upstream:
        app = create_app(
            Settings(crmt_base_url="https://crmt.example"), client=upstream
        )
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
            ) as client,
        ):
            await client.post("/mcp", json=initialize)
            admitted = await client.post("/mcp", headers=HEADERS, json=initialize)

    assert admitted.status_code == 200
    outcomes = [
        values for _, event, values in events if event != "http_request_received"
    ]
    assert outcomes[0] | {
        "duration_ms": outcomes[0]["duration_ms"],
        "trace_id": outcomes[0]["trace_id"],
    } == {
        "route": "/mcp",
        "status_code": 401,
        "result_state": "header_rejected",
        "header_admission": "rejected",
        "safe_error_code": "AUTHENTICATION_REQUIRED",
        "duration_ms": outcomes[0]["duration_ms"],
        "trace_id": outcomes[0]["trace_id"],
    }
    assert outcomes[1] | {"duration_ms": outcomes[1]["duration_ms"]} == {
        "route": "/mcp",
        "status_code": 200,
        "result_state": "completed",
        "header_admission": "accepted",
        "duration_ms": outcomes[1]["duration_ms"],
        "trace_id": HEADERS["X-Correlation-ID"],
    }
    assert [
        level for level, event, _ in events if event != "http_request_received"
    ] == [
        "warning",
        "info",
    ]


@pytest.mark.asyncio
async def test_administrative_tools_map_arguments_to_attendance_rest_api(
    app, upstream_requests
) -> None:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        await client.post(
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
        session_headers = HEADERS
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
    assert catalog.headers["X-Attendance-MCP-Contract-Version"] == "1.3.0"
    assert all(
        response.json()["result"]["structuredContent"]["items"] == []
        for response in responses
    )
    requests = upstream_requests
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
async def test_catalog_tools_preserve_names_defaults_and_rest_mappings(
    app, upstream_requests
) -> None:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        await client.post(
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
        session_headers = HEADERS
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
        "/api/v1/employees",
        "/api/v1/employees/42",
        "/api/v1/punch-types",
        "/api/v1/locations",
    ]
    assert dict(upstream_requests[0].url.params) == {"limit": "50", "offset": "0"}
    assert dict(upstream_requests[2].url.params) == {"active_only": "false"}


@pytest.mark.asyncio
async def test_catalog_includes_read_only_reporting_tools(app) -> None:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        await client.post(
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
            headers=HEADERS,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )

    names = {tool["name"] for tool in response.json()["result"]["tools"]}
    assert len(names) == 16
    assert {
        "get_current_work_status",
        "get_current_attendance",
        "get_employee_attendance_analysis",
        "get_employee_attendance_summary",
        "get_exceptions",
        "get_organization_attendance_analysis",
    } <= names


@pytest.mark.asyncio
async def test_resolve_employee_requires_exactly_one_selector_and_maps_safe_errors(
    app, upstream_requests
) -> None:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        await client.post(
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
        await client.post(
            "/mcp",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            },
        )
        catalog = await client.post(
            "/mcp",
            headers=HEADERS,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        valid = await client.post(
            "/mcp",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "resolve_employee",
                    "arguments": {"username": "ada"},
                },
            },
        )
        missing = await client.post(
            "/mcp",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "resolve_employee", "arguments": {}},
            },
        )
        multiple = await client.post(
            "/mcp",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "resolve_employee",
                    "arguments": {"employee_id": 42, "username": "ada"},
                },
            },
        )

    tool = {item["name"]: item for item in catalog.json()["result"]["tools"]}[
        "resolve_employee"
    ]
    assert tool["annotations"] == {"readOnlyHint": True}
    assert set(tool["inputSchema"]["properties"]) == {
        "employee_id",
        "username",
        "email",
    }
    assert tool["inputSchema"].get("required", []) == []
    assert valid.json()["result"].get("isError") is not True
    assert all(
        '"code":"INVALID_ARGUMENT"' in response.json()["result"]["content"][0]["text"]
        for response in (missing, multiple)
    )
    assert [request.url.path for request in upstream_requests] == [
        "/api/v1/employees/resolve",
    ]
    assert dict(upstream_requests[0].url.params) == {"username": "ada"}


@pytest.mark.asyncio
async def test_reporting_tools_map_arguments_to_attendance_rest_api(
    app, upstream_requests
) -> None:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        await client.post(
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
        await client.post(
            "/mcp",
            headers=HEADERS,
            json={
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            },
        )
        calls = [
            (
                "get_current_work_status",
                {"statuses": ["office", "remote"], "limit": 20, "offset": 3},
            ),
            (
                "get_current_attendance",
                {
                    "as_of": "2026-08-10T08:30:00",
                    "statuses": ["office", "remote"],
                    "limit": 20,
                    "offset": 3,
                },
            ),
            (
                "get_employee_attendance_analysis",
                {
                    "employee_id": 42,
                    "start_date": "2026-08-10",
                    "end_date": "2026-08-12",
                },
            ),
            (
                "get_employee_attendance_summary",
                {
                    "employee_id": 42,
                    "start_date": "2026-08-10",
                    "end_date": "2026-08-12",
                },
            ),
            (
                "get_exceptions",
                {
                    "start_date": "2026-08-10",
                    "end_date": "2026-08-12",
                    "employee_ids": [42, 43],
                    "limit": 20,
                    "offset": 3,
                },
            ),
            (
                "get_organization_attendance_analysis",
                {
                    "start_date": "2026-08-10",
                    "end_date": "2026-08-12",
                    "limit": 20,
                    "offset": 3,
                },
            ),
        ]
        responses = [
            await client.post(
                "/mcp",
                headers=HEADERS,
                json={
                    "jsonrpc": "2.0",
                    "id": index + 2,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                },
            )
            for index, (name, arguments) in enumerate(calls)
        ]

    assert all(
        response.json()["result"].get("isError") is not True for response in responses
    )
    requests = upstream_requests
    assert [
        (request.url.path, list(request.url.params.multi_items()))
        for request in requests
    ] == [
        (
            "/api/v1/attendance/current-status",
            [
                ("status", "office"),
                ("status", "remote"),
                ("limit", "20"),
                ("offset", "3"),
            ],
        ),
        (
            "/api/v1/attendance/current",
            [
                ("as_of", "2026-08-10T08:30:00"),
                ("status", "office"),
                ("status", "remote"),
                ("limit", "20"),
                ("offset", "3"),
            ],
        ),
        (
            "/api/v1/employees/42/attendance-analysis",
            [("start_date", "2026-08-10"), ("end_date", "2026-08-12")],
        ),
        (
            "/api/v1/employees/42/attendance-summary",
            [("start_date", "2026-08-10"), ("end_date", "2026-08-12")],
        ),
        (
            "/api/v1/attendance/exceptions",
            [
                ("start_date", "2026-08-10"),
                ("end_date", "2026-08-12"),
                ("employee_ids", "42"),
                ("employee_ids", "43"),
                ("limit", "20"),
                ("offset", "3"),
            ],
        ),
        (
            "/api/v1/attendance/organization-analysis",
            [
                ("start_date", "2026-08-10"),
                ("end_date", "2026-08-12"),
                ("limit", "20"),
                ("offset", "3"),
            ],
        ),
    ]
    assert all(
        request.headers["authorization"] == HEADERS["Authorization"]
        and request.headers["x-correlation-id"] == HEADERS["X-Correlation-ID"]
        for request in requests
    )


@pytest.mark.asyncio
async def test_current_work_status_catalog_and_invalid_filters(
    app, upstream_requests
) -> None:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        listed = await client.post(
            "/mcp",
            headers=HEADERS,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )
        responses = [
            await client.post(
                "/mcp",
                headers=HEADERS,
                json={
                    "jsonrpc": "2.0",
                    "id": identifier,
                    "method": "tools/call",
                    "params": {
                        "name": "get_current_work_status",
                        "arguments": {"statuses": statuses},
                    },
                },
            )
            for identifier, statuses in (
                (2, []),
                (3, ["office", "office"]),
                (4, ["unknown"]),
            )
        ]

    tools = {tool["name"]: tool for tool in listed.json()["result"]["tools"]}
    pilot_tool = tools["get_current_work_status"]
    assert pilot_tool["annotations"] == {"readOnlyHint": True}
    assert set(pilot_tool["inputSchema"]["properties"]) == {
        "statuses",
        "limit",
        "offset",
    }
    assert pilot_tool["inputSchema"].get("required") is None
    assert "unknown" not in str(pilot_tool["inputSchema"])
    assert "administrator" in tools["get_current_attendance"]["description"].lower()
    assert all(response.json()["result"]["isError"] for response in responses)
    assert upstream_requests == []


@pytest.mark.asyncio
async def test_current_work_status_forwards_only_allowed_headers_and_legacy_forbidden() -> (
    None
):
    received: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        received.append(request)
        if request.url.path == "/api/v1/attendance/current":
            return httpx.Response(
                403,
                json={
                    "code": "FORBIDDEN",
                    "message": "You do not have permission to do that.",
                },
                headers={"X-Attendance-API-Contract-Version": "1.0.0"},
            )
        return httpx.Response(
            200,
            json={"items": [], "limit": 50, "offset": 0, "next_offset": None},
            headers={"X-Attendance-API-Contract-Version": "1.0.0"},
        )

    async with httpx.AsyncClient(
        base_url="https://crmt.example", transport=httpx.MockTransport(handler)
    ) as rest_http:
        app = create_app(
            Settings(crmt_base_url="https://crmt.example"), client=rest_http
        )
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="https://mcp.example",
            ) as client,
        ):
            responses = [
                await client.post(
                    "/mcp",
                    headers=HEADERS | {"X-Unapproved": "discard-me"},
                    json={
                        "jsonrpc": "2.0",
                        "id": identifier,
                        "method": "tools/call",
                        "params": {"name": name, "arguments": {}},
                    },
                )
                for identifier, name in (
                    (1, "get_current_work_status"),
                    (2, "get_current_attendance"),
                )
            ]

    assert responses[0].json()["result"]["structuredContent"] == {
        "items": [],
        "limit": 50,
        "offset": 0,
        "next_offset": None,
    }
    assert '"code":"FORBIDDEN"' in responses[1].json()["result"]["content"][0]["text"]
    assert [request.url.path for request in received] == [
        "/api/v1/attendance/current-status",
        "/api/v1/attendance/current",
    ]
    assert all(
        request.headers["authorization"] == HEADERS["Authorization"]
        and request.headers["x-correlation-id"] == HEADERS["X-Correlation-ID"]
        and "x-unapproved" not in request.headers
        for request in received
    )


@pytest.mark.asyncio
async def test_current_attendance_schema_uses_statuses_and_excludes_unknown(
    app,
) -> None:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        await client.post(
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
        listed = await client.post(
            "/mcp",
            headers=HEADERS,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )

    tool = {item["name"]: item for item in listed.json()["result"]["tools"]}[
        "get_current_attendance"
    ]
    schema = tool["inputSchema"]
    assert "status" not in schema["properties"]
    assert (
        "unknown" not in schema["properties"]["statuses"]["anyOf"][0]["items"]["enum"]
    )


@pytest.mark.asyncio
async def test_current_attendance_rejects_empty_and_duplicate_statuses(
    app, upstream_requests
) -> None:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        await client.post(
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
        responses = [
            await client.post(
                "/mcp",
                headers=HEADERS,
                json={
                    "jsonrpc": "2.0",
                    "id": identifier,
                    "method": "tools/call",
                    "params": {
                        "name": "get_current_attendance",
                        "arguments": {"statuses": statuses},
                    },
                },
            )
            for identifier, statuses in ((2, []), (3, ["office", "office"]))
        ]

    assert all(
        '"code":"INVALID_ARGUMENT"' in response.json()["result"]["content"][0]["text"]
        for response in responses
    )
    assert upstream_requests == []


@pytest.mark.asyncio
async def test_tool_call_logs_safe_mcp_and_crmt_lifecycles_end_to_end(
    app, monkeypatch
) -> None:
    mcp_events: list[tuple[str, dict[str, object]]] = []
    crmt_events: list[tuple[str, dict[str, object]]] = []

    class CapturingLogger:
        def __init__(self, events: list[tuple[str, dict[str, object]]]) -> None:
            self._events = events

        def info(self, event: str, **values: object) -> None:
            self._events.append((event, values))

        def warning(self, event: str, **values: object) -> None:
            self._events.append((event, values))

    monkeypatch.setattr(
        "attendance_mcp.tool_policy.logger", CapturingLogger(mcp_events)
    )
    monkeypatch.setattr(
        "attendance_mcp.rest_client.logger", CapturingLogger(crmt_events)
    )
    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        },
    }
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
        ) as client,
    ):
        await client.post("/mcp", headers=HEADERS, json=initialize)
        session_headers = HEADERS
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

    assert response.status_code == 200
    tool_events = [event for event in mcp_events if event[0].startswith("mcp_tool_")]
    assert [event for event, _ in tool_events] == [
        "mcp_tool_operation_started",
        "mcp_tool_operation_succeeded",
    ]
    assert all(
        values["handler"] == "list_my_attendance_events" for _, values in tool_events
    )
    assert all(
        values["input_shape"]
        == ("start_date:date", "end_date:date", "limit:int", "offset:int")
        for _, values in tool_events
    )
    operation_events = [
        event
        for event in crmt_events
        if event[0].startswith("crmt_operation_")
        and event[1].get("operation") == "list_my_attendance_events"
    ]
    assert [event for event, _ in operation_events] == [
        "crmt_operation_started",
        "crmt_operation_succeeded",
    ]
    assert all(
        values["operation"] == "list_my_attendance_events"
        and values["route_template"] == "/api/v1/me/attendance-events"
        for _, values in operation_events
    )
