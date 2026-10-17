from fastapi.testclient import TestClient

from app.main import app
from app.rag.ticket_graph import run_ticket_copilot, snapshot_only_brief
from app.support_bus import worker

client = TestClient(app)

SNAPSHOT = {
    "subscription_status": "active",
    "billing_status": "ok",
    "usage_limits_setup_id": "plan-pro",
    "current_period_end": "2026-11-01T00:00:00+00:00",
    "cancel_at_period_end": False,
    "pay_as_you_go_enabled": False,
    "included_credits": 100,
    "spent_credits": 20,
    "updated_at": "2026-10-17T00:00:00+00:00",
}


def test_snapshot_brief_quotes_credits_without_a_balance() -> None:
    brief = snapshot_only_brief(SNAPSHOT)
    assert "included credits: 100" in brief
    assert "spent credits: 20" in brief
    assert "Account data" in brief
    assert "80" not in brief
    assert "remaining" not in brief.lower()


def test_grade_refusal_with_snapshot_writes_brief(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag.ticket_graph.get_account_snapshot",
        lambda user_id: SNAPSHOT,
    )
    monkeypatch.setattr(
        "app.rag.ticket_graph.hybrid_search",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        "app.rag.ticket_graph.rag_chat.chat_configured",
        lambda: False,
    )
    result = run_ticket_copilot(
        query="I was charged twice",
        user_id="u1",
        ticket_id="t1",
    )
    assert result["suggested_citations"] == []
    assert "included credits: 100" in result["suggested_reply"]
    assert result["staff_context"]["snapshot_missing"] is False
    assert result["staff_context"]["no_draft_reason"]
    assert result["staff_context"]["ticket_id"] == "t1"


def test_grade_refusal_without_snapshot_leaves_reply_empty(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag.ticket_graph.get_account_snapshot",
        lambda user_id: None,
    )
    monkeypatch.setattr(
        "app.rag.ticket_graph.hybrid_search",
        lambda *_args, **_kwargs: [],
    )
    result = run_ticket_copilot(query="button broken", user_id="u1", ticket_id="t2")
    assert result["suggested_reply"] is None
    assert result["staff_context"]["snapshot_missing"] is True
    assert result["staff_context"]["no_draft_reason"]


def test_create_bug_ticket_runs_copilot_once(monkeypatch) -> None:
    calls: list[str] = []

    def persist(**kwargs):
        return True

    def already(ticket_id):
        return False

    def run(*, query, user_id, ticket_id):
        calls.append(ticket_id)
        return {
            "staff_context": {"ticket_id": ticket_id, "snapshot_missing": True},
            "suggested_reply": None,
            "suggested_citations": [],
        }

    saved: dict = {}

    def save(**kwargs):
        saved.update(kwargs)
        return True

    monkeypatch.setattr(worker, "persist_ticket", persist)
    monkeypatch.setattr(worker, "ticket_copilot_already_ran", already)
    monkeypatch.setattr(worker, "run_ticket_copilot", run)
    monkeypatch.setattr(worker, "save_ticket_copilot", save)
    worker.handle_command(
        {
            "type": "CreateTicket",
            "command_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "user_id": "u1",
            "user_email": "u@x.y",
            "payload": {"category": "billing", "query": "credits"},
        }
    )
    assert calls == ["bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"]
    assert saved["suggested_reply"] is None


def test_staff_ticket_page_renders() -> None:
    response = client.get("/staff/tickets/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    assert response.status_code == 200
    assert "Suggested reply" in response.text
    assert "Post" in response.text
