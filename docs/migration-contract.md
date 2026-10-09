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

## Attendance history compatibility and Teams handoff

`list_my_attendance_events` maps to `GET /api/v1/me/attendance-events`;
`list_attendance_events(employee_id, ...)` maps to
`GET /api/v1/employees/{employee_id}/attendance-events`. Both require explicit
inclusive Europe/Ljubljana `start_date` and `end_date` with no maximum span.
Future end dates are allowed and REST returns only existing matching records.
REST rejects reversed dates. Personal identity is server-derived; the employee
route remains administrator-only. MCP performs no range splitting, date-span
business validation, authorization decision, or automatic page aggregation.

Each call forwards the original complete dates and one `limit`/`offset` pair
once. Default limit is 50, supported limits are 1–100, and offset defaults to 0
and must be nonnegative. REST's `items`, `limit`, `offset`, and `next_offset`
envelope is unchanged; follow a non-null `next_offset` with the same dates and
target. Final and empty pages have null `next_offset`. Ordering and lookahead
remain REST-owned. Pages read live data and do not promise a snapshot.

Accepting wider history periods is additive under pre-release MCP `1.3.0` and
REST `1.0.0`. Tool names, input schemas, required dates, defaults, routes, safe
errors, headers, and response fields remain compatible. Only the two history
descriptions change; summary, analysis, exceptions, planned-work, and
current-status policies are unaffected.

The verified upstream source is the REST owner history-pagination worktree
(42 focused and 168 full tests under Python 3.14.2). The MCP source handoff
permits Teams implementation against those unchanged interfaces: request one
complete-period page, retain dates and the resolved administrator target for
continuation, and use the requester tool without an employee selector for
personal history. Teams owns signed button continuation and must remove its
history span/page caps and window aggregation. Teams verification remains
pending; source readiness clears no deployment, Entra/OBO, audit persistence,
SQL Server, provider/privacy, signing-key provisioning, or real-account gate.

## Verification boundary

This repository's black-box suite verifies the adapter catalog, REST mappings,
safe errors, header forwarding, and Streamable HTTP behavior through the
official MCP Python SDK. A final comparison against the Attendance REST API,
including authorization outcomes and durable audit records, requires an
authorized Attendance REST API integration environment and remains a cross-service release
gate. Local mocks are not evidence of Entra, SQL Server, audit persistence, or
deployment readiness.
