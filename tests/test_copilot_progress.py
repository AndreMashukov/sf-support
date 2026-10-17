from app.support_bus.copilot_progress import copilot_progress


def test_pending_when_copilot_has_not_saved() -> None:
    progress = copilot_progress(None, None)
    assert progress["state"] == "pending"
    assert progress["steps"][0]["status"] == "done"


def test_cited_draft_when_grade_passed() -> None:
    progress = copilot_progress(
        {
            "snapshot_missing": False,
            "article_titles": ["Credits"],
            "enough_context": True,
            "langsmith_run_id": "run-1",
        },
        "See Credits.",
    )
    assert progress["state"] == "draft"
    assert progress["langsmith_run_id"] == "run-1"


def test_snapshot_brief_when_grade_refused() -> None:
    progress = copilot_progress(
        {
            "snapshot_missing": False,
            "article_titles": [],
            "enough_context": False,
            "no_draft_reason": "Not enough",
        },
        "Account data",
    )
    assert progress["state"] == "brief"
    assert progress["label"] == "Snapshot brief"
