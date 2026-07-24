"""Parse application log lines into structured events.

Deliberately regex-based, not LLM-based -- log format is fixed and known
ahead of time, so a model call would be slower, costlier, and less reliable
than a regex for this step. The LLM is reserved for the part regex can't do
well: clustering free-text error messages into groups and summarizing them
(see log_summary.py). This split -- deterministic code for deterministic
work, a model only for the part that needs judgment -- is a real design
decision worth being able to defend, not just "used an LLM for everything."
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

_LOG_LINE_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+"
    r"(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+"
    r"(?P<logger>[\w.]+):\s*"
    r"(?P<message>.*)$"
)


@dataclass
class LogEvent:
    timestamp: str
    level: str
    logger: str
    message: str


def parse_log_lines(text: str) -> List[LogEvent]:
    """Parse well-formed lines; silently skip lines that don't match (e.g.
    stack trace continuation lines), rather than raising -- a log file is
    not guaranteed to be one event per line."""
    events = []
    for line in text.splitlines():
        match = _LOG_LINE_RE.match(line.strip())
        if not match:
            continue
        events.append(LogEvent(**match.groupdict()))
    return events


def filter_by_level(events: List[LogEvent], *levels: str) -> List[LogEvent]:
    wanted = {lvl.upper() for lvl in levels}
    return [e for e in events if e.level in wanted]


def count_by_level(events: List[LogEvent]) -> dict:
    counts: dict[str, int] = {}
    for e in events:
        counts[e.level] = counts.get(e.level, 0) + 1
    return counts
