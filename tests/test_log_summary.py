import os

os.environ["LLM_PROVIDER"] = "mock"

from src.log_parser import LogEvent  # noqa: E402
from src.log_summary import summarize_errors  # noqa: E402


def test_summarize_empty_events_returns_empty_list():
    assert summarize_errors([]) == []


def test_summarize_groups_identical_messages():
    events = [
        LogEvent("2026-07-24 09:15:03", "ERROR", "db.connection", "Connection refused to host X"),
        LogEvent("2026-07-24 09:15:04", "ERROR", "db.connection", "Connection refused to host X"),
        LogEvent("2026-07-24 09:17:33", "ERROR", "auth.token", "Token validation failed"),
    ]
    clusters = summarize_errors(events)
    by_message = {c.example_message: c for c in clusters}
    assert by_message["Connection refused to host X"].count == 2
    assert by_message["Token validation failed"].count == 1
