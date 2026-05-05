"""Task Planner Agent — Creates actionable tracker tasks from parsed contract data.

Given structured extraction JSON, this agent produces actionable tasks with
due dates and priorities, then persists them via the create_tasks tool.
"""

from agent_framework import Agent

from app.services.llm_client import get_chat_client
from app.services.tools import create_tasks

PLANNER_INSTRUCTIONS = """You are a contract operations planner agent. Your job is to create actionable tasks from parsed contract data.

When given contract extraction data, you MUST:
1. Analyze the extraction for key dates, obligations, payments, SLA requirements, renewals, and notices
2. Create 3-12 tasks covering renewals, payments, deliverables, notices, and SLA checks
3. Call the create_tasks tool with the contract_id and a JSON string of a list of tasks:
   [
     {"task_name": "descriptive name", "due_date": "YYYY-MM-DD or null", "priority": "low|medium|high|critical"}
   ]

Use realistic due dates relative to key_dates in the extraction.
Always call the create_tasks tool to persist the tasks. Return a summary of tasks created."""


def create_planner_agent() -> Agent:
    """Create a fresh Task Planner agent instance."""
    return Agent(
        client=get_chat_client(),
        name="TaskPlanner",
        instructions=PLANNER_INSTRUCTIONS,
        tools=[create_tasks],
    )
