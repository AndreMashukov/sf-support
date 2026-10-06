from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.rag.graph import run_how_it_works
from app.support_bus.bus import publish_event
from app.support_bus.events import ask_completed_payload, new_write_id
from app.support_bus.postgres_copy import (
    append_ask_message,
    conversation_from_ask_messages,
    get_rag_run_for_user,
    get_ticket_category,
    is_ask_thread_closed,
    link_rag_run_escalated,
    list_ask_messages,
    list_ask_messages_for_ticket,
    mark_rag_run_confirmed,
    persist_ask_run_from_result,
    persist_ticket,
    persist_ticket_message,
    update_rag_run_latest_result,
)

logger = logging.getLogger(__name__)


def handle_command(event: dict[str, Any]) -> dict[str, Any] | None:
    command_type = str(event.get("type") or "")
    if command_type == "AskHowItWorks":
        return _handle_ask(event)
    if command_type == "FollowUpAsk":
        return _handle_follow_up_ask(event)
    if command_type == "CreateTicket":
        _handle_create_ticket(event)
        return None
    if command_type == "AppendMessage":
        _handle_append_message(event)
        return None
    if command_type == "MarkAskResolved":
        return _handle_mark_ask_resolved(event)
    logger.warning("Unknown support command type: %s", command_type)
    return None


def _iso() -> str:
    return datetime.now(UTC).isoformat()


def _rag_body_from_result(result: dict[str, Any]) -> str:
    answer = result.get("answer")
    if answer:
        body = str(answer)
        citations = result.get("citations") or []
        if citations:
            sources = ", ".join(str(item) for item in citations)
            body = f"{body}\n\nSources: {sources}"
        return body
    return str(
        result.get("no_answer_reason") or "I do not have that in the help articles."
    )


def _ask_payload_from_result_dict(
    *,
    command_id: str,
    write_id: str,
    user_id: str,
    query: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    messages = list_ask_messages(command_id)
    return ask_completed_payload(
        command_id=command_id,
        write_id=write_id,
        user_id=user_id,
        query=query,
        result=result,
        resolution=result.get("resolution"),
        resolved_at=result.get("resolved_at"),
        ticket_id=result.get("ticket_id"),
        created_at=result.get("created_at"),
        messages=messages,
    )


def _publish_ask_update(ask_command_id: str, user_id: str, query: str) -> None:
    result = get_rag_run_for_user(ask_command_id, user_id)
    if result is None:
        return
    payload = _ask_payload_from_result_dict(
        command_id=ask_command_id,
        write_id=new_write_id(),
        user_id=user_id,
        query=query or str(result.get("query") or ""),
        result=result,
    )
    if not publish_event(payload):
        logger.warning("Failed to publish ask.completed for %s", ask_command_id)


def _complete_ask_turn(
    *,
    command_id: str,
    user_id: str,
    user_query: str,
    author_id: str | None,
    conversation: list[dict[str, str]],
    initial_title_query: str | None = None,
) -> dict[str, Any] | None:
    result = run_how_it_works(user_query, user_id, conversation=conversation)
    if initial_title_query is not None:
        persist_ask_run_from_result(user_id, initial_title_query, command_id, result)
    else:
        update_rag_run_latest_result(command_id, user_id, result)

    append_ask_message(
        command_id=command_id,
        author_type="user",
        body=user_query,
        author_id=author_id,
    )
    append_ask_message(
        command_id=command_id,
        author_type="system",
        body=_rag_body_from_result(result),
        author_id=None,
    )

    snapshot = get_rag_run_for_user(command_id, user_id)
    if snapshot is None:
        snapshot = result
    return _ask_payload_from_result_dict(
        command_id=command_id,
        write_id=new_write_id(),
        user_id=user_id,
        query=str(snapshot.get("query") or initial_title_query or user_query),
        result=snapshot,
    )


def _handle_ask(event: dict[str, Any]) -> dict[str, Any] | None:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    query = str(payload.get("query") or "").strip()
    user_id = str(event.get("user_id") or "")
    command_id = str(event.get("command_id") or "")
    if not query or not command_id:
        return None
    payload_out = _complete_ask_turn(
        command_id=command_id,
        user_id=user_id,
        user_query=query,
        author_id=user_id,
        conversation=[],
        initial_title_query=query,
    )
    if payload_out is None:
        return None
    if not payload_out.get("created_at"):
        payload_out["created_at"] = _iso()
    return payload_out


def _handle_follow_up_ask(event: dict[str, Any]) -> dict[str, Any] | None:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    ask_command_id = str(payload.get("askCommandId") or "").strip()
    query = str(payload.get("query") or "").strip()
    user_id = str(event.get("user_id") or "")
    if not ask_command_id or not query or not user_id:
        return None
    if is_ask_thread_closed(ask_command_id, user_id):
        logger.warning("FollowUpAsk rejected: thread closed %s", ask_command_id)
        return None
    prior = list_ask_messages(ask_command_id)
    conversation = conversation_from_ask_messages(prior)
    return _complete_ask_turn(
        command_id=ask_command_id,
        user_id=user_id,
        user_query=query,
        author_id=user_id,
        conversation=conversation,
    )


def _append_rag_reply(
    *,
    ticket_id: str,
    user_id: str,
    query: str,
) -> None:
    result = run_how_it_works(query=query, user_id=user_id)
    write_id = new_write_id()
    message = {
        "id": str(uuid.uuid4()),
        "author_type": "system",
        "author_id": None,
        "body": _rag_body_from_result(result),
        "created_at": _iso(),
        "write_id": write_id,
    }
    if not persist_ticket_message(ticket_id=ticket_id, message=message):
        logger.warning("Could not append RAG reply to ticket %s", ticket_id)


def _handle_mark_ask_resolved(event: dict[str, Any]) -> dict[str, Any] | None:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    ask_command_id = str(payload.get("askCommandId") or "").strip()
    user_id = str(event.get("user_id") or "")
    if not ask_command_id or not user_id:
        logger.warning("MarkAskResolved missing askCommandId or user_id")
        return None
    result = mark_rag_run_confirmed(ask_command_id, user_id)
    if result is None:
        logger.warning("MarkAskResolved: no rag_run for %s", ask_command_id)
        return None
    return _ask_payload_from_result_dict(
        command_id=ask_command_id,
        write_id=new_write_id(),
        user_id=user_id,
        query=str(result.get("query") or ""),
        result=result,
    )


def _handle_create_ticket(event: dict[str, Any]) -> None:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    category = str(payload.get("category") or "bug")
    query = str(payload.get("query") or "").strip()
    url = payload.get("url")
    ask_command_id = str(payload.get("askCommandId") or "").strip()
    user_id = str(event.get("user_id") or "")
    user_email = str(event.get("user_email") or "")
    command_id = str(event.get("command_id") or "")
    try:
        ticket_id = uuid.UUID(command_id) if command_id else uuid.uuid4()
    except ValueError:
        ticket_id = uuid.uuid4()
    write_id = new_write_id()
    now = _iso()

    if category == "how_it_works" and ask_command_id:
        snapshot = get_rag_run_for_user(ask_command_id, user_id)
        if snapshot is None:
            logger.warning(
                "CreateTicket rejected: missing rag_run for ask %s", ask_command_id
            )
            return
        title = str(snapshot.get("query") or query)[:300] or "Support ticket"
        thread = list_ask_messages_for_ticket(ask_command_id, user_id)
        messages: list[dict[str, Any]] = []
        for item in thread:
            messages.append(
                {
                    "id": str(item.get("id") or uuid.uuid4()),
                    "author_type": str(item.get("author_type") or "user"),
                    "author_id": item.get("author_id"),
                    "body": str(item.get("body") or ""),
                    "created_at": item.get("created_at") or now,
                    "write_id": write_id,
                }
            )
        if not messages and query:
            messages = [
                {
                    "id": str(uuid.uuid4()),
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
        if link_rag_run_escalated(ask_command_id, user_id, ticket_id):
            _publish_ask_update(ask_command_id, user_id, title)
        return

    title = query[:300] or "Support ticket"
    messages = [
        {
            "id": str(uuid.uuid4()),
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
    if category == "how_it_works" and query:
        _append_rag_reply(ticket_id=str(ticket_id), user_id=user_id, query=query)


def _handle_append_message(event: dict[str, Any]) -> None:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    ticket_id = str(payload.get("ticketId") or "")
    body = str(payload.get("body") or "").strip()
    user_id = str(event.get("user_id") or "")
    if not ticket_id or not body:
        return
    write_id = new_write_id()
    message = {
        "id": str(uuid.uuid4()),
        "author_type": "user",
        "author_id": user_id,
        "body": body,
        "created_at": _iso(),
        "write_id": write_id,
    }
    if not persist_ticket_message(ticket_id=ticket_id, message=message):
        logger.warning("AppendMessage for unknown ticket %s", ticket_id)
        return
    if get_ticket_category(ticket_id) == "how_it_works":
        _append_rag_reply(ticket_id=ticket_id, user_id=user_id, query=body)
