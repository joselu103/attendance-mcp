# MCP/REST Integration Contract

Treat the versioned Attendance REST API v1 contract and the accepted REST-core
MCP-adapter architecture decision as the canonical sources for route behavior.
Do not invent endpoints, token claims, employee mapping, authorization rules, or
response fields beyond those contracts.

The adapter preserves existing MCP tool names, argument names, defaults,
descriptions, and response JSON while mapping each read-only tool to its REST
v1 route. Keep MCP contract `1.2.0` until parity is proven. Publish `1.3.0` only
after its documented read-only annotations, compatible `NOT_FOUND` behavior, and
black-box tests pass.

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
