"""Pub/Sub push consumer: fetch the command, persist Postgres, publish domain events."""

from __future__ import annotations

import base64
import json
import logging

from fastapi import APIRouter, Request, Response

from app.support_bus.bus import publish_event
from app.support_bus.collections import COMMANDS
from app.support_bus.events import command_submitted_payload
from app.support_bus.firestore_io import get_doc
from app.support_bus.worker import handle_command

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/pubsub/push")
async def pubsub_push(request: Request) -> Response:
    body = await request.body()
    try:
        envelope = json.loads(body)
        message = envelope.get("message") or {}
        data_b64 = message.get("data") or ""
        payload = json.loads(base64.b64decode(data_b64).decode("utf-8"))
    except Exception:
        return Response(status_code=400)
    if not isinstance(payload, dict):
        return Response(status_code=400)
    event_type = str(payload.get("event_type") or "")
    if event_type != "command.submitted":
        return Response(status_code=204)
    try:
        command_id = str(payload.get("command_id") or "")
        doc = get_doc(COMMANDS, command_id) if command_id else None
        if doc is None:
            return Response(status_code=500)
        event = command_submitted_payload(command_id, doc)
        domain = handle_command(event)
        if domain is not None and not publish_event(domain):
            return Response(status_code=500)
    except Exception:
        logger.exception("pubsub push failed for %s", event_type)
        return Response(status_code=500)
    return Response(status_code=204)
