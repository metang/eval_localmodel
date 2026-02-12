# eval_localmodel

Modular evaluation framework for testing local LLM **tool-calling accuracy and agentic orchestration** across different runtimes.

## Supported Runtimes

| Runtime | Mode | How It Connects |
|---|---|---|
| **Ollama** | OpenAI-compat API | `http://localhost:11434/v1` |
| **llama-cpp-python** | In-process or server | Direct `Llama()` or `http://localhost:8000/v1` |
| **Foundry Local (ORT)** | OpenAI-compat API | Auto-start via `foundry-local-sdk` or manual endpoint |

## Quick Start

```bash
# 1. Activate the conda environment
conda activate eval_localmodel

# 2. Run a single model evaluation (e.g. Ollama + llama3.1)
python -m src.cli run -r ollama -m llama3.1

# 3. Run specific test suites
python -m src.cli run -r ollama -m llama3.1 -s simple_single -s tool_selection

# 4. Compare multiple models side-by-side
python -m src.cli compare -c config/compare_example.yaml

# 5. Export results to CSV
python -m src.cli run -r ollama -m llama3.1 --csv results.csv
```

## Test Suites

| Suite | Tests | What It Measures |
|---|---|---|
| `simple_single` | 3 | Single tool call with correct name + arguments |
| `tool_selection` | 2 | Picking the right tool from multiple options |
| `multi_tool` | 2 | Parallel / multi-function calls in one turn |
| `negative` | 3 | Correctly refusing when no tool applies |

Add new suites by dropping a `.json` file into `src/test_suites/data/`.

## Architecture

```
src/
├── models.py              # Shared data models (TestCase, EvalResult, etc.)
├── cli.py                 # Click CLI entry point
├── runtimes/              # Plugin-based runtime backends
│   ├── base.py            # Abstract BaseRuntime interface
│   ├── registry.py        # Runtime discovery & factory
│   ├── ollama_rt.py       # Ollama backend
│   ├── llamacpp_rt.py     # llama-cpp-python backend
│   └── foundry_rt.py      # Foundry Local backend
├── eval/                  # Evaluation engine
│   ├── runner.py          # Test runner / orchestrator
│   ├── matchers.py        # Argument matching (exact/fuzzy/type-only)
│   └── results.py         # Aggregation & summary statistics
├── test_suites/           # Test case loader + data
│   ├── __init__.py        # Suite loader API
│   └── data/*.json        # Test case definitions
└── reporting/             # Output formatting
    └── console.py         # Rich console tables + CSV export
```

## Adding a New Runtime

1. Create `src/runtimes/my_rt.py`
2. Subclass `BaseRuntime` and implement `chat_with_tools()`, `list_models()`, `health_check()`
3. Decorate with `@register_runtime("my-runtime")`
4. Import in `src/runtimes/registry.py`

## Adding a New Test Suite

Create a JSON file in `src/test_suites/data/` following this schema:

```json
[
  {
    "id": "unique_test_id",
    "category": "my_category",
    "description": "What this tests",
    "messages": [{"role": "user", "content": "..."}],
    "tools": [{"type": "function", "function": {...}}],
    "expected_tool_calls": [{"name": "fn", "arguments": {"key": "val"}}],
    "match_level": "fuzzy",
    "is_negative": false
  }
]
```
