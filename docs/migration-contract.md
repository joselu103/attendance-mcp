# Attendance MCP migration contract

## Public ownership

Attendance MCP owns the public Streamable HTTP `POST /mcp` endpoint. It is a
stateless, read-only protocol adapter and publishes MCP contract version
`1.2.0`. `GET /health` is public liveness only; it does not establish CRMT,
identity, audit, database, or MCP readiness.

Attendance CRMT owns the private REST authority behind the adapter. It validates
the delegated bearer, derives requester identity and employee mapping, applies
authorization and attendance rules, records audit outcomes, and accesses SQL
Server. The adapter does not interpret tokens or claims, make authorization
decisions, persist audit records, or access SQL Server.

## Request and response contract

For every protected MCP request, callers provide exactly one delegated
`Authorization: Bearer <token>` and exactly one UUID `X-Correlation-ID`.
Attendance MCP forwards those two headers unchanged to CRMT and forwards no
other caller-controlled headers. It uses CRMT's private session-admission
operation before MCP initialization; that operation never returns principal or
credential data.

CRMT REST v1 is the canonical route and safe-error contract. The adapter maps
only CRMT's validated `{ "code", "message" }` safe envelope into MCP tool
errors. It must not expose raw upstream bodies, URLs, claims, tokens, SQL, or
diagnostics. Existing tool schemas and safe `NOT_FOUND` behavior remain
compatible under major version 1.

## Legacy tool inventory

The adapter preserves these fourteen read-only legacy tool names and maps them
to the REST v1 inventory maintained by Attendance CRMT:

| Area | Tools |
| --- | --- |
| Requester attendance | `list_my_attendance_events` |
| Catalog | `list_employees`, `get_employee`, `list_punch_types`, `list_locations` |
| Administrative attendance | `list_attendance_events`, `get_attendance_event`, `get_daily_attendance`, `get_planned_work` |
| Reporting | `get_current_attendance`, `get_employee_attendance_analysis`, `get_employee_attendance_summary`, `get_exceptions`, `get_organization_attendance_analysis` |

## Verification boundary

This repository's black-box suite verifies the adapter catalog, REST mappings,
safe errors, header forwarding, and Streamable HTTP behavior through the
official MCP Python SDK. A final comparison against the temporary embedded CRMT
bridge—including authorization outcomes and durable CRMT audit records—requires
an authorized CRMT integration environment and remains a cross-service release
gate. Local mocks are not evidence of Entra, SQL Server, audit persistence, or
deployment readiness.
