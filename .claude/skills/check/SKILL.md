---
name: check
description: Run ruff check and format check without modifying files. Use before commits or when asked to check quality.
allowed-tools: Bash
---

# Check

From the repo root:

```bash
ruff check app
ruff format --check app
```

If `tests/` has tests, also run `pytest`.

Stop on first failure. Report file paths. Do not claim pass without command output.
