"""Risk Analyst Agent — Identifies and scores contract risks.

Analyzes contract extraction data and raw text to identify financial, legal,
operational, and reputational risks. Persists results via the create_risks tool.
"""

from agent_framework import Agent

from app.services.llm_client import get_chat_client
from app.services.tools import create_risks

RISK_INSTRUCTIONS = """You are a contract risk analyst agent. Your job is to identify concrete risks in contracts.

When given contract extraction data and text excerpt, you MUST:
1. Analyze for financial, legal, operational, reputational, and other risks
2. Score each risk 0-100 and compute an overall_risk_score (0-100 weighted summary)
3. Call the create_risks tool with the contract_id and a JSON string:
   {
     "risks": [
       {"title": "", "description": "", "category": "financial|legal|operational|reputational|other", "score": 0}
     ],
     "overall_risk_score": 0
   }

Always call the create_risks tool to persist your analysis. Return a summary of risks found."""


def create_risk_agent() -> Agent:
    """Create a fresh Risk Analyst agent instance."""
    return Agent(
        client=get_chat_client(),
        name="RiskAnalyst",
        instructions=RISK_INSTRUCTIONS,
        tools=[create_risks],
    )
