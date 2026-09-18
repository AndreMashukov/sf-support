from __future__ import annotations

import json
import time
import uuid
from typing import Any


def new_write_id() -> str:
    return f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"


def command_submitted_payload(command_id: str, doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "v": 1,
        "event_type": "command.submitted",
        "write_id": str(doc.get("write_id") or new_write_id()),
        "command_id": command_id,
        "type": str(doc.get("type") or ""),
        "user_id": str(doc.get("userId") or ""),
        "user_email": str(doc.get("userEmail") or ""),
        "payload": doc.get("payload") if isinstance(doc.get("payload"), dict) else {},
    }


def parse_document_path(ce_document: str) -> tuple[str, str] | None:
    """Return (collection, doc_id) from an Eventarc document/subject path."""
    if not ce_document:
        return None
    decoded = ce_document.lstrip("/")
    if "/documents/" in decoded:
        rel = decoded.split("/documents/", 1)[1]
    elif decoded.startswith("documents/"):
        rel = decoded[len("documents/") :]
    else:
        rel = decoded
    parts = [part for part in rel.split("/") if part]
    if len(parts) < 2:
        return None
    return parts[0], parts[1]


def encode_bus_message(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload).encode("utf-8")
