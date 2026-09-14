# Current Directive

> **Status:** Completed
>
> **Objective:** Reproduce and resolve attendance-teams-bot MCP tool discovery
> failure using the adapter's actual Streamable HTTP catalog and the bot's
> compatible validation.
>
> **Contract context:** Preserve MCP contract `1.2.0`, Streamable HTTP behavior,
> legacy tool names, schemas, descriptions, and allowed header forwarding. CRMT
> remains the authority for token validation, identity, authorization, audit,
> and attendance behavior. Do not use secrets, SQL Server, raw attendance data,
> or external deployments. Diagnostics, if needed, must be correlation-scoped
> DEBUG and value-free metadata only.
>
> **Verification:** The in-process adapter/bot bridge discovers all fourteen
> tools and admits the frozen requester catalog. Verified with `uv run pytest`
> (36 passed), `uv run ruff check .`, and `uv run ruff format --check .`.
>
> **Definition of done:** Completed locally: the catalog rejection is resolved
> with SDK-compatible metadata, a bounded FastMCP 3.4.5 dependency, and
> regression coverage. External deployment and end-to-end limitations remain.

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
