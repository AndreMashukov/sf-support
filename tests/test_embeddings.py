from app.rag.embeddings import embeddings_configured, format_e5_input


def test_embeddings_configured_rejects_placeholder(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag.embeddings.settings.openrouter_api_key",
        "your-openrouter-api-key",
    )
    assert embeddings_configured() is False


def test_embeddings_configured_accepts_key(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag.embeddings.settings.openrouter_api_key",
        "sk-or-real",
    )
    assert embeddings_configured() is True


def test_format_e5_adds_passage_prefix() -> None:
    assert format_e5_input("hello", "passage") == "passage: hello"


def test_format_e5_keeps_existing_prefix() -> None:
    assert format_e5_input("passage: hello", "query") == "passage: hello"
