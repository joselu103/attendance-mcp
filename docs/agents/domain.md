# Domain Docs

Before exploring this repository, read `CONTEXT.md` at the repository root, if it
exists, and any relevant decisions in `docs/adr/`. If either is absent, proceed
silently. Create domain documentation only when terminology or decisions need
recording.

Use one repository context:

```text
/
├── CONTEXT.md
├── docs/adr/
└── src/
```

Use terminology defined in `CONTEXT.md` when it exists. Surface conflicts with an
existing ADR rather than silently overriding it.
