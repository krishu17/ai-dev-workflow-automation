"""Command-line entry point.

    python -m src.cli boilerplate "a Point dataclass with x and y fields"
    python -m src.cli logs sample_logs/app.log
    python -m src.cli review "Added a new /transfer endpoint..."
"""
from __future__ import annotations

import argparse
import json

from .boilerplate import generate_module
from .log_parser import filter_by_level, parse_log_lines
from .log_summary import summarize_errors
from .review_checklist import generate_checklist


def _cmd_boilerplate(args: argparse.Namespace) -> None:
    scaffold = generate_module(args.spec)
    print(f"# {scaffold.filename}")
    print(scaffold.code)
    print(f"# test_{scaffold.filename}")
    print(scaffold.test_code)


def _cmd_logs(args: argparse.Namespace) -> None:
    with open(args.log_file, "r", encoding="utf-8") as f:
        events = parse_log_lines(f.read())
    errors = filter_by_level(events, "ERROR", "CRITICAL")
    print(f"Parsed {len(events)} events, {len(errors)} error/critical.\n")
    for cluster in summarize_errors(errors):
        print(f"[{cluster.count}x] {cluster.cluster}")
        print(f"    example: {cluster.example_message}")
        print(f"    likely cause: {cluster.likely_cause}")


def _cmd_review(args: argparse.Namespace) -> None:
    for item in generate_checklist(args.summary):
        print(f"[{item.severity.upper():6}] ({item.category}) {item.item}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-assisted developer workflow utilities.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_boiler = sub.add_parser("boilerplate", help="Generate a module + test scaffold from a spec")
    p_boiler.add_argument("spec")
    p_boiler.set_defaults(func=_cmd_boilerplate)

    p_logs = sub.add_parser("logs", help="Parse a log file and summarize error clusters")
    p_logs.add_argument("log_file")
    p_logs.set_defaults(func=_cmd_logs)

    p_review = sub.add_parser("review", help="Generate a review checklist from a change summary")
    p_review.add_argument("summary")
    p_review.set_defaults(func=_cmd_review)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
