from __future__ import annotations

import json
import time
import uuid
from typing import Any
from urllib.parse import unquote


def new_write_id() -> str:
    return f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"


def command_submitted_payload(command_id: str, doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "v": 1,
        "event_type": "command.submitted",
        "write_id": str(doc.get("write_id") or new_write_id()),
        "command_id": command_id,
        "type": str(doc.get("type") or ""),
        "user_id": str(doc.get("userId") or ""),
        "user_email": str(doc.get("userEmail") or ""),
        "payload": doc.get("payload") if isinstance(doc.get("payload"), dict) else {},
    }


def ask_completed_payload(
    *,
    command_id: str,
    write_id: str,
    user_id: str,
    query: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "v": 1,
        "event_type": "ask.completed",
        "write_id": write_id,
        "command_id": command_id,
        "user_id": user_id,
        "query": query,
        "enough_context": result.get("enough_context", False),
        "answer": result.get("answer"),
        "citations": result.get("citations") or [],
        "no_answer_reason": result.get("no_answer_reason"),
        "status": "completed",
    }


def ticket_updated_payload(ticket: dict[str, Any]) -> dict[str, Any]:
    return {
        "v": 1,
        "event_type": "ticket.updated",
        "write_id": ticket.get("write_id"),
        "ticket_id": ticket.get("ticket_id"),
        "user_id": ticket.get("user_id"),
        "user_email": ticket.get("user_email"),
        "category": ticket.get("category"),
        "status": ticket.get("status") or "open",
        "title": ticket.get("title"),
        "url": ticket.get("url"),
        "created_at": ticket.get("created_at"),
        "closed_at": ticket.get("closed_at"),
        "closed_by": ticket.get("closed_by"),
        "messages": ticket.get("messages") or [],
    }


def parse_document_path(ce_document: str) -> tuple[str, str] | None:
    """Return (collection, doc_id) from an Eventarc document/subject path."""
    if not ce_document:
        return None
    decoded = unquote(ce_document).lstrip("/")
    if "/documents/" in decoded:
        rel = decoded.split("/documents/", 1)[1]
    elif decoded.startswith("documents/"):
        rel = decoded[len("documents/") :]
    else:
        rel = decoded
    parts = [part for part in rel.split("/") if part]
    if len(parts) < 2:
        return None
    return parts[0], parts[1]


def encode_bus_message(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload).encode("utf-8")
