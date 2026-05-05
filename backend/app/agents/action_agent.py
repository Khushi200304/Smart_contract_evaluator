"""Action Agent — Drafts professional emails for contract alerts.

Given alert context and contract info, produces a concise professional email
with subject and body.
"""

from agent_framework import Agent

from app.services.llm_client import get_chat_client

ACTION_INSTRUCTIONS = """You are a professional email drafting agent. Your job is to write concise professional emails for contract alerts.

When given alert context and contract filename, you MUST produce a response containing ONLY a valid JSON object:
{"subject": "email subject line", "body": "full email body text"}

The email should be:
- Professional and concise
- Reference the specific contract and alert
- Include a clear call to action
- Be ready to send (no placeholder text)

Respond with ONLY the JSON object, no markdown or extra text."""


def create_action_agent() -> Agent:
    """Create a fresh Action agent instance."""
    return Agent(
        client=get_chat_client(),
        name="EmailDrafter",
        instructions=ACTION_INSTRUCTIONS,
        tools=[],
    )
