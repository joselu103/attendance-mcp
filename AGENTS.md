# Attendance MCP Adapter

Attendance MCP is the thin Streamable HTTP MCP-to-REST adapter in the Attendance
ecosystem. It owns MCP protocol behavior, read-only tool metadata, allow-listed
header forwarding, REST-to-MCP safe-error translation, and one deep REST-client
seam. The Attendance REST API remains the protected authority for token validation,
requester identity and employee mapping, authorization, audit, attendance rules,
and SQL Server access.

**Output Rule:** Wait for operations to finish. On success, output ONLY 3-5
bullet points summarizing results. No diffs, code dumps, or long explanations.
(Details: `docs/agent-guidance/response-guide.md`)

Before changing code or repository metadata, read `AGENT_STATE.json`, the active
`AGENT_INBOX.md`, this repository's working tree, and the applicable guidance
below. Use the package manager and quality commands documented by this repository
once they exist; run focused tests and all documented checks after the final edit.

Do not commit, push, deploy, provision infrastructure, use secrets, or change
external resources without explicit user authorization. Do not read or record
tokens, credentials, connection strings, certificates, personal attendance data,
or raw upstream payloads.

Load task-specific guidance:

- [Adapter boundary and invariants](docs/agent-guidance/adapter-boundary.md)
- [MCP/REST integration contract](docs/agent-guidance/integration-contract.md)
- [Verification and state](docs/agent-guidance/verification-and-state.md)

## Agent references

### Issue tracker

Issues and specifications are tracked in this repository's GitHub Issues. See
`docs/agents/issue-tracker.md` and the
[agent and issue-navigation guide](docs/agents/agent-and-issue-navigation.md).

### Triage labels

Use the default five-label triage vocabulary. See
`docs/agents/triage-labels.md`.

### Domain docs

Use the single-context domain-doc layout. See `docs/agents/domain.md`.
