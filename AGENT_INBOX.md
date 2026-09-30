# Current Directive

> **Status:** Completed
>
> **Objective:** Add MCP parity for privileged exact employee resolution and
> user-facing current-attendance status filtering after the verified Attendance
> REST API v1 handoff.
>
> **Contract context:** Add read-only `resolve_employee` over `GET
> /api/v1/employees/resolve`, requiring exactly one `employee_id`, `username`,
> or `email`; preserve contract `1.2.0`, header forwarding, safe error mapping,
> and REST-owned authorization. Remove `unknown` from the
> `get_current_attendance` status schema.
>
> **Verification:** Added REST-client and Streamable HTTP MCP black-box coverage
> for resolver route/parameters, allowed headers, safe `NOT_FOUND`, selector
> validation, catalog inventory, and exclusion of `unknown`; verified with
> `uv run pytest`, `uv run ruff check .`, and `uv run ruff format --check .`.
>
> **Definition of done:** Completed locally: the fifteen-tool read-only catalog
> forwards the resolver only through the established client seam, rejects
> missing/multiple selectors safely, and exposes only user-facing current
> attendance statuses.

## Prior Directive

> **Status:** Completed
>
> **Objective:** Collapse the MCP HTTP lifecycle behind one private ASGI-facing
> module.
>
> **Contract context:** Preserve MCP contract `1.2.0`, Streamable HTTP behavior,
> tool names, schemas, defaults, descriptions, routes, allow-listed header
> forwarding, and all safe logging/redaction guarantees. Preserve the named
> `CrmtRestClient` interface and its sole REST-client seam; the Attendance REST API remains the
> authority for token validation, identity, authorization, audit, and attendance
> behavior. Do not use secrets, SQL Server, raw attendance data, or external
> deployments.
>
> **Verification:** Added public ASGI coverage for safe rejected-header and
> oversized-body responses, duplicate correlation rejection, contract-version
> publication, and generated trace IDs. Verified with
> `uv run pytest tests/test_app.py tests/test_logging.py` (19 passed),
> `uv run pytest` (39 passed), `uv run ruff check .`, and
> `uv run ruff format --check .`.
>
> **Definition of done:** Completed locally: one private lifecycle wrapper owns header admission,
> initialization admission, safe lifecycle outcomes, contract-version
> publication, tracing, body replay, and lifecycle logging without middleware
> ordering knowledge. Preserve MCP contract `1.2.0`, public health, the
> FastMCP implementation, safe error behavior, and all adapter boundaries.

The repository has been initialized with its agent operating documentation only.
Before beginning an implementation slice, record an approved, bounded directive
here with its objective, required contract context, verification, definition of
done, and evidence-backed `AGENT_STATE.json` update.

## Standing Context

- The repository implements a thin Streamable HTTP MCP adapter over the
  Attendance REST API v1.
- Preserve MCP contract `1.2.0` until black-box REST parity is proven.
- The adapter must forward the delegated Attendance bearer token and the same
  UUID `X-Correlation-ID` unchanged; it must not parse, validate, cache, store,
  or log that token.
- Identity, authorization, audit, attendance behavior, and SQL Server access
  remain exclusively in the Attendance REST API.
- All product tools are read-only until a separately approved contract changes
  that scope.
