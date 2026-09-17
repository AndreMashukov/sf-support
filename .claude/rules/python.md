---
paths:
  - "app/**/*.py"
  - "tests/**/*.py"
---

# Python

- Type hints on public functions. Prefer `X | None` over `Optional[X]`.
- No `Any` to silence the type checker.
- FastAPI: Pydantic models for request bodies. No raw dict in/out on new endpoints.
- SQLAlchemy 2.0 mapped columns. Do not use `query()` legacy API.
- Early returns for 401/403/404.
