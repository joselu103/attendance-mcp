# Current Directive

> **Status:** Completed
>
> **Objective:** Complete attendance-mcp#21 by instrumenting public health and
> Streamable HTTP MCP request admission and lifecycle events.
>
> **Contract context:** Preserve MCP contract `1.2.0` and the thin adapter
> boundary. CRMT remains the sole authority for token validation, identity, and
> authorization. Log only trace ID, route, duration, HTTP outcome, local header
> admission outcome, and CRMT's safe admission result; never log headers,
> tokens, sessions, identities, upstream payloads, or attendance data.
>
> **Verification:** Added focused lifecycle/admission tests for generated health
> traces, valid correlation trace binding, safe header rejection, CRMT admission,
> and safe CRMT denial. Verified with `uv run pytest` (19 passed), `uv run ruff
> check .`, and `uv run ruff format --check .`.
>
> **Definition of done:** Complete for #21's repository-owned request lifecycle
> instrumentation: every public HTTP request has a safe received and
> completed/failed lifecycle record, valid caller correlation IDs are trace IDs,
> health and rejected requests use logging-only UUIDs, and header/admission
> outcomes are covered without claiming authority owned by CRMT.

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
