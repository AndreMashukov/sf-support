from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app.models import (
    AskMessage,
    AskResolution,
    AuthorType,
    Message,
    RagRun,
    Ticket,
    TicketCategory,
    TicketStatus,
)

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def rag_run_to_result(run: RagRun) -> dict[str, Any]:
    return {
        "query": run.query,
        "enough_context": bool(run.enough_context),
        "answer": run.answer,
        "citations": list(run.citations or []),
        "no_answer_reason": run.no_answer_reason,
        "chunk_ids": [str(item) for item in (run.chunk_ids or [])],
        "user_id": run.user_id,
        "resolution": run.resolution,
        "ticket_id": str(run.ticket_id) if run.ticket_id else None,
        "resolved_at": run.resolved_at.isoformat() if run.resolved_at else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def _message_row_to_dict(row: AskMessage) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "author_type": row.author_type.value,
        "author_id": row.author_id,
        "body": row.body,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_ask_messages(command_id: str) -> list[dict[str, Any]]:
    if not command_id:
        return []
    try:
        db = SessionLocal()
        try:
            rows = (
                db.query(AskMessage)
                .filter(AskMessage.command_id == command_id)
                .order_by(AskMessage.created_at.asc())
                .all()
            )
            return [_message_row_to_dict(row) for row in rows]
        finally:
            db.close()
    except OperationalError:
        logger.warning("Skip ask_messages list: Postgres is not available")
        return []
    except Exception:
        logger.exception("Skip ask_messages list")
        return []


def conversation_from_ask_messages(
    messages: list[dict[str, Any]],
) -> list[dict[str, str]]:
    conversation: list[dict[str, str]] = []
    for message in messages:
        author = str(message.get("author_type") or "")
        body = str(message.get("body") or "").strip()
        if not body:
            continue
        if author == "user":
            conversation.append({"role": "user", "content": body})
        elif author == "system":
            conversation.append({"role": "assistant", "content": body})
    return conversation


def append_ask_message(
    *,
    command_id: str,
    author_type: str,
    body: str,
    author_id: str | None = None,
    message_id: uuid.UUID | None = None,
) -> dict[str, Any] | None:
    try:
        db = SessionLocal()
        try:
            row = AskMessage(
                id=message_id or uuid.uuid4(),
                command_id=command_id,
                author_type=AuthorType(author_type),
                author_id=author_id,
                body=body,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return _message_row_to_dict(row)
        finally:
            db.close()
    except OperationalError:
        logger.warning("Skip ask_message persist: Postgres is not available")
        return None
    except Exception:
        logger.exception("Skip ask_message persist")
        return None


def get_rag_run_row(command_id: str, user_id: str) -> RagRun | None:
    try:
        db = SessionLocal()
        try:
            return (
                db.query(RagRun)
                .filter(
                    RagRun.command_id == command_id,
                    RagRun.user_id == user_id,
                )
                .one_or_none()
            )
        finally:
            db.close()
    except OperationalError:
        return None
    except Exception:
        logger.exception("Skip rag_run row lookup")
        return None


def is_ask_thread_closed(command_id: str, user_id: str) -> bool:
    run = get_rag_run_row(command_id, user_id)
    if run is None:
        return True
    return run.resolution in {
        AskResolution.confirmed_helped.value,
        AskResolution.escalated.value,
    }


def update_rag_run_latest_result(
    command_id: str,
    user_id: str,
    result: dict[str, Any],
) -> None:
    try:
        db = SessionLocal()
        try:
            run = (
                db.query(RagRun)
                .filter(
                    RagRun.command_id == command_id,
                    RagRun.user_id == user_id,
                )
                .one_or_none()
            )
            if run is None:
                return
            chunk_ids = result.get("chunk_ids") or []
            run.enough_context = bool(result.get("enough_context"))
            run.answer = result.get("answer")
            run.citations = list(result.get("citations") or [])
            run.no_answer_reason = result.get("no_answer_reason")
            run.chunk_ids = [str(item) for item in chunk_ids]
            db.commit()
        finally:
            db.close()
    except OperationalError:
        logger.warning("Skip rag_run update: Postgres is not available")
    except Exception:
        logger.exception("Skip rag_run update")


def list_ask_messages_for_ticket(command_id: str, user_id: str) -> list[dict[str, Any]]:
    run = get_rag_run_row(command_id, user_id)
    if run is None:
        return []
    return list_ask_messages(command_id)


def persist_ask_run_from_result(
    user_id: str,
    query: str,
    command_id: str,
    result: dict[str, Any],
) -> None:
    if not command_id:
        return
    try:
        db = SessionLocal()
        try:
            existing = (
                db.query(RagRun).filter(RagRun.command_id == command_id).first()
            )
            if existing is not None:
                return
            chunk_ids = result.get("chunk_ids") or []
            db.add(
                RagRun(
                    user_id=user_id,
                    category=TicketCategory.how_it_works,
                    query=query,
                    command_id=command_id,
                    enough_context=bool(result.get("enough_context")),
                    answer=result.get("answer"),
                    citations=list(result.get("citations") or []),
                    no_answer_reason=result.get("no_answer_reason"),
                    chunk_ids=[str(item) for item in chunk_ids],
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


def get_rag_run_for_user(command_id: str, user_id: str) -> dict[str, Any] | None:
    if not command_id or not user_id:
        return None
    try:
        db = SessionLocal()
        try:
            run = (
                db.query(RagRun)
                .filter(
                    RagRun.command_id == command_id,
                    RagRun.user_id == user_id,
                )
                .one_or_none()
            )
            if run is None:
                return None
            return rag_run_to_result(run)
        finally:
            db.close()
    except OperationalError:
        logger.warning("Skip rag_run lookup: Postgres is not available")
        return None
    except Exception:
        logger.exception("Skip rag_run lookup")
        return None


def mark_rag_run_confirmed(command_id: str, user_id: str) -> dict[str, Any] | None:
    try:
        db = SessionLocal()
        try:
            run = (
                db.query(RagRun)
                .filter(
                    RagRun.command_id == command_id,
                    RagRun.user_id == user_id,
                )
                .one_or_none()
            )
            if run is None:
                return None
            if run.resolution in {
                AskResolution.confirmed_helped.value,
                AskResolution.escalated.value,
            }:
                return rag_run_to_result(run)
            run.resolution = AskResolution.confirmed_helped.value
            run.resolved_at = _utc_now()
            db.commit()
            db.refresh(run)
            return rag_run_to_result(run)
        finally:
            db.close()
    except OperationalError:
        logger.warning("Skip rag_run confirm: Postgres is not available")
        return None
    except Exception:
        logger.exception("Skip rag_run confirm")
        return None


def link_rag_run_escalated(
    command_id: str,
    user_id: str,
    ticket_id: uuid.UUID,
) -> bool:
    try:
        db = SessionLocal()
        try:
            run = (
                db.query(RagRun)
                .filter(
                    RagRun.command_id == command_id,
                    RagRun.user_id == user_id,
                )
                .one_or_none()
            )
            if run is None:
                return False
            if run.resolution == AskResolution.confirmed_helped.value:
                return False
            run.ticket_id = ticket_id
            run.resolution = AskResolution.escalated.value
            run.resolved_at = _utc_now()
            db.commit()
            return True
        finally:
            db.close()
    except OperationalError:
        logger.warning("Skip rag_run escalate link: Postgres is not available")
        return False
    except Exception:
        logger.exception("Skip rag_run escalate link")
        return False


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


def get_ticket_category(ticket_id: str) -> str | None:
    try:
        db = SessionLocal()
        try:
            ticket = db.get(Ticket, uuid.UUID(ticket_id))
            if ticket is None:
                return None
            return str(ticket.category.value)
        finally:
            db.close()
    except OperationalError:
        logger.warning("Skip ticket lookup: Postgres is not available")
        return None
    except Exception:
        logger.exception("Skip ticket lookup")
        return None


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
