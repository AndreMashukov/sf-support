import json

from fastapi.testclient import TestClient

from app.main import app
from app.support_bus import bus, cdc, worker

client = TestClient(app)

TICKET_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def test_create_ticket_does_not_publish(monkeypatch) -> None:
    monkeypatch.setattr(worker, "persist_ticket", lambda **kwargs: None)
    result = worker.handle_command(
        {
            "type": "CreateTicket",
            "command_id": TICKET_ID,
            "user_id": "u1",
            "user_email": "u@x.y",
            "payload": {"category": "bug", "query": "broken"},
        }
    )
    assert result is None


def test_gcs_datastream_publishes_ticket_updated(monkeypatch) -> None:
    record = {
        "read_method": "postgres-cdc-wal",
        "table": "tickets",
        "change_type": "INSERT",
        "payload": {"id": TICKET_ID},
    }
    monkeypatch.setattr(
        cdc,
        "_download_gcs_object",
        lambda bucket, name: (json.dumps(record) + "\n").encode("utf-8"),
    )
    monkeypatch.setattr(
        cdc,
        "publish_ticket_from_postgres",
        lambda ticket_id: "msg-1" if ticket_id == TICKET_ID else None,
    )
    bus.reset_memory()
    response = client.post(
        "/__eventarc/publish",
        headers={"ce-type": "google.cloud.storage.object.v1.finalized"},
        content=json.dumps({"bucket": "proj-sf-support-cdc", "name": "support-cdc/x"}),
    )
    assert response.status_code == 204


def test_gcs_publish_failure_returns_500(monkeypatch) -> None:
    record = {
        "read_method": "postgres-cdc-wal",
        "table": "tickets",
        "change_type": "INSERT",
        "payload": {"id": TICKET_ID},
    }
    monkeypatch.setattr(
        cdc,
        "_download_gcs_object",
        lambda bucket, name: json.dumps(record).encode("utf-8"),
    )
    monkeypatch.setattr(cdc, "publish_ticket_from_postgres", lambda ticket_id: None)
    response = client.post(
        "/__eventarc/publish",
        headers={"ce-type": "google.cloud.storage.object.v1.finalized"},
        content=json.dumps({"bucket": "b", "name": "n"}),
    )
    assert response.status_code == 500
