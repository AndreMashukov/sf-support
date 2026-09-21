from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import selectinload

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
            if command_id:
                existing = (
                    db.query(RagRun).filter(RagRun.command_id == command_id).first()
                )
                if existing is not None:
                    return
            db.add(
                RagRun(
                    user_id=user_id,
                    category=TicketCategory.how_it_works,
                    query=query,
                    command_id=command_id,
                )
            )
            db.commit()
        except IntegrityError:
            db.rollback()
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
    write_id: str,
) -> None:
    try:
        db = SessionLocal()
        try:
            existing = db.get(Ticket, ticket_id)
            if existing is not None:
                return
            ticket = Ticket(
                id=ticket_id,
                user_id=user_id,
                user_email=user_email,
                category=TicketCategory(category),
                status=TicketStatus.open,
                title=title,
                url=url,
                write_id=write_id,
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
        except IntegrityError:
            db.rollback()
        finally:
            db.close()
    except OperationalError:
        logger.warning("Skip ticket persist: Postgres is not available")
    except Exception:
        logger.exception("Skip ticket persist")


def persist_ticket_message(*, ticket_id: str, message: dict[str, Any]) -> bool:
    write_id = str(message.get("write_id") or "")
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
                return False
            db.add(
                Message(
                    id=uuid.UUID(str(message["id"])),
                    ticket_id=ticket.id,
                    author_type=AuthorType(message["author_type"]),
                    author_id=message.get("author_id"),
                    body=message["body"],
                )
            )
            ticket.write_id = write_id
            db.commit()
            return True
        finally:
            db.close()
    except OperationalError:
        logger.warning("Skip ticket message persist: Postgres is not available")
        return False
    except Exception:
        logger.exception("Skip ticket message persist")
        return False
