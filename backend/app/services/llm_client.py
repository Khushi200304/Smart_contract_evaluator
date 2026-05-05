"""Microsoft Agent Framework chat client — connects to Groq via OpenAI-compatible Chat Completions API."""

import json
import re
from typing import Any

from agent_framework import Agent, Message
from agent_framework.openai import OpenAIChatCompletionClient

from app.config import settings


def get_chat_client() -> OpenAIChatCompletionClient:
    """Returns a Microsoft Agent Framework chat client pointing at Groq.

    Uses OpenAIChatCompletionClient (Chat Completions API) instead of
    OpenAIChatClient (Responses API) because Groq does not support the
    Responses API fields like ``previous_response_id``.
    """
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to your environment or .env file.")
    return OpenAIChatCompletionClient(
        api_key=settings.groq_api_key,
        base_url=settings.groq_base_url,
        model=settings.groq_model,
    )


async def chat_json_via_agent(system: str, user: str, temperature: float = 0.2) -> dict[str, Any]:
    """Low-level helper: send system+user messages, parse JSON from response.

    Used by agents that need structured JSON output without tool-calling.
    """
    client = get_chat_client()
    messages = [
        Message("system", [system + "\nYou must output only valid JSON, no markdown."]),
        Message("user", [user]),
    ]
    response = await client.get_response(messages)
    raw = response.messages[0].text if response.messages else "{}"

    return _parse_json(raw)


async def chat_text_via_agent(system: str, user: str, temperature: float = 0.4) -> str:
    """Low-level helper: send system+user messages, return plain text."""
    client = get_chat_client()
    messages = [
        Message("system", [system]),
        Message("user", [user]),
    ]
    response = await client.get_response(messages)
    return (response.messages[0].text if response.messages else "").strip()


def _parse_json(raw: str) -> dict[str, Any]:
    """Parse JSON from LLM output, with regex fallback for markdown-wrapped responses."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            return json.loads(m.group(0))
        raise
