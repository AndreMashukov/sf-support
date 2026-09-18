from __future__ import annotations

from typing import Any

from app.support_bus.collections import ASK_RESULTS_LEAN, MESSAGES, TICKETS_LEAN
from app.support_bus.firestore_io import get_doc, lean_newer, set_doc, set_subdoc


def materialize_ask_result(sot: dict[str, Any]) -> None:
    command_id = str(sot.get("command_id") or sot.get("_id") or "")
    write_id = str(sot.get("write_id") or "")
    if not command_id:
        return
    existing = get_doc(ASK_RESULTS_LEAN, command_id)
    if not lean_newer(existing, write_id):
        return
    set_doc(
        ASK_RESULTS_LEAN,
        command_id,
        {
            "userId": sot.get("user_id"),
            "query": sot.get("query"),
            "enoughContext": sot.get("enough_context", False),
            "answer": sot.get("answer"),
            "citations": sot.get("citations") or [],
            "noAnswerReason": sot.get("no_answer_reason"),
            "status": sot.get("status") or "completed",
            "write_id": write_id,
        },
    )


def materialize_ticket(sot: dict[str, Any]) -> None:
    ticket_id = str(sot.get("ticket_id") or sot.get("_id") or "")
    write_id = str(sot.get("write_id") or "")
    if not ticket_id:
        return
    existing = get_doc(TICKETS_LEAN, ticket_id)
    if not lean_newer(existing, write_id):
        return
    set_doc(
        TICKETS_LEAN,
        ticket_id,
        {
            "userId": sot.get("user_id"),
            "userEmail": sot.get("user_email"),
            "category": sot.get("category"),
            "status": sot.get("status") or "open",
            "title": sot.get("title"),
            "url": sot.get("url"),
            "createdAt": sot.get("created_at"),
            "closedAt": sot.get("closed_at"),
            "closedBy": sot.get("closed_by"),
            "write_id": write_id,
        },
    )
    for message in sot.get("messages") or []:
        if not isinstance(message, dict):
            continue
        message_id = str(message.get("id") or "")
        if not message_id:
            continue
        set_subdoc(
            TICKETS_LEAN,
            ticket_id,
            MESSAGES,
            message_id,
            {
                "authorType": message.get("author_type"),
                "authorId": message.get("author_id"),
                "body": message.get("body"),
                "createdAt": message.get("created_at"),
                "write_id": message.get("write_id") or write_id,
            },
        )
