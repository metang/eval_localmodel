# Project Guidelines

## Architecture

Plugin-based evaluation framework with three layers:

- **Runtimes** (`src/runtimes/`) — abstracted backends behind `BaseRuntime`. All use OpenAI-compatible chat completions API. Registry pattern via `@register_runtime("name")` decorator.
- **Eval engine** (`src/eval/`) — drives test cases through a runtime, scores tool-call accuracy (name + argument matching), collects performance metrics.
- **Test suites** (`src/test_suites/data/*.json`) — declarative JSON test cases. Loader in `src/test_suites/__init__.py`.

Key interfaces:
- `BaseRuntime.chat_with_tools()` → `ToolCallResult` (the contract every runtime must satisfy)
- `TestCase` / `EvalResult` in `src/models.py` (shared data models)

## Code Style

- Python 3.11+, type hints everywhere (`from __future__ import annotations`)
- Dataclasses for all data carriers (not dicts)
- `MatchLevel` enum for fuzzy/exact/type-only scoring
- One module per runtime in `src/runtimes/`, suffixed `_rt.py`
- CLI uses Click (`src/cli.py`)
- Modern type syntax: `list[dict]`, `str | None` (not `Optional`, `List`)
- Private helpers prefixed with `_` (e.g., `_parse_tool_calls`, `_evaluate_single`)
- Module-level docstrings on every file
- See `src/runtimes/ollama_rt.py` as the canonical runtime example

## Build and Test

```bash
conda activate eval_localmodel

# Verify framework loads
python -c "from src.runtimes.registry import list_runtimes; print(list_runtimes())"

# Run eval (requires a running runtime like ollama)
python -m src.cli run -r ollama -m llama3.1

# Compare multiple models
python -m src.cli compare -c config/compare_example.yaml
```

## Project Conventions

- **Runtime registration**: Every runtime file decorates its class with `@register_runtime("name")` and is imported in `registry.py`.
- **Test cases**: JSON files in `src/test_suites/data/`. Schema: `id`, `category`, `messages`, `tools`, `expected_tool_calls`, `match_level`, `is_negative`.
- **Matching**: Argument comparison uses `rapidfuzz` for fuzzy string matching (threshold ≥80 token-sort-ratio). See `src/eval/matchers.py`.
- **All runtimes converge on the OpenAI Python client** pointed at different `base_url`s. Runtime-specific logic (e.g., Ollama native perf data, llama-cpp in-process mode) lives only in the runtime module.

## Integration Points

- **Ollama**: expects `ollama serve` running at `localhost:11434`
- **llama-cpp-python**: either in-process (needs GGUF path) or server at `localhost:8000`
- **Foundry Local**: auto-starts via `foundry-local-sdk` or manual `foundry model run <alias>`
- All communicate via OpenAI chat completions `/v1/chat/completions` with `tools` parameter
