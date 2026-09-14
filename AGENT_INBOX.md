# Current Directive

> **Status:** Completed
>
> **Objective:** Complete attendance-mcp#20 by establishing safe structlog
> runtime logging with correlation-aware request context, environment-specific
> rendering, and recursive redaction.
>
> **Contract context:** Preserve MCP contract `1.2.0` and the thin adapter
> boundary. Never log delegated tokens, raw upstream payloads, or attendance
> data. Bind only the admitted correlation ID for the lifetime of a request,
> then clear context before the next request.
>
> **Verification:** Added six focused logging tests for renderer/level selection,
> standard metadata, async correlation context cleanup, recursive non-mutating
> redaction, and formatted exception redaction. Verified with `uv run pytest`
> (17 passed), `uv run ruff check .`, and `uv run ruff format --check .`.
>
> **Definition of done:** Complete for #20's repository-owned structured logging
> foundation. No external deployment, identity, audit, or CRMT integration
> evidence is claimed.

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
