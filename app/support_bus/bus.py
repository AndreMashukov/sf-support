"""Pub/Sub publish. The Eventarc handler is the only caller."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from app.settings import settings

logger = logging.getLogger(__name__)

_memory: list[dict[str, Any]] = []


def reset_memory() -> None:
    _memory.clear()


def memory_messages() -> list[dict[str, Any]]:
    return list(_memory)


def publish_event(payload: dict[str, Any]) -> str | None:
    """Return message id, or None if publish failed."""
    backend = (settings.support_events_backend or "memory").strip().lower()
    if backend != "pubsub":
        message_id = str(uuid.uuid4())
        _memory.append({"message_id": message_id, "payload": dict(payload)})
        logger.info("bus.memory %s %s", payload.get("event_type"), message_id)
        return message_id
    try:
        from google.cloud import pubsub_v1

        project = settings.gcp_project_id or settings.firebase_project_id
        topic = settings.support_events_topic
        if topic.startswith("projects/"):
            topic_path = topic
        else:
            topic_path = f"projects/{project}/topics/{topic}"
        client = pubsub_v1.PublisherClient()
        data = json.dumps(payload, default=str).encode("utf-8")
        event_type = str(payload.get("event_type") or "")
        future = client.publish(topic_path, data=data, event_type=event_type)
        return str(future.result(timeout=8))
    except Exception:
        logger.exception("bus.pubsub failed")
        return None
