# Test Cases Reference

This document describes all test cases used by the eval-localmodel framework to evaluate tool-calling accuracy in local LLMs.

## Overview

| Suite | Tests | Description |
|---|---|---|
| `simple_single` | 3 | Single tool call with straightforward prompts |
| `tool_selection` | 2 | Correct tool chosen from multiple candidates |
| `multi_tool` | 2 | Multiple tool calls expected in a single turn |
| `negative` | 3 | Model should **not** call any tool |
| **Total** | **10** | |

---

## Schema

Each test case is a JSON object with these fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `string` | yes | Unique identifier (e.g. `simple_weather_01`) |
| `category` | `string` | yes | Suite/category name |
| `description` | `string` | yes | Human-readable purpose |
| `messages` | `list[dict]` | yes | OpenAI-format chat messages sent to the model |
| `tools` | `list[dict]` | yes | OpenAI-format tool definitions available to the model |
| `expected_tool_calls` | `list[dict]` | yes | Expected tool calls: `[{"name": "...", "arguments": {...}}]` |
| `match_level` | `string` | no | `"exact"`, `"fuzzy"` (default), or `"type_only"` |
| `is_negative` | `bool` | no | If `true`, the model should produce **zero** tool calls |
| `tags` | `list[string]` | no | Optional labels (e.g. `parallel`, `multi_function`) |

---

## Suite: `simple_single`

Basic single-tool invocation tests. Each prompt maps to exactly one tool call with clear arguments.

### `simple_weather_01` — Basic weather lookup

| | |
|---|---|
| **Description** | Basic weather lookup — single required argument |
| **Match level** | `fuzzy` |
| **User prompt** | *"What is the current weather in San Francisco?"* |

**Available tools:**

| Tool | Parameters | Required |
|---|---|---|
| `get_weather` | `location` (string), `unit` (string, enum: celsius/fahrenheit) | `location` |

**Expected tool call:**

```json
{
  "name": "get_weather",
  "arguments": { "location": "San Francisco" }
}
```

**What it tests:** Can the model extract a city name and call the correct function with a single required argument.

---

### `simple_weather_02` — Weather with explicit unit

| | |
|---|---|
| **Description** | Weather with explicit unit request |
| **Match level** | `fuzzy` |
| **User prompt** | *"Tell me the weather in Tokyo in celsius."* |

**Available tools:**

| Tool | Parameters | Required |
|---|---|---|
| `get_weather` | `location` (string), `unit` (string, enum: celsius/fahrenheit) | `location` |

**Expected tool call:**

```json
{
  "name": "get_weather",
  "arguments": { "location": "Tokyo", "unit": "celsius" }
}
```

**What it tests:** Can the model populate both required and optional arguments when both are mentioned in the prompt.

---

### `simple_search_01` — Product search with price constraint

| | |
|---|---|
| **Description** | Database search with required query |
| **Match level** | `fuzzy` |
| **User prompt** | *"Search for wireless headphones under $50"* |

**Available tools:**

| Tool | Parameters | Required |
|---|---|---|
| `search_products` | `query` (string), `max_price` (number), `category` (string, enum) | `query` |

**Expected tool call:**

```json
{
  "name": "search_products",
  "arguments": { "query": "wireless headphones", "max_price": 50 }
}
```

**What it tests:** Can the model extract a text query and a numeric constraint from natural language and map them to the correct parameters.

---

## Suite: `tool_selection`

The model is given multiple tools and must select the correct one for the task. Tests the model's ability to discriminate between tool purposes.

### `select_calc_01` — Calculator over weather/search

| | |
|---|---|
| **Description** | Should pick calculator over weather when asked to compute |
| **Match level** | `fuzzy` |
| **User prompt** | *"What is 15% of 230?"* |

**Available tools (3):**

| Tool | Description |
|---|---|
| `get_weather` | Get current weather for a city |
| `calculate` | Evaluate a mathematical expression |
| `search_web` | Search the web for information |

**Expected tool call:**

```json
{
  "name": "calculate",
  "arguments": { "expression": "0.15 * 230" }
}
```

**What it tests:** Given a math question and three tools, the model should pick `calculate` — not search or weather. The argument must translate "15% of 230" into a valid math expression.

---

### `select_email_01` — Send email from a large toolset

| | |
|---|---|
| **Description** | Pick send_email from a large toolset |
| **Match level** | `fuzzy` |
| **User prompt** | *"Send an email to alice@example.com with subject 'Meeting Tomorrow' and body 'Hi Alice, can we meet at 3pm?'"* |

**Available tools (4):**

| Tool | Description |
|---|---|
| `get_weather` | Get weather for a location |
| `send_email` | Send an email message |
| `create_calendar_event` | Create a calendar event |
| `search_contacts` | Search contacts by name |

**Expected tool call:**

```json
{
  "name": "send_email",
  "arguments": {
    "to": "alice@example.com",
    "subject": "Meeting Tomorrow",
    "body": "Hi Alice, can we meet at 3pm?"
  }
}
```

**What it tests:** With four plausible tools (including calendar and contacts that are semantically close), the model must pick `send_email` and correctly extract all three required arguments from the prompt.

---

## Suite: `multi_tool`

The model is expected to produce **multiple** tool calls in a single turn — either parallel calls to the same tool or calls to different tools.

### `parallel_weather_01` — Same tool, two cities

| | |
|---|---|
| **Description** | Should call weather for two cities in parallel |
| **Match level** | `fuzzy` |
| **Tags** | `parallel` |
| **User prompt** | *"What is the weather in both New York and London?"* |

**Available tools:**

| Tool | Parameters | Required |
|---|---|---|
| `get_weather` | `location` (string) | `location` |

**Expected tool calls (2):**

```json
[
  { "name": "get_weather", "arguments": { "location": "New York" } },
  { "name": "get_weather", "arguments": { "location": "London" } }
]
```

**What it tests:** Can the model recognize a request involving two entities and emit two parallel calls to the same tool with different arguments.

---

### `multi_different_01` — Two different tools in one turn

| | |
|---|---|
| **Description** | Should call two different tools in one turn |
| **Match level** | `fuzzy` |
| **Tags** | `parallel`, `multi_function` |
| **User prompt** | *"What is the weather in Paris and also calculate 25 * 4?"* |

**Available tools (2):**

| Tool | Description |
|---|---|
| `get_weather` | Get current weather for a city |
| `calculate` | Evaluate a math expression |

**Expected tool calls (2):**

```json
[
  { "name": "get_weather", "arguments": { "location": "Paris" } },
  { "name": "calculate", "arguments": { "expression": "25 * 4" } }
]
```

**What it tests:** Can the model decompose a compound request into two separate tool calls to different functions in a single turn.

---

## Suite: `negative`

Negative tests verify the model correctly **refuses** to call tools when a tool call would be inappropriate. A passing result means zero tool calls were emitted.

### `neg_irrelevant_01` — Prompt unrelated to available tools

| | |
|---|---|
| **Description** | Prompt is irrelevant to available tools — should NOT call anything |
| **Negative** | `true` |
| **User prompt** | *"Tell me a joke about penguins."* |

**Available tools:** `get_weather`, `search_products`

**Expected:** No tool calls.

**What it tests:** The model should answer conversationally rather than force-fitting an irrelevant request into a tool call.

---

### `neg_irrelevant_02` — General knowledge, wrong tools

| | |
|---|---|
| **Description** | General knowledge question — no tool needed |
| **Negative** | `true` |
| **User prompt** | *"What is the capital of France?"* |

**Available tools:** `calculate`, `send_email`

**Expected:** No tool calls.

**What it tests:** A factual question the model can answer from training data. Neither `calculate` nor `send_email` is appropriate.

---

### `neg_missing_info_01` — Insufficient info to call tool

| | |
|---|---|
| **Description** | Not enough info to call the tool — should ask for clarification |
| **Negative** | `true` |
| **Tags** | `missing_info` |
| **User prompt** | *"Send an email for me."* |

**Available tools:**

| Tool | Parameters | Required |
|---|---|---|
| `send_email` | `to` (string), `subject` (string), `body` (string) | `to`, `subject`, `body` |

**Expected:** No tool calls.

**What it tests:** All three parameters are required but the prompt provides none. The model should ask for clarification instead of hallucinating values for `to`, `subject`, and `body`.

---

## Match Levels

The framework supports three argument comparison modes:

| Level | Description | Matcher |
|---|---|---|
| `exact` | Arguments must match character-for-character | String equality |
| `fuzzy` | Arguments compared with fuzzy string matching (≥80 token-sort-ratio via `rapidfuzz`) | Handles minor wording differences |
| `type_only` | Only the argument types must match (e.g. string→string, number→number) | Structural check only |

Most test cases use `fuzzy` matching to tolerate minor phrasing differences (e.g. `"San Francisco"` vs. `"San Francisco, CA"`).

## Adding New Test Cases

1. Create or edit a JSON file in `src/test_suites/data/`.
2. Follow the schema above — at minimum: `id`, `category`, `messages`, `tools`, `expected_tool_calls`.
3. Set `is_negative: true` for cases where the model should **not** call any tool.
4. The loader auto-discovers all `.json` files in the data directory — no registration needed.
