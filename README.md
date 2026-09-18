# StudyForge Support

Separate Python app for StudyForge tickets and hybrid RAG help. Spec: [docs/architecture.md](docs/architecture.md). Remaining v1 work: [docs/implementation-plan.md](docs/implementation-plan.md). Domain terms: [CONTEXT.md](CONTEXT.md). Agent conventions: [AGENTS.md](AGENTS.md).

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

`seed/workspace-agent-knowledge-base.md` is a copy of StudyForge platform policy. `seed/faq.md` is a small support FAQ.

Ingest loads those files as published Help articles (`source: seed`), chunks at 800/120 characters, embeds with OpenRouter e5, and writes `tsvector` from title plus chunk text. Reindex of one article is delete-then-insert in the same transaction.

```bash
# Compose API runs this on startup when OPENROUTER_API_KEY is set
docker compose up --build

# Host uvicorn (Postgres on :5433)
python -m app.ingest
```

Staff can reindex one article with `POST /api/articles/{id}/reindex`. Hybrid search is not wired yet.

If you already had a local volume from before Help-chunk columns existed: `docker compose down -v` then bring the stack up again.

## Auth

Firebase ID tokens from the same project as StudyForge. Sign in on `/` and `/staff` with email and password. The API expects `Authorization: Bearer <idToken>` and verifies it with Firebase Admin. Staff is custom claim `role: admin`. Anonymous accounts are rejected.

Local with StudyForge Firebase emulators: set `FIREBASE_AUTH_EMULATOR_HOST` for the API and `FIREBASE_WEB_AUTH_EMULATOR_URL=http://127.0.0.1:9099` for the browser. Seed user `test@example.com` / `Test123456!` has `role: admin`.
