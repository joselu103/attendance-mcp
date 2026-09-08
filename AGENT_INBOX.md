# Current Directive

> **Status:** Completed
>
> **Objective:** Implement attendance-mcp issue #3: map the four legacy catalog
> MCP tools to their Attendance CRMT REST v1 operations.
>
> **Contract context:** CRMT owns delegated-token validation, requester identity,
> authorization, audit, catalog behavior, and safe errors. The adapter forwards
> exactly one bearer `Authorization` and one UUID `X-Correlation-ID` unchanged
> to `GET /api/v1/employees`, `GET /api/v1/employees/{employee_id}`,
> `GET /api/v1/punch-types`, and `GET /api/v1/locations`.
>
> **Verification:** Add black-box REST-client and MCP Streamable HTTP tests for
> catalog tool parity, route and argument mapping, allowed-header propagation,
> safe failures, and secret-safe error translation. Run focused tests and all
> documented repository quality checks.
>
> **Definition of done:** `list_employees`, `get_employee`, `list_punch_types`,
> and `list_locations` retain their legacy MCP contracts while delegating only to
> CRMT REST through the single REST-client seam; repository checks pass and state
> records direct local evidence.

The repository has been initialized with its agent operating documentation only.
Before beginning an implementation slice, record an approved, bounded directive
here with its objective, required contract context, verification, definition of
done, and evidence-backed `AGENT_STATE.json` update.

## Standing Context

- The repository implements a thin Streamable HTTP MCP adapter over Attendance
  CRMT REST v1.
- Preserve MCP contract `1.2.0` until black-box REST parity is proven.
- The adapter must forward the delegated Attendance bearer token and the same
  UUID `X-Correlation-ID` unchanged; it must not parse, validate, cache, store,
  or log that token.
- Identity, authorization, audit, attendance behavior, and SQL Server access
  remain exclusively in Attendance CRMT.
- All product tools are read-only until a separately approved contract changes
  that scope.
