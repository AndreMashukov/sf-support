"""Load ticket state from Postgres and publish ticket.updated to the bus."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app.models import Ticket
from app.support_bus.bus import publish_event
from app.support_bus.events import ticket_updated_payload

logger = logging.getLogger(__name__)


def load_ticket_event(ticket_id: str) -> dict[str, Any] | None:
    try:
        db = SessionLocal()
        try:
            ticket = (
                db.query(Ticket)
                .options(selectinload(Ticket.messages))
                .filter(Ticket.id == uuid.UUID(ticket_id))
                .one_or_none()
            )
            if ticket is None:
                return None
            return _ticket_event(ticket)
        finally:
            db.close()
    except OperationalError:
        logger.warning("Skip ticket load: Postgres is not available")
        return None
    except Exception:
        logger.exception("Skip ticket load for %s", ticket_id)
        return None


def publish_ticket_from_postgres(ticket_id: str) -> str | None:
    event = load_ticket_event(ticket_id)
    if event is None:
        logger.warning("No ticket row for publish: %s", ticket_id)
        return None
    payload = ticket_updated_payload(event)
    message_id = publish_event(payload)
    if message_id:
        logger.info(
            "ticket.publish ticket_id=%s write_id=%s message_id=%s",
            ticket_id,
            payload.get("write_id"),
            message_id,
        )
    return message_id


def _ticket_event(ticket: Ticket) -> dict[str, Any]:
    write_id = str(ticket.write_id or "")
    messages = []
    for row in ticket.messages:
        messages.append(
            {
                "id": str(row.id),
                "author_type": row.author_type.value,
                "author_id": row.author_id,
                "body": row.body,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "write_id": write_id,
            }
        )
    return {
        "ticket_id": str(ticket.id),
        "user_id": ticket.user_id,
        "user_email": ticket.user_email,
        "category": ticket.category.value,
        "status": ticket.status.value,
        "title": ticket.title,
        "url": ticket.url,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        "closed_by": ticket.closed_by,
        "write_id": write_id,
        "messages": messages,
    }
