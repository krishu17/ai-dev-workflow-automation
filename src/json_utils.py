"""Make LLM output reliable enough to feed into a scripted pipeline.

Models asked for JSON don't always return *only* JSON -- they wrap it in a
markdown code fence, add a sentence of preamble, or occasionally emit a
trailing comma. parse_structured_response() tries a few progressively looser
strategies before giving up, so a scripted pipeline doesn't crash on the
first minor formatting slip.

This is the "structured output prompting" half of the reliability story; the
other half is the few-shot examples baked into each prompt in boilerplate.py
/ log_summary.py / review_checklist.py, which reduce how often the model
strays from the format in the first place.
"""
from __future__ import annotations

import json
import re
from typing import Any


class StructuredOutputError(ValueError):
    """Raised when a model response could not be parsed as the expected JSON shape."""

    def __init__(self, message: str, raw_response: str):
        super().__init__(message)
        self.raw_response = raw_response


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",\s*([\]}])")


def _strip_code_fence(text: str) -> str:
    match = _FENCE_RE.search(text)
    return match.group(1) if match else text


def _extract_json_span(text: str) -> str:
    """Return the substring from the first '{' or '[' to its matching close,
    scanning for the first span that parses. Falls back to the raw text."""
    starts = [i for i, ch in enumerate(text) if ch in "{["]
    for start in starts:
        opener = text[start]
        closer = "}" if opener == "{" else "]"
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        break  # try the next start position
    return text


def parse_structured_response(raw: str) -> Any:
    """Parse a model response into JSON, trying progressively looser recovery.

    Raises StructuredOutputError (with the original text attached) if every
    strategy fails, so the caller can log/retry/surface the raw response
    instead of getting an opaque JSONDecodeError.
    """
    attempts = [raw, _strip_code_fence(raw)]
    attempts.append(_extract_json_span(attempts[-1]))
    # Last resort: fix a single common malformation (trailing commas) on the
    # best candidate span found so far.
    attempts.append(_TRAILING_COMMA_RE.sub(r"\1", attempts[-1]))

    last_error: json.JSONDecodeError | None = None
    for candidate in attempts:
        try:
            return json.loads(candidate.strip())
        except json.JSONDecodeError as exc:
            last_error = exc
            continue

    raise StructuredOutputError(
        f"Could not parse model response as JSON: {last_error}", raw_response=raw
    )
