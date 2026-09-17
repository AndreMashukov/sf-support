# Claude Code Setup — StudyForge Support

How this repo is configured for Claude Code, and how it stays aligned with Cursor.

## Layout

```
CLAUDE.md                 # Thin always-on memory (do not @-import AGENTS.md)
CLAUDE.local.md           # Optional personal overrides (gitignored)
AGENTS.md                 # Full conventions — read on demand
CONTEXT.md                # Domain glossary
.claude/
├── settings.json
├── hooks/
├── rules/
├── skills/
├── agents/
└── SETUP.md
.cursor/rules/            # Cursor mirrors
```

## Memory

| Layer | When loaded | Purpose |
| --- | --- | --- |
| Root `CLAUDE.md` | Every session | Commands, gotchas |
| `.claude/rules/*.md` | Matching paths | MUST/NEVER |
| Skills / agents | On invoke | Workflows |
| `AGENTS.md` | When you Read it | Handbook |

## Hooks

| Event | Script |
| --- | --- |
| PreToolUse Bash | `block-dangerous-bash.sh` |
| PreToolUse Edit\|Write | `block-secrets.sh` |
| PostToolUse Edit\|Write | `format-on-write.sh` (ruff) |
| Stop | `remind-check-on-stop.sh` |

## Validation

```bash
ruff check app
ruff format --check app
```

Or `/check`. Agent `verify-changes` reviews before you claim done.
