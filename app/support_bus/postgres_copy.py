from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.exc import OperationalError

from app.db import SessionLocal
from app.models import (
    AuthorType,
    Message,
    RagRun,
    Ticket,
    TicketCategory,
    TicketStatus,
)

logger = logging.getLogger(__name__)


def persist_ask_run(user_id: str, query: str, command_id: str) -> None:
    try:
        db = SessionLocal()
        try:
            db.add(
                RagRun(
                    user_id=user_id,
                    category=TicketCategory.how_it_works,
                    query=query,
                    command_id=command_id,
                )
            )
            db.commit()
        finally:
            db.close()
    except OperationalError:
        logger.warning("Skip rag_runs persist: Postgres is not available")
    except Exception:
        logger.exception("Skip rag_runs persist")


def persist_ticket(
    *,
    ticket_id: uuid.UUID,
    user_id: str,
    user_email: str,
    category: str,
    title: str,
    url: str | None,
    messages: list[dict[str, Any]],
) -> None:
    try:
        db = SessionLocal()
        try:
            ticket = Ticket(
                id=ticket_id,
                user_id=user_id,
                user_email=user_email,
                category=TicketCategory(category),
                status=TicketStatus.open,
                title=title,
                url=url,
            )
            db.add(ticket)
            for message in messages:
                db.add(
                    Message(
                        id=uuid.UUID(str(message["id"])),
                        ticket_id=ticket_id,
                        author_type=AuthorType(message["author_type"]),
                        author_id=message.get("author_id"),
                        body=message["body"],
                    )
                )
            db.commit()
        finally:
            db.close()
    except OperationalError:
        logger.warning("Skip ticket persist: Postgres is not available")
    except Exception:
        logger.exception("Skip ticket persist")
