# Current Directive

> **Status:** Completed
>
> **Objective:** Complete attendance-mcp#22 by instrumenting all fourteen
> read-only MCP tools and the CRMT REST-client seam with safe operation
> lifecycle events.
>
> **Contract context:** Preserve MCP contract `1.2.0`, allowed header
> forwarding, and the thin adapter boundary. CRMT remains the authority for
> token validation, identity, authorization, audit, and attendance behavior.
> Log stable handlers and route templates, sanitized argument shapes, durations,
> and safe outcomes only; never log headers, values, tokens, identities, URLs,
> query strings, request bodies, upstream payloads, or attendance data.
>
> **Verification:** Added focused REST operation lifecycle and complete catalog
> route-template coverage. Verified with `uv run pytest` (34 passed), `uv run
> ruff check .`, and `uv run ruff format --check .`.
>
> **Definition of done:** Every registered read-only tool records a safe
> operation lifecycle around its CRMT call, and every CRMT call records stable
> operation and route-template lifecycle data without disclosing protected data.

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
