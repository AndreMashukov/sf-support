import os
from unittest.mock import MagicMock

import pytest

from app.rag.graph import (
    DEFAULT_NO_ANSWER,
    get_graph,
    run_how_it_works,
)


def _chunk(title: str, text: str = "body") -> dict:
    return {
        "text": text,
        "article_title": title,
        "article_id": "a1",
        "score": 0.5,
        "chunk_id": "c1",
    }


@pytest.fixture(autouse=True)
def reset_graph_cache() -> None:
    import app.rag.graph as graph_module

    graph_module._compiled_graph = None
    yield
    graph_module._compiled_graph = None


def test_zero_chunks_skips_llm(monkeypatch) -> None:
    grade = MagicMock()
    generate = MagicMock()
    monkeypatch.setattr("app.rag.graph.hybrid_search", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("app.rag.graph.rag_chat.grade_context", grade)
    monkeypatch.setattr("app.rag.graph.rag_chat.generate_cited_answer", generate)

    result = run_how_it_works("credits", "user-1")

    assert result["enough_context"] is False
    assert result["answer"] is None
    assert result["citations"] == []
    assert result["no_answer_reason"] == DEFAULT_NO_ANSWER
    assert result["user_id"] == "user-1"
    grade.assert_not_called()
    generate.assert_not_called()


def test_grade_false_skips_generate(monkeypatch) -> None:
    generate = MagicMock()
    monkeypatch.setattr(
        "app.rag.graph.hybrid_search",
        lambda *_args, **_kwargs: [_chunk("FAQ")],
    )
    monkeypatch.setattr(
        "app.rag.graph.rag_chat.chat_configured",
        lambda: True,
    )
    monkeypatch.setattr(
        "app.rag.graph.rag_chat.grade_context",
        lambda _q, _c: (False, "Chunks are off-topic."),
    )
    monkeypatch.setattr("app.rag.graph.rag_chat.generate_cited_answer", generate)

    result = run_how_it_works("credits", "user-2")

    assert result["enough_context"] is False
    assert result["no_answer_reason"] == DEFAULT_NO_ANSWER
    generate.assert_not_called()


def test_grade_true_returns_answer_and_citations(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag.graph.hybrid_search",
        lambda *_args, **_kwargs: [_chunk("StudyForge FAQ", "Credits reset monthly.")],
    )
    monkeypatch.setattr("app.rag.graph.rag_chat.chat_configured", lambda: True)
    monkeypatch.setattr(
        "app.rag.graph.rag_chat.grade_context",
        lambda _q, _c: (True, ""),
    )
    monkeypatch.setattr(
        "app.rag.graph.rag_chat.generate_cited_answer",
        lambda _q, _c: ("Credits reset monthly.", ["StudyForge FAQ"]),
    )

    result = run_how_it_works("How do credits work?", "user-3")

    assert result["enough_context"] is True
    assert result["answer"] == "Credits reset monthly."
    assert result["citations"] == ["StudyForge FAQ"]
    assert result["no_answer_reason"] is None


def test_grade_failure_is_no_answer_not_exception(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag.graph.hybrid_search",
        lambda *_args, **_kwargs: [_chunk("FAQ")],
    )
    monkeypatch.setattr("app.rag.graph.rag_chat.chat_configured", lambda: True)

    def boom(_q, _c):
        raise RuntimeError("Together down")

    monkeypatch.setattr("app.rag.graph.rag_chat.grade_context", boom)

    result = run_how_it_works("billing", "user-4")
    assert result["enough_context"] is False
    assert result["no_answer_reason"] == DEFAULT_NO_ANSWER


def test_generate_failure_is_no_answer(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.rag.graph.hybrid_search",
        lambda *_args, **_kwargs: [_chunk("FAQ")],
    )
    monkeypatch.setattr("app.rag.graph.rag_chat.chat_configured", lambda: True)
    monkeypatch.setattr(
        "app.rag.graph.rag_chat.grade_context",
        lambda _q, _c: (True, ""),
    )

    def boom(_q, _c):
        raise ValueError("parse fail")

    monkeypatch.setattr("app.rag.graph.rag_chat.generate_cited_answer", boom)

    result = run_how_it_works("rules", "user-5")
    assert result["enough_context"] is False
    assert result["answer"] is None
    assert result["no_answer_reason"] == DEFAULT_NO_ANSWER


def test_langsmith_project_env(monkeypatch) -> None:
    monkeypatch.setattr("app.rag.graph.hybrid_search", lambda *_a, **_k: [])
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.setattr(
        "app.rag.graph.settings.langsmith_project",
        "study-forge-support",
    )
    run_how_it_works("q", "u")
    assert os.environ.get("LANGSMITH_PROJECT") == "study-forge-support"


def test_graph_compiles_with_named_nodes() -> None:
    graph = get_graph()
    assert graph is not None
