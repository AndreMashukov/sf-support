from fastapi.testclient import TestClient

from app.auth import principal_from_claims
from app.db import get_db
from app.main import app

client = TestClient(app)


def test_me_requires_bearer() -> None:
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing Bearer token"


def test_me_maps_verified_token(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.auth.verify_id_token",
        lambda _token: {
            "uid": "user-1",
            "email": "user@example.com",
            "role": "student",
            "firebase": {"sign_in_provider": "password"},
        },
    )
    response = client.get("/api/me", headers={"Authorization": "Bearer fake-id-token"})
    assert response.status_code == 200
    assert response.json() == {
        "user_id": "user-1",
        "email": "user@example.com",
        "is_staff": False,
    }


def test_staff_claim_allows_articles(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.auth.verify_id_token",
        lambda _token: {
            "uid": "admin-1",
            "email": "test@example.com",
            "role": "admin",
            "firebase": {"sign_in_provider": "password"},
        },
    )
    response = client.get(
        "/api/articles",
        headers={"Authorization": "Bearer fake-id-token"},
    )
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_non_staff_forbidden_on_articles(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.auth.verify_id_token",
        lambda _token: {
            "uid": "user-1",
            "email": "user@example.com",
            "firebase": {"sign_in_provider": "password"},
        },
    )
    response = client.get(
        "/api/articles",
        headers={"Authorization": "Bearer fake-id-token"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Staff only"


def test_anonymous_token_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.auth.verify_id_token",
        lambda _token: {
            "uid": "anon-1",
            "firebase": {"sign_in_provider": "anonymous"},
        },
    )
    response = client.get("/api/me", headers={"Authorization": "Bearer fake-id-token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Anonymous sign-in is not allowed"


def test_principal_from_admin_claims() -> None:
    principal = principal_from_claims(
        {
            "uid": "admin-1",
            "email": "test@example.com",
            "role": "admin",
            "firebase": {"sign_in_provider": "password"},
        }
    )
    assert principal.is_staff is True


def test_reindex_unknown_article_404(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.auth.verify_id_token",
        lambda _token: {
            "uid": "admin-1",
            "email": "test@example.com",
            "role": "admin",
            "firebase": {"sign_in_provider": "password"},
        },
    )

    class _Db:
        def get(self, _model, _id):
            return None

    def _override_db():
        yield _Db()

    app.dependency_overrides[get_db] = _override_db
    try:
        response = client.post(
            "/api/articles/11111111-1111-1111-1111-111111111111/reindex",
            headers={"Authorization": "Bearer fake-id-token"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 404
    assert response.json()["detail"] == "Article not found"
