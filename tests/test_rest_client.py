import httpx
import pytest

from attendance_mcp.rest_client import CrmtRestClient, RestFailure


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
            await CrmtRestClient(client=http_client).list_employees(
                headers={
                    "Authorization": "Bearer delegated-token",
                    "X-Correlation-ID": "11111111-1111-1111-1111-111111111111",
                },
                params={"limit": 50, "offset": 0},
            )

    assert raised.value.error.code == "BACKEND_UNAVAILABLE"
    assert "diagnostic" not in raised.value.error.model_dump_json()


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
