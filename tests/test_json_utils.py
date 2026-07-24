import pytest

from src.json_utils import StructuredOutputError, parse_structured_response


def test_parses_clean_json():
    assert parse_structured_response('{"a": 1}') == {"a": 1}


def test_parses_json_wrapped_in_code_fence():
    raw = '```json\n{"a": 1, "b": [1, 2, 3]}\n```'
    assert parse_structured_response(raw) == {"a": 1, "b": [1, 2, 3]}


def test_parses_json_with_surrounding_prose():
    raw = "Sure, here you go:\n```json\n{\"a\": 1}\n```\nLet me know if that helps!"
    assert parse_structured_response(raw) == {"a": 1}


def test_recovers_from_trailing_comma():
    assert parse_structured_response('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}


def test_extracts_json_from_inline_prose():
    raw = "Here is your answer: {\"a\": 1} -- hope that helps!"
    assert parse_structured_response(raw) == {"a": 1}


def test_raises_structured_output_error_with_raw_text_on_failure():
    with pytest.raises(StructuredOutputError) as exc_info:
        parse_structured_response("not json at all")
    assert exc_info.value.raw_response == "not json at all"
