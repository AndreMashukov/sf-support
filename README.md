# StudyForge Support

Separate Python app for StudyForge tickets and hybrid RAG help. Spec: [docs/architecture.md](docs/architecture.md). Domain terms: [CONTEXT.md](CONTEXT.md). Agent conventions: [AGENTS.md](AGENTS.md).

Sibling of `../study-forge`. Do not import `@study-forge` packages.

## Run

```bash
cp .env.example .env
docker compose up --build
```

- App: http://127.0.0.1:8000
- Health: http://127.0.0.1:8000/health
- Postgres: `127.0.0.1:5433` (user/password/db `support`)
- Set `STUDYFORGE_WEB_URL=http://localhost:4200` so the UI can link back to StudyForge web.

Local without Docker (Postgres must already be up):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

## Check

```bash
ruff check app
ruff format --check app
```

## Seed

`seed/workspace-agent-knowledge-base.md` is a copy of StudyForge platform policy. `seed/faq.md` is a small support FAQ. Ingest/reindex is not wired yet.

## Auth

Firebase ID tokens from the same project as StudyForge. Staff is custom claim `role: admin`. Verification is a 501 stub until wired.
