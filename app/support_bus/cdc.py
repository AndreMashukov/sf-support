"""Optional Eventarc HTTP publisher for command.submitted (CLI and leftover triggers)."""

from __future__ import annotations

import logging
from urllib.parse import unquote

from fastapi import APIRouter, Request, Response

from app.support_bus.bus import publish_event
from app.support_bus.collections import COMMANDS
from app.support_bus.events import command_submitted_payload, parse_document_path
from app.support_bus.firestore_io import get_doc, should_ignore_collection

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/__eventarc/publish")
async def eventarc_publish(request: Request) -> Response:
    subject = (
        request.headers.get("ce-subject") or request.headers.get("ce-document") or ""
    )
    parsed = parse_document_path(unquote(subject))
    if parsed is None:
        return Response(status_code=204)
    collection, doc_id = parsed
    if should_ignore_collection(collection) or collection != COMMANDS:
        return Response(status_code=204)
    doc = get_doc(collection, doc_id)
    if doc is None:
        return Response(status_code=500)
    payload = command_submitted_payload(doc_id, doc)
    message_id = publish_event(payload)
    if not message_id:
        return Response(status_code=500)
    logger.info(
        "eventarc.publish %s %s message_id=%s",
        payload.get("event_type"),
        doc_id,
        message_id,
    )
    return Response(status_code=204)
