"""Together chat via LangChain OpenAI-compatible client."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.settings import settings

TOGETHER_BASE_URL = "https://api.together.ai/v1"

GRADE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "enough_context": {
            "type": "boolean",
            "description": (
                "True if the chunks contain enough facts to answer without guessing."
            ),
        },
        "reason": {
            "type": "string",
            "description": (
                "Internal note for logs. Not shown to the user. "
                "Empty if enough_context is true."
            ),
        },
    },
    "required": ["enough_context", "reason"],
    "additionalProperties": False,
}

GENERATE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": (
                "Plain-language answer for the user. Do not mention retrieval, "
                "chunks, passages, or missing context."
            ),
        },
        "citation_titles": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Article titles cited. Each must appear in the allowed list."
            ),
        },
    },
    "required": ["answer", "citation_titles"],
    "additionalProperties": False,
}


def chat_configured() -> bool:
    key = settings.together_ai_api_key.strip()
    if not key or key.startswith("your-"):
        return False
    return True


def _thinking_off_extra_body(
    *, response_format: dict[str, Any] | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "reasoning": {"enabled": False},
        "thinking": {"type": "disabled"},
    }
    if response_format is not None:
        body["response_format"] = response_format
    return body


def _chat_model(*, response_format: dict[str, Any] | None = None) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.together_chat_model,
        api_key=settings.together_ai_api_key,
        base_url=TOGETHER_BASE_URL,
        temperature=0,
        extra_body=_thinking_off_extra_body(response_format=response_format),
    )


def _json_schema_format(name: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "schema": schema,
            "strict": True,
        },
    }


def _parse_json_content(content: str) -> dict[str, Any] | None:
    text = content.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None


def _format_chunks_for_prompt(chunks: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        title = str(chunk.get("article_title") or "Help article")
        body = str(chunk.get("text") or "").strip()
        blocks.append(f"[{index}] Title: {title}\n{body}")
    return "\n\n".join(blocks)


def grade_context(query: str, chunks: list[dict[str, Any]]) -> tuple[bool, str]:
    if not chat_configured():
        raise RuntimeError("TOGETHER_AI_API_KEY is not set")
    allowed_titles = _allowed_titles(chunks)
    system = (
        "You grade whether help excerpts can answer a StudyForge how-it-works "
        "question without guessing. Set enough_context true only when the excerpts "
        "clearly contain the facts needed. Do not infer billing amounts or credit "
        "numbers unless they appear in the excerpts. "
        "The reason is an internal log note and is not shown to the user."
    )
    human = (
        f"Question:\n{query}\n\n"
        f"Chunks:\n{_format_chunks_for_prompt(chunks)}\n\n"
        f"Allowed citation titles (for reference only): {', '.join(allowed_titles)}"
    )
    model = _chat_model(
        response_format=_json_schema_format("grade_context", GRADE_JSON_SCHEMA)
    )
    response = model.invoke(
        [SystemMessage(content=system), HumanMessage(content=human)]
    )
    content = (
        response.content if isinstance(response.content, str) else str(response.content)
    )
    parsed = _parse_json_content(content)
    if parsed is None or "enough_context" not in parsed:
        return False, "Could not parse grade response."
    enough = bool(parsed.get("enough_context"))
    reason = str(parsed.get("reason") or "").strip()
    return enough, reason


def generate_cited_answer(
    query: str,
    chunks: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    if not chat_configured():
        raise RuntimeError("TOGETHER_AI_API_KEY is not set")
    allowed = _allowed_titles(chunks)
    allowed_set = set(allowed)
    system = (
        "Answer the user question using only the help excerpts. "
        "Write for the user in plain language. "
        "Never mention chunks, excerpts, retrieval, context, passages, "
        "or that some information was missing. "
        "Do not invent policies, features, or credit numbers. "
        "citation_titles must be a subset of the allowed titles list and only "
        "include titles you actually used."
    )
    human = (
        f"Question:\n{query}\n\n"
        f"Help excerpts (internal, do not mention them):\n"
        f"{_format_chunks_for_prompt(chunks)}\n\n"
        f"Allowed citation titles: {json.dumps(allowed)}"
    )
    model = _chat_model(
        response_format=_json_schema_format("generate_cited", GENERATE_JSON_SCHEMA)
    )
    response = model.invoke(
        [SystemMessage(content=system), HumanMessage(content=human)]
    )
    content = (
        response.content if isinstance(response.content, str) else str(response.content)
    )
    parsed = _parse_json_content(content)
    if parsed is None:
        raise ValueError("Could not parse generate response.")
    answer = str(parsed.get("answer") or "").strip()
    if not answer:
        raise ValueError("Empty answer from generate.")
    raw_titles = parsed.get("citation_titles")
    if not isinstance(raw_titles, list):
        raw_titles = []
    citations: list[str] = []
    for title in raw_titles:
        if not isinstance(title, str):
            continue
        trimmed = title.strip()
        if trimmed in allowed_set and trimmed not in citations:
            citations.append(trimmed)
    if not citations and allowed:
        citations = allowed[:1]
    return answer, citations


def _allowed_titles(chunks: list[dict[str, Any]]) -> list[str]:
    titles: list[str] = []
    for chunk in chunks:
        title = str(chunk.get("article_title") or "").strip()
        if title and title not in titles:
            titles.append(title)
    return titles
