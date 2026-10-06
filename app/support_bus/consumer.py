"""Pub/Sub push consumer: persist Postgres from the event body, publish domain events."""

from __future__ import annotations

import base64
import json
import logging

from fastapi import APIRouter, Request, Response

from app.support_bus.bus import publish_event
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
    command_id = str(payload.get("command_id") or "").strip()
    command_type = str(payload.get("type") or "").strip()
    if not command_id or not command_type:
        logger.warning("command.submitted missing command_id or type")
        return Response(status_code=204)
    try:
        domain = handle_command(payload)
        if domain is not None and not publish_event(domain):
            return Response(status_code=500)
        logger.info(
            "command.submitted handled %s type=%s domain=%s",
            command_id,
            command_type,
            None if domain is None else domain.get("event_type"),
        )
    except Exception:
        logger.exception("pubsub push failed for %s", command_id)
        return Response(status_code=500)
    return Response(status_code=204)
