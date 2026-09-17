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

Report the health result. Do not claim the RAG graph works until embeddings and hybrid search are implemented.
