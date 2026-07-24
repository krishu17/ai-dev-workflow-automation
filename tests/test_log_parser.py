from src.log_parser import count_by_level, filter_by_level, parse_log_lines

SAMPLE = """\
2026-07-24 09:12:01 INFO app.startup: Application started on port 8080
2026-07-24 09:15:03 ERROR db.connection: Connection refused to host 10.0.0.5:5432
Traceback (most recent call last):
  File "worker.py", line 42, in run
ValueError: invalid job payload
2026-07-24 09:18:02 CRITICAL app.worker: Worker process crashed with exit code 1
"""


def test_parses_well_formed_lines():
    events = parse_log_lines(SAMPLE)
    assert len(events) == 3
    assert events[0].level == "INFO"
    assert events[1].logger == "db.connection"


def test_skips_non_matching_lines_like_stack_traces():
    events = parse_log_lines(SAMPLE)
    messages = [e.message for e in events]
    assert not any("Traceback" in m for m in messages)


def test_filter_by_level():
    events = parse_log_lines(SAMPLE)
    errors = filter_by_level(events, "ERROR", "CRITICAL")
    assert len(errors) == 2
    assert all(e.level in {"ERROR", "CRITICAL"} for e in errors)


def test_count_by_level():
    events = parse_log_lines(SAMPLE)
    counts = count_by_level(events)
    assert counts == {"INFO": 1, "ERROR": 1, "CRITICAL": 1}
