from __future__ import annotations

from typing import Any

from firebase_admin import firestore

from app.firebase_admin_app import init_firebase
from app.support_bus.collections import ASK_RESULTS_LEAN, MESSAGES, TICKETS_LEAN


def firestore_client():
    init_firebase()
    return firestore.client()


def get_doc(collection: str, doc_id: str) -> dict[str, Any] | None:
    snap = firestore_client().collection(collection).document(doc_id).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    data["_id"] = snap.id
    return data


def set_doc(collection: str, doc_id: str, data: dict[str, Any]) -> None:
    firestore_client().collection(collection).document(doc_id).set(data)


def set_subdoc(
    collection: str, doc_id: str, subcollection: str, sub_id: str, data: dict[str, Any]
) -> None:
    (
        firestore_client()
        .collection(collection)
        .document(doc_id)
        .collection(subcollection)
        .document(sub_id)
        .set(data)
    )


def should_ignore_collection(collection: str) -> bool:
    return collection in {TICKETS_LEAN, ASK_RESULTS_LEAN, MESSAGES}


def lean_newer(existing: dict[str, Any] | None, write_id: str) -> bool:
    if existing is None:
        return True
    return str(existing.get("write_id") or "") != write_id
