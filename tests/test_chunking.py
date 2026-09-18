from pathlib import Path

from app.rag.chunking import chunk_text, hash_content, title_from_markdown


def test_chunk_text_empty() -> None:
    assert chunk_text("  ") == []


def test_chunk_text_overlap() -> None:
    text = "a" * 1000
    chunks = chunk_text(text, chunk_size=800, overlap=120)
    assert len(chunks) == 2
    assert len(chunks[0]) == 800
    assert chunks[1].startswith("a" * 120)
    assert chunks[0][-120:] == chunks[1][:120]


def test_hash_content_stable() -> None:
    assert hash_content("hello") == hash_content("hello")
    assert hash_content("hello") != hash_content("Hello")


def test_title_from_first_heading(tmp_path: Path) -> None:
    path = tmp_path / "faq.md"
    title = title_from_markdown(path, "# StudyForge Support FAQ\n\nHello\n")
    assert title == "StudyForge Support FAQ"


def test_title_from_filename(tmp_path: Path) -> None:
    path = tmp_path / "workspace-agent-knowledge-base.md"
    assert title_from_markdown(path, "no heading") == "workspace agent knowledge base"
