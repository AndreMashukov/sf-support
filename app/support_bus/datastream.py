"""Parse Datastream GCS JSON and extract ticket ids to publish."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

WATCHED_TABLES = frozenset({"tickets", "messages"})
SKIP_CHANGE_TYPES = frozenset({"DELETE", "UPDATE-DELETE"})


def parse_datastream_object(raw: bytes) -> set[str]:
    """Return ticket ids referenced by CDC records in a GCS object."""
    ticket_ids: set[str] = set()
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return ticket_ids
    for record in _iter_records(text):
        ticket_id = _ticket_id_from_record(record)
        if ticket_id:
            ticket_ids.add(ticket_id)
    return ticket_ids


def _iter_records(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    stripped = text.lstrip()
    if stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            logger.exception("Datastream JSON array parse failed")
            return records
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    records.append(item)
        return records
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("Skip invalid Datastream JSON line")
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def _ticket_id_from_record(record: dict[str, Any]) -> str | None:
    read_method = str(record.get("read_method") or "")
    if read_method.startswith("postgresql-backfill"):
        return None
    meta = record.get("source_metadata")
    meta_map = meta if isinstance(meta, dict) else {}
    table = str(record.get("table") or meta_map.get("table") or "")
    if table not in WATCHED_TABLES:
        return None
    change_type = str(
        record.get("change_type") or meta_map.get("change_type") or ""
    ).upper()
    if change_type in SKIP_CHANGE_TYPES:
        return None
    if meta_map.get("is_deleted") is True:
        return None
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return None
    if table == "tickets":
        ticket_id = payload.get("id")
    else:
        ticket_id = payload.get("ticket_id")
    if ticket_id is None:
        return None
    value = str(ticket_id).strip()
    return value or None
