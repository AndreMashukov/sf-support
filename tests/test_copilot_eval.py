from __future__ import annotations

from app.rag.copilot_eval import (
    EvalCase,
    load_cases,
    run_case_with_fixtures,
    run_code_checks,
)
from app.rag.ticket_graph import NO_DRAFT_REASON, run_ticket_copilot


def test_load_cases_has_four_fixtures() -> None:
    cases = load_cases()
    assert len(cases) == 4
    classes = {case.class_name for case in cases}
    assert classes == {
        "answerable",
        "abstain",
        "billing_trap_with_snapshot",
        "billing_trap_no_snapshot",
    }


def test_code_checks_answerable_requires_citation() -> None:
    case = EvalCase(
        id="x",
        class_name="answerable",
        query="q",
        snapshot=None,
        chunks=[],
        expected_citation_titles=["Using StudyForge"],
    )
    failed = run_code_checks(
        case,
        {
            "suggested_reply": "A quiz costs about 5 credits.",
            "suggested_citations": [],
            "staff_context": {},
        },
    )
    assert any(not item.ok for item in failed)

    passed = run_code_checks(
        case,
        {
            "suggested_reply": "See Using StudyForge for estimates.",
            "suggested_citations": ["Using StudyForge"],
            "staff_context": {},
        },
    )
    assert passed[-1].ok


def test_code_checks_billing_trap_forbids_remaining_balance() -> None:
    case = EvalCase(
        id="b",
        class_name="billing_trap_with_snapshot",
        query="balance?",
        snapshot={"included_credits": 100, "spent_credits": 20},
        chunks=[],
        expected_citation_titles=[],
    )
    checks = run_code_checks(
        case,
        {
            "suggested_reply": (
                "Account data: included credits 100, spent credits 20. "
                "You have 80 credits left."
            ),
            "suggested_citations": [],
            "staff_context": {},
        },
    )
    assert any("remaining balance" in item.detail for item in checks if not item.ok)


def _stub_copilot(monkeypatch, case: EvalCase | None = None) -> None:
    monkeypatch.setattr(
        "app.rag.ticket_graph.rag_chat.chat_configured",
        lambda: True,
    )

    def grade_with_reason(query: str, chunks: list) -> tuple[bool, str]:
        if case and case.class_name == "answerable" and chunks:
            return True, ""
        return False, NO_DRAFT_REASON

    def draft(query: str, chunks: list, snapshot: dict | None) -> tuple[str, list[str]]:
        return (
            "A quiz typically costs about 5 credits. See Using StudyForge.",
            ["Using StudyForge"],
        )

    monkeypatch.setattr(
        "app.rag.ticket_graph.rag_chat.grade_context",
        grade_with_reason,
    )
    monkeypatch.setattr("app.rag.ticket_graph.rag_chat.draft_staff_reply", draft)


def _run_stubbed_case(case: EvalCase, monkeypatch) -> dict:
    monkeypatch.setattr(
        "app.rag.ticket_graph.get_account_snapshot",
        lambda user_id: case.snapshot,
    )
    monkeypatch.setattr(
        "app.rag.ticket_graph.hybrid_search",
        lambda query, limit=6: list(case.chunks),
    )
    _stub_copilot(monkeypatch, case)
    return run_ticket_copilot(
        query=case.query,
        user_id="eval-user",
        ticket_id=f"eval-{case.id}",
    )


def test_eval_cases_stubbed_end_to_end(monkeypatch) -> None:
    for case in load_cases():
        result = _run_stubbed_case(case, monkeypatch)
        checks = run_code_checks(case, result)
        assert all(item.ok for item in checks), (case.id, checks)


def test_run_case_with_fixtures_helper(monkeypatch) -> None:
    case = next(c for c in load_cases() if c.id == "billing-trap-with-snapshot")
    _stub_copilot(monkeypatch, case)
    result = run_case_with_fixtures(case)
    checks = run_code_checks(case, result)
    assert all(item.ok for item in checks)
