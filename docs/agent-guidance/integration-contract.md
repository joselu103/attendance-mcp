# MCP/REST Integration Contract

Treat the versioned Attendance REST API v1 contract and the accepted REST-core
MCP-adapter architecture decision as the canonical sources for route behavior.
Do not invent endpoints, token claims, employee mapping, authorization rules, or
response fields beyond those contracts.

`resolve_employee` maps exactly one `employee_id`, `username`, or `email` query
selector to `GET /api/v1/employees/resolve`. The MCP tool rejects missing or
multiple selectors with the established safe `INVALID_ARGUMENT` envelope and
does not make local authorization decisions. `get_current_attendance` exposes
only `office`, `remote`, `customer_site`, `break`, `absence`, and `no_status`;
`unknown` must not be accepted or advertised. Its optional `statuses` array
selects a union and is forwarded as repeated REST `status` query keys; omitted
means all recognized statuses, while empty and duplicate arrays are invalid.

For the pilot workforce view, `get_current_work_status` maps to
`GET /api/v1/attendance/current-status` and accepts only optional `statuses`
(the same six recognized values), `limit=50`, and `offset=0`. It has no `as_of`
or identity selector. The REST API samples current Europe/Ljubljana time,
authorizes any mapped delegated employee, and returns only paginated
`first_name`, `last_name`, and `status` rows. Omitted statuses request all
recognized categories; a supplied nonempty, unique array forwards as repeated
REST `status` keys. REST owns bounds and business rules. The old
`get_current_attendance` maps unchanged to the detailed REST route but is now
administrator-only; ordinary employee clients must migrate to
`get_current_work_status` and must not rely on the old tool's former access.

The adapter preserves existing MCP tool names, defaults, descriptions, and
response JSON while mapping each read-only tool to its REST v1 route. The
current-attendance scalar `status` argument was replaced by `statuses` in MCP
contract `1.3.0`. The pilot adds the read-only workforce tool while keeping the
pre-release contract label `1.3.0` until an actual release. This does not promise
authorization compatibility for non-administrative callers of the detailed tool.

For every protected REST request, forward exactly one delegated `Authorization`
bearing the Attendance token and exactly one UUID `X-Correlation-ID`. Forward no
other caller-controlled headers. The adapter neither creates a second OBO exchange
nor changes the existing Attendance audience or `attendance.access` delegated
scope.

Map only the Attendance REST API's safe error envelope to MCP-safe errors. Never expose tokens,
claims, SQL, stack traces, raw upstream payloads, URLs, connection strings, or
attendance data in tool errors, logs, fixtures, or verification evidence.

`GET /health` is public liveness only and does not demonstrate REST, Entra,
database, audit, or MCP readiness.
