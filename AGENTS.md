# StudyForge Support — conventions

Python FastAPI app. Read [CONTEXT.md](CONTEXT.md) for domain terms. Spec: [docs/architecture.md](docs/architecture.md).

## Stack

| Concern | Choice |
| --- | --- |
| API / UI | FastAPI + Jinja templates |
| DB | PostgreSQL 16 + pgvector. One database for tickets, articles, chunks. |
| Search | Hybrid: cosine + `tsvector`, RRF. Top 6 chunks to the graph. |
| RAG | LangGraph: retrieve, grade context, generate or no-answer. How-it-works only. |
| Auth | Firebase ID token. Staff = `role: admin`. |
| Models | OpenRouter e5 embeddings. Together/MiniMax chat. Thinking off for structured JSON. |
| Traces | LangSmith project `study-forge-support` |
| Run | Docker Compose. Not Firebase Hosting. Not the StudyForge NX monorepo. |

## Must follow

- Users see only their tickets. Staff see all. Enforce in the API (`WHERE user_id = :uid`). v1 does not use Postgres RLS (single service role).
- Answer how-it-works only from retrieved **Help chunks**. Cite article titles. No invented credit numbers.
- Do not embed raw ticket bodies or billing amounts.
- Do not import `@study-forge` or other NX packages.
- Never use MUI.
- Never commit `.env`, service account JSON, or API keys.
- Do not auto-close tickets from the model.

## Commands

```bash
docker compose up --build
ruff check app
ruff format app
pytest
```

Before reporting done: `/check` (ruff check + format check).

## Git

Branch: `<type>/<description>/<initials>` (feat, fix, docs, chore, refactor, test).

## Docs

| Topic | Path |
| --- | --- |
| Architecture | `docs/architecture.md` |
| Glossary | `CONTEXT.md` |
| Claude setup | `.claude/SETUP.md` |
| Cursor rules | `.cursor/rules/README.md` |
