# Skill: AI API Facade & Configuration Management

**For the `skill` Python package — AI agent skill management**

---

## 1. Recommended AI API facade library

### Executive recommendation: **Build a thin custom facade, with `aisuite` as the optional backend**

After evaluating all candidates, the right strategy for `skill` is a **two-layer architecture**:

1. **`skill.ai`** — a minimal facade module (~150 LOC) that defines the contract: `chat()`, `complete()`, `embeddings()`, and a `SkillAIClient` protocol class. This layer has **zero mandatory AI dependencies**.
2. **Pluggable backends** — the facade resolves to a concrete backend based on configuration. Supported backends, in priority order: `aisuite` (recommended default), direct SDK (`anthropic`, `openai`), or `litellm` (power users).

This mirrors the approach in the landscape survey [1], where tools like **Smithery.ai** and **PRPM** keep their core dependency-free and shell out to provider SDKs only when needed. It also follows the `skill` package definition's principle that **AI is optional** — core CRUD, keyword search, install, and validate work without any AI API [2].

### Candidate evaluation

| Library | Providers | Tool calling | Streaming | Dependencies | Verdict |
|---------|-----------|-------------|-----------|-------------|---------|
| **litellm** | 100+ | Yes | Yes | **56 direct+indirect** [3] | Too heavy for a CLI tool. Good as an optional power-user backend. |
| **aisuite** | ~12 (OpenAI, Anthropic, Google, Groq, Mistral, Ollama, Cohere, AWS, HuggingFace, Cerebras, Watsonx) | Yes (incl. MCP tools) | Yes | **1 core dep** (`docstring-parser`); providers are all optional extras [4] | **Best fit.** Lightweight, familiar `"provider:model"` syntax, provider SDKs are optional extras. |
| **aix** (Thor's own) | Multi-provider via `prompt_func`, `chat`, `embeddings` | Partial | Partial | Lightweight | Worth **using internally** as the bridge layer in `skill.ai`, since it's in Thor's ecosystem. But not mature enough to be the sole external recommendation. |
| **instructor** | 15+ via `from_provider()` | Core feature | Yes | **11 direct deps** (openai, pydantic, aiohttp, tenacity, jinja2, rich, typer, etc.) [5] | Excellent for structured output extraction (e.g., parsing skill search results), but it's a **complement**, not a replacement for a chat facade. |
| **pydantic-ai** | All major (OpenAI, Anthropic, Gemini, Bedrock, Ollama, etc.) | Yes (decorated tools, MCP, A2A) | Yes | Heavy (pydantic-graph, pydantic-evals ecosystem) [6] | Overkill as a dependency. It's an agent *framework*, not a lightweight facade. Great for agentic search as an optional extra. |
| **magentic** | OpenAI (native), Anthropic, Ollama, LiteLLM backend | Yes (`FunctionCall`, `ParallelFunctionCall`) | Yes | Moderate (openai + optional anthropic/litellm) [7] | Elegant `@prompt` decorator pattern — worth studying for `prompt_func` design in `aix`. But too opinionated for a generic facade. |
| **langchain-core** | All major | Yes | Yes | **Very heavy** transitive tree | Firmly rejected. Wrong layer of abstraction. |
| **Direct SDKs** | 1 each | Yes | Yes | Minimal per-provider | Best control, most work. Good as a fallback strategy. |

### Why aisuite wins

The `"provider:model"` string convention (e.g., `"anthropic:claude-sonnet-4-20250514"`) is becoming a de facto standard — used by aisuite, instructor's `from_provider()`, and litellm's model prefixes. This convention maps cleanly to a config value:

```json
{"ai_service": {"provider_model": "anthropic:claude-sonnet-4-20250514"}}
```

Aisuite's architecture — **base package has zero provider deps, each provider is an optional extra** — directly mirrors the `skill` package's own dependency strategy [2]. Install `aisuite` for the facade; install `aisuite[anthropic]` only if you need Anthropic. The `pip install skill[ai]` extra maps naturally to `pip install aisuite[anthropic]` (or whichever provider the user configures).

### Where `aix` fits

`aix` already provides `chat()`, `prompt_func()`, `embeddings()`, and `models.discover()` in Thor's idiom [8]. Rather than depending on aisuite *and* aix, the recommended approach:

- `skill.ai` **protocol** defines the interface (a `Mapping`-flavored contract, consistent with the package's `dol`-based architecture)
- `aix` is the **default backend** if installed (since it's in Thor's ecosystem and already handles multi-provider resolution)
- `aisuite` is the **recommended backend** documented for external users who don't have `aix`
- Direct SDK calls are the **fallback** for users who want zero facade dependencies

This is the progressive disclosure pattern from the package definition [2]: simple `chat("query")` for beginners, full `SkillAIClient(backend="litellm", model="...")` for power users.

---

## 2. Config file format recommendation

### Recommendation: **TOML** (with JSON as the serialization format for programmatic writes)

**Rationale:**

- Python 3.11+ ships `tomllib` in stdlib — **zero extra dependencies** for reading
- TOML supports comments, which is critical for a user-edited config file (JSON doesn't)
- The `skill` ecosystem is a developer tool; TOML is the native config format for Python packaging (`pyproject.toml`) — familiar territory
- For programmatic config writes, use `tomli_w` (tiny optional dep, ~3KB) or fall back to JSON
- The landscape survey [1] shows tools like **cursor-doctor** and **Ruler** use YAML, but YAML requires `pyyaml` as a dependency and has well-known gotchas (implicit type coercion: `no` → `False`, `3.10` → `3.1`)

**Convention borrowed from ecosystem:** The **Vercel Skills CLI** uses JSON for its `skills-lock.json` [1], and **PRPM** uses YAML for test configs. TOML splits the difference: human-readable like YAML, no extra deps like JSON.

---

## 3. Config schema definition

```toml
# ~/.config/skill/config.toml  (Linux)
# ~/Library/Application Support/skill/config.toml  (macOS)
# %APPDATA%\skill\config.toml  (Windows)

[defaults]
agent_targets = ["claude-code"]       # which agents to install to
scope = "project"                     # "project" | "global"
install_method = "symlink"            # "symlink" | "copy"

[ai]
provider_model = "anthropic:claude-sonnet-4-20250514"
api_key = "$ANTHROPIC_API_KEY"        # $-prefixed = env var resolution
# Alternative models for cost-sensitive operations:
# provider_model_fast = "anthropic:claude-haiku-4-5-20251001"

[backends]
github = true
skills_sh = true
agensi = false
# smithery = false  # future integration

[search]
index_cache_ttl = 3600                # seconds
semantic_search_enabled = true        # requires [ai] to be configured

[behavior]
confirm_directory_creation = true     # prompt before creating .claude/, .cursor/, etc.
color_output = true
```

**As a Pydantic model** (the programmatic SSOT):

```python
from pydantic import BaseModel, Field
from typing import Literal

class AIConfig(BaseModel):
    """AI service configuration."""
    provider_model: str = "anthropic:claude-sonnet-4-20250514"
    api_key: str = "$ANTHROPIC_API_KEY"
    provider_model_fast: str | None = None

class BackendsConfig(BaseModel):
    """Remote search backend toggles."""
    github: bool = True
    skills_sh: bool = True
    agensi: bool = False

class DefaultsConfig(BaseModel):
    """Installation defaults."""
    agent_targets: list[str] = Field(default_factory=lambda: ["claude-code"])
    scope: Literal["project", "global"] = "project"
    install_method: Literal["symlink", "copy"] = "symlink"

class SearchConfig(BaseModel):
    """Search behavior."""
    index_cache_ttl: int = 3600
    semantic_search_enabled: bool = True

class BehaviorConfig(BaseModel):
    """UX behavior."""
    confirm_directory_creation: bool = True
    color_output: bool = True

class SkillConfig(BaseModel):
    """Root config schema for the skill package."""
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    backends: BackendsConfig = Field(default_factory=BackendsConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    behavior: BehaviorConfig = Field(default_factory=BehaviorConfig)
```

---

## 4. Environment variable resolution strategy

### Recommendation: **`$VAR_NAME` syntax with stdlib `os.environ` resolution**

The convention: any string value in the config that starts with `$` is resolved from `os.environ` at load time. This is the simplest approach and follows widespread precedent:

- Docker Compose uses `$VAR` and `${VAR}` syntax
- The Vercel Skills CLI reads API keys from environment [1]
- `aisuite` and `litellm` both rely on `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` env vars natively

**Implementation sketch:**

```python
import os
import re

def _resolve_env_vars(value: str) -> str:
    """Resolve $VAR_NAME and ${VAR_NAME} references in config values."""
    if not isinstance(value, str):
        return value
    
    def _replace(match):
        var_name = match.group(1) or match.group(2)
        result = os.environ.get(var_name)
        if result is None:
            raise EnvironmentError(
                f"Environment variable {var_name!r} not set. "
                f"Set it with: export {var_name}=your-key-here"
            )
        return result
    
    return re.sub(r'\$\{(\w+)\}|\$(\w+)', _replace, value)
```

**Both `$VAR` and `${VAR}` are supported.** The `${VAR}` form allows embedding in longer strings (e.g., `"Bearer ${MY_TOKEN}"`), while `$VAR` is the simple case. No `env:VAR_NAME` prefix — it adds vocabulary without adding value.

**Key UX decision:** When env var resolution fails, provide an actionable error message with the exact `export` command needed. This follows the package definition's UX principle of guiding users dynamically [2].

---

## 5. Dependency management strategy

### Core dependencies (always installed)

| Package | Purpose | Size |
|---------|---------|------|
| `platformdirs` | Cross-platform config/data paths | Tiny (~15KB) |
| `argh` | CLI dispatch (SSOT pattern) | Small |
| `dol` | Mapping abstractions for stores | In Thor's ecosystem |
| `pydantic` | Config schema, Skill dataclass validation | Already ubiquitous |

**Stdlib only:** `tomllib` (Python 3.11+), `json`, `pathlib`, `os`, `subprocess`, `re`

### Optional dependency groups

```toml
[project.optional-dependencies]
ai = ["aisuite"]                                    # AI facade (no provider SDKs yet)
anthropic = ["aisuite", "anthropic"]                # AI + Anthropic provider
openai = ["aisuite", "openai"]                      # AI + OpenAI provider  
ollama = ["aisuite"]                                # Ollama needs no extra SDK
ai-all = ["aisuite[all]"]                           # All AI providers
mcp = ["py2mcp"]                                    # MCP server generation
test = ["promptfoo"]                                # Skill testing (future)
all = ["skill[ai-all]", "skill[mcp]", "skill[test]"]
```

### Graceful degradation pattern

Borrowed from the landscape survey's observation that **AI-optional** is a core architectural decision [2]:

```python
# skill/ai.py
"""AI service facade. All AI features degrade gracefully when deps are missing."""

def _check_ai_available():
    """Check if an AI backend is available, with helpful install instructions."""
    try:
        import aisuite
        return True
    except ImportError:
        pass
    try:
        import aix
        return True
    except ImportError:
        pass
    return False

def chat(prompt: str, *, model: str | None = None, **kwargs) -> str:
    """Send a chat prompt to the configured AI provider.
    
    >>> # Requires: pip install skill[ai] and a configured API key
    """
    if not _check_ai_available():
        raise ImportError(
            "AI features require an AI backend. Install one with:\n"
            "  pip install 'skill[anthropic]'   # Anthropic Claude\n"
            "  pip install 'skill[openai]'      # OpenAI GPT\n"
            "  pip install 'skill[ollama]'      # Local models via Ollama\n"
            "\nThen configure your API key:\n"
            "  export ANTHROPIC_API_KEY=your-key-here\n"
            "  skill config set ai.provider_model anthropic:claude-sonnet-4-20250514"
        )
    # ... dispatch to backend
```

---

## 6. First-run experience design

### Recommendation: **Zero-config with progressive prompting**

The first-run experience should follow the **"pit of success"** pattern — `skill search "react"` should work immediately for keyword search (no config needed), and only prompt when AI features are requested.

**Flow:**

1. **First invocation of any command:** `skill` creates its data directory silently via `platformdirs`. No wizard. No prompts.

2. **First invocation of a keyword-search command:** Works immediately — indexes local skills by scanning known agent directories (`.claude/skills/`, `.cursor/rules/`, etc.).

3. **First invocation of an AI-requiring command** (e.g., `skill search --semantic "react patterns"`):
   - Check for config file → not found → check for common env vars
   - **Auto-detect sequence:** `$ANTHROPIC_API_KEY` → `$OPENAI_API_KEY` → `$GOOGLE_API_KEY`
   - If found: auto-configure, inform user: `"Found $ANTHROPIC_API_KEY, using anthropic:claude-sonnet-4-20250514. Run 'skill config' to change."`
   - If not found: print actionable guidance:
     ```
     AI features require an API key. Fastest setup:
       export ANTHROPIC_API_KEY=your-key-here
       
     Or configure manually:
       skill config set ai.provider_model openai:gpt-4o
       skill config set ai.api_key $OPENAI_API_KEY
       
     Or use local models (no API key needed):
       skill config set ai.provider_model ollama:llama3.2
     ```

4. **Explicit `skill config init`:** Interactive wizard for users who want full control. Walks through provider selection, API key, default agent targets, install method. This is the power-user path.

**Borrowed from ecosystem:** This mirrors how the **Vercel Skills CLI** works — `npx skills add` just works, no init step [1]. It also follows `aisuite`'s pattern where env vars are auto-detected [4].

---

## 7. Code sketch of the facade interface

```python
"""skill/ai.py — AI service facade for the skill package.

Provides a thin, backend-agnostic interface for LLM operations needed by skill:
- chat(): simple prompt → response (for semantic search, linting, creation)  
- complete_structured(): prompt → Pydantic model (for structured search results)

All functions accept an optional `model` override; default comes from config.
"""

from __future__ import annotations

import os
from typing import TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel

T = TypeVar('T')


# ---------------------------------------------------------------------------
# Backend resolution
# ---------------------------------------------------------------------------

def _resolve_config():
    """Load AI config from skill's config file, with env var resolution."""
    from skill.config import load_config
    cfg = load_config()
    return cfg.ai


def _get_backend():
    """Resolve the AI backend in priority order.
    
    Priority: aix → aisuite → direct anthropic SDK → direct openai SDK.
    """
    # Try aix first (Thor's ecosystem)
    try:
        from aix import chat as _aix_chat
        return 'aix'
    except ImportError:
        pass
    
    # Try aisuite
    try:
        import aisuite
        return 'aisuite'
    except ImportError:
        pass
    
    # Try direct SDKs
    try:
        import anthropic
        return 'anthropic'
    except ImportError:
        pass
    
    try:
        import openai
        return 'openai'
    except ImportError:
        pass
    
    return None


def _ensure_backend():
    """Ensure an AI backend is available or raise with install instructions."""
    backend = _get_backend()
    if backend is None:
        raise ImportError(
            "No AI backend found. Install one:\n"
            "  pip install 'skill[anthropic]'\n"
            "  pip install 'skill[openai]'\n"
            "  pip install 'skill[ollama]'\n"
        )
    return backend


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chat(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Send a prompt and get a text response.

    Uses the configured provider_model from skill's config, 
    or the `model` override if given.

    >>> chat("What is 2+2?")  # doctest: +SKIP
    'The answer is 4.'
    """
    backend = _ensure_backend()
    cfg = _resolve_config()
    provider_model = model or cfg.provider_model
    api_key = _resolve_env_var(cfg.api_key)
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    if backend == 'aix':
        from aix import chat as aix_chat
        return aix_chat(prompt, model=provider_model)
    
    elif backend == 'aisuite':
        import aisuite as ai
        client = ai.Client()
        response = client.chat.completions.create(
            model=provider_model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content
    
    elif backend == 'anthropic':
        import anthropic
        _, model_name = provider_model.split(":", 1) if ":" in provider_model else ("anthropic", provider_model)
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model_name,
            max_tokens=4096,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    
    elif backend == 'openai':
        import openai
        _, model_name = provider_model.split(":", 1) if ":" in provider_model else ("openai", provider_model)
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content


def complete_structured(
    prompt: str,
    response_model: type[T],
    *,
    system: str | None = None,
    model: str | None = None,
) -> T:
    """Send a prompt and parse the response into a Pydantic model.
    
    Uses instructor if available, falls back to JSON-mode + manual parsing.
    
    >>> from pydantic import BaseModel
    >>> class SkillMatch(BaseModel):
    ...     name: str
    ...     relevance: float
    >>> complete_structured("Find skills for React", SkillMatch)  # doctest: +SKIP
    SkillMatch(name='react-best-practices', relevance=0.95)
    """
    try:
        import instructor
        cfg = _resolve_config()
        provider_model = model or cfg.provider_model
        client = instructor.from_provider(provider_model)
        return client.chat.completions.create(
            response_model=response_model,
            messages=[
                *([{"role": "system", "content": system}] if system else []),
                {"role": "user", "content": prompt},
            ],
        )
    except ImportError:
        # Fallback: ask for JSON, parse manually
        import json
        json_prompt = (
            f"{prompt}\n\nRespond ONLY with a JSON object matching this schema:\n"
            f"{response_model.model_json_schema()}"
        )
        raw = chat(json_prompt, system=system, model=model)
        # Strip markdown fences if present
        clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
        return response_model.model_validate_json(clean)


def _resolve_env_var(value: str) -> str:
    """Resolve $VAR or ${VAR} references."""
    if not value.startswith("$"):
        return value
    var_name = value.lstrip("$").strip("{}")
    result = os.environ.get(var_name)
    if result is None:
        raise EnvironmentError(
            f"Environment variable {var_name!r} not set.\n"
            f"Set it with: export {var_name}=your-key-here"
        )
    return result
```

**Design notes:**

- The `chat()` function signature borrows from `aix.chat()` — minimal, functional, no class instantiation required [8]
- The `complete_structured()` function uses `instructor.from_provider()` when available — its `"provider/model"` convention (slash-separated) vs. aisuite's `"provider:model"` (colon-separated) needs a thin adapter. The instructor `from_provider()` pattern [5] is the cleanest API for structured extraction
- The `_get_backend()` priority chain follows the progressive disclosure principle: Thor's `aix` first (ecosystem loyalty), then the recommended public option (`aisuite`), then direct SDKs as fallback
- The whole module is importable without any AI dependencies installed — all imports are lazy

---

## Appendix: Comparison matrix (quick reference)

| Criterion | litellm | aisuite | aix | instructor | pydantic-ai | magentic | Direct SDKs |
|-----------|---------|---------|-----|------------|-------------|----------|-------------|
| Core deps | 56 | 1 | ~2 | 11 | moderate | ~3 | 1 each |
| Provider count | 100+ | ~12 | multi | 15+ | all major | 3+litellm | 1 each |
| Tool/fn calling | Yes | Yes | partial | core | Yes | Yes | Yes |
| Streaming | Yes | Yes | partial | Yes | Yes | Yes | Yes |
| Structured output | via SDK | via SDK | partial | **core** | **core** | Yes | manual |
| `provider:model` convention | prefix-based | Yes | implicit | slash-based | Yes | config | N/A |
| Suitable as dep for CLI tool | No (heavy) | **Yes** | **Yes** | Maybe | No (framework) | Maybe | **Yes** |
| MCP integration | experimental | Yes | No | No | Yes (A2A too) | No | No |

---

## REFERENCES

[1] Landscape survey: "The AI agent skills ecosystem — a complete landscape survey" (uploaded document). Covers Vercel Skills CLI, skills.sh, format conversion tools, and ecosystem gaps.

[2] Skill package definition: "`skill` — A Python Package for AI Agent Skill Management" (uploaded document). Defines architecture, config schema, and the AI-optional principle.

[3] [litellm (PyPI)](https://pypi.org/project/litellm/) — 56 direct+indirect dependencies per deps.dev. 100+ LLM providers, MIT license. Latest release March 2026.

[4] [aisuite (GitHub)](https://github.com/andrewyng/aisuite) — Andrew Ng's lightweight multi-provider facade. 12K+ stars. Only core dep is `docstring-parser`; all providers are optional extras. Supports tool calling and MCP.

[5] [instructor (GitHub)](https://github.com/567-labs/instructor) — 11K stars, 3M+ monthly downloads. Structured output extraction with Pydantic. `from_provider("provider/model")` unified interface. Core deps include openai, pydantic, tenacity, aiohttp.

[6] [pydantic-ai (PyPI)](https://pypi.org/project/pydantic-ai/) — Pydantic team's agent framework. Full agent lifecycle with tools, evals, MCP, A2A. Latest v1.69.0, March 2026.

[7] [magentic (GitHub)](https://github.com/jackmpcollins/magentic) — Decorator-based LLM integration. `@prompt` and `@chatprompt` for function-as-prompt pattern. Supports OpenAI, Anthropic, Ollama, and LiteLLM backends.

[8] [aix (PyPI)](https://pypi.org/project/aix/) — Thor's own AI operations library. Provides `chat()`, `prompt_func()`, `embeddings()`, `models.discover()`. v0.0.25, Feb 2026. Apache-2.0.
