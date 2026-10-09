"""History compatibility at the public MCP transport and HTTPX REST seam."""

import json

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from attendance_mcp.app import create_app
from attendance_mcp.settings import Settings

HEADERS = {
    "Authorization": "Bearer synthetic-test-token",
    "X-Correlation-ID": "11111111-1111-1111-1111-111111111111",
    "X-Unapproved": "discard-me",
}
HISTORY_TOOLS = [
    ("list_my_attendance_events", {}, "/api/v1/me/attendance-events"),
    (
        "list_attendance_events",
        {"employee_id": 42},
        "/api/v1/employees/42/attendance-events",
    ),
]


@pytest.mark.parametrize(("name", "selector", "path"), HISTORY_TOOLS)
@pytest.mark.asyncio
async def test_history_full_period_single_request_and_live_pages(name, selector, path):
    received = []
    pages = [
        {
            "items": [{"attendance_event_id": 101}],
            "limit": 50,
            "offset": 0,
            "next_offset": 50,
        },
        {
            "items": [{"attendance_event_id": 102}],
            "limit": 100,
            "offset": 50,
            "next_offset": None,
        },
        {"items": [], "limit": 1, "offset": 1000, "next_offset": None},
    ]

    async def handler(request):
        received.append(request)
        return httpx.Response(
            200,
            json=pages[len(received) - 1],
            headers={"X-Attendance-API-Contract-Version": "1.0.0"},
        )

    async with httpx.AsyncClient(
        base_url="https://rest.example", transport=httpx.MockTransport(handler)
    ) as rest_http:
        app = create_app(
            Settings(crmt_base_url="https://rest.example"), client=rest_http
        )

        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), headers=HEADERS
            ) as mcp_http,
            streamable_http_client("https://mcp.example/mcp", http_client=mcp_http) as (
                read,
                write,
                _,
            ),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            catalog = await session.list_tools()
            tool = next(tool for tool in catalog.tools if tool.name == name)
            schema = tool.inputSchema
            assert set(schema["properties"]) == set(selector) | {
                "start_date",
                "end_date",
                "limit",
                "offset",
            }
            assert set(schema["required"]) == set(selector) | {
                "start_date",
                "end_date",
            }
            assert schema["properties"]["limit"]["default"] == 50
            assert schema["properties"]["offset"]["default"] == 0
            assert tool.annotations.readOnlyHint is True
            assert received == []
            for index, pagination in enumerate(
                ({}, {"limit": 100, "offset": 50}, {"limit": 1, "offset": 1000})
            ):
                result = await session.call_tool(
                    name,
                    selector
                    | {
                        "start_date": "2020-01-01",
                        "end_date": "2099-12-31",
                    }
                    | pagination,
                )
                assert result.isError is False
                assert result.structuredContent == pages[index]
                assert json.loads(result.content[0].text) == pages[index]
                assert len(received) == index + 1

    assert [
        (request.method, request.url.path, dict(request.url.params))
        for request in received
    ] == [
        (
            "GET",
            path,
            {
                "start_date": "2020-01-01",
                "end_date": "2099-12-31",
                "limit": "50",
                "offset": "0",
            },
        ),
        (
            "GET",
            path,
            {
                "start_date": "2020-01-01",
                "end_date": "2099-12-31",
                "limit": "100",
                "offset": "50",
            },
        ),
        (
            "GET",
            path,
            {
                "start_date": "2020-01-01",
                "end_date": "2099-12-31",
                "limit": "1",
                "offset": "1000",
            },
        ),
    ]
    for request in received:
        assert request.headers["authorization"] == HEADERS["Authorization"]
        assert request.headers["x-correlation-id"] == HEADERS["X-Correlation-ID"]
        assert "x-unapproved" not in request.headers


@pytest.mark.parametrize(("name", "selector", "path"), HISTORY_TOOLS)
@pytest.mark.parametrize(
    ("arguments", "status", "payload", "expected"),
    [
        (
            {"start_date": "2099-12-31", "end_date": "2020-01-01"},
            400,
            {
                "code": "INVALID_ARGUMENT",
                "message": "Check the attendance date range and pagination values and try again.",
            },
            "INVALID_ARGUMENT",
        ),
        (
            {
                "start_date": "2020-01-01",
                "end_date": "2099-12-31",
                "limit": 101,
                "offset": -1,
            },
            400,
            {
                "code": "INVALID_ARGUMENT",
                "message": "Check the attendance date range and pagination values and try again.",
            },
            "INVALID_ARGUMENT",
        ),
        (
            {"start_date": "2020-01-01", "end_date": "2099-12-31"},
            403,
            {"code": "FORBIDDEN", "message": "You do not have permission to do that."},
            "FORBIDDEN",
        ),
        (
            {"start_date": "2020-01-01", "end_date": "2099-12-31"},
            500,
            {"code": "INTERNAL_ERROR", "message": "synthetic-private-diagnostic"},
            "BACKEND_UNAVAILABLE",
        ),
    ],
    ids=["reversed-dates", "invalid-pagination", "authorization", "unsafe-error"],
)
@pytest.mark.asyncio
async def test_history_preserves_rest_validation_authority_and_safe_errors(
    name, selector, path, arguments, status, payload, expected
):
    received = []

    async def handler(request):
        received.append(request)
        return httpx.Response(
            status, json=payload, headers={"X-Attendance-API-Contract-Version": "1.0.0"}
        )

    async with httpx.AsyncClient(
        base_url="https://rest.example", transport=httpx.MockTransport(handler)
    ) as rest_http:
        app = create_app(
            Settings(crmt_base_url="https://rest.example"), client=rest_http
        )
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), headers=HEADERS
            ) as mcp_http,
            streamable_http_client("https://mcp.example/mcp", http_client=mcp_http) as (
                read,
                write,
                _,
            ),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            result = await session.call_tool(name, selector | arguments)

    assert result.isError is True
    error = json.loads(result.content[0].text)
    assert error["code"] == expected
    assert set(error) == {"code", "message"}
    assert "synthetic-private-diagnostic" not in result.model_dump_json()
    assert len(received) == 1
    assert received[0].url.path == path
    assert dict(received[0].url.params) == {
        "start_date": arguments["start_date"],
        "end_date": arguments["end_date"],
        "limit": str(arguments.get("limit", 50)),
        "offset": str(arguments.get("offset", 0)),
    }
