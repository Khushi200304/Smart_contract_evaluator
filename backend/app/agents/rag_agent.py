"""RAG Query Agent — Answers questions about contracts using retrieved context.

Uses the query_rag tool to retrieve relevant document chunks, then synthesizes
a grounded answer based only on the provided context.
"""

from agent_framework import Agent

from app.services.llm_client import get_chat_client
from app.services.tools import get_contract_text, query_rag

RAG_INSTRUCTIONS = """You are a contract question-answering agent. Your job is to answer questions about contracts using retrieved context.

When given a question about a contract, you MUST:
1. Call the query_rag tool with the contract_id and question to retrieve relevant chunks
2. If the RAG result is empty, call the get_contract_text tool to get the full text as fallback
3. Analyze the retrieved context carefully
4. Answer the question based ONLY on the context provided
5. If the answer is not in the context, say you cannot find it in the contract text

Your final response must be a clear, concise answer to the question. Only use information from the retrieved context."""


def create_rag_agent() -> Agent:
    """Create a fresh RAG Query agent instance."""
    return Agent(
        client=get_chat_client(),
        name="ContractQA",
        instructions=RAG_INSTRUCTIONS,
        tools=[query_rag, get_contract_text],
    )
