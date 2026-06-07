[Skip to main content](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#__docusaurus_skipToContent_fallback)

[![Hermes Agent](https://hermes-agent.nousresearch.com/docs/img/logo.png)\\
**Hermes Agent**](https://hermes-agent.nousresearch.com/docs/) [Docs](https://hermes-agent.nousresearch.com/docs/user-stories) [Skills](https://hermes-agent.nousresearch.com/docs/skills) [Download](https://hermes-agent.nousresearch.com/desktop)

[English](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#)

- [English](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching)
- [简体中文](https://hermes-agent.nousresearch.com/docs/zh-Hans/developer-guide/context-compression-and-caching)

[Home](https://hermes-agent.nousresearch.com/) [GitHub](https://github.com/NousResearch/hermes-agent) [Discord](https://discord.gg/NousResearch)

`ctrl`  `K`

- [User Stories & Use Cases](https://hermes-agent.nousresearch.com/docs/user-stories)
- [Getting Started](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#)

- [Using Hermes](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#)

- [Features](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#)

- [Messaging Platforms](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#)

- [Integrations](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#)

- [Guides & Tutorials](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#)

- [Developer Guide](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#)

  - [Contributing](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing)
  - [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#)

    - [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)
    - [Agent Loop Internals](https://hermes-agent.nousresearch.com/docs/developer-guide/agent-loop)
    - [Prompt Assembly](https://hermes-agent.nousresearch.com/docs/developer-guide/prompt-assembly)
    - [Context Compression and Caching](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching)
    - [Gateway Internals](https://hermes-agent.nousresearch.com/docs/developer-guide/gateway-internals)
    - [Session Storage](https://hermes-agent.nousresearch.com/docs/developer-guide/session-storage)
    - [Provider Runtime Resolution](https://hermes-agent.nousresearch.com/docs/developer-guide/provider-runtime)
    - [Programmatic Integration](https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration)
  - [Extending](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#)

  - [Internals](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#)
- [Reference](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#)


- [Home page](https://hermes-agent.nousresearch.com/docs/)
- Developer Guide
- Architecture
- Context Compression and Caching

On this page

# Context Compression and Caching

Hermes Agent uses a dual compression system and Anthropic prompt caching to
manage context window usage efficiently across long conversations.

Source files: `agent/context_engine.py` (ABC), `agent/context_compressor.py` (default engine),
`agent/prompt_caching.py`, `gateway/run.py` (session hygiene), `run_agent.py` (search for `_compress_context`)

## Pluggable Context Engine [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#pluggable-context-engine "Direct link to Pluggable Context Engine")

Context management is built on the `ContextEngine` ABC (`agent/context_engine.py`). The built-in `ContextCompressor` is the default implementation, but plugins can replace it with alternative engines (e.g., Lossless Context Management).

```yaml
context:
  engine: "compressor"    # default — built-in lossy summarization
  engine: "lcm"           # example — plugin providing lossless context
```

The engine is responsible for:

- Deciding when compaction should fire (`should_compress()`)
- Performing compaction (`compress()`)
- Optionally exposing tools the agent can call (e.g., `lcm_grep`)
- Tracking token usage from API responses

Selection is config-driven via `context.engine` in `config.yaml`. The resolution order:

1. Check `plugins/context_engine/<name>/` directory
2. Check general plugin system (`register_context_engine()`)
3. Fall back to built-in `ContextCompressor`

Plugin engines are **never auto-activated** — the user must explicitly set `context.engine` to the plugin's name. The default `"compressor"` always uses the built-in.

Configure via `hermes plugins` → Provider Plugins → Context Engine, or edit `config.yaml` directly.

For building a context engine plugin, see [Context Engine Plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/context-engine-plugin).

## Dual Compression System [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#dual-compression-system "Direct link to Dual Compression System")

Hermes has two separate compression layers that operate independently:

```text
                     ┌──────────────────────────┐
  Incoming message   │   Gateway Session Hygiene │  Fires at 85% of context
  ─────────────────► │   (pre-agent, rough est.) │  Safety net for large sessions
                     └─────────────┬────────────┘
                                   │
                                   ▼
                     ┌──────────────────────────┐
                     │   Agent ContextCompressor │  Fires at 50% of context (default)
                     │   (in-loop, real tokens)  │  Normal context management
                     └──────────────────────────┘
```

### 1\. Gateway Session Hygiene (85% threshold) [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#1-gateway-session-hygiene-85-threshold "Direct link to 1. Gateway Session Hygiene (85% threshold)")

Located in `gateway/run.py` (search for `Session hygiene: auto-compress`). This is a **safety net** that
runs before the agent processes a message. It prevents API failures when sessions
grow too large between turns (e.g., overnight accumulation in Telegram/Discord).

- **Threshold**: Fixed at 85% of model context length
- **Token source**: Prefers actual API-reported tokens from last turn; falls back
to rough character-based estimate (`estimate_messages_tokens_rough`)
- **Fires**: Only when `len(history) >= 4` and compression is enabled
- **Purpose**: Catch sessions that escaped the agent's own compressor

The gateway hygiene threshold is intentionally higher than the agent's compressor.
Setting it at 50% (same as the agent) caused premature compression on every turn
in long gateway sessions.

### 2\. Agent ContextCompressor (50% threshold, configurable) [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#2-agent-contextcompressor-50-threshold-configurable "Direct link to 2. Agent ContextCompressor (50% threshold, configurable)")

Located in `agent/context_compressor.py`. This is the **primary compression**
**system** that runs inside the agent's tool loop with access to accurate,
API-reported token counts.

## Configuration [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#configuration "Direct link to Configuration")

All compression settings are read from `config.yaml` under the `compression` key:

```yaml
compression:
  enabled: true              # Enable/disable compression (default: true)
  threshold: 0.50            # Fraction of context window (default: 0.50 = 50%)
  target_ratio: 0.20         # How much of threshold to keep as tail (default: 0.20)
  protect_last_n: 20         # Minimum protected tail messages (default: 20)

# Summarization model/provider configured under auxiliary:
auxiliary:
  compression:
    model: null              # Override model for summaries (default: auto-detect)
    provider: auto           # Provider: "auto", "openrouter", "nous", "main", etc.
    base_url: null           # Custom OpenAI-compatible endpoint
```

### Parameter Details [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#parameter-details "Direct link to Parameter Details")

| Parameter | Default | Range | Description |
| --- | --- | --- | --- |
| `threshold` | `0.50` | 0.0-1.0 | Compression triggers when prompt tokens ≥ `threshold × context_length` |
| `target_ratio` | `0.20` | 0.10-0.80 | Controls tail protection token budget: `threshold_tokens × target_ratio` |
| `protect_last_n` | `20` | ≥1 | Minimum number of recent messages always preserved |
| `protect_first_n` | `3` | (hardcoded) | System prompt + first exchange always preserved |

### Computed Values (for a 200K context model at defaults) [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#computed-values-for-a-200k-context-model-at-defaults "Direct link to Computed Values (for a 200K context model at defaults)")

```text
context_length       = 200,000
threshold_tokens     = 200,000 × 0.50 = 100,000
tail_token_budget    = 100,000 × 0.20 = 20,000
max_summary_tokens   = min(200,000 × 0.05, 12,000) = 10,000
```

Threshold is derived from the MAIN model's context window

`threshold_tokens` is always `threshold × context_length`, where `context_length`
is the **main agent model's** context window — never the auxiliary/summary
model's. On a 262,144-token model at the default `0.50`, the threshold is
`262,144 × 0.50 = 131,072`. That number being close to a common "128K context"
is a coincidence of the percentage, not a sign that the auxiliary model's window
is the trigger. The auxiliary model's context window is a separate concern — see
the "Summary model context length" warning below for how it affects whether a
summary can be produced, not when compression fires.

## Compression Algorithm [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#compression-algorithm "Direct link to Compression Algorithm")

The `ContextCompressor.compress()` method follows a 4-phase algorithm:

### Phase 1: Prune Old Tool Results (cheap, no LLM call) [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#phase-1-prune-old-tool-results-cheap-no-llm-call "Direct link to Phase 1: Prune Old Tool Results (cheap, no LLM call)")

Old tool results (>200 chars) outside the protected tail are replaced with:

```text
[Old tool output cleared to save context space]
```

This is a cheap pre-pass that saves significant tokens from verbose tool
outputs (file contents, terminal output, search results).

### Phase 2: Determine Boundaries [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#phase-2-determine-boundaries "Direct link to Phase 2: Determine Boundaries")

```text
┌─────────────────────────────────────────────────────────────┐
│  Message list                                               │
│                                                             │
│  [0..2]  ← protect_first_n (system + first exchange)        │
│  [3..N]  ← middle turns → SUMMARIZED                        │
│  [N..end] ← tail (by token budget OR protect_last_n)        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Tail protection is **token-budget based**: walks backward from the end,
accumulating tokens until the budget is exhausted. Falls back to the fixed
`protect_last_n` count if the budget would protect fewer messages.

Boundaries are aligned to avoid splitting tool\_call/tool\_result groups.
The `_align_boundary_backward()` method walks past consecutive tool results
to find the parent assistant message, keeping groups intact.

### Phase 3: Generate Structured Summary [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#phase-3-generate-structured-summary "Direct link to Phase 3: Generate Structured Summary")

Summary model context length

The summary model must have a context window **at least as large** as the main agent model's. The entire middle section is sent to the summary model in a single `call_llm(task="compression")` call. If the summary model's context is smaller, the API returns a context-length error — `_generate_summary()` catches it, logs a warning, and returns `None`. The compressor then drops the middle turns **without a summary**, silently losing conversation context. This is the most common cause of degraded compaction quality.

The middle turns are summarized using the auxiliary LLM with a structured
template:

```text
## Goal
[What the user is trying to accomplish]

## Constraints & Preferences
[User preferences, coding style, constraints, important decisions]

## Progress
### Done
[Completed work — specific file paths, commands run, results]
### In Progress
[Work currently underway]
### Blocked
[Any blockers or issues encountered]

## Key Decisions
[Important technical decisions and why]

## Relevant Files
[Files read, modified, or created — with brief note on each]

## Next Steps
[What needs to happen next]

## Critical Context
[Specific values, error messages, configuration details]
```

Summary budget scales with the amount of content being compressed:

- Formula: `content_tokens × 0.20` (the `_SUMMARY_RATIO` constant)
- Minimum: 2,000 tokens
- Maximum: `min(context_length × 0.05, 12,000)` tokens

### Phase 4: Assemble Compressed Messages [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#phase-4-assemble-compressed-messages "Direct link to Phase 4: Assemble Compressed Messages")

The compressed message list is:

1. Head messages (with a note appended to system prompt on first compression)
2. Summary message (role chosen to avoid consecutive same-role violations)
3. Tail messages (unmodified)

Orphaned tool\_call/tool\_result pairs are cleaned up by `_sanitize_tool_pairs()`:

- Tool results referencing removed calls → removed
- Tool calls whose results were removed → stub result injected

### Iterative Re-compression [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#iterative-re-compression "Direct link to Iterative Re-compression")

On subsequent compressions, the previous summary is passed to the LLM with
instructions to **update** it rather than summarize from scratch. This preserves
information across multiple compactions — items move from "In Progress" to "Done",
new progress is added, and obsolete information is removed.

The `_previous_summary` field on the compressor instance stores the last summary
text for this purpose.

## Before/After Example [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#beforeafter-example "Direct link to Before/After Example")

### Before Compression (45 messages, ~95K tokens) [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#before-compression-45-messages-95k-tokens "Direct link to Before Compression (45 messages, ~95K tokens)")

```text
[0] system:    "You are a helpful assistant..." (system prompt)
[1] user:      "Help me set up a FastAPI project"
[2] assistant: <tool_call> terminal: mkdir project </tool_call>
[3] tool:      "directory created"
[4] assistant: <tool_call> write_file: main.py </tool_call>
[5] tool:      "file written (2.3KB)"
    ... 30 more turns of file editing, testing, debugging ...
[38] assistant: <tool_call> terminal: pytest </tool_call>
[39] tool:      "8 passed, 2 failed\n..."  (5KB output)
[40] user:      "Fix the failing tests"
[41] assistant: <tool_call> read_file: tests/test_api.py </tool_call>
[42] tool:      "import pytest\n..."  (3KB)
[43] assistant: "I see the issue with the test fixtures..."
[44] user:      "Great, also add error handling"
```

### After Compression (25 messages, ~45K tokens) [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#after-compression-25-messages-45k-tokens "Direct link to After Compression (25 messages, ~45K tokens)")

```text
[0] system:    "You are a helpful assistant...
               [Note: Some earlier conversation turns have been compacted...]"
[1] user:      "Help me set up a FastAPI project"
[2] assistant: "[CONTEXT COMPACTION] Earlier turns were compacted...

               ## Goal
               Set up a FastAPI project with tests and error handling

               ## Progress
               ### Done
               - Created project structure: main.py, tests/, requirements.txt
               - Implemented 5 API endpoints in main.py
               - Wrote 10 test cases in tests/test_api.py
               - 8/10 tests passing

               ### In Progress
               - Fixing 2 failing tests (test_create_user, test_delete_user)

               ## Relevant Files
               - main.py — FastAPI app with 5 endpoints
               - tests/test_api.py — 10 test cases
               - requirements.txt — fastapi, pytest, httpx

               ## Next Steps
               - Fix failing test fixtures
               - Add error handling"
[3] user:      "Fix the failing tests"
[4] assistant: <tool_call> read_file: tests/test_api.py </tool_call>
[5] tool:      "import pytest\n..."
[6] assistant: "I see the issue with the test fixtures..."
[7] user:      "Great, also add error handling"
```

## Prompt Caching (Anthropic) [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#prompt-caching-anthropic "Direct link to Prompt Caching (Anthropic)")

Source: `agent/prompt_caching.py`

Reduces input token costs by ~75% on multi-turn conversations by caching the
conversation prefix. Uses Anthropic's `cache_control` breakpoints.

### Strategy: system\_and\_3 [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#strategy-system_and_3 "Direct link to Strategy: system_and_3")

Anthropic allows a maximum of 4 `cache_control` breakpoints per request. Hermes
uses the "system\_and\_3" strategy:

```text
Breakpoint 1: System prompt           (stable across all turns)
Breakpoint 2: 3rd-to-last non-system message  ─┐
Breakpoint 3: 2nd-to-last non-system message   ├─ Rolling window
Breakpoint 4: Last non-system message          ─┘
```

### How It Works [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#how-it-works "Direct link to How It Works")

`apply_anthropic_cache_control()` deep-copies the messages and injects
`cache_control` markers:

```python
# Cache marker format
marker = {"type": "ephemeral"}
# Or for 1-hour TTL:
marker = {"type": "ephemeral", "ttl": "1h"}
```

The marker is applied differently based on content type:

| Content Type | Where Marker Goes |
| --- | --- |
| String content | Converted to `[{"type": "text", "text": ..., "cache_control": ...}]` |
| List content | Added to the last element's dict |
| None/empty | Added as `msg["cache_control"]` |
| Tool messages | Added as `msg["cache_control"]` (native Anthropic only) |

### Cache-Aware Design Patterns [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#cache-aware-design-patterns "Direct link to Cache-Aware Design Patterns")

1. **Stable system prompt**: The system prompt is breakpoint 1 and cached across
all turns. Avoid mutating it mid-conversation (compression appends a note
only on the first compaction).

2. **Message ordering matters**: Cache hits require prefix matching. Adding or
removing messages in the middle invalidates the cache for everything after.

3. **Compression cache interaction**: After compression, the cache is invalidated
for the compressed region but the system prompt cache survives. The rolling
3-message window re-establishes caching within 1-2 turns.

4. **TTL selection**: Default is `5m` (5 minutes). Use `1h` for long-running
sessions where the user takes breaks between turns.


### Enabling Prompt Caching [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#enabling-prompt-caching "Direct link to Enabling Prompt Caching")

Prompt caching is automatically enabled when:

- The model is an Anthropic Claude model (detected by model name)
- The provider supports `cache_control` (native Anthropic API or OpenRouter)

```yaml
# config.yaml — TTL is configurable (must be "5m" or "1h")
prompt_caching:
  cache_ttl: "5m"
```

The CLI shows caching status at startup:

```text
💾 Prompt caching: ENABLED (Claude via OpenRouter, 5m TTL)
```

## Context Pressure Warnings [​](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching\#context-pressure-warnings "Direct link to Context Pressure Warnings")

Intermediate context-pressure warnings have been removed (see the iteration-budget block in `run_agent.py`, which notes: "No intermediate pressure warnings — they caused models to 'give up' prematurely on complex tasks"). Compression fires when prompt tokens reach the configured `compression.threshold` (default 50%) with no prior warning step; gateway session hygiene fires as the secondary safety net at 85% of the model's context window.

[Edit this page](https://github.com/NousResearch/hermes-agent/edit/main/website/docs/developer-guide/context-compression-and-caching.md)

[Previous\\
\\
Prompt Assembly](https://hermes-agent.nousresearch.com/docs/developer-guide/prompt-assembly) [Next\\
\\
Gateway Internals](https://hermes-agent.nousresearch.com/docs/developer-guide/gateway-internals)

- [Pluggable Context Engine](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#pluggable-context-engine)
- [Dual Compression System](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#dual-compression-system)
  - [1\. Gateway Session Hygiene (85% threshold)](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#1-gateway-session-hygiene-85-threshold)
  - [2\. Agent ContextCompressor (50% threshold, configurable)](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#2-agent-contextcompressor-50-threshold-configurable)
- [Configuration](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#configuration)
  - [Parameter Details](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#parameter-details)
  - [Computed Values (for a 200K context model at defaults)](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#computed-values-for-a-200k-context-model-at-defaults)
- [Compression Algorithm](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#compression-algorithm)
  - [Phase 1: Prune Old Tool Results (cheap, no LLM call)](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#phase-1-prune-old-tool-results-cheap-no-llm-call)
  - [Phase 2: Determine Boundaries](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#phase-2-determine-boundaries)
  - [Phase 3: Generate Structured Summary](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#phase-3-generate-structured-summary)
  - [Phase 4: Assemble Compressed Messages](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#phase-4-assemble-compressed-messages)
  - [Iterative Re-compression](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#iterative-re-compression)
- [Before/After Example](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#beforeafter-example)
  - [Before Compression (45 messages, ~95K tokens)](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#before-compression-45-messages-95k-tokens)
  - [After Compression (25 messages, ~45K tokens)](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#after-compression-25-messages-45k-tokens)
- [Prompt Caching (Anthropic)](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#prompt-caching-anthropic)
  - [Strategy: system\_and\_3](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#strategy-system_and_3)
  - [How It Works](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#how-it-works)
  - [Cache-Aware Design Patterns](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#cache-aware-design-patterns)
  - [Enabling Prompt Caching](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#enabling-prompt-caching)
- [Context Pressure Warnings](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching#context-pressure-warnings)

Docs

- [Getting Started](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)
- [User Guide](https://hermes-agent.nousresearch.com/docs/user-guide/cli)
- [Developer Guide](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)
- [Reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands)

Community

- [Discord](https://discord.gg/NousResearch)
- [GitHub Issues](https://github.com/NousResearch/hermes-agent/issues)
- [Skills Hub](https://agentskills.io/)

More

- [Desktop Download](https://hermes-agent.nousresearch.com/desktop)
- [GitHub](https://github.com/NousResearch/hermes-agent)
- [Nous Research](https://nousresearch.com/)

Built by [Nous Research](https://nousresearch.com/) · MIT License · 2026