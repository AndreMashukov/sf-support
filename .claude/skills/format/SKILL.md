---
name: format
description: Format Python with ruff. Use before commits or when format issues are reported.
allowed-tools: Bash
---

# Format

```bash
ruff format app
ruff check --fix app
```

Do not format `.env` or seed binaries.
