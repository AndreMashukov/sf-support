import uuid
from unittest.mock import MagicMock

from app.models import AskResolution
from app.support_bus import worker


def test_handle_ask_persists_full_result(monkeypatch) -> None:
    captured: dict = {}
    stored_messages: list[dict] = []

    def capture(user_id, query, command_id, result):
        captured["args"] = (user_id, query, command_id, result)

    def append(**kwargs):
        row = {
            "id": f"m{len(stored_messages)}",
            "author_type": kwargs.get("author_type"),
            "body": kwargs.get("body"),
            "created_at": "2026-10-06T00:00:00+00:00",
        }
        stored_messages.append(row)
        return row

    monkeypatch.setattr(
        worker,
        "run_how_it_works",
        lambda query, user_id, conversation=None: {
            "enough_context": True,
            "answer": "Yes",
            "citations": ["FAQ"],
            "no_answer_reason": None,
            "chunk_ids": ["chunk-1"],
            "user_id": user_id,
        },
    )
    monkeypatch.setattr(worker, "persist_ask_run_from_result", capture)
    monkeypatch.setattr(worker, "append_ask_message", append)
    monkeypatch.setattr(worker, "list_ask_messages", lambda command_id: stored_messages)
    monkeypatch.setattr(
        worker,
        "get_rag_run_for_user",
        lambda command_id, user_id: {
            "query": "credits",
            "enough_context": True,
            "answer": "Yes",
            "citations": ["FAQ"],
            "no_answer_reason": None,
            "chunk_ids": ["chunk-1"],
            "user_id": user_id,
            "created_at": "2026-10-05T00:00:00+00:00",
        },
    )

    result = worker.handle_command(
        {
            "type": "AskHowItWorks",
            "command_id": "ask-1",
            "user_id": "user-1",
            "payload": {"query": "credits"},
        }
    )

    assert result is not None
    assert result["event_type"] == "ask.completed"
    assert captured["args"][2] == "ask-1"
    assert captured["args"][3]["chunk_ids"] == ["chunk-1"]
    assert result.get("created_at")


def test_create_ticket_with_ask_command_id_is_rejected(monkeypatch) -> None:
    graph = MagicMock()
    monkeypatch.setattr(worker, "run_how_it_works", graph)
    persisted: dict = {}
    monkeypatch.setattr(
        worker,
        "persist_ticket",
        lambda **kwargs: persisted.update(kwargs) or True,
    )
    published: list[dict] = []
    monkeypatch.setattr(
        worker, "publish_event", lambda payload: published.append(payload) or True
    )

    worker.handle_command(
        {
            "type": "CreateTicket",
            "command_id": str(uuid.uuid4()),
            "user_id": "user-1",
            "user_email": "a@b.c",
            "payload": {
                "category": "how_it_works",
                "query": "How?",
                "askCommandId": "ask-1",
            },
        }
    )

    graph.assert_not_called()
    assert persisted == {}
    assert published == []


def test_complete_ask_turn_fails_when_message_append_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        worker,
        "run_how_it_works",
        lambda query, user_id, conversation=None: {
            "enough_context": True,
            "answer": "Yes",
            "citations": [],
            "no_answer_reason": None,
            "chunk_ids": [],
            "user_id": user_id,
        },
    )
    monkeypatch.setattr(worker, "persist_ask_run_from_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker, "append_ask_message", lambda **kwargs: None)

    try:
        worker.handle_command(
            {
                "type": "AskHowItWorks",
                "command_id": "ask-fail",
                "user_id": "user-1",
                "payload": {"query": "credits"},
            }
        )
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_mark_ask_resolved_returns_payload(monkeypatch) -> None:
    monkeypatch.setattr(worker, "list_ask_messages", lambda command_id: [])
    monkeypatch.setattr(
        worker,
        "mark_rag_run_confirmed",
        lambda command_id, user_id: {
            "query": "Q",
            "enough_context": True,
            "answer": "A",
            "citations": [],
            "no_answer_reason": None,
            "chunk_ids": [],
            "user_id": user_id,
            "resolution": AskResolution.confirmed_helped.value,
            "resolved_at": "2026-10-06T00:00:00+00:00",
            "ticket_id": None,
            "created_at": "2026-10-05T00:00:00+00:00",
        },
    )

    result = worker.handle_command(
        {
            "type": "MarkAskResolved",
            "command_id": "mark-1",
            "user_id": "user-1",
            "payload": {"askCommandId": "ask-1"},
        }
    )

    assert result is not None
    assert result["resolution"] == AskResolution.confirmed_helped.value
    assert result["command_id"] == "ask-1"
