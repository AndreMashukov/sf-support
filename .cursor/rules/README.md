# Cursor Rules — StudyForge Support

Path-scoped rules that mirror [`.claude/rules/`](../../.claude/rules/).

| Cursor rule | Claude equivalent | Scope |
| --- | --- | --- |
| `sf-support-core.mdc` | Root `CLAUDE.md` | Always apply |
| `python.mdc` | `.claude/rules/python.md` | `app/**/*.py` |
| `auth-tickets.mdc` | `.claude/rules/auth-tickets.md` | Auth + API |
| `rag.mdc` | `.claude/rules/rag.md` | `app/rag/**` |

Shared: [`AGENTS.md`](../../AGENTS.md), [`CLAUDE.md`](../../CLAUDE.md), [`.claude/SETUP.md`](../../.claude/SETUP.md).
