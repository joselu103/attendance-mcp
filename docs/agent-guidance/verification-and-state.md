# Verification and State

Use RED -> minimal GREEN -> review/refactor for behavior changes. Add black-box
tests at the MCP and REST-client seams; do not test documentation or configuration
prose. For each implementation slice, verify tool catalog parity, route and
argument mapping, header and correlation propagation, safe failures, and
Streamable HTTP behavior through the official MCP SDK. Run focused tests and all
documented repository checks after the final edit.

Do not start implementation work on `main` or `master`. Before editing, inspect
the working tree, recent commits, and relevant diff. Preserve unrelated work; do
not reset, stash, rebase, or absorb it without explicit user direction. Do not
commit, push, open a pull request, merge, deploy, provision infrastructure, or
use secrets without explicit authorization.

Update `AGENT_STATE.json` only with direct evidence. Local tests, container
builds, and unpublished images do not establish deployment, Entra/OBO, audit,
or production-readiness evidence. Mark an inbox directive completed only after
all repository-owned work and required verification pass; retain unresolved
external blockers precisely.
