"""Cluster and summarize error-level log events using an LLM.

Regex parsing (log_parser.py) gets us structured events; it can't tell us
that "Connection refused to host X" and "Connection timed out to host X"
are the same underlying incident, or suggest what to check first. That part
needs judgment, so it's the one LLM call in this module -- prompted with a
strict JSON schema and a worked few-shot example so the output is reliable
enough to feed straight into a ticket/report generator without a human
rewriting it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from langchain_core.messages import HumanMessage

from .json_utils import StructuredOutputError, parse_structured_response
from .llm import get_llm
from .log_parser import LogEvent

_FEW_SHOT_EXAMPLE = """\
Example input:
1. [db.pool] Connection refused to host 10.0.0.9:5432
2. [db.pool] Connection refused to host 10.0.0.9:5432
3. [cache.redis] Redis SETEX failed: connection reset

Example output:
[
  {"cluster": "Database connection failures", "count": 2, "example_message": "Connection refused to host 10.0.0.9:5432", "likely_cause": "Database host unreachable or down"},
  {"cluster": "Redis write failures", "count": 1, "example_message": "Redis SETEX failed: connection reset", "likely_cause": "Redis connection instability"}
]
"""


@dataclass
class ErrorCluster:
    cluster: str
    count: int
    example_message: str
    likely_cause: str


def _build_prompt(events: List[LogEvent]) -> str:
    numbered = "\n".join(f"{i+1}. [{e.logger}] {e.message}" for i, e in enumerate(events))
    return (
        "### TASK: LOG_SUMMARY\n"
        "You are triaging application error logs. Group the numbered error messages "
        "below into clusters of the same underlying issue. Respond with ONLY a JSON "
        "array, no prose, matching this shape: "
        '[{"cluster": str, "count": int, "example_message": str, "likely_cause": str}]\n\n'
        f"{_FEW_SHOT_EXAMPLE}\n"
        "ERRORS:\n"
        f"{numbered}\n"
    )


def summarize_errors(events: List[LogEvent]) -> List[ErrorCluster]:
    if not events:
        return []

    llm = get_llm()
    response = llm.invoke([HumanMessage(content=_build_prompt(events))])

    try:
        data = parse_structured_response(response.content)
    except StructuredOutputError as exc:
        raise StructuredOutputError(
            f"Log summarizer returned unparseable output: {exc}", raw_response=response.content
        ) from exc

    if not isinstance(data, list):
        raise StructuredOutputError(
            "Expected a JSON array of clusters", raw_response=response.content
        )

    clusters = []
    for item in data:
        clusters.append(
            ErrorCluster(
                cluster=item["cluster"],
                count=int(item["count"]),
                example_message=item["example_message"],
                likely_cause=item["likely_cause"],
            )
        )
    return clusters
