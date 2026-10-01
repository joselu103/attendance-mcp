# Agent and Issue Navigation

Attendance MCP is the stateless, public MCP-to-REST adapter. The Attendance REST
API is the only authority for delegated-token validation, requester identity
and employee mapping, authorization, audit, attendance business rules, and SQL
Server access. The Attendance REST API implementation is maintained in
[Attendance CRMT](https://github.com/joselu103/attendance-crmt); the public MCP
runtime is maintained in [Attendance MCP](https://github.com/joselu103/attendance-mcp).

The adapter provides the MCP tool interface and forwards exactly the delegated
bearer and correlation headers to the Attendance REST API. It does not implement
the Attendance REST API's
domain behavior, derive identity or authorization, or hard-code credentials,
hostnames, or environment data.

## Required Starting Context

Before implementing an Attendance MCP issue, read these sources in order and
then follow the REST/MCP contracts they name:

1. [Attendance CRMT AGENTS.md](https://github.com/joselu103/attendance-crmt/blob/main/AGENTS.md)
   for service ownership and verification rules.
2. [Service boundary and invariants](https://github.com/joselu103/attendance-crmt/blob/main/docs/agent-guidance/service-boundary.md).
3. [REST/MCP migration guidance](https://github.com/joselu103/attendance-crmt/blob/main/docs/agent-guidance/rest-migration.md).
4. [Teams-to-CRMT MCP contract](https://github.com/joselu103/attendance-crmt/blob/main/docs/integrations/teams-bot-mcp-auth-contract.md).
5. The published REST adapter contract in
   [attendance-crmt#17](https://github.com/joselu103/attendance-crmt/issues/17).

Do not discover adapter scope by searching the Attendance REST API implementation.
Use the contract and this fixed MCP tool inventory instead:

| Area | MCP tools |
| --- | --- |
| Requester attendance | `list_my_attendance_events` |
| Catalog | `list_employees`, `get_employee`, `list_punch_types`, `list_locations` |
| Administrative attendance | `list_attendance_events`, `get_attendance_event`, `get_daily_attendance`, `get_planned_work` |
| Reporting | `get_current_attendance`, `get_employee_attendance_analysis`, `get_employee_attendance_summary`, `get_attendance_exceptions`, `get_organization_attendance_analysis` |

## Active Issue Frontier

GitHub Issues are the work frontier. Start with the bounded ready queue, not a
broad repository search:

```bash
gh issue list --repo joselu103/attendance-mcp --state open --label ready-for-agent --limit 100
gh issue view <number> --repo joselu103/attendance-mcp --comments
```

Use `ready-for-agent` only for a fully specified issue that an agent can take
without a missing decision or external owner action. `ready-for-human` means
the remaining work requires a human owner, such as platform, identity, or
deployment authority; do not treat it as implementation authorization.

Every issue records dependency state under **Blocked by**. `None` means the
issue can start; otherwise, read each linked blocker before selecting the
issue. After a blocker changes, rerun the bounded ready-queue query and reread
the candidate issue rather than inferring that the frontier changed.
