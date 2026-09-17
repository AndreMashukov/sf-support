---
paths:
  - "app/auth.py"
  - "app/api/**/*.py"
  - "app/models.py"
---

# Auth and tickets

- Verify Firebase ID tokens. Do not trust client-supplied `user_id` without the token.
- Staff only when `role == admin`.
- Users list/get only `user_id = principal.user_id`. Staff may list all.
- Do not enable Postgres RLS in v1. The API is the access layer (one service role).
- Never persist API keys or raw ID tokens in ticket messages.
