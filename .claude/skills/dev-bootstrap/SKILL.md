---
name: dev-bootstrap
description: Bring up local Support stack — env file, Docker Compose Postgres + API.
---

# Dev bootstrap

1. Confirm you are in `sf-support` (not the StudyForge NX repo).
2. If `.env` is missing, copy `.env.example` to `.env` (user fills secrets).
3. `docker compose up --build`
4. Check `http://127.0.0.1:8000/health`
5. For sign-in, run StudyForge Firebase emulators and set `FIREBASE_AUTH_EMULATOR_HOST` plus `FIREBASE_WEB_AUTH_EMULATOR_URL`.
6. Seed ingest needs a real `OPENROUTER_API_KEY`. Compose sets `SEED_ON_STARTUP=true`. Host: `python -m app.ingest`.

Report the health result. Do not claim hybrid search or the RAG graph works until those slices are implemented.
