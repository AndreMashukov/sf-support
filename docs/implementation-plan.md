# Implementation plan (remaining v1)

What is left to build in this repo. Product decisions stay in [architecture.md](architecture.md). Domain terms stay in [CONTEXT.md](../CONTEXT.md).

The shell is in place: FastAPI routes, SQLAlchemy models, Docker Compose, seed markdown, and a StudyForge **Help** link gated by an admin feature flag. Almost none of the v1 product behavior is wired. Do this work in order. Later slices depend on earlier ones.

## Done (do not redo)

- Sibling repo, no NX / `@study-forge` Python imports
- Compose stack (FastAPI + `pgvector/pgvector`)
- Route stubs, models, Jinja user/staff home pages
- StudyForge web **Help** link and admin **Support** feature flag (lives in the StudyForge repo)
- `STUDYFORGE_WEB_URL` back-link on support pages
- Firebase ID token verify, `Principal` mapping, Jinja email sign-in, no anonymous tickets

## 1. Firebase sign-in

Done. `GET /api/me` and staff routes use a verified Bearer token. `/` and `/staff` sign in with Firebase JS (emulator URL when set).

## 2. Real Postgres use

Tables exist as SQLAlchemy models. They are not a working index yet.

- Enable pgvector and `tsvector` on **Help chunks**
- Seed ingest: load `seed/*.md` as published **Help articles** (`source: seed`)
- Chunk markdown (start ~800 tokens, overlap ~120 unless eval says otherwise)
- Embed with OpenRouter `intfloat/multilingual-e5-large`
- Write `tsv` from the same chunk text (plus title)
- Reindex a published article in one transaction: delete old chunks, insert new ones

Do not embed raw ticket bodies or billing amounts.

## 3. Hybrid search and the how-it-works graph

`hybrid_search` returns no chunks. `run_how_it_works` never generates.

- Vector: cosine on `chunks.embedding`, top k (start at 8)
- Keyword: Postgres FTS on `tsv`, top k
- Fuse with RRF. Pass top 6 chunks to the graph
- LangGraph for **how_it_works** only: retrieve, grade context, generate cited answer or no-answer
- Citations are article titles. No invented credit numbers
- Zero chunks: skip the grade LLM, set not enough
- LangSmith project `study-forge-support` (not `study-forge`)

Bug and billing tickets do not enter this graph except an optional retrieve-only helper for `staff_context`.

## 4. Tickets

Create, list, get, message, and close are stubs.

- Users see only their tickets (`WHERE user_id = :uid`). Staff see all
- **How it works**: create an **open** ticket only after **Still need help**. Store the question, RAG draft, chunk ids, and a first user message
- **Bug** and **billing**: always create an **open** ticket. Optional URL. Optional `staff_context` from retrieve-only search. Do not show a generated resolution as if the ticket is done
- Thread messages: user, staff, system (RAG draft / no-answer)
- Staff close only. Do not auto-close from the model
- Lifecycle: **open** / **closed**. No email

## 5. User UI, then staff UI

Keep FastAPI + Jinja. Do not move this into NX `web` / `admin`.

**User**

- Sign in, category, question
- How-it-works result: answer + citations, or no-answer
- **That helped** (no ticket) and **Still need help**
- My tickets and ticket thread

**Staff** (`role: admin`)

- Open queue first
- Thread, reply, close
- Help article list, editor, publish, reindex

## 6. After the product loop works

- Emulator vs production Firebase (same project id, Admin verify)
- Deploy the Compose images (not Firebase Hosting)
- Turn the StudyForge **Support** feature flag on in production only when `/` is a real URL and sign-in works

## Out of scope for v1

- Email, SLA, assignments, CSAT, waiting-on-user
- Indexing past tickets or PII for search
- File or screenshot storage
- In-app Support page inside NX
- Passing ID tokens in query strings
- Kubernetes

## Suggested first slice

Seed ingest. That unblocks hybrid search, the graph, and tickets.
