"""The adapter's single deep, safe REST-client seam."""

from collections.abc import Mapping
from time import perf_counter

import httpx
import structlog

from attendance_mcp.contracts import SafeError

REST_CONTRACT_HEADER = "X-Attendance-API-Contract-Version"
AUTHORIZATION_HEADER = "Authorization"
CORRELATION_ID_HEADER = "X-Correlation-ID"
logger = structlog.get_logger(__name__)


class RestFailure(Exception):
    """A CRMT-safe failure suitable for an MCP response."""

    def __init__(self, error: SafeError, *, status_code: int = 503) -> None:
        self.error = error
        self.status_code = status_code


class CrmtRestClient:
    """Forward only the admitted caller headers to CRMT REST."""

    def __init__(self, *, client: httpx.AsyncClient) -> None:
        self._client = client

    async def admit_session(self, headers: Mapping[str, str]) -> None:
        await self._request(
            "POST", "/internal/v1/mcp/session-admissions", headers=headers
        )

    async def list_my_attendance_events(
        self, *, headers: Mapping[str, str], params: Mapping[str, object]
    ) -> dict[str, object]:
        return await self._get_object(
            "/api/v1/me/attendance-events", headers=headers, params=params
        )

    async def list_employees(
        self, *, headers: Mapping[str, str], params: Mapping[str, object]
    ) -> dict[str, object]:
        return await self._get_object(
            "/api/v1/employees", headers=headers, params=params
        )

    async def get_employee(
        self, *, headers: Mapping[str, str], employee_id: int
    ) -> dict[str, object]:
        return await self._get_object(
            f"/api/v1/employees/{employee_id}", headers=headers
        )

    async def list_punch_types(
        self, *, headers: Mapping[str, str], active_only: bool
    ) -> list[object]:
        return await self._get_list(
            "/api/v1/punch-types", headers=headers, params={"active_only": active_only}
        )

    async def list_locations(self, *, headers: Mapping[str, str]) -> list[object]:
        return await self._get_list("/api/v1/locations", headers=headers)

    async def _get_object(
        self,
        path: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        value = await self._get_json(path, headers=headers, params=params)
        if not isinstance(value, dict):
            raise RestFailure(SafeError.for_code("BACKEND_UNAVAILABLE"))
        return value

    async def _get_list(
        self,
        path: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, object] | None = None,
    ) -> list[object]:
        value = await self._get_json(path, headers=headers, params=params)
        if not isinstance(value, list):
            raise RestFailure(SafeError.for_code("BACKEND_UNAVAILABLE"))
        return value

    async def list_attendance_events(
        self,
        *,
        employee_id: int,
        headers: Mapping[str, str],
        params: Mapping[str, object],
    ) -> dict[str, object]:
        return await self._get_object(
            f"/api/v1/employees/{employee_id}/attendance-events",
            headers=headers,
            params=params,
        )

    async def get_attendance_event(
        self, *, attendance_event_id: int, headers: Mapping[str, str]
    ) -> dict[str, object]:
        return await self._get_object(
            f"/api/v1/attendance-events/{attendance_event_id}", headers=headers
        )

    async def get_daily_attendance(
        self,
        *,
        employee_id: int,
        headers: Mapping[str, str],
        params: Mapping[str, object],
    ) -> dict[str, object]:
        return await self._get_object(
            f"/api/v1/employees/{employee_id}/daily-attendance",
            headers=headers,
            params=params,
        )

    async def get_planned_work(
        self,
        *,
        employee_id: int,
        headers: Mapping[str, str],
        params: Mapping[str, object],
    ) -> dict[str, object]:
        return await self._get_object(
            f"/api/v1/employees/{employee_id}/planned-work",
            headers=headers,
            params=params,
        )

    async def _get_json(
        self,
        path: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, object] | None = None,
    ) -> object:
        response = await self._request("GET", path, headers=headers, params=params)
        try:
            value = response.json()
        except ValueError:
            raise RestFailure(SafeError.for_code("BACKEND_UNAVAILABLE")) from None
        return value

    async def get_current_attendance(
        self, *, headers: Mapping[str, str], params: Mapping[str, object]
    ) -> dict[str, object]:
        return await self._get_object(
            "/api/v1/attendance/current", headers=headers, params=params
        )

    async def get_employee_attendance_analysis(
        self,
        *,
        employee_id: int,
        headers: Mapping[str, str],
        params: Mapping[str, object],
    ) -> dict[str, object]:
        return await self._get_object(
            f"/api/v1/employees/{employee_id}/attendance-analysis",
            headers=headers,
            params=params,
        )

    async def get_employee_attendance_summary(
        self,
        *,
        employee_id: int,
        headers: Mapping[str, str],
        params: Mapping[str, object],
    ) -> dict[str, object]:
        return await self._get_object(
            f"/api/v1/employees/{employee_id}/attendance-summary",
            headers=headers,
            params=params,
        )

    async def get_exceptions(
        self, *, headers: Mapping[str, str], params: Mapping[str, object]
    ) -> dict[str, object]:
        return await self._get_object(
            "/api/v1/attendance/exceptions", headers=headers, params=params
        )

    async def get_organization_attendance_analysis(
        self, *, headers: Mapping[str, str], params: Mapping[str, object]
    ) -> dict[str, object]:
        return await self._get_object(
            "/api/v1/attendance/organization-analysis", headers=headers, params=params
        )

    async def aclose(self) -> None:
        """Close the owned HTTP client during ASGI shutdown."""
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, object] | None = None,
    ) -> httpx.Response:
        operation, route_template = _operation_metadata(method, path)
        started_at = perf_counter()
        logger.info(
            "crmt_operation_started",
            operation=operation,
            method=method,
            route_template=route_template,
        )
        try:
            response = await self._client.request(
                method,
                path,
                headers={
                    AUTHORIZATION_HEADER: headers[AUTHORIZATION_HEADER],
                    CORRELATION_ID_HEADER: headers[CORRELATION_ID_HEADER],
                },
                params=params,
            )
        except httpx.HTTPError:
            _log_crmt_failure(
                operation, method, route_template, started_at, "BACKEND_UNAVAILABLE"
            )
            raise RestFailure(SafeError.for_code("BACKEND_UNAVAILABLE")) from None

        if self._contract_major_is_incompatible(response):
            _log_crmt_failure(
                operation, method, route_template, started_at, "BACKEND_UNAVAILABLE"
            )
            raise RestFailure(SafeError.for_code("BACKEND_UNAVAILABLE"))
        if response.is_success:
            logger.info(
                "crmt_operation_succeeded",
                operation=operation,
                method=method,
                route_template=route_template,
                outcome="succeeded",
                status_code=response.status_code,
                duration_ms=_duration_ms(started_at),
            )
            return response

        error = self._safe_error(response)
        _log_crmt_failure(
            operation,
            method,
            route_template,
            started_at,
            (error or SafeError.for_code("BACKEND_UNAVAILABLE")).code,
            status_code=response.status_code if error else 503,
        )
        raise RestFailure(
            error or SafeError.for_code("BACKEND_UNAVAILABLE"),
            status_code=response.status_code if error else 503,
        )

    @staticmethod
    def _contract_major_is_incompatible(response: httpx.Response) -> bool:
        version = response.headers.get(REST_CONTRACT_HEADER)
        return version is None or version.split(".", 1)[0] != "1"

    @staticmethod
    def _safe_error(response: httpx.Response) -> SafeError | None:
        if len(response.content) > 4096:
            return None
        try:
            return SafeError.from_upstream(response.json())
        except ValueError:
            return None


def _operation_metadata(method: str, path: str) -> tuple[str, str]:
    """Return stable labels without ever retaining a concrete upstream URL."""
    exact_routes = {
        ("POST", "/internal/v1/mcp/session-admissions"): "admit_session",
        ("GET", "/api/v1/me/attendance-events"): "list_my_attendance_events",
        ("GET", "/api/v1/employees"): "list_employees",
        ("GET", "/api/v1/punch-types"): "list_punch_types",
        ("GET", "/api/v1/locations"): "list_locations",
        ("GET", "/api/v1/attendance/current"): "get_current_attendance",
        ("GET", "/api/v1/attendance/exceptions"): "get_exceptions",
        ("GET", "/api/v1/attendance/organization-analysis"): (
            "get_organization_attendance_analysis"
        ),
    }
    if (operation := exact_routes.get((method, path))) is not None:
        return operation, path
    for suffix, operation in {
        "attendance-events": "list_attendance_events",
        "daily-attendance": "get_daily_attendance",
        "planned-work": "get_planned_work",
        "attendance-analysis": "get_employee_attendance_analysis",
        "attendance-summary": "get_employee_attendance_summary",
    }.items():
        if path.startswith("/api/v1/employees/") and path.endswith(f"/{suffix}"):
            return operation, f"/api/v1/employees/{{employee_id}}/{suffix}"
    if path.startswith("/api/v1/employees/"):
        return "get_employee", "/api/v1/employees/{employee_id}"
    if path.startswith("/api/v1/attendance-events/"):
        return "get_attendance_event", "/api/v1/attendance-events/{attendance_event_id}"
    return "unknown", "unknown"


def _log_crmt_failure(
    operation: str,
    method: str,
    route_template: str,
    started_at: float,
    safe_error_code: str,
    *,
    status_code: int | None = None,
) -> None:
    logger.warning(
        "crmt_operation_failed",
        operation=operation,
        method=method,
        route_template=route_template,
        outcome="failed",
        safe_error_code=safe_error_code,
        status_code=status_code,
        duration_ms=_duration_ms(started_at),
    )


def _duration_ms(started_at: float) -> int:
    return round((perf_counter() - started_at) * 1000)
