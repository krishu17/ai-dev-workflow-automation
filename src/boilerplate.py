"""Generate a Python module + test-file scaffold from a natural-language spec.

Structured output (filename / code / test_code as separate JSON fields)
matters here specifically because the caller needs to route each field to a
different file on disk -- a free-text response would require its own
brittle parsing step just to figure out where the module ends and the test
file begins.
"""
from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import HumanMessage

from .json_utils import StructuredOutputError, parse_structured_response
from .llm import get_llm

_FEW_SHOT_EXAMPLE = """\
Example input: "a Point dataclass with x and y float fields and a distance_to(other) method"

Example output:
{
  "filename": "point.py",
  "code": "from dataclasses import dataclass\\nimport math\\n\\n\\n@dataclass\\nclass Point:\\n    x: float\\n    y: float\\n\\n    def distance_to(self, other: \\"Point\\") -> float:\\n        return math.hypot(self.x - other.x, self.y - other.y)\\n",
  "test_code": "from point import Point\\n\\n\\ndef test_distance_to():\\n    a = Point(0, 0)\\n    b = Point(3, 4)\\n    assert a.distance_to(b) == 5\\n"
}
"""


@dataclass
class ModuleScaffold:
    filename: str
    code: str
    test_code: str


def _build_prompt(spec: str) -> str:
    return (
        "### TASK: BOILERPLATE\n"
        "Generate a small, working Python module and a matching pytest test file "
        "for the following spec. Respond with ONLY a JSON object, no prose, matching "
        'this shape: {"filename": str, "code": str, "test_code": str}\n\n'
        f"{_FEW_SHOT_EXAMPLE}\n"
        f"SPEC:\n{spec}\n"
    )


def generate_module(spec: str) -> ModuleScaffold:
    llm = get_llm()
    response = llm.invoke([HumanMessage(content=_build_prompt(spec))])

    try:
        data = parse_structured_response(response.content)
    except StructuredOutputError as exc:
        raise StructuredOutputError(
            f"Boilerplate generator returned unparseable output: {exc}",
            raw_response=response.content,
        ) from exc

    for field in ("filename", "code", "test_code"):
        if field not in data:
            raise StructuredOutputError(
                f"Boilerplate response missing required field '{field}'",
                raw_response=response.content,
            )

    return ModuleScaffold(filename=data["filename"], code=data["code"], test_code=data["test_code"])


def write_scaffold(scaffold: ModuleScaffold, directory: str) -> None:
    """Side-effecting on purpose (writes files) -- kept separate from
    generate_module() so the generation logic stays pure and easy to test."""
    import os

    os.makedirs(directory, exist_ok=True)
    module_path = os.path.join(directory, scaffold.filename)
    test_path = os.path.join(directory, f"test_{scaffold.filename}")
    with open(module_path, "w", encoding="utf-8") as f:
        f.write(scaffold.code)
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(scaffold.test_code)
