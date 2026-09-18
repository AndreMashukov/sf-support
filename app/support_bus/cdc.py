"""Eventarc Firestore trigger → Pub/Sub. Only this module publishes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request, Response

from app.support_bus.collections import ASK_SOT, COMMANDS, TICKET_SOT
from app.support_bus.events import command_submitted_payload, parse_document_path
from app.support_bus.firestore_io import get_doc, should_ignore_collection
from app.support_bus.worker import handle_command

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/__eventarc/publish")
async def eventarc_publish(request: Request) -> Response:
    subject = (
        request.headers.get("ce-subject") or request.headers.get("ce-document") or ""
    )
    parsed = parse_document_path(subject)
    if parsed is None:
        return Response(status_code=204)
    collection, doc_id = parsed
    if should_ignore_collection(collection):
        return Response(status_code=204)
    if collection not in {COMMANDS, ASK_SOT, TICKET_SOT}:
        return Response(status_code=204)
    doc = get_doc(collection, doc_id)
    if doc is None:
        return Response(status_code=500)
    payload = _payload_for(collection, doc_id, doc)
    if payload is None:
        return Response(status_code=204)
    if payload.get("event_type") == "command.submitted":
        handle_command(payload)
        return Response(status_code=204)
    # Staging: Pub/Sub publish lives here. Local shortcut materializes in the worker.
    logger.info("CDC event %s %s", payload.get("event_type"), doc_id)
    return Response(status_code=204)


def _payload_for(
    collection: str, doc_id: str, doc: dict[str, Any]
) -> dict[str, Any] | None:
    if collection == COMMANDS:
        return command_submitted_payload(doc_id, doc)
    if collection == ASK_SOT:
        return {
            "v": 1,
            "event_type": "ask.completed",
            "write_id": doc.get("write_id"),
            "command_id": doc_id,
        }
    if collection == TICKET_SOT:
        return {
            "v": 1,
            "event_type": "ticket.created",
            "write_id": doc.get("write_id"),
            "ticket_id": doc_id,
        }
    return None
