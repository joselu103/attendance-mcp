# ATTENDANCE-LOG-DURATION-TOTALS-001 — MCP handoff

## Readiness

The repository-owned MCP slice is complete and locally verified against the
REST owner's verified source handoff at
`/home/joselu/orca/workspaces/attendance-crmt/log-duration-totals/docs/issues/ATTENDANCE-LOG-DURATION-TOTALS-001-handoff.md`.
REST contract `1.0.0` remains the authority for overlap selection, duration
semantics, authorization, and audit. MCP retains pre-release `1.3.0` and
package `0.1.0`.

## MCP contract and implementation

Both `list_my_attendance_events` and administrator-only
`list_attendance_events` now advertise REST-owned overlapping history,
nullable whole-event `duration_minutes`, and page versus clipped full-period
totals. The only production source changes are the two registration
descriptions in `src/attendance_mcp/app.py`.

The existing `CrmtRestClient` and typed handlers already forward and return the
REST dictionary directly. No metric calculation, projection, validation,
aggregation, or other forwarding logic was added. Tool names, input schemas and
defaults, generic dictionary output schemas, routes, MCP/REST version labels,
headers, and safe-error authority are preserved. The shared date aliases and
unrelated descriptions were not changed.

## Verification evidence

The official MCP SDK Streamable HTTP tests use synthetic REST responses and
exercise both history routes. They preserve the verified REST history item
wire shape and a hard-coded upstream example with returned-page total 3360 and
clipped period total 1920, including positive, zero, incomplete, and reversed
null durations. Pagination coverage preserves intermediate, final, empty
beyond-last, and empty-period responses, permits a live period total to change
between pages, and checks the exact complete dates, pagination arguments,
administrator route target, single GET per invocation, unchanged allowed
headers, discarded caller header, and no REST call during initialization or
catalog discovery. Both structured content and parsed text content are asserted
unchanged. The catalog check confirms the generic object output schema.

Final verification under Python 3.14.2 from a temporary working directory, so
no repository `.env` is read:

- Focused history-duration, history-pagination, app, and REST-client tests: 53
  passed.
- Full pytest suite: 62 passed.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed (28 files formatted).
- `AGENT_STATE.json` parsed successfully; `git diff --check` passed.
- The shared issue packet matches the latest root packet byte-for-byte.

## Downstream and external gates

Teams may validate and render the live duration fields and use each page's
current REST `period_duration_minutes`; it must not accumulate period totals
across pages. These synthetic adapter checks establish field preservation only,
not domain arithmetic or deployed integration. No deployed service, Entra/OBO,
durable audit, SQL Server, provider/privacy, signing-key, or real-account
evidence was used; those gates remain external.
