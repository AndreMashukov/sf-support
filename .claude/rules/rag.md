---
paths:
  - "app/rag/**/*.py"
---

# RAG

- How-it-works only for generate. Bug and billing skip the generate node.
- Hybrid search: vector + `tsvector`, RRF, max 6 chunks.
- Index **Help articles** only. Never embed ticket bodies or billing amounts.
- If zero chunks or grade says not enough: no-answer + Still need help. Do not invent credits.
- Cite article titles. Together/MiniMax: disable thinking for structured JSON.
- LangSmith project `study-forge-support`.
