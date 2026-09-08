# Current Directive

> **Status:** Completed
>
> **Objective:** Complete the repository-owned verification and publication
> work for attendance-mcp#6: prove the standalone adapter's legacy MCP catalog,
> Streamable HTTP behavior, header/correlation forwarding, and safe-error
> behavior against the accepted CRMT REST v1 contract; publish its public
> ownership and migration contract.
>
> **Contract context:** Preserve MCP contract `1.2.0`; retain the canonical,
> catalog, administrative, and reporting REST mappings while CRMT remains the
> authority for identity, authorization, auditing, attendance behavior, and
> safe errors. The adapter must forward only the delegated bearer and UUID
> correlation ID unchanged.
>
> **Verification:** The MCP/REST black-box catalog coverage and published
> migration contract were verified with `uv run pytest` (11 passed), `uv run
> ruff check .`, `uv run ruff format --check .`, and the local Docker build.
>
> **Definition of done:** Complete for repository-owned documentation and local
> fourteen-tool contract verification. Cross-service comparison of CRMT audit
> records remains explicitly blocked until an authorized CRMT integration
> environment is made available.

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
