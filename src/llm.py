"""LLM provider abstraction.

    LLM_PROVIDER=openai      -> langchain-openai (needs OPENAI_API_KEY)
    LLM_PROVIDER=anthropic   -> langchain-anthropic (needs ANTHROPIC_API_KEY)
    LLM_PROVIDER=mock        -> deterministic offline stand-in (default)

Same pattern as the other two projects: every generation task (boilerplate,
log summarization, review checklists) goes through get_llm(), so swapping
providers is a one-line env change and none of the calling code changes.
"""
from __future__ import annotations

import os

from langchain_core.language_models.chat_models import BaseChatModel


def get_llm(temperature: float = 0.0) -> BaseChatModel:
    provider = os.getenv("LLM_PROVIDER", "mock").lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4.1"), temperature=temperature)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
            temperature=temperature,
        )

    if provider == "mock":
        from .mock_llm import MockChatModel

        return MockChatModel()

    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")
