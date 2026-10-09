# Attendance MCP

Attendance MCP is the read-only Streamable HTTP adapter between the Teams bot
and the Attendance REST API. It serves `POST /mcp` and public liveness at
`GET /health`. The REST API owns delegated token validation, requester mapping,
authorization, attendance rules, audit, and SQL Server access.

The pilot MCP catalog contains sixteen read-only tools under the pre-release
contract label `1.3.0`. For current workforce status, use
`get_current_work_status(statuses=None, limit=50, offset=0)`. Its optional
`statuses` array accepts `office`, `remote`, `customer_site`, `break`,
`absence`, or `no_status`; omit it for all categories. The response is a page
with `items` of `first_name`, `last_name`, and `status`, plus `limit`, `offset`,
and `next_offset`. The REST API evaluates the current Europe/Ljubljana day;
there is no client-selected time or employee identity.

`get_current_attendance` remains available for administrator-only detailed
queries and still accepts optional `as_of`, `statuses`, `limit`, and `offset`.
Non-administrator callers must migrate to `get_current_work_status` and will
receive a safe `FORBIDDEN` from REST on the detailed route. The unchanged
pre-release version label does not imply compatibility for those callers.

Protected MCP requests need one delegated `Authorization: Bearer` header and
one UUID `X-Correlation-ID`. The adapter forwards their values unchanged to
REST and sends no other caller-controlled header upstream. See
[`docs/migration-contract.md`](docs/migration-contract.md) for the complete
catalog and compatibility contract.

Local verification uses `uv run pytest`, `uv run ruff check .`, and
`uv run ruff format --check .`. These checks do not establish Entra, audit,
database, or deployed service readiness.
