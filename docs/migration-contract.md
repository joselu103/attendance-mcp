# Attendance MCP migration contract

## Public ownership

Attendance MCP owns the public Streamable HTTP `POST /mcp` endpoint. It is a
stateless, read-only protocol adapter and publishes the pre-release MCP contract
label `1.3.0`. `GET /health` is public liveness only; it does not establish readiness
of the Attendance REST API, identity, audit, database, or MCP services.

The Attendance REST API is the private authority behind the adapter. It validates
the delegated bearer, derives requester identity and employee mapping, applies
authorization and attendance rules, records audit outcomes, and accesses SQL
Server. The adapter does not interpret tokens or claims, make authorization
decisions, persist audit records, or access SQL Server.

## Request and response contract

For every protected MCP request, callers provide exactly one delegated
`Authorization: Bearer <token>` and exactly one UUID `X-Correlation-ID`.
Attendance MCP forwards those two headers unchanged to the Attendance REST API and forwards no
other caller-controlled headers. MCP initialization remains local protocol handling;
protected tool routes are the only adapter-to-REST requests.

Attendance REST API v1 is the canonical route and safe-error contract. The adapter maps
only the Attendance REST API's validated `{ "code", "message" }` safe envelope into MCP tool
errors. It must not expose raw upstream bodies, URLs, claims, tokens, SQL, or
diagnostics. Existing tool schemas and safe `NOT_FOUND` behavior remain
compatible under major version 1.

## MCP tool inventory

The adapter provides these sixteen read-only MCP tools and maps them to the
Attendance REST API v1 inventory:

| Area | Tools |
| --- | --- |
| Requester attendance | `list_my_attendance_events` |
| Catalog | `list_employees`, `get_employee`, `resolve_employee`, `list_punch_types`, `list_locations` |
| Administrative attendance | `list_attendance_events`, `get_attendance_event`, `get_daily_attendance`, `get_planned_work` |
| Reporting | `get_current_work_status`, `get_current_attendance`, `get_employee_attendance_analysis`, `get_employee_attendance_summary`, `get_exceptions`, `get_organization_attendance_analysis` |

`resolve_employee` accepts exactly one of `employee_id`, `username`, or `email`
and returns the REST API's directory-safe employee summary. The REST API remains
the sole authorization authority. `get_current_attendance` accepts only the
user-facing `office`, `remote`, `customer_site`, `break`, `absence`, and
`no_status` values through an optional `statuses` array; omitted `statuses`
requests all recognized statuses. The adapter forwards an array as repeated REST
`status` query keys, and rejects empty or duplicate arrays. `unknown` is not
part of the MCP contract. The detailed `get_current_attendance` tool is retained
for administrators only; it still accepts optional `as_of`, `statuses`, `limit`,
and `offset` and maps to `GET /api/v1/attendance/current`. The REST API now
returns safe `FORBIDDEN` to non-administrators. MCP does not infer roles or hide
this tool based on caller identity.

The pilot `get_current_work_status` tool accepts optional `statuses` from the
same six values, `limit=50`, and `offset=0`. It has no `as_of` or employee
selector. The adapter rejects empty or duplicate status arrays and forwards a
valid array as repeated REST `status` query keys to
`GET /api/v1/attendance/current-status`. The REST API samples the current
Europe/Ljubljana day and returns a page with `items` containing only
`first_name`, `last_name`, and `status`, plus `limit`, `offset`, and
`next_offset`. REST validates pagination, authorization, and status semantics;
MCP forwards only the safe result or safe error.

Teams and other ordinary employee clients must discover and call
`get_current_work_status` for workforce status before pilot use. The prior
`get_current_attendance` access is not wire-compatible for those callers even
though its name and input shape remain. The pre-release MCP version label stays
`1.3.0` as directed; this source change does not represent a released contract
version or an assurance of old client behavior.

## Verification boundary

This repository's black-box suite verifies the adapter catalog, REST mappings,
safe errors, header forwarding, and Streamable HTTP behavior through the
official MCP Python SDK. A final comparison against the Attendance REST API,
including authorization outcomes and durable audit records, requires an
authorized Attendance REST API integration environment and remains a cross-service release
gate. Local mocks are not evidence of Entra, SQL Server, audit persistence, or
deployment readiness.
