"""Staff copilot for bug and billing tickets. Not shown to the user."""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, is_dataclass
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.rag import chat as rag_chat
from app.rag.hybrid import hybrid_search
from app.settings import settings
from app.support_bus.postgres_copy import get_account_snapshot

logger = logging.getLogger(__name__)

NO_DRAFT_REASON = "Help articles do not cover this report."
DRAFT_FAILED = "Copilot draft failed."


class TicketCopilotState(TypedDict, total=False):
    query: str
    user_id: str
    ticket_id: str
    snapshot: dict | None
    snapshot_missing: bool
    chunks: list[dict]
    enough_context: bool
    suggested_reply: str | None
    citations: list[str]
    no_draft_reason: str | None
    copilot_error: str | None


_compiled_graph = None


def snapshot_only_brief(snapshot: dict[str, Any]) -> str:
    """Quote snapshot fields. Does not compute a remaining balance."""
    return (
        "Account data (not a help article):\n"
        f"subscription status: {snapshot.get('subscription_status')}\n"
        f"billing status: {snapshot.get('billing_status')}\n"
        f"usage limits setup: {snapshot.get('usage_limits_setup_id')}\n"
        f"current period end: {snapshot.get('current_period_end')}\n"
        f"cancel at period end: {snapshot.get('cancel_at_period_end')}\n"
        f"pay as you go: {snapshot.get('pay_as_you_go_enabled')}\n"
        f"included credits: {snapshot.get('included_credits')}\n"
        f"spent credits: {snapshot.get('spent_credits')}"
    )


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


def _load_snapshot(state: TicketCopilotState) -> dict:
    snapshot = get_account_snapshot(state.get("user_id") or "")
    if snapshot is None:
        return {"snapshot": None, "snapshot_missing": True}
    return {"snapshot": snapshot, "snapshot_missing": False}


def _retrieve(state: TicketCopilotState) -> dict:
    chunks = hybrid_search(state.get("query") or "", limit=6)
    return {"chunks": [_chunk_to_dict(chunk) for chunk in chunks]}


def _grade(state: TicketCopilotState) -> dict:
    chunks = state.get("chunks") or []
    query = state.get("query") or ""
    if not chunks or not rag_chat.chat_configured():
        return {"enough_context": False, "no_draft_reason": NO_DRAFT_REASON}
    try:
        enough, reason = rag_chat.grade_context(query, chunks)
    except Exception:
        logger.exception("ticket copilot grade failed")
        return {
            "enough_context": False,
            "no_draft_reason": NO_DRAFT_REASON,
            "copilot_error": DRAFT_FAILED,
        }
    if enough:
        return {"enough_context": True, "no_draft_reason": None}
    return {
        "enough_context": False,
        "no_draft_reason": reason or NO_DRAFT_REASON,
    }


def _route_after_grade(
    state: TicketCopilotState,
) -> Literal["draft_reply", "no_draft"]:
    if state.get("enough_context"):
        return "draft_reply"
    return "no_draft"


def _draft_reply(state: TicketCopilotState) -> dict:
    try:
        answer, citations = rag_chat.draft_staff_reply(
            state.get("query") or "",
            state.get("chunks") or [],
            state.get("snapshot"),
        )
    except Exception:
        logger.exception("ticket copilot draft failed")
        return {
            "suggested_reply": None,
            "citations": [],
            "copilot_error": DRAFT_FAILED,
        }
    return {
        "suggested_reply": answer,
        "citations": citations,
        "copilot_error": None,
    }


def _no_draft(state: TicketCopilotState) -> dict:
    snapshot = state.get("snapshot")
    reply = snapshot_only_brief(snapshot) if snapshot else None
    return {
        "suggested_reply": reply,
        "citations": [],
        "no_draft_reason": state.get("no_draft_reason") or NO_DRAFT_REASON,
    }


def _build_graph():
    builder = StateGraph(TicketCopilotState)
    builder.add_node("load_account_snapshot", _load_snapshot)
    builder.add_node("retrieve", _retrieve)
    builder.add_node("grade_context", _grade)
    builder.add_node("draft_reply", _draft_reply)
    builder.add_node("no_draft", _no_draft)
    builder.add_edge(START, "load_account_snapshot")
    builder.add_edge("load_account_snapshot", "retrieve")
    builder.add_edge("retrieve", "grade_context")
    builder.add_conditional_edges(
        "grade_context",
        _route_after_grade,
        {"draft_reply": "draft_reply", "no_draft": "no_draft"},
    )
    builder.add_edge("draft_reply", END)
    builder.add_edge("no_draft", END)
    return builder.compile()


def get_ticket_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph()
    return _compiled_graph


def _invoke(state: TicketCopilotState) -> tuple[dict, str | None]:
    graph = get_ticket_graph()
    metadata = {
        "ticket_id": state.get("ticket_id") or "",
        "snapshot_present": not bool(state.get("snapshot_missing")),
    }
    config = {"metadata": metadata, "run_name": "ticket_copilot"}
    try:
        from langchain_core.tracers.context import collect_runs
    except ImportError:
        return graph.invoke(state, config=config), None
    with collect_runs() as collected:
        final = graph.invoke(state, config=config)
    run_id = None
    traced = getattr(collected, "traced_runs", None) or []
    if traced:
        run_id = str(traced[0].id)
    return final, run_id


def run_ticket_copilot(*, query: str, user_id: str, ticket_id: str) -> dict[str, Any]:
    _ensure_langsmith_project()
    final, run_id = _invoke(
        {
            "query": query,
            "user_id": user_id,
            "ticket_id": ticket_id,
            "snapshot": None,
            "snapshot_missing": True,
            "chunks": [],
            "enough_context": False,
            "suggested_reply": None,
            "citations": [],
            "no_draft_reason": None,
            "copilot_error": None,
        }
    )
    chunks = final.get("chunks") or []
    titles: list[str] = []
    snippets: list[dict[str, str]] = []
    chunk_ids: list[str] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        chunk_id = str(chunk.get("chunk_id") or "")
        title = str(chunk.get("article_title") or "")
        if chunk_id:
            chunk_ids.append(chunk_id)
        if title and title not in titles:
            titles.append(title)
        snippets.append(
            {
                "chunk_id": chunk_id,
                "article_title": title,
                "text": str(chunk.get("text") or ""),
            }
        )
    raw_snapshot = final.get("snapshot")
    snapshot = raw_snapshot if isinstance(raw_snapshot, dict) else None
    staff_context = {
        "snapshot_missing": snapshot is None,
        "snapshot": snapshot,
        "chunk_ids": chunk_ids,
        "article_titles": titles,
        "snippets": snippets,
        "no_draft_reason": final.get("no_draft_reason"),
        "copilot_error": final.get("copilot_error"),
        "langsmith_run_id": run_id,
        "enough_context": bool(final.get("enough_context")),
        "ticket_id": ticket_id,
    }
    citations = list(final.get("citations") or [])
    return {
        "staff_context": staff_context,
        "suggested_reply": final.get("suggested_reply"),
        "suggested_citations": citations,
    }
