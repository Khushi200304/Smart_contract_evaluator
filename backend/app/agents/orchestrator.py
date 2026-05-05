"""Contract Orchestrator Agent — Master coordinator for the full contract processing pipeline.

This agent receives a contract processing request and autonomously coordinates
the specialized agents (parser, planner, risk analyst) through tool-calling.
It decides the order and handles the full pipeline.
"""

import json
from typing import Annotated

from pydantic import Field

from agent_framework import Agent

from app.services.llm_client import get_chat_client
from app.services.tools import (
    create_risks,
    create_tasks,
    get_contract_text,
    index_for_rag,
    save_parsed_data,
)

ORCHESTRATOR_INSTRUCTIONS = """You are the Contract Processing Orchestrator — the master coordinator agent.

When asked to process a contract, you MUST complete ALL of the following steps in order:

**Step 1 — Parse:** Read the contract text provided and extract structured data. Call the save_parsed_data tool with the contract_id and a JSON string containing:
{
  "parties": [{"name": "", "role": ""}],
  "key_dates": [{"label": "", "date_iso": "YYYY-MM-DD or empty"}],
  "payment_terms": {"summary": "", "amounts": [], "schedule": ""},
  "penalties": [{"description": "", "severity": "low|medium|high"}],
  "sla": [{"metric": "", "target": "", "remedy": ""}],
  "termination": {"notice_days": null, "summary": ""},
  "obligations": [{"party": "", "obligation": ""}]
}

**Step 2 — Plan Tasks:** Based on the extraction, create 3-12 actionable tasks. Call the create_tasks tool with the contract_id and a JSON array string:
[{"task_name": "", "due_date": "YYYY-MM-DD or null", "priority": "low|medium|high|critical"}]

**Step 3 — Assess Risks:** Analyze the contract for risks. Call the create_risks tool with the contract_id and a JSON string:
{"risks": [{"title": "", "description": "", "category": "financial|legal|operational|reputational|other", "score": 0}], "overall_risk_score": 0}

**Step 4 — Index for RAG:** Call the index_for_rag tool with the contract_id and the raw contract text.

You MUST call all four tools (save_parsed_data, create_tasks, create_risks, index_for_rag) to complete processing.
After all tools are called, provide a brief summary of what was extracted, how many tasks/risks were created, and the overall risk score."""


def create_orchestrator_agent() -> Agent:
    """Create a fresh Orchestrator agent instance.
    
    The orchestrator has access to all persistence tools and coordinates
    the full contract processing pipeline autonomously.
    """
    return Agent(
        client=get_chat_client(),
        name="ContractOrchestrator",
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        tools=[save_parsed_data, create_tasks, create_risks, index_for_rag, get_contract_text],
    )
