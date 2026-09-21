# Attendance MCP migration contract

## Public ownership

Attendance MCP owns the public Streamable HTTP `POST /mcp` endpoint. It is a
stateless, read-only protocol adapter and publishes MCP contract version
`1.2.0`. `GET /health` is public liveness only; it does not establish readiness
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
other caller-controlled headers. It uses the Attendance REST API's private session-admission
operation before MCP initialization; that operation never returns principal or
credential data.

Attendance REST API v1 is the canonical route and safe-error contract. The adapter maps
only the Attendance REST API's validated `{ "code", "message" }` safe envelope into MCP tool
errors. It must not expose raw upstream bodies, URLs, claims, tokens, SQL, or
diagnostics. Existing tool schemas and safe `NOT_FOUND` behavior remain
compatible under major version 1.

## MCP tool inventory

The adapter provides these fourteen read-only MCP tools and maps them to the
Attendance REST API v1 inventory:

| Area | Tools |
| --- | --- |
| Requester attendance | `list_my_attendance_events` |
| Catalog | `list_employees`, `get_employee`, `list_punch_types`, `list_locations` |
| Administrative attendance | `list_attendance_events`, `get_attendance_event`, `get_daily_attendance`, `get_planned_work` |
| Reporting | `get_current_attendance`, `get_employee_attendance_analysis`, `get_employee_attendance_summary`, `get_exceptions`, `get_organization_attendance_analysis` |

## Verification boundary

This repository's black-box suite verifies the adapter catalog, REST mappings,
safe errors, header forwarding, and Streamable HTTP behavior through the
official MCP Python SDK. A final comparison against the Attendance REST API,
including authorization outcomes and durable audit records, requires an
authorized Attendance REST API integration environment and remains a cross-service release
gate. Local mocks are not evidence of Entra, SQL Server, audit persistence, or
deployment readiness.
