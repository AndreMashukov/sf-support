from app.support_bus.events import command_submitted_payload, parse_document_path


def test_parse_eventarc_subject() -> None:
    parsed = parse_document_path("documents/supportCommands/cmd-1")
    assert parsed == ("supportCommands", "cmd-1")


def test_command_submitted_payload() -> None:
    payload = command_submitted_payload(
        "cmd-1",
        {
            "type": "AskHowItWorks",
            "userId": "user-1",
            "userEmail": "a@b.c",
            "write_id": "w1",
            "payload": {"query": "How do credits work?"},
        },
    )
    assert payload["event_type"] == "command.submitted"
    assert payload["user_id"] == "user-1"
    assert payload["payload"]["query"] == "How do credits work?"


def test_handle_ask_uses_graph(monkeypatch) -> None:
    from app.support_bus import worker

    monkeypatch.setattr(
        worker,
        "run_how_it_works",
        lambda query, user_id: {
            "enough_context": False,
            "answer": None,
            "citations": [],
            "no_answer_reason": "No help-article chunks retrieved.",
            "user_id": user_id,
        },
    )
    monkeypatch.setattr(worker, "persist_ask_run", lambda *args: None)

    result = worker.handle_command(
        {
            "type": "AskHowItWorks",
            "command_id": "cmd-1",
            "user_id": "user-1",
            "payload": {"query": "credits"},
        }
    )
    assert result is not None
    assert result["event_type"] == "ask.completed"
    assert result["command_id"] == "cmd-1"
    assert result["enough_context"] is False
