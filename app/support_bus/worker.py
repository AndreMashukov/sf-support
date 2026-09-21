from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.rag.graph import run_how_it_works
from app.support_bus.events import ask_completed_payload, new_write_id
from app.support_bus.postgres_copy import persist_ask_run, persist_ticket, persist_ticket_message

logger = logging.getLogger(__name__)


def handle_command(event: dict[str, Any]) -> dict[str, Any] | None:
    command_type = str(event.get("type") or "")
    if command_type == "AskHowItWorks":
        return _handle_ask(event)
    if command_type == "CreateTicket":
        _handle_create_ticket(event)
        return None
    if command_type == "AppendMessage":
        _handle_append_message(event)
        return None
    logger.warning("Unknown support command type: %s", command_type)
    return None


def _iso() -> str:
    return datetime.now(UTC).isoformat()


def _handle_ask(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    query = str(payload.get("query") or "").strip()
    user_id = str(event.get("user_id") or "")
    command_id = str(event.get("command_id") or "")
    result = run_how_it_works(query=query, user_id=user_id)
    persist_ask_run(user_id, query, command_id)
    return ask_completed_payload(
        command_id=command_id,
        write_id=new_write_id(),
        user_id=user_id,
        query=query,
        result=result,
    )


def _handle_create_ticket(event: dict[str, Any]) -> None:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    category = str(payload.get("category") or "bug")
    query = str(payload.get("query") or "").strip()
    url = payload.get("url")
    user_id = str(event.get("user_id") or "")
    user_email = str(event.get("user_email") or "")
    try:
        ticket_id = uuid.UUID(str(event.get("command_id") or ""))
    except ValueError:
        ticket_id = uuid.uuid4()
    message_id = uuid.uuid4()
    write_id = new_write_id()
    now = _iso()
    title = query[:300] or "Support ticket"
    messages = [
        {
            "id": str(message_id),
            "author_type": "user",
            "author_id": user_id,
            "body": query,
            "created_at": now,
            "write_id": write_id,
        }
    ]
    persist_ticket(
        ticket_id=ticket_id,
        user_id=user_id,
        user_email=user_email,
        category=category,
        title=title,
        url=str(url) if url else None,
        messages=messages,
        write_id=write_id,
    )


def _handle_append_message(event: dict[str, Any]) -> None:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    ticket_id = str(payload.get("ticketId") or "")
    body = str(payload.get("body") or "").strip()
    if not ticket_id or not body:
        return
    write_id = new_write_id()
    message = {
        "id": str(uuid.uuid4()),
        "author_type": "user",
        "author_id": str(event.get("user_id") or ""),
        "body": body,
        "created_at": _iso(),
        "write_id": write_id,
    }
    if not persist_ticket_message(ticket_id=ticket_id, message=message):
        logger.warning("AppendMessage for unknown ticket %s", ticket_id)
