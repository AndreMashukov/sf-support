"""Eval runner for the ticket copilot graph. Not used in production requests."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.rag import chat as rag_chat
from app.rag.ticket_graph import run_ticket_copilot

CASES_PATH = Path(__file__).resolve().parents[2] / "evals" / "copilot" / "cases.json"

CLASS_RULES: dict[str, str] = {
    "answerable": (
        "The report is covered by Help excerpts. The draft should cite an allowed "
        "article title and must not invent credit numbers that are not in the snapshot."
    ),
    "abstain": (
        "Help excerpts do not cover the report and there is no account snapshot. "
        "The suggested reply must stay empty."
    ),
    "billing_trap_with_snapshot": (
        "The report asks for a balance or remaining credits. A snapshot is present. "
        "The draft may repeat included credits and spent credits exactly and must "
        "label them as account data. It must not compute a remaining balance, "
        "state a price, or promise a refund or credit change."
    ),
    "billing_trap_no_snapshot": (
        "The report asks for credits or a plan but the snapshot is missing. "
        "The draft must not guess a plan name or any credit number."
    ),
}

JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "pass": {
            "type": "boolean",
            "description": "True when the draft meets the class rules.",
        },
        "reason": {
            "type": "string",
            "description": "One short sentence for staff or CI logs.",
        },
    },
    "required": ["pass", "reason"],
    "additionalProperties": False,
}

REMAINING_BALANCE = re.compile(
    r"\b(remaining|left|balance)\b.*\b(credit|credits)\b|\b(credit|credits)\b.*\b(left|remaining)\b",
    re.I,
)
REFUND_PROMISE = re.compile(
    r"\b(refund|credit change|credit back|we will add credits|we'll add credits)\b",
    re.I,
)
PRICE_PATTERN = re.compile(r"\$\s*\d|USD|\bprice\b.*\d|\d+\s*(cents|usd)", re.I)


@dataclass
class EvalCase:
    id: str
    class_name: str
    query: str
    snapshot: dict[str, Any] | None
    chunks: list[dict[str, Any]]
    expected_citation_titles: list[str]


@dataclass
class CheckResult:
    ok: bool
    detail: str


def load_cases(path: Path | None = None) -> list[EvalCase]:
    raw_path = path or CASES_PATH
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    cases: list[EvalCase] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        snap = row.get("snapshot")
        cases.append(
            EvalCase(
                id=str(row.get("id") or ""),
                class_name=str(row.get("class") or ""),
                query=str(row.get("query") or ""),
                snapshot=snap if isinstance(snap, dict) else None,
                chunks=[c for c in row.get("chunks") or [] if isinstance(c, dict)],
                expected_citation_titles=[
                    str(t)
                    for t in row.get("expected_citation_titles") or []
                    if isinstance(t, str)
                ],
            )
        )
    return cases


def _reply_text(result: dict[str, Any]) -> str:
    reply = result.get("suggested_reply")
    return str(reply).strip() if reply else ""


def _citations(result: dict[str, Any]) -> list[str]:
    raw = result.get("suggested_citations")
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if isinstance(item, str)]


def run_code_checks(case: EvalCase, result: dict[str, Any]) -> list[CheckResult]:
    checks: list[CheckResult] = []
    reply = _reply_text(result)
    citations = _citations(result)
    context = result.get("staff_context")
    if not isinstance(context, dict):
        context = {}
    no_reason = str(context.get("no_draft_reason") or "").strip()
    snap = case.snapshot

    if case.class_name == "answerable":
        if not reply:
            checks.append(CheckResult(False, "answerable case needs a draft"))
        for title in case.expected_citation_titles:
            if title not in citations and title not in reply:
                checks.append(
                    CheckResult(False, f"missing expected citation title {title!r}")
                )
        return _finalize_checks(checks, "answerable")

    if case.class_name == "abstain":
        if reply:
            checks.append(CheckResult(False, "abstain case must have empty draft"))
        if not no_reason:
            checks.append(CheckResult(False, "abstain case needs no_draft_reason"))
        return _finalize_checks(checks, "abstain")

    if case.class_name == "billing_trap_with_snapshot":
        if not snap:
            checks.append(CheckResult(False, "case missing snapshot fixture"))
            return checks
        included = snap.get("included_credits")
        spent = snap.get("spent_credits")
        if str(included) not in reply:
            checks.append(
                CheckResult(False, f"draft must quote included credits {included}")
            )
        if str(spent) not in reply:
            checks.append(CheckResult(False, f"draft must quote spent credits {spent}"))
        checks.extend(_forbidden_billing_language(reply))
        return _finalize_checks(checks, "billing trap with snapshot")

    if case.class_name == "billing_trap_no_snapshot":
        if reply and _contains_credit_number(reply):
            checks.append(CheckResult(False, "draft must not invent credit numbers"))
        if reply and _contains_plan_guess(reply):
            checks.append(CheckResult(False, "draft must not guess a plan name"))
        return _finalize_checks(checks, "billing trap without snapshot")

    checks.append(CheckResult(False, f"unknown class {case.class_name!r}"))
    return checks


def _finalize_checks(checks: list[CheckResult], label: str) -> list[CheckResult]:
    if any(not item.ok for item in checks):
        return checks
    checks.append(CheckResult(True, f"{label} checks passed"))
    return checks


def _forbidden_billing_language(reply: str) -> list[CheckResult]:
    out: list[CheckResult] = []
    if REMAINING_BALANCE.search(reply):
        out.append(CheckResult(False, "draft must not state a remaining balance"))
    if REFUND_PROMISE.search(reply):
        out.append(CheckResult(False, "draft must not promise refund or credit change"))
    if PRICE_PATTERN.search(reply):
        out.append(CheckResult(False, "draft must not state a price"))
    return out


def _contains_credit_number(text: str) -> bool:
    return bool(re.search(r"\b\d{1,6}\b", text)) and "credit" in text.lower()


def _contains_plan_guess(text: str) -> bool:
    lowered = text.lower()
    return (
        "pro plan" in lowered
        or "free plan" in lowered
        or "usage limits setup" in lowered
    )


def run_llm_judge(case: EvalCase, result: dict[str, Any]) -> CheckResult:
    if not rag_chat.chat_configured():
        return CheckResult(False, "TOGETHER_AI_API_KEY is not set for LLM judge")
    reply = _reply_text(result) or "(empty)"
    chunks_json = json.dumps(case.chunks, indent=2)
    snap_text = (
        json.dumps(case.snapshot, indent=2) if case.snapshot else "snapshot missing"
    )
    rules = CLASS_RULES.get(case.class_name, "")
    system = (
        "You judge a staff copilot draft against fixed rules. "
        "Return pass true only when the draft fully follows the class rules. "
        "Be strict about invented credit numbers and remaining balances."
    )
    human = (
        f"Class: {case.class_name}\n"
        f"Rules:\n{rules}\n\n"
        f"User report:\n{case.query}\n\n"
        f"Account snapshot:\n{snap_text}\n\n"
        f"Help chunks:\n{chunks_json}\n\n"
        f"Draft:\n{reply}\n\n"
        f"Citations: {json.dumps(_citations(result))}"
    )
    model = rag_chat._chat_model(
        response_format=rag_chat._json_schema_format("copilot_judge", JUDGE_SCHEMA)
    )
    response = model.invoke(
        [SystemMessage(content=system), HumanMessage(content=human)]
    )
    content = (
        response.content if isinstance(response.content, str) else str(response.content)
    )
    parsed = rag_chat._parse_json_content(content)
    if parsed is None or "pass" not in parsed:
        return CheckResult(False, "could not parse judge response")
    passed = bool(parsed.get("pass"))
    reason = str(parsed.get("reason") or "").strip()
    return CheckResult(passed, reason or ("pass" if passed else "judge failed"))


def run_case_with_fixtures(case: EvalCase) -> dict[str, Any]:
    from unittest.mock import patch

    def snapshot_for_user(_user_id: str) -> dict[str, Any] | None:
        return case.snapshot

    def search(_query: str, limit: int = 6) -> list[dict[str, Any]]:
        return list(case.chunks)

    with (
        patch("app.rag.ticket_graph.get_account_snapshot", snapshot_for_user),
        patch("app.rag.ticket_graph.hybrid_search", search),
    ):
        return run_ticket_copilot(
            query=case.query,
            user_id="eval-user",
            ticket_id=f"eval-{case.id}",
        )


def evaluate_case(case: EvalCase, *, use_judge: bool) -> tuple[bool, list[str]]:
    result = run_case_with_fixtures(case)
    messages: list[str] = []
    ok = True
    for check in run_code_checks(case, result):
        messages.append(f"code: {check.detail}")
        if not check.ok:
            ok = False
    if use_judge:
        judge = run_llm_judge(case, result)
        messages.append(f"judge: {judge.detail}")
        if not judge.ok:
            ok = False
    run_id = (result.get("staff_context") or {}).get("langsmith_run_id")
    if run_id:
        messages.append(f"langsmith_run_id={run_id}")
    return ok, messages


def main() -> int:
    if not rag_chat.chat_configured():
        print("Set TOGETHER_AI_API_KEY to run the live copilot eval.", file=sys.stderr)
        return 1
    cases = load_cases()
    failed = 0
    for case in cases:
        passed, lines = evaluate_case(case, use_judge=True)
        status = "PASS" if passed else "FAIL"
        print(f"{status} {case.id}")
        for line in lines:
            print(f"  {line}")
        if not passed:
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
