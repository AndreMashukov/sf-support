# Copilot eval: LLM judge and LangSmith traces

This doc explains the **LLM judge** used in the ticket copilot offline eval, the theory behind it, and how to read runs in LangSmith.

Implementation: `app/rag/copilot_eval.py`. Fixtures: `evals/copilot/cases.json`. Live command: `python -m app.rag.copilot_eval` (not CI).

---

## What we are evaluating

The **ticket copilot** is a LangGraph that loads an account snapshot, retrieves Help chunks, grades context, then either drafts a cited staff reply or refuses (with optional snapshot-only brief). Evals replay **four fixed stories** without hitting Postgres or hybrid search. Only **grade** and **draft** call the model in the live eval (plus the judge).

The judge does **not** run in production on real tickets. It only scores offline eval runs when you change prompts or models.

---

## Two layers: code checks and LLM judge

| Layer | Role | When it runs |
| --- | --- | --- |
| **Code checks** | Hard rules: regex, exact credit strings, empty draft, citation titles for answerable cases | Pytest (CI) and live eval |
| **LLM judge** | Soft compliance with **class rules** in natural language | Live eval only |

Both must pass for the live command to exit 0. Pytest stubs grade/draft and asserts **code checks only** so CI stays fast and deterministic without a Together key.

### Why not judge-only?

Code checks own **numbers and forbidden phrases** (included/spent credits, no “80 left”, no `$`, no refund promise). A judge can miss or misread digits. Code checks cannot capture every acceptable wording or edge phrasing. Together they reduce both **false pass** (unsafe draft slips through) and **false fail** (good draft rejected for style).

### LLM-as-judge (theory)

**LLM-as-judge** means a second model reads the **inputs the copilot had** (within limits) plus the **draft**, and returns a structured verdict against a **rubric** (here: `CLASS_RULES` per case class). It is common in eval pipelines when:

- Success is **policy-shaped** (“do not invent credits”, “cite Help”) rather than exact string match.
- Full human review does not scale on every prompt change.

Limitations to keep in mind:

- The judge is **another model**: it can disagree with code checks or with a human.
- It is **not calibrated** like a production classifier; treat it as a **regression signal** when prompts change.
- It does **not** see the golden “expected citation” field from JSON (by design), so it cannot cheat by matching a hidden label.

Our judge uses **structured JSON** (`pass`, `reason`) via the same Together client as grade/draft, with **thinking off** for reliable JSON.

---

## Case classes and judge rubric

Each row in `cases.json` has a `class`. The judge receives the matching paragraph from `CLASS_RULES`:

| Class | Intent |
| --- | --- |
| `answerable` | Help covers the report; draft should cite allowed article titles; no invented credit numbers outside snapshot. |
| `abstain` | Weak Help and no snapshot; **empty** suggested reply. |
| `billing_trap_with_snapshot` | User asks for balance; snapshot present; may quote **included** and **spent** exactly as account data; must not compute remaining balance, price, or refund/credit-change promises. |
| `billing_trap_no_snapshot` | User asks for credits/plan; snapshot missing; must not guess plan name or any credit number. |

Code checks enforce the strictest numeric and regex rules; the judge checks **overall** adherence to the class story (tone, labeling account data, empty vs harmful fill-in).

---

## What the judge sees

Built in `run_llm_judge()`:

**System message (fixed):**

- Judge the draft against class rules.
- `pass: true` only if fully compliant.
- Be strict on invented credits and remaining balances.

**User message (per case):**

- Class name and **Rules** text
- **User report** (`query` from fixture)
- **Account snapshot** (JSON or the string `snapshot missing`)
- **Help chunks** (fixed JSON from fixture)
- **Draft** (copilot `suggested_reply`, or `(empty)`)
- **Citations** list from the graph

**Not included:** `expected_citation_titles` from JSON (code checks use that for answerable cases).

---

## End-to-end flow (one case, live eval)

```
evals/copilot/cases.json
        |
        v
run_case_with_fixtures()     # stubs get_account_snapshot + hybrid_search
        |
        v
run_ticket_copilot()         # LangGraph: grade + draft (real Together)
        |                      LangSmith run name: ticket_copilot
        v
run_code_checks()            # deterministic
        |
        v
run_llm_judge()              # ChatOpenAI trace (Together)
        |
        v
PASS/FAIL line + langsmith_run_id
```

For each of the four cases you typically get **one root `ticket_copilot` trace** and **one `ChatOpenAI` trace** (the judge). An answerable case may include extra LLM child runs inside the graph (grade, draft).

---

## How to read LangSmith traces

### Project and environment

Traces go to LangSmith project **`sf-support`** (`LANGSMITH_PROJECT` in `.env`).

In the **agent** UI (sf-support), the default **Local** environment often shows “Waiting for traces…” because the app sends **classic project** traces, not `LANGSMITH_AGENT_ID` + `LANGSMITH_AGENT_ENVIRONMENT=local`.

To see eval runs in the UI:

- Open the **Production** environment for sf-support, or
- Use the workspace **session** view for project `sf-support` (direct project URL from LangSmith after opening a trace).

Set `LANGSMITH_TRACING=true` and a valid `LANGSMITH_API_KEY` before `python -m app.rag.copilot_eval`.

### Run names

| Run name | What it is |
| --- | --- |
| **`ticket_copilot`** | Root LangGraph run for one eval case. Metadata includes `ticket_id` like `eval-<case-id>`. Open this to see load snapshot, retrieve, grade_context, draft_reply or no_draft. |
| **`ChatOpenAI`** | Usually the **LLM judge** when input contains `Class: …` and `Rules:`. Output is JSON `{"pass": bool, "reason": string}`. |
| **`grade_context`**, **`draft_staff_reply`**, etc. | Child steps inside `ticket_copilot` when the graph called the model. |

Filter by **run name** `ticket_copilot` to see only copilot graphs; filter `ChatOpenAI` to see judge (and other LLM) calls.

### Reading a judge trace (`ChatOpenAI`)

1. **Input → Human message**  
   - **Class / Rules**: rubric for this fixture.  
   - **User report**: simulated ticket text.  
   - **Account snapshot**: fixture data or `snapshot missing`.  
   - **Help chunks**: what retrieval was stubbed to return.  
   - **Draft**: what staff would see as suggested reply (empty is valid for abstain / billing no snapshot).  
   - **Citations**: article titles the graph attached.

2. **Output**  
   - Parsed JSON: `pass` and `reason`.  
   - This does **not** change the draft; it only records eval outcome.

3. **Match to copilot**  
   Find **`ticket_copilot`** with the same **Start time** and the same **User report** in input. That run shows **why** the draft is empty or cites Help (routing, grade, no_draft, snapshot brief).

### Reading a copilot trace (`ticket_copilot`)

1. **Input**  
   Often the user query string (eval case query).

2. **Output / child runs**  
   - **`enough_context` false** and **`no_draft`**: empty reply or `snapshot_only_brief` when snapshot exists.  
   - **`draft_reply`**: cited answer for answerable cases.

3. **Metadata**  
   `ticket_id`, `snapshot_present`, LangGraph tags. Staff context in the app also stores `langsmith_run_id` on real tickets; eval uses fake ids `eval-<case-id>`.

### Time range

Eval batches finish in seconds. Use **Last 1 day** (or “Last 15 minutes” right after a run). Expect about **8 traces** per full eval (4 copilot + 4 judge) if each case grades and judges once.

---

## Commands

```bash
# CI-style (no Together, no judge)
pytest tests/test_copilot_eval.py

# Live eval + judge + traces
set -a && source .env && set +a
python -m app.rag.copilot_eval
```

Exit code **1** if any case fails code checks or judge `pass: false`.

---

## When to change what

| Change | Action |
| --- | --- |
| Copilot prompt or model in `app/rag/chat.py` / graph | Run live eval; review `ticket_copilot` and judge traces |
| New policy (e.g. new forbidden billing phrase) | Prefer **code check** first; extend `CLASS_RULES` if judge should enforce wording |
| New scenario | Add a row to `cases.json`, extend `run_code_checks` and pytest stubs |

---

## Related files

- `app/rag/copilot_eval.py` - `CLASS_RULES`, `JUDGE_SCHEMA`, `run_llm_judge`, `main()`
- `app/rag/ticket_graph.py` - `run_ticket_copilot`, LangSmith `run_name=ticket_copilot`
- `tests/test_copilot_eval.py` - stubbed graph, code checks only
- `evals/copilot/cases.json` - four fixtures
