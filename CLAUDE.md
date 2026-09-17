# StudyForge Support — Claude Code

Thin always-on memory. Full conventions live in `AGENTS.md` (read on demand, do not `@`-import). Path-scoped rules in `.claude/rules/` load when matching files are touched.

## Commands

```bash
docker compose up --build
ruff check app
ruff format app
pytest
```

Before reporting done: `/check`.

## Must follow

- Firebase ID tokens. Staff = `role: admin`. Users only see their tickets.
- How-it-works answers only from retrieved Help chunks. Cite titles. No invented credits.
- Do not embed ticket text. Do not import `@study-forge`.
- Never commit secrets. No Firebase Hosting deploy (this is not the StudyForge web app).
- Domain terms: [CONTEXT.md](CONTEXT.md). Spec: [docs/architecture.md](docs/architecture.md).

## Git

**Branch naming:** `<type>/<description>/<initials>`. Set initials in `~/.claude/CLAUDE.md`.

## Skills / Agents

| Kind | Names |
| --- | --- |
| Planning | `/grill-with-docs` |
| Knowledge | `langsmith-trace` |
| Tools | `/check`, `/format`, `/dev-bootstrap` |
| Agents | `verify-changes` |

## Hooks

- PreToolUse Bash: block force-push / destructive rm
- PreToolUse Edit\|Write: block obvious secrets
- PostToolUse Edit\|Write: ruff format on `app/**/*.py`
- Stop: remind to `/check` when `app/` is dirty

Cursor parity: `.cursor/rules/`. Personal: `CLAUDE.local.md` (gitignored).
