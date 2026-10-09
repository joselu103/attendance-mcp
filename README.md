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

For attendance history, `list_my_attendance_events(start_date, end_date,
limit=50, offset=0)` and administrator-only `list_attendance_events(employee_id,
start_date, end_date, limit=50, offset=0)` accept explicit inclusive
Europe/Ljubljana dates without a maximum span, including future end dates.
Each call forwards the complete period once and returns one REST page unchanged.
Follow `next_offset` with the same dates and target; final and empty pages have
null `next_offset`. REST requires end >= start, limit 1–100, and offset >= 0.
Pages read live data with no snapshot guarantee. Wider periods are additive;
MCP pre-release `1.3.0` and REST `1.0.0` schemas/defaults are unchanged.

Teams source implementation may now consume complete-period pages against the
verified REST and MCP history-pagination worktrees. Teams must remove history
window splitting/aggregation and provide user-controlled continuation. This
handoff does not establish deployed end-to-end readiness; unrelated report,
summary, planned-work, and current-status rules retain their existing scope.

Protected MCP requests need one delegated `Authorization: Bearer` header and
one UUID `X-Correlation-ID`. The adapter forwards their values unchanged to
REST and sends no other caller-controlled header upstream. See
[`docs/migration-contract.md`](docs/migration-contract.md) for the complete
catalog and compatibility contract.

Local verification uses `uv run pytest`, `uv run ruff check .`, and
`uv run ruff format --check .`. These checks do not establish Entra, audit,
database, or deployed service readiness.
