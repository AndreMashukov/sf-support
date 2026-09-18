"""Emulator shortcut: poll supportCommands and run the worker."""

from __future__ import annotations

import logging
import threading
import time

from app.support_bus.bus import publish_event
from app.support_bus.collections import COMMANDS
from app.support_bus.events import command_submitted_payload
from app.support_bus.firestore_io import firestore_client
from app.support_bus.worker import handle_command

logger = logging.getLogger(__name__)

_started = False


def start_local_command_watch() -> None:
    global _started
    if _started:
        return
    _started = True
    thread = threading.Thread(target=_watch, name="support-command-watch", daemon=True)
    thread.start()
    logger.info("Local CDC shortcut polling %s", COMMANDS)


def _watch() -> None:
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_local_command_watch()
    threading.Event().wait()
