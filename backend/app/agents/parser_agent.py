"""Contract Parser Agent — Extracts structured data from raw contract text.

This agent receives raw contract text and produces a structured JSON object
with parties, key dates, payment terms, penalties, SLAs, termination clauses,
and obligations. It then persists the result via the save_parsed_data tool.
"""

from agent_framework import Agent

from app.services.llm_client import get_chat_client
from app.services.tools import save_parsed_data

PARSER_INSTRUCTIONS = """You are a legal contract analyst agent. Your job is to extract structured data from contract text.

When given contract text, you MUST:
1. Analyze the text carefully
2. Extract: parties, key_dates, payment_terms, penalties, sla, termination, obligations
3. Call the save_parsed_data tool with the contract_id and a JSON string containing:
   {
     "parties": [{"name": "", "role": ""}],
     "key_dates": [{"label": "", "date_iso": "YYYY-MM-DD or empty if unknown"}],
     "payment_terms": {"summary": "", "amounts": [], "schedule": ""},
     "penalties": [{"description": "", "severity": "low|medium|high"}],
     "sla": [{"metric": "", "target": "", "remedy": ""}],
     "termination": {"notice_days": null, "summary": ""},
     "obligations": [{"party": "", "obligation": ""}]
   }

Use empty strings or null when data is unknown. Dates must be ISO YYYY-MM-DD when inferrable.
Always call the save_parsed_data tool to persist your extraction. Return a summary of what you found."""


def create_parser_agent() -> Agent:
    """Create a fresh Contract Parser agent instance."""
    return Agent(
        client=get_chat_client(),
        name="ContractParser",
        instructions=PARSER_INSTRUCTIONS,
        tools=[save_parsed_data],
    )
