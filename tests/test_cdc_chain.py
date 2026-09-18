import base64
import json

from fastapi.testclient import TestClient

from app.main import app
from app.support_bus import bus, cdc, consumer, materialize, worker
from app.support_bus.collections import ASK_RESULTS_LEAN, ASK_SOT, COMMANDS, TICKET_SOT

client = TestClient(app)


def _envelope(payload: dict) -> dict:
    raw = json.dumps(payload).encode("utf-8")
    return {
        "message": {
            "data": base64.b64encode(raw).decode("ascii"),
            "messageId": "t",
        }
    }


def test_eventarc_unknown_path_is_noop() -> None:
    response = client.post(
        "/__eventarc/publish",
        headers={"ce-subject": "documents/other/x"},
    )
    assert response.status_code == 204


def test_command_to_ask_completed_without_firestore_writes(monkeypatch) -> None:
    store: dict[tuple[str, str], dict] = {}
    set_calls: list[tuple] = []

    def get_doc(collection: str, doc_id: str):
        row = store.get((collection, doc_id))
        if row is None:
            return None
        return {**row, "_id": doc_id}

    def set_doc(collection: str, doc_id: str, data: dict) -> None:
        set_calls.append((collection, doc_id, data))
        store[(collection, doc_id)] = dict(data)

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
    monkeypatch.setattr(worker, "persist_ask_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(cdc, "get_doc", get_doc)
    monkeypatch.setattr(consumer, "get_doc", get_doc)
    monkeypatch.setattr(consumer, "handle_command", worker.handle_command)
    monkeypatch.setattr(materialize, "get_doc", get_doc)
    monkeypatch.setattr(materialize, "set_doc", set_doc)
    bus.reset_memory()

    command_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    store[(COMMANDS, command_id)] = {
        "type": "AskHowItWorks",
        "userId": "u1",
        "userEmail": "u@x.y",
        "write_id": "w1",
        "payload": {"query": "credits"},
    }

    first = client.post(
        "/__eventarc/publish",
        headers={"ce-subject": f"documents/{COMMANDS}/{command_id}"},
    )
    assert first.status_code == 204
    published = bus.memory_messages()
    assert published[0]["payload"]["event_type"] == "command.submitted"

    bus.reset_memory()
    second = client.post("/pubsub/push", json=_envelope(published[0]["payload"]))
    assert second.status_code == 204
    assert (ASK_SOT, command_id) not in store
    domain = bus.memory_messages()
    assert domain[0]["payload"]["event_type"] == "ask.completed"
    assert domain[0]["payload"]["no_answer_reason"] == "No help-article chunks retrieved."
    assert set_calls == []

    materialize.materialize_ask_result(
        {
            "command_id": command_id,
            "write_id": domain[0]["payload"]["write_id"],
            "user_id": domain[0]["payload"]["user_id"],
            "query": domain[0]["payload"]["query"],
            "enough_context": domain[0]["payload"]["enough_context"],
            "answer": domain[0]["payload"]["answer"],
            "citations": domain[0]["payload"]["citations"],
            "no_answer_reason": domain[0]["payload"]["no_answer_reason"],
            "status": domain[0]["payload"]["status"],
        }
    )
    lean = store[(ASK_RESULTS_LEAN, command_id)]
    assert lean["userId"] == "u1"
    assert lean["noAnswerReason"] == "No help-article chunks retrieved."


def test_ticket_sot_eventarc_is_noop(monkeypatch) -> None:
    store = {
        (TICKET_SOT, "t1"): {
            "ticket_id": "t1",
            "user_id": "u1",
            "write_id": "w2",
            "title": "bug",
            "status": "open",
            "messages": [],
        }
    }

    def get_doc(collection: str, doc_id: str):
        row = store.get((collection, doc_id))
        return None if row is None else {**row, "_id": doc_id}

    monkeypatch.setattr(cdc, "get_doc", get_doc)
    bus.reset_memory()
    response = client.post(
        "/__eventarc/publish",
        headers={"ce-subject": "documents/supportTicketSot/t1"},
    )
    assert response.status_code == 204
    assert bus.memory_messages() == []
