# AI-Assisted Developer Workflow Automation

Three small CLI utilities that use an LLM for the parts of routine
engineering work that need judgment, and plain code for the parts that
don't:

| Command | What it does | Deterministic code | LLM's job |
|---|---|---|---|
| `logs` | Parse a log file, cluster and summarize the errors | Regex parsing into structured events | Group similar messages, name the cluster, guess a likely cause |
| `boilerplate` | Generate a module + matching test file from a spec | Writing the files to disk | Write the module/test code as structured JSON |
| `review` | Generate a code-review checklist from a change summary | — | Produce categorized, severity-ranked checklist items |

## Why split it that way

Log line parsing is a fixed, known format — a regex is faster, cheaper, and
more reliable than a model call, and it's what `src/log_parser.py` does with
zero LLM involvement. What a regex *can't* do is notice that "Connection
refused to host X" and "Connection timed out to host X" are the same
underlying incident worth one ticket, not two — that's the one place an LLM
call earns its cost (`src/log_summary.py`). The same split shows up in
`boilerplate.py` (generation needs a model, writing the resulting strings to
disk doesn't) — deterministic code for deterministic work, a model only for
the part that needs judgment, not "used an LLM for everything because it's
the current tool."

## Making structured output actually reliable

Every generation call asks for a specific JSON shape and includes one
worked few-shot example of that shape in the prompt (see `_FEW_SHOT_EXAMPLE`
in each module) — this alone cuts down how often a real model wanders off
the format. The second half is `src/json_utils.py`: real models still wrap
JSON in a markdown code fence, add a sentence of preamble, or leave a
trailing comma, so `parse_structured_response()` tries progressively looser
recovery (strip code fence → extract the first balanced `{...}`/`[...]`
span → fix trailing commas) before raising a `StructuredOutputError` that
carries the original raw text, rather than an opaque `JSONDecodeError`
three call frames away from where it's useful.

## Pluggable LLM backend

Same pattern as the other projects in this series: `LLM_PROVIDER` selects
`mock` (default, deterministic offline stand-in), `openai`, or `anthropic`,
and none of the calling code changes when you switch. The mock isn't a real
model — for `logs` it groups by exact message text rather than semantic
similarity; for `boilerplate` it emits a minimal placeholder class, not
meaningful code; for `review` it's a small keyword-triggered rule set. All
of that is enough to exercise the JSON contract, the parsing/validation
logic, and the CLI end-to-end with zero API calls — it is not a claim that
offline testing is equivalent to testing real generation quality.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # or leave LLM_PROVIDER=mock
```

## Run it

```bash
python -m src.cli logs sample_logs/app.log
python -m src.cli boilerplate "a Point dataclass with x and y float fields and a distance_to method"
python -m src.cli review "Added a new /transfer endpoint with a token-based auth check and a new database migration."

# With a real model
LLM_PROVIDER=openai OPENAI_API_KEY=sk-... python -m src.cli logs sample_logs/app.log
```

## Test

```bash
pytest -q
```

17 tests: JSON recovery (code fences, trailing commas, inline prose, and a
genuine-failure case that should raise), log parsing (including that
stack-trace continuation lines are silently skipped rather than crashing
the parser), error clustering, boilerplate generation and file writing, and
the review checklist's keyword-triggered severity rules.

## Docker

```bash
docker build -t ai-dev-workflow-automation .
docker run ai-dev-workflow-automation logs sample_logs/app.log
```

## Known limitations

- The mock LLM's log clustering groups by exact message text, not semantic
  similarity — a real model (or a real embedding-based clustering step)
  would merge near-duplicate messages the mock treats as separate.
- `json_utils.py` recovers from common formatting slips, not arbitrary
  malformed JSON — it's a pragmatic safety net, not a full JSON repair
  library.
- `review_checklist.py` takes a plain-text change summary, not a raw diff;
  turning a diff into that summary is treated as a separate concern.
