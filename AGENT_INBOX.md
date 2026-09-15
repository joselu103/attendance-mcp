# Current Directive

> **Status:** Completed
>
> **Objective:** Apply project-owned runtime logging: preserve safe structured
> adapter lifecycle telemetry and one Uvicorn access record while suppressing
> routine external-library diagnostics by default.
>
> **Contract context:** Preserve MCP contract `1.2.0`, Streamable HTTP behavior,
> allowed header forwarding, and all safe logging/redaction guarantees. CRMT
> remains the authority for token validation, identity, authorization, audit,
> and attendance behavior. Do not use secrets, SQL Server, raw attendance data,
> or external deployments.
>
> **Verification:** Added focused logging coverage. Verified with `uv run pytest`
> (38 passed), `uv run ruff check .`, and `uv run ruff format --check .`.
>
> **Definition of done:** Completed locally: adapter logs remain structured and safe; ordinary
> third-party output is quiet by default; an explicitly enabled non-secret
> diagnostic setting restores external DEBUG logging; Uvicorn retains exactly
> one access record per request.

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
