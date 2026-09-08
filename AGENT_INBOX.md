# Current Directive

> **Status:** Completed
>
> **Objective:** Implement attendance-mcp issue #2: a deployable Streamable HTTP
> MCP-to-REST adapter with public liveness and the canonical requester attendance
> tool.
>
> **Contract context:** CRMT `POST /internal/v1/mcp/session-admissions` admits
> sessions without revealing a principal. CRMT
> `GET /api/v1/me/attendance-events` owns requester identity, authorization,
> attendance behavior, and safe errors. The adapter forwards exactly one bearer
> `Authorization` and one UUID `X-Correlation-ID` unchanged.
>
> **Verification:** Add black-box REST-client and MCP Streamable HTTP tests for
> catalog parity, request mapping, header propagation, safe failures, and
> liveness. Run the focused suite and all documented repository quality checks.
>
> **Definition of done:** The containerized service exposes `/mcp` and `/health`,
> has no CRMT domain or identity implementation, and has evidence-backed state.

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
