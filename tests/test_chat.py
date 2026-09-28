from app.rag.chat import _parse_json_content, generate_cited_answer


def test_parse_json_content_extracts_object() -> None:
    parsed = _parse_json_content(
        'Here is JSON:\n{"enough_context": true, "reason": ""}'
    )
    assert parsed == {"enough_context": True, "reason": ""}


def test_generate_filters_unknown_citation_titles(monkeypatch) -> None:
    monkeypatch.setattr("app.rag.chat.chat_configured", lambda: True)

    class FakeModel:
        def invoke(self, _messages):
            return type(
                "R",
                (),
                {
                    "content": (
                        '{"answer": "Use directories.", '
                        '"citation_titles": ["Real FAQ", "Invented"]}'
                    )
                },
            )()

    monkeypatch.setattr("app.rag.chat._chat_model", lambda **_kwargs: FakeModel())

    chunks = [{"article_title": "Real FAQ", "text": "Directories hold documents."}]
    answer, citations = generate_cited_answer("How do directories work?", chunks)
    assert answer == "Use directories."
    assert citations == ["Real FAQ"]
