"""Eventarc HTTP publisher: Firestore commands and Datastream GCS ticket CDC."""

from __future__ import annotations

import json
import logging
from urllib.parse import unquote

from fastapi import APIRouter, Request, Response

from app.settings import settings
from app.support_bus.bus import publish_event
from app.support_bus.collections import COMMANDS
from app.support_bus.datastream import parse_datastream_object
from app.support_bus.events import command_submitted_payload, parse_document_path
from app.support_bus.firestore_io import get_doc, should_ignore_collection
from app.support_bus.ticket_publish import publish_ticket_from_postgres

logger = logging.getLogger(__name__)

router = APIRouter()

GCS_FINALIZED = "google.cloud.storage.object.v1.finalized"


@router.post("/__eventarc/publish")
async def eventarc_publish(request: Request) -> Response:
    ce_type = request.headers.get("ce-type") or ""
    if GCS_FINALIZED in ce_type:
        return await _handle_gcs_finalized(request)
    return await _handle_firestore_command(request)


async def _handle_firestore_command(request: Request) -> Response:
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


async def _handle_gcs_finalized(request: Request) -> Response:
    body = await request.body()
    if not body:
        return Response(status_code=400)
    try:
        event_data = json.loads(body)
    except json.JSONDecodeError:
        return Response(status_code=400)
    if not isinstance(event_data, dict):
        return Response(status_code=400)
    bucket = str(event_data.get("bucket") or "")
    name = str(event_data.get("name") or "")
    if not bucket or not name:
        return Response(status_code=400)
    expected_bucket = (settings.support_cdc_gcs_bucket or "").strip()
    if expected_bucket and bucket != expected_bucket:
        logger.info("Skip GCS object from unexpected bucket %s", bucket)
        return Response(status_code=204)
    try:
        raw = _download_gcs_object(bucket, name)
    except Exception:
        logger.exception("GCS download failed for gs://%s/%s", bucket, name)
        return Response(status_code=500)
    ticket_ids = parse_datastream_object(raw)
    if not ticket_ids:
        return Response(status_code=204)
    for ticket_id in sorted(ticket_ids):
        message_id = publish_ticket_from_postgres(ticket_id)
        if not message_id:
            return Response(status_code=500)
    logger.info(
        "eventarc.datastream gs://%s/%s tickets=%s",
        bucket,
        name,
        ",".join(sorted(ticket_ids)),
    )
    return Response(status_code=204)


def _download_gcs_object(bucket: str, name: str) -> bytes:
    from google.cloud import storage

    client = storage.Client(project=settings.gcp_project_id or None)
    blob = client.bucket(bucket).blob(name)
    return blob.download_as_bytes()
