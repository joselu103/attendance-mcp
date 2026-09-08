# Response Guide

## Core Directive

Before answering the user after a prompt, always wait for all tool executions and
background operations to fully finish.

## Success Format

When operations succeed:

- Respond using **bullet points only** (maximum 3-5 items).
- Focus strictly on key outcomes, state changes, or test status.
- Do not include git diffs, code snippets, or lengthy explanations unless
  explicitly requested.

## Exception (Error Handling)

When operations fail, provide the exact error, a brief root-cause analysis, and
the proposed fix.
