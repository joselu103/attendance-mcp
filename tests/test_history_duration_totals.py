"""Transparent duration and summary forwarding through the MCP transport."""

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
async def test_history_duration_fields_are_forwarded_unchanged(name, selector, path):
    received = []
    payload = {
        "items": [
            {
                "attendance_event_id": 102,
                "employee_id": 42,
                "punch_type": None,
                "location": None,
                "checked_in_at": "2026-08-09T07:30:00+02:00",
                "checked_out_at": None,
                "note": None,
                "duration_minutes": None,
            },
            {
                "attendance_event_id": 100,
                "employee_id": 42,
                "punch_type": None,
                "location": None,
                "checked_in_at": "2026-08-09T12:00:00+02:00",
                "checked_out_at": "2026-08-11T12:00:00+02:00",
                "note": None,
                "duration_minutes": 2880,
            },
            {
                "attendance_event_id": 104,
                "employee_id": 42,
                "punch_type": None,
                "location": None,
                "checked_in_at": "2026-08-10T00:00:00+02:00",
                "checked_out_at": "2026-08-10T00:00:00+02:00",
                "note": None,
                "duration_minutes": 0,
            },
            {
                "attendance_event_id": 101,
                "employee_id": 42,
                "punch_type": None,
                "location": None,
                "checked_in_at": "2026-08-10T08:00:00+02:00",
                "checked_out_at": "2026-08-10T16:00:00+02:00",
                "note": None,
                "duration_minutes": 480,
            },
            {
                "attendance_event_id": 103,
                "employee_id": 42,
                "punch_type": None,
                "location": None,
                "checked_in_at": "2026-08-10T12:00:00+02:00",
                "checked_out_at": "2026-08-10T10:00:00+02:00",
                "note": None,
                "duration_minutes": None,
            },
        ],
        "limit": 50,
        "offset": 0,
        "next_offset": None,
        "summary": {
            "page_duration_minutes": 3360,
            "period_duration_minutes": 1920,
        },
    }

    async def handler(request):
        received.append(request)
        return httpx.Response(
            200,
            json=payload,
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
            assert tool.outputSchema == {
                "additionalProperties": True,
                "type": "object",
            }
            assert received == []

            result = await session.call_tool(
                name,
                selector | {"start_date": "2026-08-10", "end_date": "2026-08-10"},
            )

    assert result.isError is False
    assert result.structuredContent == payload
    assert json.loads(result.content[0].text) == payload
    assert len(received) == 1
    request = received[0]
    assert (request.method, request.url.path, dict(request.url.params)) == (
        "GET",
        path,
        {
            "start_date": "2026-08-10",
            "end_date": "2026-08-10",
            "limit": "50",
            "offset": "0",
        },
    )
    assert request.headers["authorization"] == HEADERS["Authorization"]
    assert request.headers["x-correlation-id"] == HEADERS["X-Correlation-ID"]
    assert "x-unapproved" not in request.headers


@pytest.mark.parametrize(("name", "selector", "path"), HISTORY_TOOLS)
@pytest.mark.asyncio
async def test_history_duration_summaries_preserve_live_pagination(
    name, selector, path
):
    received = []
    pages = [
        {
            "items": [
                {
                    "attendance_event_id": 101,
                    "employee_id": 42,
                    "punch_type": None,
                    "location": None,
                    "checked_in_at": "2026-08-10T08:00:00+02:00",
                    "checked_out_at": "2026-08-10T10:00:00+02:00",
                    "note": None,
                    "duration_minutes": 120,
                }
            ],
            "limit": 50,
            "offset": 0,
            "next_offset": 50,
            "summary": {
                "page_duration_minutes": 120,
                "period_duration_minutes": 4320,
            },
        },
        {
            "items": [
                {
                    "attendance_event_id": 102,
                    "employee_id": 42,
                    "punch_type": None,
                    "location": None,
                    "checked_in_at": "2026-08-09T07:30:00+02:00",
                    "checked_out_at": None,
                    "note": None,
                    "duration_minutes": None,
                }
            ],
            "limit": 100,
            "offset": 50,
            "next_offset": None,
            "summary": {
                "page_duration_minutes": 0,
                "period_duration_minutes": 4200,
            },
        },
        {
            "items": [],
            "limit": 1,
            "offset": 1000,
            "next_offset": None,
            "summary": {
                "page_duration_minutes": 0,
                "period_duration_minutes": 4200,
            },
        },
        {
            "items": [],
            "limit": 50,
            "offset": 0,
            "next_offset": None,
            "summary": {
                "page_duration_minutes": 0,
                "period_duration_minutes": 0,
            },
        },
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
            await session.list_tools()
            assert received == []
            calls = [
                ({"start_date": "2020-01-01", "end_date": "2099-12-31"}, pages[0]),
                (
                    {
                        "start_date": "2020-01-01",
                        "end_date": "2099-12-31",
                        "limit": 100,
                        "offset": 50,
                    },
                    pages[1],
                ),
                (
                    {
                        "start_date": "2020-01-01",
                        "end_date": "2099-12-31",
                        "limit": 1,
                        "offset": 1000,
                    },
                    pages[2],
                ),
                (
                    {"start_date": "2099-12-30", "end_date": "2099-12-31"},
                    pages[3],
                ),
            ]
            for index, (arguments, expected) in enumerate(calls, start=1):
                result = await session.call_tool(name, selector | arguments)
                assert result.isError is False
                assert result.structuredContent == expected
                assert json.loads(result.content[0].text) == expected
                assert len(received) == index

    expected_requests = [
        {
            "start_date": "2020-01-01",
            "end_date": "2099-12-31",
            "limit": "50",
            "offset": "0",
        },
        {
            "start_date": "2020-01-01",
            "end_date": "2099-12-31",
            "limit": "100",
            "offset": "50",
        },
        {
            "start_date": "2020-01-01",
            "end_date": "2099-12-31",
            "limit": "1",
            "offset": "1000",
        },
        {
            "start_date": "2099-12-30",
            "end_date": "2099-12-31",
            "limit": "50",
            "offset": "0",
        },
    ]
    assert len(received) == 4
    for request, params in zip(received, expected_requests, strict=True):
        assert (request.method, request.url.path, dict(request.url.params)) == (
            "GET",
            path,
            params,
        )
        assert request.headers["authorization"] == HEADERS["Authorization"]
        assert request.headers["x-correlation-id"] == HEADERS["X-Correlation-ID"]
        assert "x-unapproved" not in request.headers
