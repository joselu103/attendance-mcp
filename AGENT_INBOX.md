# Current Directive

> **Status:** Completed
>
> **Objective:** Deepen the internal MCP tool-call policy so all fourteen typed
> read-only tool handlers share header acquisition, REST-to-MCP safe-error
> translation, and value-free lifecycle logging.
>
> **Contract context:** Preserve MCP contract `1.2.0`, Streamable HTTP behavior,
> tool names, schemas, defaults, descriptions, routes, allow-listed header
> forwarding, and all safe logging/redaction guarantees. `CrmtRestClient`
> remains the sole REST-client seam; CRMT remains the authority for token
> validation, identity, authorization, audit, and attendance behavior. Do not
> use secrets, SQL Server, raw attendance data, or external deployments.
>
> **Verification:** Added MCP-level reporting route and header-forwarding
> coverage. Verified with `uv run pytest` (39 passed), `uv run ruff check .`,
> and `uv run ruff format --check .`.
>
> **Definition of done:** Completed locally: a private policy module derives
> safe handler metadata from the actual typed handler interface and centrally
> invokes CRMT operations, while every public tool preserves its frozen MCP
> contract and verified behavior.

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
