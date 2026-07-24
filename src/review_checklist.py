"""Generate a code-review checklist from a plain-text description of a diff.

Takes a human-written (or `git diff --stat`-derived) summary of what changed
rather than a raw diff, since a raw diff blows past useful context length
fast on anything but a tiny change -- summarizing what changed is treated as
a separate, upstream concern from this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from langchain_core.messages import HumanMessage

from .json_utils import StructuredOutputError, parse_structured_response
from .llm import get_llm

_FEW_SHOT_EXAMPLE = """\
Example input: "Added a new /transfer endpoint that moves funds between two user accounts. \
Touches accounts.py and adds a new migration."

Example output:
[
  {"category": "Security", "item": "Confirm the endpoint checks the caller is authorized to move funds out of the source account.", "severity": "high"},
  {"category": "Correctness", "item": "Confirm the transfer is wrapped in a database transaction so a partial failure can't debit one account without crediting the other.", "severity": "high"},
  {"category": "Testing", "item": "Check for a test covering a transfer that fails partway through.", "severity": "medium"},
  {"category": "Migration", "item": "Confirm the migration has a corresponding rollback.", "severity": "low"}
]
"""


@dataclass
class ChecklistItem:
    category: str
    item: str
    severity: str


def _build_prompt(diff_summary: str) -> str:
    return (
        "### TASK: REVIEW_CHECKLIST\n"
        "Generate a code review checklist for the change described below. Respond "
        "with ONLY a JSON array, no prose, matching this shape: "
        '[{"category": str, "item": str, "severity": "low"|"medium"|"high"}]\n\n'
        f"{_FEW_SHOT_EXAMPLE}\n"
        f"CHANGE SUMMARY:\n{diff_summary}\n"
    )


def generate_checklist(diff_summary: str) -> List[ChecklistItem]:
    llm = get_llm()
    response = llm.invoke([HumanMessage(content=_build_prompt(diff_summary))])

    try:
        data = parse_structured_response(response.content)
    except StructuredOutputError as exc:
        raise StructuredOutputError(
            f"Review checklist generator returned unparseable output: {exc}",
            raw_response=response.content,
        ) from exc

    if not isinstance(data, list):
        raise StructuredOutputError("Expected a JSON array of checklist items", raw_response=response.content)

    return [ChecklistItem(category=i["category"], item=i["item"], severity=i["severity"]) for i in data]
