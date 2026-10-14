# ATTENDANCE-LOG-DURATION-TOTALS-001 — MCP owner plan

## Status and ownership

Planning only, 13 October 2026. This plan awaits reconciliation with the REST
and Teams plans; it is not an implementation or a verified new-contract handoff.
The shared [packet](ATTENDANCE-LOG-DURATION-TOTALS-001.md) is copied verbatim from
the root coordination worktree. Only this MCP worktree is owned by this worker:
`/home/joselu/orca/workspaces/attendance-mcp/log-duration-totals`, branch
`joselu103/log-duration-totals`, starting HEAD
`8774f1483acc4dbd63c77ccc7fa8a22f49850e47`. The starting tree was clean.

Read local AGENTS.md, AGENT_STATE.json, all active/completed inbox context,
adapter boundary, integration, verification/state, response and issue-navigation
guidance, migration contract, README, package configuration, recent commits,
history transport tests, catalog/schema tests, and the generic REST-client and
tool-policy seams. Read root `docs/codex-handoff.md`, root integration guidance,
and root REST coordination contract. Completed inbox instructions are historical.
The root handoff and current contracts describe earlier history behavior;
the approved packet supplies the proposed duration/overlap changes. Old signed
continuation instructions are superseded by the root's database-backed Teams
continuation record and must not cause new MCP continuation work.

## Findings and smallest implementation

Both history handlers in `src/attendance_mcp/app.py` return
`dict[str, object]` from `ToolCallPolicy.call` and one named `CrmtRestClient`
operation. `CrmtRestClient._get_object` validates the outer object and returns
the parsed dictionary directly. There is no history DTO, response projection,
metric calculation, pagination aggregation, or attendance output model to extend.
FastMCP exposes the generic dictionary output contract; the official SDK tests
already compare both `structuredContent` and parsed text content with REST JSON.
Read-only official SDK catalog inspection in this worktree confirms both history
tools publish `outputSchema = {"additionalProperties": true, "type": "object"}`.
No field-specific MCP output schema should be introduced.

Expected production change: only the two history registration descriptions.
Advertise REST-owned overlapping history, nullable whole-event duration, and
page versus clipped full-period totals, preserving concise selection guidance,
personal server-derived identity and administrator-only authorization guidance.
Do not change common `StartDate`/`EndDate` aliases, argument examples, or unrelated
tool metadata: those are shared with other endpoints. Keep live registrations
the canonical model-selection source; Teams must discover their updated metadata.

Add focused forwarding evidence, and update README,
`docs/migration-contract.md`, and the history section of
`docs/agent-guidance/integration-contract.md` to document the verified contract.
During implementation only, record a bounded directive in AGENT_INBOX.md before
source edits; after final checks update AGENT_STATE.json and write
`docs/issues/ATTENDANCE-LOG-DURATION-TOTALS-001-handoff.md` with direct evidence.
Do not mark this issue implemented or alter historical verification during planning.

If new transport assertions already pass on current forwarding, retain that
evidence and change no handler/client logic. Do not manufacture a RED failure
for metadata changes. If a real forwarding failure appears, report it and apply
the smallest adapter-only correction with behavior-level RED/GREEN evidence.
No metric arithmetic, clipping, selection, anomaly policy, typed attendance
validation, dependency updates, or rendering belongs in MCP.

## Interface and version expectations

| Surface | Required expectation |
| --- | --- |
| Personal tool | `list_my_attendance_events(start_date, end_date, limit=50, offset=0)` → `GET /api/v1/me/attendance-events`; no employee selector |
| Administrator tool | `list_attendance_events(employee_id, start_date, end_date, limit=50, offset=0)` → `GET /api/v1/employees/{employee_id}/attendance-events` |
| Inputs | Same explicit inclusive Europe/Ljubljana dates, no maximum span, future ends allowed; same required fields and default/bounded pagination |
| History response | Existing `items`, `limit`, `offset`, `next_offset` plus root `summary` with `page_duration_minutes` and `period_duration_minutes`; only history items gain `duration_minutes` |
| Catalog/output | Sixteen read-only tools; unchanged input schemas, bilingual valid-call examples, generic dictionary output structure and annotations |
| Versions | REST namespace v1 and `X-Attendance-API-Contract-Version: 1.0.0`; MCP pre-release `1.3.0` and `X-Attendance-MCP-Contract-Version: 1.3.0`; package `0.1.0` unchanged |
| Transport | Local MCP initialization; exactly one complete-period REST request per tool page; unchanged delegated bearer and UUID; no extra caller-controlled headers |
| Failures | Existing safe REST errors and incompatible/malformed upstream response policy; REST remains sole identity, authorization and audit authority |

The response additions and expanded overlap selection are deliberate changes
under existing development labels. Do not claim the entire response or selection
behavior is unchanged. Bot consumes the new contract directly, without a
legacy fallback. Other event representations and all other endpoint shapes stay
unchanged. Period totals may differ across live pages; no snapshot or accumulated
client total is promised.

REST must publish `duration_minutes` as an integer or null: UTC elapsed whole
event minutes truncated independently, null for missing/reversed endpoints, zero
for zero intervals. `page_duration_minutes` sums non-null returned durations;
`period_duration_minutes` sums independently truncated, valid completed overlaps
clipped to the half-open Europe/Ljubljana period. Wholly contained contributions
reuse event duration; independent overlaps both contribute; empty totals are zero.
An empty beyond-last page can have page total zero and positive period total.
MCP preserves these values, including null and zero, without recomputation.

## Exact proposed verification

Add `tests/test_history_duration_totals.py` using the established
`httpx.MockTransport` → real `create_app` ASGI → official MCP SDK
`streamable_http_client`/`ClientSession` path. Parametrize each history case
over both existing `HISTORY_TOOLS` mappings; use synthetic values only.

1. `test_history_duration_fields_are_forwarded_unchanged`: return a mixed page
   containing REST-owned positive, zero, and null duration values, including a
   completed event crossing the requested boundary, active pre-period event,
   reversed/incomplete eligible anomalies, midnight and DST-offset timestamps.
   Include fractional-second endpoints whose already computed REST minutes are
   passed through. Assert exact entire dictionary equality in structured and
   parsed text content, with unchanged item/timestamp order and scalar types.
   Assert the period total is independent of the page total. Expected values
   must be taken from verified REST synthetic examples, never calculated by a
   helper implementing the domain rules in this repository.
2. `test_history_duration_summaries_preserve_live_pagination`: return an
   intermediate page, final page, empty beyond-last page with a positive period
   total, and empty-period page with both totals zero. Assert every page's exact
   summary and envelope in both MCP representations. Allow the upstream period
   total to change on a subsequent live page, proving there is no cached total
   or client accumulation. Assert default and explicit limit/offset, same dates
   and administrator target, one GET per invocation, unchanged headers, discarded
   unapproved header, and no upstream request during initialization/discovery.

Reuse rather than duplicate these existing regressions:

- `tests/test_history_pagination.py::test_history_full_period_single_request_and_live_pages`
  for complete multi-year/future periods, schemas/defaults, both response forms,
  headers and paging; add a behavioral catalog assertion for the captured
  `{"additionalProperties": true, "type": "object"}` output schema for both
  history tools (no prose equality assertions).
- `tests/test_history_pagination.py::test_history_preserves_rest_validation_authority_and_safe_errors`
  for reversed dates, invalid pagination, REST FORBIDDEN and unsafe-error filtering.
- `tests/test_app.py::test_catalog_admits_every_read_only_tool_for_the_teams_bot`
  and `test_catalog_metadata_examples_are_schema_valid_and_forward_safely`
  for sixteen read-only tools, schema-visible guidance, en/sl examples and headers.
- Existing administrative/catalog/reporting REST-client and public transport
  tests for unchanged routes and unrelated outputs. The REST owner must prove
  unchanged non-history endpoint models; MCP must not synthesize metrics on them.

The full overlap boundary, self/admin isolation, incomplete/reversed/zero,
independent overlap, fractional minute and spring/fallback DST arithmetic matrix
belongs to REST acceptance. MCP's synthetic examples prove preservation through
transport, not correctness of selection/calculation. Local FORBIDDEN forwarding
does not establish actual upstream authorization or audit persistence.

Implementation focused command after the proposed tests exist:

```sh
uv run pytest -q tests/test_history_duration_totals.py tests/test_history_pagination.py tests/test_app.py tests/test_rest_client.py
```

Required final checks after the final implementation/documentation/state edit:

```sh
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run python -c 'import json; from pathlib import Path; json.loads(Path("AGENT_STATE.json").read_text()); print("state JSON valid")'
git diff --check
```

Run pytest from an empty temporary working directory through the selected project
environment and absolute test/config paths, so `Settings` cannot read a local
`.env`. Use mocks only; no real REST service, bearer, SQL Server, or attendance
records. This repository documents no mypy/Compose/build gate for this slice.
Packet equality and changed-file scope are also checked; no documentation tests
are added. Planning baseline evidence is recorded below after execution.

## REST dependency, reconciliation and handoff

MCP implementation is blocked pending reconciliation of all three plans and a
verified REST handoff for this issue. Prior history-pagination and tool-metadata
verification does not prove the new fields or overlap behavior. The REST handoff
must identify the actual verified source revision/worktree, published history
models/envelope, selection and arithmetic semantics, unchanged non-history shapes,
authorization/audit guarantees, exact focused/full check outcomes, version labels,
and remaining external gates. Compare the handoff with this packet before using
its synthetic examples. Any mismatch in field names, nullability, empty/beyond-last
summary behavior, date boundaries or version expectation returns to reconciliation.

No additional product decision is identified for MCP. Recommend GPT-6 Luna for
implementation: transport verification and narrow metadata/docs are a small
adapter slice. Verify the effective model from the implementation launch receipt;
use the coordinator's requested complexity escalation if a genuine seam defect
changes that assessment. Read-only `orca orchestration worker-show --dispatch
ctx_660bd2e7b301 --json` confirms this planning launch's requested and effective
model are `gpt-6.1-sol`, effort `high`, with matching provider projection.

On verified MCP completion, publish actual test counts, command outcomes and
contract/schema evidence in the owner state and handoff, then signal the
coordinator. Teams can then validate the newly required typed fields and render
EN/SL event/segment totals and period footers; MCP does not own that presentation.
Coordinator owns root handoff/HANDOVER and cross-plan reconciliation. Only local
source readiness can advance; deployment, Entra/OBO, real-account authorization,
SQL Server, durable audit, Teams delivery and provider/privacy remain external.
No secrets, real data, external changes, commits, pushes, PRs, merges or deployments
are authorized by this plan.

## Planning verification evidence

Python 3.14.2 baseline verification passed: focused history/app/REST-client tests
49 passed; full pytest 58 passed; Ruff check passed; Ruff format check passed
(26 files); state JSON validation and `git diff --check` passed. Pytest used
`uv run python` with a temporary current directory and absolute `-c pyproject.toml`
and test paths so no local `.env` was read. The official SDK catalog inspection
also passed and confirmed the two generic output schemas above. These are
existing-source baseline results, not duration-contract implementation evidence.

The root packet was reread and recopied after its model identifiers were
clarified during planning. Final packet byte equality, changed-file scope and
documented checks are rechecked after this final report edit. Only the packet
copy and this plan are changed; source, tests, state and inbox are untouched.
