import httpx
import pytest

from attendance_mcp.rest_client import CrmtRestClient, RestFailure, _operation_metadata


@pytest.mark.parametrize(
    ("path", "operation", "route_template"),
    [
        (
            "/api/v1/me/attendance-events",
            "list_my_attendance_events",
            "/api/v1/me/attendance-events",
        ),
        ("/api/v1/employees", "list_employees", "/api/v1/employees"),
        ("/api/v1/employees/42", "get_employee", "/api/v1/employees/{employee_id}"),
        ("/api/v1/punch-types", "list_punch_types", "/api/v1/punch-types"),
        ("/api/v1/locations", "list_locations", "/api/v1/locations"),
        (
            "/api/v1/employees/42/attendance-events",
            "list_attendance_events",
            "/api/v1/employees/{employee_id}/attendance-events",
        ),
        (
            "/api/v1/attendance-events/100",
            "get_attendance_event",
            "/api/v1/attendance-events/{attendance_event_id}",
        ),
        (
            "/api/v1/employees/42/daily-attendance",
            "get_daily_attendance",
            "/api/v1/employees/{employee_id}/daily-attendance",
        ),
        (
            "/api/v1/employees/42/planned-work",
            "get_planned_work",
            "/api/v1/employees/{employee_id}/planned-work",
        ),
        (
            "/api/v1/attendance/current",
            "get_current_attendance",
            "/api/v1/attendance/current",
        ),
        (
            "/api/v1/employees/42/attendance-analysis",
            "get_employee_attendance_analysis",
            "/api/v1/employees/{employee_id}/attendance-analysis",
        ),
        (
            "/api/v1/employees/42/attendance-summary",
            "get_employee_attendance_summary",
            "/api/v1/employees/{employee_id}/attendance-summary",
        ),
        (
            "/api/v1/attendance/exceptions",
            "get_exceptions",
            "/api/v1/attendance/exceptions",
        ),
        (
            "/api/v1/attendance/organization-analysis",
            "get_organization_attendance_analysis",
            "/api/v1/attendance/organization-analysis",
        ),
    ],
)
def test_rest_operation_metadata_covers_the_complete_tool_catalog(
    path: str, operation: str, route_template: str
) -> None:
    assert _operation_metadata("GET", path) == (operation, route_template)


@pytest.mark.asyncio
async def test_rest_client_logs_stable_operation_and_route_template_only(
    monkeypatch,
) -> None:
    events: list[tuple[str, dict[str, object]]] = []

    class CapturingLogger:
        def info(self, event: str, **values: object) -> None:
            events.append((event, values))

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"items": []},
            headers={"X-Attendance-API-Contract-Version": "1.0.0"},
        )

    monkeypatch.setattr("attendance_mcp.rest_client.logger", CapturingLogger())
    async with httpx.AsyncClient(
        base_url="https://crmt.example", transport=httpx.MockTransport(handler)
    ) as http_client:
        await CrmtRestClient(client=http_client).get_employee_attendance_analysis(
            employee_id=42,
            headers={
                "Authorization": "Bearer delegated-token",
                "X-Correlation-ID": "11111111-1111-1111-1111-111111111111",
            },
            params={"start_date": "2026-08-01", "end_date": "2026-08-02"},
        )

    assert [event for event, _ in events] == [
        "crmt_operation_started",
        "crmt_operation_succeeded",
    ]
    assert events[0][1] == {
        "operation": "get_employee_attendance_analysis",
        "method": "GET",
        "route_template": "/api/v1/employees/{employee_id}/attendance-analysis",
    }
    assert events[1][1] | {"duration_ms": events[1][1]["duration_ms"]} == {
        "operation": "get_employee_attendance_analysis",
        "method": "GET",
        "route_template": "/api/v1/employees/{employee_id}/attendance-analysis",
        "outcome": "succeeded",
        "status_code": 200,
        "duration_ms": events[1][1]["duration_ms"],
    }


@pytest.mark.asyncio
async def test_requester_events_preserve_the_frozen_route_arguments_and_headers() -> (
    None
):
    received: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        received.append(request)
        return httpx.Response(
            200,
            json={"items": [], "limit": 50, "offset": 0, "next_offset": None},
            headers={"X-Attendance-API-Contract-Version": "1.0.0"},
        )

    async with httpx.AsyncClient(
        base_url="https://crmt.example", transport=httpx.MockTransport(handler)
    ) as http_client:
        client = CrmtRestClient(client=http_client)
        result = await client.list_my_attendance_events(
            headers={
                "Authorization": "Bearer delegated-token",
                "X-Correlation-ID": "11111111-1111-1111-1111-111111111111",
            },
            params={
                "start_date": "2026-08-01",
                "end_date": "2026-08-02",
                "limit": 50,
                "offset": 0,
            },
        )

    assert result["items"] == []
    assert received[0].url.path == "/api/v1/me/attendance-events"
    assert dict(received[0].url.params) == {
        "start_date": "2026-08-01",
        "end_date": "2026-08-02",
        "limit": "50",
        "offset": "0",
    }
    assert received[0].headers["authorization"] == "Bearer delegated-token"
    assert (
        received[0].headers["x-correlation-id"]
        == "11111111-1111-1111-1111-111111111111"
    )


@pytest.mark.asyncio
async def test_rest_client_exposes_only_a_validated_safe_crmt_error() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "code": "INVALID_ARGUMENT",
                "message": "Check the attendance date range and pagination values and try again.",
                "diagnostic": "must not pass through",
            },
            headers={"X-Attendance-API-Contract-Version": "1.0.0"},
        )

    async with httpx.AsyncClient(
        base_url="https://crmt.example", transport=httpx.MockTransport(handler)
    ) as http_client:
        with pytest.raises(RestFailure) as raised:
            await CrmtRestClient(client=http_client).list_my_attendance_events(
                headers={
                    "Authorization": "Bearer delegated-token",
                    "X-Correlation-ID": "11111111-1111-1111-1111-111111111111",
                },
                params={},
            )

    assert raised.value.error.code == "BACKEND_UNAVAILABLE"
    assert "diagnostic" not in raised.value.error.model_dump_json()


@pytest.mark.asyncio
async def test_administrative_routes_preserve_safe_crmt_failures() -> None:
    failures = {
        "/api/v1/employees/42/attendance-events": (403, "FORBIDDEN"),
        "/api/v1/attendance-events/100": (404, "NOT_FOUND"),
        "/api/v1/employees/42/daily-attendance": (400, "INVALID_ARGUMENT"),
        "/api/v1/employees/42/planned-work": (503, "BACKEND_UNAVAILABLE"),
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        status_code, code = failures[request.url.path]
        return httpx.Response(
            status_code,
            json={
                "code": code,
                "message": {
                    "FORBIDDEN": "You do not have permission to do that.",
                    "NOT_FOUND": "The requested attendance resource was not found.",
                    "INVALID_ARGUMENT": "Check the attendance date range and pagination values and try again.",
                    "BACKEND_UNAVAILABLE": "Attendance is temporarily unavailable. Please try again shortly.",
                }[code],
            },
            headers={"X-Attendance-API-Contract-Version": "1.0.0"},
        )

    headers = {
        "Authorization": "Bearer delegated-token",
        "X-Correlation-ID": "11111111-1111-1111-1111-111111111111",
    }
    async with httpx.AsyncClient(
        base_url="https://crmt.example", transport=httpx.MockTransport(handler)
    ) as http_client:
        client = CrmtRestClient(client=http_client)
        operations = [
            client.list_attendance_events(employee_id=42, headers=headers, params={}),
            client.get_attendance_event(attendance_event_id=100, headers=headers),
            client.get_daily_attendance(employee_id=42, headers=headers, params={}),
            client.get_planned_work(employee_id=42, headers=headers, params={}),
        ]
        for operation, (_, expected_code) in zip(
            operations, failures.values(), strict=True
        ):
            with pytest.raises(RestFailure) as raised:
                await operation
            assert raised.value.error.code == expected_code


@pytest.mark.asyncio
async def test_catalog_routes_preserve_arguments_and_forward_only_allowed_headers() -> (
    None
):
    received: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        received.append(request)
        payload: object = (
            []
            if request.url.path in {"/api/v1/punch-types", "/api/v1/locations"}
            else {"items": []}
        )
        return httpx.Response(
            200,
            json=payload,
            headers={"X-Attendance-API-Contract-Version": "1.0.0"},
        )

    headers = {
        "Authorization": "Bearer delegated-token",
        "X-Correlation-ID": "11111111-1111-1111-1111-111111111111",
        "X-Caller-Controlled": "must-not-forward",
    }
    async with httpx.AsyncClient(
        base_url="https://crmt.example", transport=httpx.MockTransport(handler)
    ) as http_client:
        client = CrmtRestClient(client=http_client)
        await client.list_employees(headers=headers, params={"limit": 25, "offset": 3})
        await client.get_employee(headers=headers, employee_id=42)
        await client.list_punch_types(headers=headers, active_only=False)
        await client.list_locations(headers=headers)

    assert [(request.url.path, dict(request.url.params)) for request in received] == [
        ("/api/v1/employees", {"limit": "25", "offset": "3"}),
        ("/api/v1/employees/42", {}),
        ("/api/v1/punch-types", {"active_only": "false"}),
        ("/api/v1/locations", {}),
    ]
    for request in received:
        assert request.headers["authorization"] == headers["Authorization"]
        assert request.headers["x-correlation-id"] == headers["X-Correlation-ID"]
        assert "x-caller-controlled" not in request.headers


@pytest.mark.asyncio
async def test_reporting_routes_preserve_arguments_and_safe_failures() -> None:
    received: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        received.append(request)
        if request.url.path.endswith("exceptions"):
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
            json={"items": []},
            headers={"X-Attendance-API-Contract-Version": "1.0.0"},
        )

    headers = {
        "Authorization": "Bearer delegated-token",
        "X-Correlation-ID": "11111111-1111-1111-1111-111111111111",
    }
    async with httpx.AsyncClient(
        base_url="https://crmt.example", transport=httpx.MockTransport(handler)
    ) as http_client:
        client = CrmtRestClient(client=http_client)
        await client.get_current_attendance(
            headers=headers, params={"status": "remote", "limit": 25, "offset": 2}
        )
        await client.get_employee_attendance_analysis(
            employee_id=42,
            headers=headers,
            params={"start_date": "2026-08-01", "end_date": "2026-08-02"},
        )
        await client.get_employee_attendance_summary(
            employee_id=42,
            headers=headers,
            params={"start_date": "2026-08-01", "end_date": "2026-08-02"},
        )
        with pytest.raises(RestFailure) as raised:
            await client.get_exceptions(
                headers=headers,
                params={"start_date": "2026-08-01", "end_date": "2026-08-02"},
            )
        await client.get_organization_attendance_analysis(
            headers=headers,
            params={"start_date": "2026-08-01", "end_date": "2026-08-02"},
        )

    assert raised.value.error.code == "FORBIDDEN"
    assert [request.url.path for request in received] == [
        "/api/v1/attendance/current",
        "/api/v1/employees/42/attendance-analysis",
        "/api/v1/employees/42/attendance-summary",
        "/api/v1/attendance/exceptions",
        "/api/v1/attendance/organization-analysis",
    ]
    assert dict(received[0].url.params) == {
        "status": "remote",
        "limit": "25",
        "offset": "2",
    }
