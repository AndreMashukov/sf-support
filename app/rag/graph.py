"""LangGraph: retrieve, grade context, generate or no-answer."""

from app.rag.hybrid import hybrid_search


def run_how_it_works(query: str, user_id: str) -> dict:
    chunks = hybrid_search(query)
    if not chunks:
        return {
            "enough_context": False,
            "answer": None,
            "citations": [],
            "no_answer_reason": "No help-article chunks retrieved.",
            "user_id": user_id,
        }
    return {
        "enough_context": False,
        "answer": None,
        "citations": [],
        "no_answer_reason": "Generate node is not wired yet.",
        "user_id": user_id,
    }
