# Adapter Boundary and Invariants

Attendance MCP is a replaceable protocol adapter, not an identity, security, or
domain boundary. It owns Streamable HTTP MCP transport, tool registration and
metadata, allow-listed forwarding of `Authorization` and `X-Correlation-ID`,
REST-client timeouts and bounded JSON parsing, contract-major checks, and
REST-safe-error to MCP-safe-error translation.

Attendance CRMT exclusively validates the delegated token, derives the requester
and employee, applies authorization and attendance rules, persists audit records,
and accesses SQL Server. The adapter must not interpret JWT claims, make
authorization decisions, derive an employee or role, persist audit data, access
SQL Server, or duplicate attendance logic.

Use one deep REST-client module. MCP tool registrations are thin route and
argument mappings; they do not create a second domain model. Keep only direct
adapter runtime dependencies: FastMCP, HTTPX, Pydantic Settings, and Uvicorn.
Do not introduce SQLAlchemy, PyODBC, PyJWT, audit, Teams, or OpenAI dependencies.

The token and correlation flow is fixed: the Teams bot performs the single OBO
exchange, then the adapter forwards the resulting Attendance bearer token and
the same canonical UUID to CRMT unchanged. Reject missing, malformed, or duplicate
forwarded headers without exposing their values. Never cache, store, parse, or
log tokens, raw REST bodies, or attendance data.
