"""LangGraph: retrieve, grade context, generate or no-answer."""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, is_dataclass
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.rag import chat as rag_chat
from app.rag.hybrid import hybrid_search
from app.settings import settings

logger = logging.getLogger(__name__)

NO_CHUNKS_REASON = "No help-article chunks retrieved."
DEFAULT_NO_ANSWER = "I do not have that in the help articles."


class HowItWorksState(TypedDict, total=False):
    query: str
    user_id: str
    chunks: list[dict]
    enough_context: bool
    answer: str | None
    citations: list[str]
    no_answer_reason: str | None


_compiled_graph = None


def _ensure_langsmith_project() -> None:
    project = settings.langsmith_project.strip()
    if project:
        os.environ["LANGSMITH_PROJECT"] = project


def _chunk_to_dict(chunk: object) -> dict:
    if isinstance(chunk, dict):
        return chunk
    if is_dataclass(chunk):
        return asdict(chunk)
    raise TypeError("chunk must be RetrievedChunk or dict")


def _retrieve(state: HowItWorksState) -> dict:
    query = state["query"]
    chunks = hybrid_search(query, limit=6)
    return {"chunks": [_chunk_to_dict(chunk) for chunk in chunks]}


def _route_after_retrieve(
    state: HowItWorksState,
) -> Literal["grade_context", "no_answer"]:
    if not state.get("chunks"):
        return "no_answer"
    return "grade_context"


def _grade_context(state: HowItWorksState) -> dict:
    chunks = state.get("chunks") or []
    query = state["query"]
    if not rag_chat.chat_configured():
        return {
            "enough_context": False,
            "no_answer_reason": DEFAULT_NO_ANSWER,
        }
    try:
        enough, reason = rag_chat.grade_context(query, chunks)
    except Exception:
        return {
            "enough_context": False,
            "no_answer_reason": DEFAULT_NO_ANSWER,
        }
    if enough:
        return {"enough_context": True, "no_answer_reason": None}
    logger.info("how-it-works grade refused: %s", reason or "empty")
    return {
        "enough_context": False,
        "no_answer_reason": DEFAULT_NO_ANSWER,
    }


def _route_after_grade(
    state: HowItWorksState,
) -> Literal["generate_cited", "no_answer"]:
    if state.get("enough_context"):
        return "generate_cited"
    return "no_answer"


def _generate_cited(state: HowItWorksState) -> dict:
    chunks = state.get("chunks") or []
    query = state["query"]
    try:
        answer, citations = rag_chat.generate_cited_answer(query, chunks)
    except Exception:
        return {
            "enough_context": False,
            "answer": None,
            "citations": [],
            "no_answer_reason": DEFAULT_NO_ANSWER,
        }
    return {
        "enough_context": True,
        "answer": answer,
        "citations": citations,
        "no_answer_reason": None,
    }


def _no_answer(state: HowItWorksState) -> dict:
    if not state.get("chunks"):
        logger.info(NO_CHUNKS_REASON)
    return {
        "enough_context": False,
        "answer": None,
        "citations": [],
        "no_answer_reason": state.get("no_answer_reason") or DEFAULT_NO_ANSWER,
    }


def _build_graph():
    builder = StateGraph(HowItWorksState)
    builder.add_node("retrieve", _retrieve)
    builder.add_node("grade_context", _grade_context)
    builder.add_node("generate_cited", _generate_cited)
    builder.add_node("no_answer", _no_answer)
    builder.add_edge(START, "retrieve")
    builder.add_conditional_edges(
        "retrieve",
        _route_after_retrieve,
        {"grade_context": "grade_context", "no_answer": "no_answer"},
    )
    builder.add_conditional_edges(
        "grade_context",
        _route_after_grade,
        {"generate_cited": "generate_cited", "no_answer": "no_answer"},
    )
    builder.add_edge("generate_cited", END)
    builder.add_edge("no_answer", END)
    return builder.compile()


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph()
    return _compiled_graph


def _state_to_result(state: HowItWorksState) -> dict:
    return {
        "enough_context": bool(state.get("enough_context")),
        "answer": state.get("answer"),
        "citations": list(state.get("citations") or []),
        "no_answer_reason": state.get("no_answer_reason"),
        "user_id": state.get("user_id", ""),
    }


def run_how_it_works(query: str, user_id: str) -> dict:
    _ensure_langsmith_project()
    graph = get_graph()
    final = graph.invoke(
        {
            "query": query,
            "user_id": user_id,
            "chunks": [],
            "enough_context": False,
            "answer": None,
            "citations": [],
            "no_answer_reason": None,
        }
    )
    return _state_to_result(final)
