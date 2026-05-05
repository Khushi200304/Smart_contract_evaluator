"""Pipeline — Agent-orchestrated contract processing.

Replaces the old sequential LLM pipeline with autonomous agents powered
by the Microsoft Agent Framework. Each public function delegates to a
specialized agent that uses tool-calling to persist results.

Public API (unchanged from before):
  - process_contract_full(db, contract) -> dict
  - rag_answer(db, contract_id, question, contract_excerpt) -> (str, list[str])
  - draft_action_message(alert_message, contract_filename) -> dict
"""

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import Contract, ContractRisk, ContractTask
from app.agents.orchestrator import create_orchestrator_agent
from app.agents.rag_agent import create_rag_agent
from app.agents.action_agent import create_action_agent
from app.services.llm_client import _parse_json

logger = logging.getLogger(__name__)

MAX_CHARS = 14000


def _truncate(text: str) -> str:
    t = text.strip()
    if len(t) <= MAX_CHARS:
        return t
    return t[:MAX_CHARS] + "\n\n[... document truncated for processing ...]"


# ---------------------------------------------------------------------------
# SYSTEM prompts (kept for reference / fallback compatibility)
# ---------------------------------------------------------------------------

SYSTEM_PARSE = """You are a legal contract analyst. Extract structured data from the contract text.
Respond with ONLY a valid JSON object (no markdown) matching this shape:
{
  "parties": [{"name": "", "role": ""}],
  "key_dates": [{"label": "", "date_iso": "YYYY-MM-DD or empty if unknown"}],
  "payment_terms": {"summary": "", "amounts": [], "schedule": ""},
  "penalties": [{"description": "", "severity": "low|medium|high"}],
  "sla": [{"metric": "", "target": "", "remedy": ""}],
  "termination": {"notice_days": null, "summary": ""},
  "obligations": [{"party": "", "obligation": ""}]
}
Use empty strings or null when unknown. Dates must be ISO YYYY-MM-DD when you can infer them."""

SYSTEM_PLAN = """You are a contract operations planner. Given structured contract extraction JSON and optional raw excerpt,
produce actionable tracker tasks. Respond with ONLY valid JSON:
{
  "tasks": [
    {"task_name": "", "due_date": "YYYY-MM-DD or null", "priority": "low|medium|high|critical"}
  ]
}
Create 3–12 tasks covering renewals, payments, deliverables, notices, and SLA checks. Use realistic due dates relative to key_dates in the extraction."""

SYSTEM_RISK = """You are a contract risk analyst. Given contract extraction JSON and a short text excerpt,
identify concrete risks. Respond with ONLY valid JSON:
{
  "risks": [
    {"title": "", "description": "", "category": "financial|legal|operational|reputational|other", "score": 0}
  ],
  "overall_risk_score": 0
}
score is 0-100 per risk; overall_risk_score is 0-100 weighted summary."""

SYSTEM_ACTION = """You write concise professional emails. Given alert context, produce a short draft.
Respond with ONLY valid JSON: {"subject": "", "body": ""}"""


# ---------------------------------------------------------------------------
# Main pipeline entry — now fully agentic
# ---------------------------------------------------------------------------

async def process_contract_full(db: Session, contract: Contract) -> dict[str, Any]:
    """Process a contract through the full agentic pipeline.

    The Orchestrator agent autonomously:
    1. Parses the contract text into structured JSON
    2. Creates actionable tasks
    3. Assesses risks and scores them
    4. Indexes the text for RAG retrieval

    All persistence happens through agent tool-calls.
    """
    text = _truncate(contract.raw_text)

    orchestrator = create_orchestrator_agent()
    result = await orchestrator.run(
        f"Process contract ID {contract.id}. Here is the contract text:\n\n{text}"
    )
    logger.info(f"Orchestrator completed for contract {contract.id}: {result}")

    # Refresh from DB to get persisted state (agents wrote via tools)
    db.refresh(contract)

    # Gather counts for the response
    task_count = db.query(ContractTask).filter(
        ContractTask.contract_id == contract.id
    ).count()
    risk_count = db.query(ContractRisk).filter(
        ContractRisk.contract_id == contract.id
    ).count()

    try:
        parsed = json.loads(contract.parsed_json) if contract.parsed_json else {}
    except json.JSONDecodeError:
        parsed = {}

    return {
        "parsed": parsed,
        "task_count": task_count,
        "risk_count": risk_count,
        "overall_risk_score": contract.overall_risk_score,
    }


# ---------------------------------------------------------------------------
# RAG query — agentic
# ---------------------------------------------------------------------------

async def rag_answer(
    db: Session, contract_id: int, question: str, contract_excerpt: str
) -> tuple[str, list[str]]:
    """Answer a question about a contract using the RAG Agent.

    The RAG agent autonomously:
    1. Queries the RAG store for relevant chunks
    2. Falls back to full text if no chunks found
    3. Synthesizes an answer grounded in the context
    """
    rag_agent = create_rag_agent()
    result = await rag_agent.run(
        f"Answer this question about contract ID {contract_id}: {question}"
    )
    answer = str(result) if result else ""

    # Determine sources from the answer
    sources = ["agent_rag_retrieval"]
    return answer, sources


# ---------------------------------------------------------------------------
# Action email draft — agentic
# ---------------------------------------------------------------------------

async def draft_action_message(
    alert_message: str, contract_filename: str
) -> dict[str, str]:
    """Draft an email for a contract alert using the Action Agent."""
    action_agent = create_action_agent()
    result = await action_agent.run(
        json.dumps(
            {"contract_file": contract_filename, "alert": alert_message},
            ensure_ascii=False,
        )
    )
    raw = str(result) if result else "{}"

    try:
        out = _parse_json(raw)
    except (json.JSONDecodeError, Exception):
        out = {"subject": "Contract reminder", "body": raw}

    return {
        "subject": str(out.get("subject", "Contract reminder")),
        "body": str(out.get("body", "")),
    }
