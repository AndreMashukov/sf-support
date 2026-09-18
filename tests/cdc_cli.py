"""CLI evidence: command CDC, sfs Postgres path, no Firestore writes from sfs."""

from __future__ import annotations

import base64
import json
import sys

from fastapi.testclient import TestClient

from app.main import app
from app.support_bus import bus, cdc, consumer, materialize, worker
from app.support_bus.collections import ASK_RESULTS_LEAN, ASK_SOT, COMMANDS


def _envelope(payload: dict) -> dict:
    raw = json.dumps(payload).encode("utf-8")
    return {
        "message": {
            "data": base64.b64encode(raw).decode("ascii"),
            "messageId": "cli",
        }
    }


def main() -> int:
    store: dict[tuple[str, str], dict] = {}
    set_calls: list[tuple] = []

    def get_doc(collection: str, doc_id: str):
        row = store.get((collection, doc_id))
        if row is None:
            return None
        return {**row, "_id": doc_id}

    def set_doc(collection: str, doc_id: str, data: dict) -> None:
        set_calls.append((collection, doc_id))
        store[(collection, doc_id)] = dict(data)

    worker.run_how_it_works = lambda query, user_id: {  # type: ignore[method-assign]
        "enough_context": False,
        "answer": None,
        "citations": [],
        "no_answer_reason": "No help-article chunks retrieved.",
        "user_id": user_id,
    }
    worker.persist_ask_run = lambda *args, **kwargs: None  # type: ignore[method-assign]
    cdc.get_doc = get_doc  # type: ignore[method-assign]
    consumer.get_doc = get_doc  # type: ignore[method-assign]
    consumer.handle_command = worker.handle_command  # type: ignore[method-assign]
    materialize.get_doc = get_doc  # type: ignore[method-assign]
    materialize.set_doc = set_doc  # type: ignore[method-assign]
    bus.reset_memory()

    command_id = "11111111-1111-1111-1111-111111111111"
    store[(COMMANDS, command_id)] = {
        "type": "AskHowItWorks",
        "userId": "user-1",
        "userEmail": "user@example.com",
        "write_id": "w-cmd",
        "payload": {"query": "How do credits work?"},
    }

    client = TestClient(app)
    print("1. CDC POST /__eventarc/publish supportCommands")
    r1 = client.post(
        "/__eventarc/publish",
        headers={"ce-subject": f"documents/{COMMANDS}/{command_id}"},
    )
    print(f"   status={r1.status_code}")
    msgs = bus.memory_messages()
    print(f"   published={msgs[0]['payload']['event_type'] if msgs else None}")
    if r1.status_code != 204 or not msgs:
        return 1

    print("2. Pub/Sub POST /pubsub/push command.submitted")
    r2 = client.post("/pubsub/push", json=_envelope(msgs[0]["payload"]))
    print(f"   status={r2.status_code}")
    print(f"   sot_written={ (ASK_SOT, command_id) in store }")
    domain = bus.memory_messages()
    completed = [m for m in domain if m["payload"].get("event_type") == "ask.completed"]
    print(f"   ask_completed={bool(completed)}")
    if r2.status_code != 204 or (ASK_SOT, command_id) in store or not completed:
        return 1
    sfs_writes = list(set_calls)
    if sfs_writes:
        print(f"   unexpected_sfs_writes={sfs_writes}")
        return 1

    print("3. StudyForge lean projector (local stand-in)")
    payload = completed[0]["payload"]
    materialize.materialize_ask_result(
        {
            "command_id": command_id,
            "write_id": payload["write_id"],
            "user_id": payload["user_id"],
            "query": payload["query"],
            "enough_context": payload["enough_context"],
            "answer": payload["answer"],
            "citations": payload["citations"],
            "no_answer_reason": payload["no_answer_reason"],
            "status": payload["status"],
        }
    )
    lean = store.get((ASK_RESULTS_LEAN, command_id))
    print(f"   lean_reason={None if lean is None else lean.get('noAnswerReason')}")
    if lean is None:
        return 1

    print("EVIDENCE_OK")
    print(
        json.dumps(
            {
                "eventarc_command": r1.status_code,
                "consumer_command": r2.status_code,
                "sfs_firestore_writes": sfs_writes,
                "lean": lean,
            },
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
