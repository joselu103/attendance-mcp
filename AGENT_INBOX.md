# Directive: ATTENDANCE-HISTORY-PAGINATION-001

> **Status:** Completed repository-owned MCP slice; Teams source ready.
>
> **Objective:** Advertise and verify complete-period history paging after the
> verified REST history-pagination source handoff (42 focused, 168 full tests).
>
> **Contract:** Required inclusive Europe/Ljubljana start/end dates have no
> maximum span; future ends are allowed. Preserve pre-release MCP `1.3.0`,
> REST `1.0.0`, tool schemas/defaults, one complete-period REST call per page,
> delegated bearer/UUID forwarding, REST authorization and safe errors.
>
> **Verification:** Ten new official SDK Streamable HTTP/HTTPX regressions
> passed against existing handlers before production edits; no forwarding change
> or artificial RED was needed. Two obsolete prose-equality assertions were
> removed after they failed on the new descriptions. Python 3.14.2 final gates:
> focused history/app/REST-client tests 48 passed; full pytest 57 passed; Ruff
> check and format check (24 files), state JSON validation and diff check passed.
>
> **Definition of done:** Two descriptions and README/migration contract updated;
> schemas, defaults, thin mapping, headers, safe errors and envelopes preserved.
> Teams has now completed full-period single-page calls and signed continuation
> against the verified REST/MCP worktrees (247 tests,71 signer/SDK cases and
> required checks passed). Deployment, Entra/OBO, SQL Server, audit persistence,
> provider/privacy, signing-key provisioning and real-account evidence remain
> separate gates. No env/secrets/data/external changes, commits, pushes, PRs,
> merges or subagents. Branch: `joselu103/history-pagination`, base `ae324f4`.

## Historical completed directive

# Current Directive

> **Status:** Completed locally; downstream and external gates remain.
>
> **Objective:** Add the read-only pilot workforce-status mapping after the
> verified Attendance REST API source handoff, and retain the detailed current
> attendance mapping as an administrator-only compatibility path.
>
> **Contract context:** Map `get_current_work_status(statuses=None, limit=50,
> offset=0)` to `GET /api/v1/attendance/current-status` without client `as_of` or
> identity selectors. Keep the pre-release MCP version label `1.3.0` and REST v1
> `1.0.0`, publish the changed catalog and mandatory non-admin client migration,
> and preserve delegated bearer/UUID correlation forwarding and safe errors.
>
> **Verification:** Focused Streamable HTTP and REST-client tests (19 passed),
> `uv run pytest -q` (47 passed), `uv run ruff check .`,
> `uv run ruff format --check .` (23 files formatted), `git diff --check`, and
> JSON state validation passed under Python 3.14.2.
>
> **Definition of done:** Sixteen read-only tools include the new category-only
> route and an explicitly administrator-only detailed tool; route arguments,
> headers, validation, and safe failures are locally verified. Teams migration
> and cross-service activation remain separate gates.

## Prior Directive

> **Status:** Completed
>
> **Objective:** Remove the obsolete Attendance REST API session-admission
> operation and all initialization-time coupling from Attendance MCP.
>
> **Contract context:** Preserve public Streamable HTTP `POST /mcp` contract
> `1.2.0`, all fifteen read-only tools, names, schemas, defaults, malformed and
> duplicate-header rejection, public `GET /health`, allowed header forwarding,
> and REST-safe-error mapping. Attendance REST API v1 `1.0.0` is MCP-free, so
> initialization remains local protocol handling and only protected tool routes
> call REST.
>
> **Verification:** Fixture-backed black-box MCP tests demonstrate successful
> initialization with no upstream REST request; all fifteen route mappings,
> allowed headers, and safe errors remain covered. Verified with `uv run pytest`
> (43 passed), `uv run ruff check .`, and `uv run ruff format --check .`.
>
> **Definition of done:** Completed locally after final verification: no adapter
> source or migration contract invokes session admission, while the
> established MCP and REST seams remain behaviorally compatible.

## Prior Directive

> **Status:** Completed
>
> **Objective:** Add MCP parity for privileged exact employee resolution and
> user-facing current-attendance status filtering after the verified Attendance
> REST API v1 handoff.
>
> **Contract context:** Add read-only `resolve_employee` over `GET
> /api/v1/employees/resolve`, requiring exactly one `employee_id`, `username`,
> or `email`; preserve contract `1.2.0`, header forwarding, safe error mapping,
> and REST-owned authorization. Remove `unknown` from the
> `get_current_attendance` status schema.
>
> **Verification:** Added REST-client and Streamable HTTP MCP black-box coverage
> for resolver route/parameters, allowed headers, safe `NOT_FOUND`, selector
> validation, catalog inventory, and exclusion of `unknown`; verified with
> `uv run pytest`, `uv run ruff check .`, and `uv run ruff format --check .`.
>
> **Definition of done:** Completed locally: the fifteen-tool read-only catalog
> forwards the resolver only through the established client seam, rejects
> missing/multiple selectors safely, and exposes only user-facing current
> attendance statuses.

## Prior Directive

> **Status:** Completed
>
> **Objective:** Collapse the MCP HTTP lifecycle behind one private ASGI-facing
> module.
>
> **Contract context:** Preserve MCP contract `1.2.0`, Streamable HTTP behavior,
> tool names, schemas, defaults, descriptions, routes, allow-listed header
> forwarding, and all safe logging/redaction guarantees. Preserve the named
> `CrmtRestClient` interface and its sole REST-client seam; the Attendance REST API remains the
> authority for token validation, identity, authorization, audit, and attendance
> behavior. Do not use secrets, SQL Server, raw attendance data, or external
> deployments.
>
> **Verification:** Added public ASGI coverage for safe rejected-header and
> oversized-body responses, duplicate correlation rejection, contract-version
> publication, and generated trace IDs. Verified with
> `uv run pytest tests/test_app.py tests/test_logging.py` (19 passed),
> `uv run pytest` (39 passed), `uv run ruff check .`, and
> `uv run ruff format --check .`.
>
> **Definition of done:** Completed locally: one private lifecycle wrapper owns header admission,
> initialization admission, safe lifecycle outcomes, contract-version
> publication, tracing, body replay, and lifecycle logging without middleware
> ordering knowledge. Preserve MCP contract `1.2.0`, public health, the
> FastMCP implementation, safe error behavior, and all adapter boundaries.

The repository has been initialized with its agent operating documentation only.
Before beginning an implementation slice, record an approved, bounded directive
here with its objective, required contract context, verification, definition of
done, and evidence-backed `AGENT_STATE.json` update.

## Standing Context

- The repository implements a thin Streamable HTTP MCP adapter over the
  Attendance REST API v1.
- Keep the pre-release MCP contract label `1.3.0` until an actual release or a
  separately approved versioning decision; document catalog and compatibility
  changes explicitly.
- The adapter must forward the delegated Attendance bearer token and the same
  UUID `X-Correlation-ID` unchanged; it must not parse, validate, cache, store,
  or log that token.
- Identity, authorization, audit, attendance behavior, and SQL Server access
  remain exclusively in the Attendance REST API.
- All product tools are read-only until a separately approved contract changes
  that scope.
