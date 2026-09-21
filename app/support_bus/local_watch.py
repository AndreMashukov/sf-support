"""Emulator shortcut: poll supportCommands and ticket write_id, skip Datastream."""

from __future__ import annotations

import logging
import threading
import time

from sqlalchemy.exc import OperationalError

from app.db import SessionLocal
from app.models import Ticket
from app.support_bus.bus import publish_event
from app.support_bus.collections import COMMANDS
from app.support_bus.events import command_submitted_payload
from app.support_bus.firestore_io import firestore_client
from app.support_bus.ticket_publish import publish_ticket_from_postgres
from app.support_bus.worker import handle_command

logger = logging.getLogger(__name__)

_started = False


def start_local_command_watch() -> None:
    global _started
    if _started:
        return
    _started = True
    threading.Thread(
        target=_watch_commands, name="support-command-watch", daemon=True
    ).start()
    threading.Thread(
        target=_watch_tickets, name="support-ticket-cdc", daemon=True
    ).start()
    logger.info(
        "Local CDC shortcut polling %s and tickets.write_id", COMMANDS
    )


def _watch_commands() -> None:
    seen: set[str] = set()
    while True:
        try:
            for snap in firestore_client().collection(COMMANDS).stream():
                if snap.id in seen:
                    continue
                doc = snap.to_dict() or {}
                if doc.get("processed"):
                    seen.add(snap.id)
                    continue
                event = command_submitted_payload(snap.id, doc)
                domain = handle_command(event)
                if domain is not None:
                    publish_event(domain)
                seen.add(snap.id)
        except Exception:
            logger.exception("Local command poll failed")
        time.sleep(1)


def _watch_tickets() -> None:
    seen: dict[str, str] = {}
    while True:
        try:
            db = SessionLocal()
            try:
                rows = db.query(Ticket.id, Ticket.write_id).all()
            finally:
                db.close()
            for ticket_id, write_id in rows:
                tid = str(ticket_id)
                wid = str(write_id or "")
                if not wid:
                    continue
                if seen.get(tid) == wid:
                    continue
                publish_ticket_from_postgres(tid)
                seen[tid] = wid
        except OperationalError:
            pass
        except Exception:
            logger.exception("Local ticket poll failed")
        time.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_local_command_watch()
    threading.Event().wait()
