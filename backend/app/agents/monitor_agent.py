"""Monitor Agent — Sweeps for deadline alerts on open tasks.

Uses the sweep_deadlines tool to check all open tasks for upcoming
and overdue deadlines, creating alert records for any found.
"""

from agent_framework import Agent

from app.services.llm_client import get_chat_client
from app.services.tools import sweep_deadlines

MONITOR_INSTRUCTIONS = """You are a deadline monitoring agent. Your job is to check for upcoming and overdue contract deadlines.

When asked to check deadlines, you MUST:
1. Call the sweep_deadlines tool to scan all open tasks
2. Report the results: how many new alerts were created

Always call the sweep_deadlines tool. Return a summary of the sweep results."""


def create_monitor_agent() -> Agent:
    """Create a fresh Monitor agent instance."""
    return Agent(
        client=get_chat_client(),
        name="DeadlineMonitor",
        instructions=MONITOR_INSTRUCTIONS,
        tools=[sweep_deadlines],
    )
