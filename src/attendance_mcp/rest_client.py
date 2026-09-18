"""The adapter's single deep, safe REST-client seam."""

from collections.abc import Mapping
from dataclasses import dataclass
from time import perf_counter

import httpx
import structlog

from attendance_mcp.contracts import SafeError

REST_CONTRACT_HEADER = "X-Attendance-API-Contract-Version"
AUTHORIZATION_HEADER = "Authorization"
CORRELATION_ID_HEADER = "X-Correlation-ID"
logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class _Operation:
    """One CRMT operation's routing and safe observability facts."""

    name: str
    method: str
    route_template: str

    def path(self, route_values: Mapping[str, int] | None = None) -> str:
        return self.route_template.format(**(route_values or {}))


_ADMIT_SESSION = _Operation(
    "admit_session", "POST", "/internal/v1/mcp/session-admissions"
)
_LIST_MY_ATTENDANCE_EVENTS = _Operation(
    "list_my_attendance_events", "GET", "/api/v1/me/attendance-events"
)
_LIST_EMPLOYEES = _Operation("list_employees", "GET", "/api/v1/employees")
_GET_EMPLOYEE = _Operation("get_employee", "GET", "/api/v1/employees/{employee_id}")
_LIST_PUNCH_TYPES = _Operation("list_punch_types", "GET", "/api/v1/punch-types")
_LIST_LOCATIONS = _Operation("list_locations", "GET", "/api/v1/locations")
_LIST_ATTENDANCE_EVENTS = _Operation(
    "list_attendance_events", "GET", "/api/v1/employees/{employee_id}/attendance-events"
)
_GET_ATTENDANCE_EVENT = _Operation(
    "get_attendance_event", "GET", "/api/v1/attendance-events/{attendance_event_id}"
)
_GET_DAILY_ATTENDANCE = _Operation(
    "get_daily_attendance", "GET", "/api/v1/employees/{employee_id}/daily-attendance"
)
_GET_PLANNED_WORK = _Operation(
    "get_planned_work", "GET", "/api/v1/employees/{employee_id}/planned-work"
)
_GET_CURRENT_ATTENDANCE = _Operation(
    "get_current_attendance", "GET", "/api/v1/attendance/current"
)
_GET_EMPLOYEE_ATTENDANCE_ANALYSIS = _Operation(
    "get_employee_attendance_analysis",
    "GET",
    "/api/v1/employees/{employee_id}/attendance-analysis",
)
_GET_EMPLOYEE_ATTENDANCE_SUMMARY = _Operation(
    "get_employee_attendance_summary",
    "GET",
    "/api/v1/employees/{employee_id}/attendance-summary",
)
_GET_EXCEPTIONS = _Operation("get_exceptions", "GET", "/api/v1/attendance/exceptions")
_GET_ORGANIZATION_ATTENDANCE_ANALYSIS = _Operation(
    "get_organization_attendance_analysis",
    "GET",
    "/api/v1/attendance/organization-analysis",
)


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
        await self._request(_ADMIT_SESSION, headers=headers)

    async def list_my_attendance_events(
        self, *, headers: Mapping[str, str], params: Mapping[str, object]
    ) -> dict[str, object]:
        return await self._get_object(
            _LIST_MY_ATTENDANCE_EVENTS, headers=headers, params=params
        )

    async def list_employees(
        self, *, headers: Mapping[str, str], params: Mapping[str, object]
    ) -> dict[str, object]:
        return await self._get_object(_LIST_EMPLOYEES, headers=headers, params=params)

    async def get_employee(
        self, *, headers: Mapping[str, str], employee_id: int
    ) -> dict[str, object]:
        return await self._get_object(
            _GET_EMPLOYEE, headers=headers, route_values={"employee_id": employee_id}
        )

    async def list_punch_types(
        self, *, headers: Mapping[str, str], active_only: bool
    ) -> list[object]:
        return await self._get_list(
            _LIST_PUNCH_TYPES, headers=headers, params={"active_only": active_only}
        )

    async def list_locations(self, *, headers: Mapping[str, str]) -> list[object]:
        return await self._get_list(_LIST_LOCATIONS, headers=headers)

    async def _get_object(
        self,
        operation: _Operation,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, object] | None = None,
        route_values: Mapping[str, int] | None = None,
    ) -> dict[str, object]:
        value = await self._get_json(
            operation, headers=headers, params=params, route_values=route_values
        )
        if not isinstance(value, dict):
            raise RestFailure(SafeError.for_code("BACKEND_UNAVAILABLE"))
        return value

    async def _get_list(
        self,
        operation: _Operation,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, object] | None = None,
        route_values: Mapping[str, int] | None = None,
    ) -> list[object]:
        value = await self._get_json(
            operation, headers=headers, params=params, route_values=route_values
        )
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
            _LIST_ATTENDANCE_EVENTS,
            headers=headers,
            params=params,
            route_values={"employee_id": employee_id},
        )

    async def get_attendance_event(
        self, *, attendance_event_id: int, headers: Mapping[str, str]
    ) -> dict[str, object]:
        return await self._get_object(
            _GET_ATTENDANCE_EVENT,
            headers=headers,
            route_values={"attendance_event_id": attendance_event_id},
        )

    async def get_daily_attendance(
        self,
        *,
        employee_id: int,
        headers: Mapping[str, str],
        params: Mapping[str, object],
    ) -> dict[str, object]:
        return await self._get_object(
            _GET_DAILY_ATTENDANCE,
            headers=headers,
            params=params,
            route_values={"employee_id": employee_id},
        )

    async def get_planned_work(
        self,
        *,
        employee_id: int,
        headers: Mapping[str, str],
        params: Mapping[str, object],
    ) -> dict[str, object]:
        return await self._get_object(
            _GET_PLANNED_WORK,
            headers=headers,
            params=params,
            route_values={"employee_id": employee_id},
        )

    async def _get_json(
        self,
        operation: _Operation,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, object] | None = None,
        route_values: Mapping[str, int] | None = None,
    ) -> object:
        response = await self._request(
            operation, headers=headers, params=params, route_values=route_values
        )
        try:
            value = response.json()
        except ValueError:
            raise RestFailure(SafeError.for_code("BACKEND_UNAVAILABLE")) from None
        return value

    async def get_current_attendance(
        self, *, headers: Mapping[str, str], params: Mapping[str, object]
    ) -> dict[str, object]:
        return await self._get_object(
            _GET_CURRENT_ATTENDANCE, headers=headers, params=params
        )

    async def get_employee_attendance_analysis(
        self,
        *,
        employee_id: int,
        headers: Mapping[str, str],
        params: Mapping[str, object],
    ) -> dict[str, object]:
        return await self._get_object(
            _GET_EMPLOYEE_ATTENDANCE_ANALYSIS,
            headers=headers,
            params=params,
            route_values={"employee_id": employee_id},
        )

    async def get_employee_attendance_summary(
        self,
        *,
        employee_id: int,
        headers: Mapping[str, str],
        params: Mapping[str, object],
    ) -> dict[str, object]:
        return await self._get_object(
            _GET_EMPLOYEE_ATTENDANCE_SUMMARY,
            headers=headers,
            params=params,
            route_values={"employee_id": employee_id},
        )

    async def get_exceptions(
        self, *, headers: Mapping[str, str], params: Mapping[str, object]
    ) -> dict[str, object]:
        return await self._get_object(_GET_EXCEPTIONS, headers=headers, params=params)

    async def get_organization_attendance_analysis(
        self, *, headers: Mapping[str, str], params: Mapping[str, object]
    ) -> dict[str, object]:
        return await self._get_object(
            _GET_ORGANIZATION_ATTENDANCE_ANALYSIS, headers=headers, params=params
        )

    async def aclose(self) -> None:
        """Close the owned HTTP client during ASGI shutdown."""
        await self._client.aclose()

    async def _request(
        self,
        operation: _Operation,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, object] | None = None,
        route_values: Mapping[str, int] | None = None,
    ) -> httpx.Response:
        started_at = perf_counter()
        logger.info(
            "crmt_operation_started",
            operation=operation.name,
            method=operation.method,
            route_template=operation.route_template,
        )
        try:
            response = await self._client.request(
                operation.method,
                operation.path(route_values),
                headers={
                    AUTHORIZATION_HEADER: headers[AUTHORIZATION_HEADER],
                    CORRELATION_ID_HEADER: headers[CORRELATION_ID_HEADER],
                },
                params=params,
            )
        except httpx.HTTPError:
            _log_crmt_failure(operation, started_at, "BACKEND_UNAVAILABLE")
            raise RestFailure(SafeError.for_code("BACKEND_UNAVAILABLE")) from None

        if self._contract_major_is_incompatible(response):
            _log_crmt_failure(operation, started_at, "BACKEND_UNAVAILABLE")
            raise RestFailure(SafeError.for_code("BACKEND_UNAVAILABLE"))
        if response.is_success:
            logger.info(
                "crmt_operation_succeeded",
                operation=operation.name,
                method=operation.method,
                route_template=operation.route_template,
                outcome="succeeded",
                status_code=response.status_code,
                duration_ms=_duration_ms(started_at),
            )
            return response

        error = self._safe_error(response)
        _log_crmt_failure(
            operation,
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


def _log_crmt_failure(
    operation: _Operation,
    started_at: float,
    safe_error_code: str,
    *,
    status_code: int | None = None,
) -> None:
    logger.warning(
        "crmt_operation_failed",
        operation=operation.name,
        method=operation.method,
        route_template=operation.route_template,
        outcome="failed",
        safe_error_code=safe_error_code,
        status_code=status_code,
        duration_ms=_duration_ms(started_at),
    )


def _duration_ms(started_at: float) -> int:
    return round((perf_counter() - started_at) * 1000)
