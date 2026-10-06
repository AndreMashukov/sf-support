"""Emulator shortcut: poll tickets.write_id and publish ticket.updated. No Firestore."""

from __future__ import annotations

import logging
import threading
import time

from sqlalchemy.exc import OperationalError

from app.db import SessionLocal
from app.models import Ticket
from app.support_bus.ticket_publish import publish_ticket_from_postgres

logger = logging.getLogger(__name__)

_started = False


def start_local_command_watch() -> None:
    global _started
    if _started:
        return
    _started = True
    threading.Thread(
        target=_watch_tickets, name="support-ticket-cdc", daemon=True
    ).start()
    logger.info("Local CDC shortcut polling tickets.write_id")


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
