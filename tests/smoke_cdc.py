"""CDC smoke: Eventarc path parsing plus command.submitted handling."""

from fastapi.testclient import TestClient

from app.main import app
from app.support_bus.events import parse_document_path

client = TestClient(app)


def test_eventarc_unknown_path_is_noop() -> None:
    response = client.post(
        "/__eventarc/publish",
        headers={"ce-subject": "documents/other/x"},
    )
    assert response.status_code == 204


def test_parse_ticket_sot_path() -> None:
    assert parse_document_path(
        "projects/p/databases/(default)/documents/supportTicketSot/t1"
    ) == ("supportTicketSot", "t1")
