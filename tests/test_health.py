from fastapi.testclient import TestClient

from app.main import app
from app.settings import settings

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_user_home_links_back_to_studyforge(monkeypatch) -> None:
    monkeypatch.setattr(settings, "studyforge_web_url", "http://localhost:4200")
    response = client.get("/")
    assert response.status_code == 200
    assert "StudyForge Support" in response.text
    assert "Back to StudyForge" in response.text
    assert 'href="http://localhost:4200"' in response.text
