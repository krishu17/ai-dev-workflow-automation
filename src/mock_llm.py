"""Deterministic offline stand-in for the three generation tasks in this repo.

NOT a language model. Routes on the "### TASK: <NAME>" marker each prompt
builder writes and returns valid-shaped JSON built directly from the input
(grouping identical error messages, echoing the spec, etc.) so
json_utils.parse_structured_response() and each module's own parsing/
validation logic can be exercised end to end without an API key. Swap
LLM_PROVIDER to openai/anthropic for real generation quality.
"""
from __future__ import annotations

import json
import re
from typing import Any, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class MockChatModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:  # pragma: no cover - trivial
        return "mock-dev-automation-chat-model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        prompt = messages[-1].content
        reply = self._route(prompt)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=reply))])

    def _route(self, prompt: str) -> str:
        if "### TASK: LOG_SUMMARY" in prompt:
            return self._log_summary(prompt)
        if "### TASK: BOILERPLATE" in prompt:
            return self._boilerplate(prompt)
        if "### TASK: REVIEW_CHECKLIST" in prompt:
            return self._review_checklist(prompt)
        return "{}"

    def _log_summary(self, prompt: str) -> str:
        errors_block = _after_marker(prompt, "ERRORS:\n")
        lines = [l.strip() for l in errors_block.strip().splitlines() if l.strip()]

        groups: dict[str, dict] = {}
        for line in lines:
            m = re.match(r"\d+\.\s*\[(?P<logger>[^\]]+)\]\s*(?P<msg>.*)", line)
            if not m:
                continue
            msg = m.group("msg")
            if msg not in groups:
                groups[msg] = {"count": 0, "logger": m.group("logger")}
            groups[msg]["count"] += 1

        clusters = [
            {
                "cluster": f"{info['logger']} issues",
                "count": info["count"],
                "example_message": msg,
                "likely_cause": "See example message for details.",
            }
            for msg, info in groups.items()
        ]
        return json.dumps(clusters)

    def _boilerplate(self, prompt: str) -> str:
        spec = _after_marker(prompt, "SPEC:\n").strip()
        slug = re.sub(r"[^a-z0-9]+", "_", spec.lower()).strip("_")[:30] or "module"
        class_name = "".join(word.capitalize() for word in slug.split("_")[:3]) or "Generated"

        code = (
            f'"""Auto-generated from spec: {spec}"""\n\n\n'
            f"class {class_name}:\n"
            f'    """{spec}"""\n\n'
            f"    pass\n"
        )
        test_code = (
            f"from {slug} import {class_name}\n\n\n"
            f"def test_{slug}_can_be_instantiated():\n"
            f"    assert {class_name}() is not None\n"
        )
        return json.dumps({"filename": f"{slug}.py", "code": code, "test_code": test_code})

    def _review_checklist(self, prompt: str) -> str:
        summary = _after_marker(prompt, "CHANGE SUMMARY:\n").strip().lower()
        items = [
            {"category": "Testing", "item": "Confirm new/changed logic has test coverage.", "severity": "medium"},
            {"category": "Readability", "item": "Confirm naming and structure match the rest of the codebase.", "severity": "low"},
        ]
        if any(w in summary for w in ("auth", "password", "token", "permission", "security")):
            items.insert(0, {
                "category": "Security",
                "item": "Confirm authorization/authentication is checked on the new code path.",
                "severity": "high",
            })
        if any(w in summary for w in ("database", "migration", "schema", "sql")):
            items.append({
                "category": "Migration",
                "item": "Confirm the migration has a corresponding rollback.",
                "severity": "medium",
            })
        return json.dumps(items)


def _after_marker(prompt: str, marker: str) -> str:
    idx = prompt.find(marker)
    if idx == -1:
        return ""
    rest = prompt[idx + len(marker):]
    end = rest.find("\n\n")
    return rest if end == -1 else rest[:end]
