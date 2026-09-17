---
name: dev-bootstrap
description: Bring up local Support stack — env file, Docker Compose Postgres + API.
---

# Dev bootstrap

1. Confirm you are in `sf-support` (not the StudyForge NX repo).
2. If `.env` is missing, copy `.env.example` to `.env` (user fills secrets).
3. `docker compose up --build`
4. Check `http://127.0.0.1:8000/health`
5. Do not start StudyForge Firebase emulators unless the user is wiring Auth verify.

Report the health result. Do not claim the RAG graph works until embeddings and hybrid search are implemented.
