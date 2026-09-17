---
name: langsmith-trace
description: Use when adding or debugging LangSmith tracing for the how-it-works LangGraph.
---

# LangSmith tracing

- Project: `study-forge-support` (not `study-forge`).
- Set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` in `.env`.
- Trace the LangGraph how-it-works run. Do not attach online judges on production traces in v1.
- Never print API keys.
