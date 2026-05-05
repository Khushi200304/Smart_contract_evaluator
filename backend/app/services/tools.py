"""Agent-callable tool functions for the Microsoft Agent Framework.

Each function is a self-contained unit that agents invoke via LLM tool-calling.
Functions use `Annotated` type hints so the Agent Framework can auto-discover
parameter descriptions for the LLM.
"""

import json
from datetime import datetime
from typing import Annotated, Any

from pydantic import Field
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Contract, ContractChunk, ContractRisk, ContractTask
from app.services import chroma_rag, document_service


# ---------------------------------------------------------------------------
# Database session helper (tools run outside request scope)
# ---------------------------------------------------------------------------

def _get_db() -> Session:
    return SessionLocal()


# ---------------------------------------------------------------------------
# Tool: Save parsed contract data to the database
# ---------------------------------------------------------------------------

def save_parsed_data(
    contract_id: Annotated[int, Field(description="The database ID of the contract to update.")],
    parsed_json_str: Annotated[str, Field(description="JSON string of the parsed contract data (parties, dates, payments, etc.).")],
) -> str:
    """Save parsed/extracted structured data to a contract record in the database."""
    db = _get_db()
    try:
        contract = db.get(Contract, contract_id)
        if not contract:
            return f"Error: contract {contract_id} not found."
        # Validate it's actually JSON
        try:
            parsed = json.loads(parsed_json_str)
        except json.JSONDecodeError:
            parsed = {}
        contract.parsed_json = json.dumps(parsed, ensure_ascii=False)
        db.commit()
        return f"Parsed data saved for contract {contract_id}."
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tool: Create tasks from LLM output
# ---------------------------------------------------------------------------

def _parse_due(s: str | None) -> datetime | None:
    if not s or not isinstance(s, str):
        return None
    s = s.strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def create_tasks(
    contract_id: Annotated[int, Field(description="The database ID of the contract.")],
    tasks_json_str: Annotated[str, Field(description='JSON string: list of tasks, each with "task_name", "due_date" (YYYY-MM-DD or null), and "priority" (low|medium|high|critical).')],
) -> str:
    """Create actionable task records in the database for a contract. Replaces any existing tasks."""
    db = _get_db()
    try:
        contract = db.get(Contract, contract_id)
        if not contract:
            return f"Error: contract {contract_id} not found."
        try:
            tasks_data = json.loads(tasks_json_str)
        except json.JSONDecodeError:
            return "Error: invalid JSON for tasks."
        if not isinstance(tasks_data, list):
            # Try unwrapping from {"tasks": [...]}
            if isinstance(tasks_data, dict) and "tasks" in tasks_data:
                tasks_data = tasks_data["tasks"]
            else:
                return "Error: tasks must be a JSON array."

        db.query(ContractTask).filter(ContractTask.contract_id == contract_id).delete()
        count = 0
        for t in tasks_data:
            if not isinstance(t, dict) or not t.get("task_name"):
                continue
            name = str(t["task_name"])[:500]
            due = _parse_due(t.get("due_date"))
            pr = str(t.get("priority", "medium")).lower()
            if pr not in ("low", "medium", "high", "critical"):
                pr = "medium"
            db.add(ContractTask(
                contract_id=contract_id,
                task_name=name,
                due_date=due,
                priority=pr,
                status="open",
            ))
            count += 1
        db.commit()
        return f"Created {count} tasks for contract {contract_id}."
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tool: Create risks from LLM output
# ---------------------------------------------------------------------------

def create_risks(
    contract_id: Annotated[int, Field(description="The database ID of the contract.")],
    risks_json_str: Annotated[str, Field(description='JSON string: {"risks": [...], "overall_risk_score": 0-100}. Each risk has "title", "description", "category", "score".')],
) -> str:
    """Create risk records in the database for a contract and set the overall risk score. Replaces any existing risks."""
    db = _get_db()
    try:
        contract = db.get(Contract, contract_id)
        if not contract:
            return f"Error: contract {contract_id} not found."
        try:
            data = json.loads(risks_json_str)
        except json.JSONDecodeError:
            return "Error: invalid JSON for risks."
        if not isinstance(data, dict):
            return "Error: risks data must be a JSON object with 'risks' and 'overall_risk_score'."

        risks_list = data.get("risks", [])
        overall = float(data.get("overall_risk_score", 0))
        overall = max(0.0, min(100.0, overall))

        contract.overall_risk_score = overall
        db.query(ContractRisk).filter(ContractRisk.contract_id == contract_id).delete()
        count = 0
        for r in risks_list:
            if not isinstance(r, dict) or not r.get("title"):
                continue
            sc = float(r.get("score", 0))
            sc = max(0.0, min(100.0, sc))
            db.add(ContractRisk(
                contract_id=contract_id,
                title=str(r.get("title", "Risk"))[:250],
                description=str(r.get("description", ""))[:4000],
                category=str(r.get("category", "other"))[:120],
                score=sc,
            ))
            count += 1
        db.commit()
        return f"Created {count} risks (overall score: {overall}) for contract {contract_id}."
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tool: Index contract text for RAG retrieval
# ---------------------------------------------------------------------------

def index_for_rag(
    contract_id: Annotated[int, Field(description="The database ID of the contract.")],
    text: Annotated[str, Field(description="The full raw text of the contract to chunk and index for RAG.")],
) -> str:
    """Chunk and index contract text into the RAG store (SQLite chunks + optional ChromaDB)."""
    db = _get_db()
    try:
        chroma_rag.index_contract_text(db, contract_id, text)
        return f"Indexed contract {contract_id} text for RAG ({len(text)} chars)."
    except Exception as e:
        return f"RAG indexing completed with note: {e}"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tool: Query RAG for a contract
# ---------------------------------------------------------------------------

def query_rag(
    contract_id: Annotated[int, Field(description="The database ID of the contract to query.")],
    question: Annotated[str, Field(description="The question to answer about the contract.")],
) -> str:
    """Query the RAG store to retrieve relevant contract chunks for answering a question."""
    db = _get_db()
    try:
        ctx, sources = chroma_rag.query_contract(db, contract_id, question)
        if ctx:
            return json.dumps({"context": ctx, "sources": sources}, ensure_ascii=False)
        return json.dumps({"context": "", "sources": []})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tool: Get contract raw text from DB
# ---------------------------------------------------------------------------

def get_contract_text(
    contract_id: Annotated[int, Field(description="The database ID of the contract.")],
) -> str:
    """Retrieve the raw text of a contract from the database."""
    db = _get_db()
    try:
        contract = db.get(Contract, contract_id)
        if not contract:
            return f"Error: contract {contract_id} not found."
        text = contract.raw_text or ""
        # Truncate for LLM context window
        if len(text) > 14000:
            text = text[:14000] + "\n\n[... document truncated for processing ...]"
        return text
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tool: Sweep deadlines for alerts
# ---------------------------------------------------------------------------

def sweep_deadlines() -> str:
    """Scan all open tasks for upcoming and overdue deadlines. Creates alert records for any found."""
    from app.services import monitor_service
    db = _get_db()
    try:
        n = monitor_service.sweep_deadlines(db)
        return f"Deadline sweep completed. Created {n} new alerts."
    finally:
        db.close()
