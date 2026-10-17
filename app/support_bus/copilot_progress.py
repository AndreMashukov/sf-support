"""Staff-facing summary of one ticket copilot run."""

from __future__ import annotations

from typing import Any


def _draft_status(*, error: str, has_reply: bool) -> str:
    if error and not has_reply:
        return "failed"
    if has_reply:
        return "done"
    return "skipped"


def copilot_progress(
    staff_context: dict[str, Any] | None,
    suggested_reply: str | None,
) -> dict[str, Any]:
    context = staff_context if isinstance(staff_context, dict) else None
    if context is None:
        return {
            "state": "pending",
            "label": "Copilot has not finished",
            "steps": [
                {"id": "saved", "label": "Ticket saved", "status": "done"},
                {"id": "copilot", "label": "Copilot graph", "status": "waiting"},
            ],
        }
    error = str(context.get("copilot_error") or "").strip()
    snapshot_missing = bool(context.get("snapshot_missing"))
    titles = context.get("article_titles")
    title_count = len(titles) if isinstance(titles, list) else 0
    enough = bool(context.get("enough_context"))
    reason = str(context.get("no_draft_reason") or "").strip()
    has_reply = bool(suggested_reply and str(suggested_reply).strip())
    steps = [
        {"id": "saved", "label": "Ticket saved", "status": "done", "detail": ""},
        {
            "id": "snapshot",
            "label": "Account snapshot",
            "status": "skipped" if snapshot_missing else "done",
            "detail": "Missing" if snapshot_missing else "Loaded",
        },
        {
            "id": "retrieve",
            "label": "Help retrieve",
            "status": "done" if title_count else "skipped",
            "detail": f"{title_count} article titles" if title_count else "No chunks",
        },
        {
            "id": "grade",
            "label": "Grade context",
            "status": "done" if enough else "skipped",
            "detail": "Enough Help context" if enough else (reason or "Not enough"),
        },
        {
            "id": "draft",
            "label": "Suggested reply",
            "status": _draft_status(error=error, has_reply=has_reply),
            "detail": error or ("Draft ready" if has_reply else "Empty"),
        },
    ]
    if error:
        state = "error"
        label = "Copilot error"
    elif has_reply and enough:
        state = "draft"
        label = "Cited draft"
    elif has_reply:
        state = "brief"
        label = "Snapshot brief"
    else:
        state = "empty"
        label = "No draft"
    return {
        "state": state,
        "label": label,
        "steps": steps,
        "langsmith_run_id": context.get("langsmith_run_id"),
    }
