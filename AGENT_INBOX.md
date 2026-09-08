# Current Directive

> **Status:** Completed
>
> **Objective:** Resolve standalone adapter wire incompatibilities with the
> current Attendance CRMT embedded MCP bridge.
>
> **Contract context:** Preserve MCP contract `1.2.0`, including legacy date
> schemas and `X-Attendance-MCP-Contract-Version` responses. CRMT remains the
> authority for identity, authorization, auditing, attendance behavior, and
> safe errors.
>
> **Verification:** Black-box MCP catalog and HTTP checks verify date schemas
> and contract-version response headers. `uv run pytest`, `uv run ruff check .`,
> `uv run ruff format --check .`, and the local Docker build completed
> successfully.
>
> **Definition of done:** The adapter's inherited MCP schemas and HTTP contract
> match CRMT's published bridge behavior without adding CRMT domain logic.

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
