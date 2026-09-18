from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.rag.graph import run_how_it_works
from app.settings import settings
from app.support_bus.collections import ASK_SOT, TICKET_SOT
from app.support_bus.events import new_write_id
from app.support_bus.firestore_io import set_doc
from app.support_bus.materialize import materialize_ask_result, materialize_ticket
from app.support_bus.postgres_copy import persist_ask_run, persist_ticket

logger = logging.getLogger(__name__)


def handle_command(event: dict[str, Any]) -> None:
    command_type = str(event.get("type") or "")
    if command_type == "AskHowItWorks":
        _handle_ask(event)
        return
    if command_type == "CreateTicket":
        _handle_create_ticket(event)
        return
    if command_type == "AppendMessage":
        _handle_append_message(event)
        return
    logger.warning("Unknown support command type: %s", command_type)


def _iso() -> str:
    return datetime.now(UTC).isoformat()


def _handle_ask(event: dict[str, Any]) -> None:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    query = str(payload.get("query") or "").strip()
    user_id = str(event.get("user_id") or "")
    command_id = str(event.get("command_id") or "")
    result = run_how_it_works(query=query, user_id=user_id)
    persist_ask_run(user_id, query, command_id)
    write_id = new_write_id()
    sot = {
        "command_id": command_id,
        "user_id": user_id,
        "query": query,
        "enough_context": result.get("enough_context", False),
        "answer": result.get("answer"),
        "citations": result.get("citations") or [],
        "no_answer_reason": result.get("no_answer_reason"),
        "status": "completed",
        "write_id": write_id,
    }
    set_doc(ASK_SOT, command_id, sot)
    if settings.local_cdc_shortcut:
        materialize_ask_result({**sot, "_id": command_id})


def _handle_create_ticket(event: dict[str, Any]) -> None:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    category = str(payload.get("category") or "bug")
    query = str(payload.get("query") or "").strip()
    url = payload.get("url")
    user_id = str(event.get("user_id") or "")
    user_email = str(event.get("user_email") or "")
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
    )
    sot = {
        "ticket_id": str(ticket_id),
        "user_id": user_id,
        "user_email": user_email,
        "category": category,
        "status": "open",
        "title": title,
        "url": url,
        "created_at": now,
        "closed_at": None,
        "closed_by": None,
        "write_id": write_id,
        "messages": messages,
    }
    set_doc(TICKET_SOT, str(ticket_id), sot)
    if settings.local_cdc_shortcut:
        materialize_ticket({**sot, "_id": str(ticket_id)})


def _handle_append_message(event: dict[str, Any]) -> None:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    ticket_id = str(payload.get("ticketId") or "")
    body = str(payload.get("body") or "").strip()
    if not ticket_id or not body:
        return
    from app.support_bus.firestore_io import get_doc

    existing = get_doc(TICKET_SOT, ticket_id)
    if existing is None:
        logger.warning("AppendMessage for unknown ticket %s", ticket_id)
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
    messages = list(existing.get("messages") or [])
    messages.append(message)
    existing["messages"] = messages
    existing["write_id"] = write_id
    set_doc(TICKET_SOT, ticket_id, existing)
    if settings.local_cdc_shortcut:
        materialize_ticket(existing)
