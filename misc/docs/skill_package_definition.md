# `skill` — A Python Package for AI Agent Skill Management

## Package Identity

- **PyPI name**: `skill`
- **Primary target**: Claude Code (skills in `.claude/skills/`)
- **Secondary targets**: Claude.ai (Customize > Skills), Cursor (`.cursor/rules/`), GitHub Copilot (`.github/copilot-instructions.md`), Windsurf (`.windsurf/rules/`), Codex, Gemini CLI, and any agent supporting the emerging **Agent Skills specification** (SKILL.md format)
- **Architecture style**: Mapping-based facades (à la `haggle`/`hfdol`), functional core, `dol` for storage abstraction, `platformdirs` for cross-platform paths, `argh` for CLI dispatch

---

## Terminology

| Term | Meaning |
|------|---------|
| **Skill** | A folder containing a `SKILL.md` (YAML frontmatter + Markdown body), plus optional `scripts/`, `references/`, `assets/` subdirectories. The atomic unit of reusable agent context. |
| **Skill package** | A git repo (or directory) containing one or more skills. The unit of distribution (analogous to an npm package or Python distribution). |
| **Frontmatter** | The YAML block between `---` markers at the top of `SKILL.md`. Contains `name` and `description` (required), plus optional `allowed-tools`, `compatibility`, etc. This is the **metadata** that agents index for routing. |
| **Skill body** | The Markdown content after the frontmatter. The actual instructions the agent loads into context on activation. |
| **Bundled resources** | Supporting files alongside `SKILL.md`: `scripts/` (executable code), `references/` (docs loaded on demand), `assets/` (templates, icons). |
| **Agent Skills specification** | The open standard (originated by Anthropic, adopted by Vercel/skills CLI and 40+ agents) defining the SKILL.md format, progressive disclosure model, and folder conventions. See [agentskills.io](https://agentskills.io). |
| **Skill store** | A `Mapping`-based abstraction over a collection of skills (local or remote). Keys are canonical identifiers (e.g., `"owner/skill-name"`). |
| **Skill registry / hub** | A remote source of skill packages: GitHub repos, skills.sh directory, Agensi.io marketplace, Anthropic's official `anthropics/skills` repo, etc. |
| **Agent target** | A specific AI coding tool that consumes skills (claude-code, cursor, copilot, windsurf, etc.). Each has its own filesystem layout for skill/rule installation. |
| **Installation** | Placing a skill (by symlink or copy) into an agent target's expected directory, at project or global scope. |
| **Progressive disclosure** | The loading model: agents see only frontmatter (~100 tokens) at startup; load full `SKILL.md` on activation; load bundled resources on demand. |

---

## Core Functionality Areas

### 1. Skill Discovery (Search)

**Local search:**
- Scan frontmatter of all locally installed skills (across all agent targets and the `skill` app data folder)
- Build/cache a lightweight index: `{skill_id: {name, description, path, agent_targets, ...}}`
- Keyword matching against name + description
- Semantic search mode: feed the index to an LLM and let it pick the best matches for a natural-language query
- Agentic search mode: an agent that uses the search tools iteratively, reading deeper into skill bodies when needed to assess relevance

**Remote search:**
- Facade over multiple backend APIs (GitHub search, skills.sh, Agensi.io, Anthropic's official repo, etc.)
- Unified `search(query, *, backends=None, max_results=10)` interface
- Each backend adapter returns a common `SkillInfo` dataclass: `{id, name, description, source, url, author, ...}`
- Filter, keyword, and (where supported) semantic search delegated to backends

### 2. Skill CRUD (Local Management)

**Storage abstraction** (Mapping protocol, `dol`-based):
- `SkillStore` — a `MutableMapping[str, Skill]` over the `skill` app data folder (`~/.local/share/skill/skills/` on Linux, platform equivalent elsewhere via `platformdirs`)
- Keys: canonical `"owner/skill-name"` or just `"skill-name"` for local-only skills
- `__getitem__` returns a `Skill` object (parsed frontmatter + body + resource manifest)
- `__setitem__` writes a well-formed skill folder
- `__delitem__` removes the skill folder (and any symlinks pointing to it)
- `__iter__` yields keys of locally stored skills
- Two-tier sourced store pattern (à la `haggle`): local store + remote source, with cache-miss fetch

**CRUD operations exposed as functions:**
- `create(name, description, body, *, scripts=None, references=None, assets=None)` → writes a new skill
- `read(skill_id)` → returns Skill object
- `update(skill_id, *, description=None, body=None, ...)` → patches an existing skill
- `delete(skill_id)` → removes skill and unlinks from all agent targets
- `list(*, agent_target=None, scope='all')` → lists installed skills, optionally filtered

### 3. Skill Installation (Cross-Agent Deployment)

**Installation targets** — each agent has a known directory layout:
| Agent | Global path | Project path |
|-------|------------|-------------|
| Claude Code | `~/.claude/skills/<name>/` | `.claude/skills/<name>/` |
| Claude.ai | ZIP upload via UI (or API) | N/A |
| Cursor | `~/.cursor/rules/` (or `.cursor/rules/`) | `.cursor/rules/` |
| Copilot | N/A | `.github/copilot-instructions.md` |
| Windsurf | `~/.windsurf/rules/` | `.windsurf/rules/` |
| AGENTS.md | N/A | `AGENTS.md` (project root) |
| Vercel skills CLI | Via `npx skills add` | Via `npx skills add` |

**Installation strategy:**
1. Skill lives canonically in `skill`'s own app data folder (e.g., `~/.local/share/skill/skills/owner/skill-name/`)
2. By default, install creates a **symlink** from the agent target's directory to the canonical location
3. Flag `--copy` forces a full copy instead of symlink
4. On Windows, uses `mklink /D` (directory junction) for symlink equivalent
5. Before creating `.claude/` (or any agent directory) in a project, check if it already exists; if not, prompt the user for confirmation to avoid littering
6. `install(skill_id, *, agent_targets=None, scope='project', copy=False)` — main install function
7. `uninstall(skill_id, *, agent_targets=None, scope='project')` — removes links/copies

**Format translation** (when needed):
- Claude Code skills (SKILL.md) are the canonical internal format
- For Cursor: translate to `.mdc` file (YAML frontmatter with `description`, `globs`, `alwaysApply` + Markdown body)
- For Copilot: append to `copilot-instructions.md` (flat Markdown, no frontmatter)
- For Windsurf: translate to `.md` rule file in `.windsurf/rules/`
- For AGENTS.md: append a section to the project-root `AGENTS.md`
- Translation is lossy in some directions (Cursor's glob-scoping has no equivalent in Copilot); the translator should warn about lost semantics

### 4. Skill Creation & Maintenance Tools

- `scaffold(name, *, description=None, template=None)` — generates a new skill folder with boilerplate `SKILL.md` and optional subdirectories
- `validate(skill_path)` — checks frontmatter correctness, body length, resource references, etc.
- `lint(skill_path)` — checks best practices (description is "pushy" enough, body under 5000 words, etc.)
- `test(skill_path, *, prompts=None)` — runs sample prompts against the skill (requires AI API)
- `diff(skill_a, skill_b)` — compares two skills structurally
- `import_from(path_or_url, *, format='auto')` — imports a skill from external format (Cursor `.mdc`, Copilot instructions, etc.) into canonical SKILL.md format

### 5. Skill Reuse (Derived Artifacts)

- **MCP server generation**: Given a skill with `scripts/`, generate a minimal MCP server (using `py2mcp` or `FastMCP`) that exposes those scripts as tools
- **Subagent specification**: Generate a subagent config (for Claude Code's `.claude/agents/` or similar) from a skill's instructions
- **Prompt template extraction**: Extract the skill body as a reusable prompt template for use in API calls
- **Skill composition**: Combine multiple skills into a meta-skill that references them

### 6. Configuration & Preferences

**Config location** (via `platformdirs`):
- Linux: `~/.config/skill/config.json`
- macOS: `~/Library/Application Support/skill/config.json`
- Windows: `%APPDATA%\skill\config.json`

**Data location** (via `platformdirs`):
- Linux: `~/.local/share/skill/`
- macOS: `~/Library/Application Support/skill/`
- Windows: `%LOCALAPPDATA%\skill\`

**Config contents:**
```json
{
  "default_agent_targets": ["claude-code"],
  "default_scope": "project",
  "install_method": "symlink",
  "ai_service": {
    "provider": "anthropic",
    "api_key": "$ANTHROPIC_API_KEY",
    "model": "claude-sonnet-4-20250514"
  },
  "remote_backends": {
    "github": {"enabled": true},
    "skills_sh": {"enabled": true},
    "agensi": {"enabled": false}
  },
  "search_index_cache_ttl": 3600
}
```

- Values starting with `$` are resolved from `os.environ`
- AI service config supports multiple providers via a facade (research needed on best library)

---

## Interfaces / Surfaces

### 1. Python API (primary)
The `skill` package itself. `from skill import search, install, create, ...`

### 2. CLI (via `argh`)
`python -m skill search "react best practices"`  
`python -m skill install anthropics/skills --skill frontend-design`  
`python -m skill create my-skill --description "..."`  
`python -m skill list --agent claude-code`  
`python -m skill validate ./my-skill/`

### 3. MCP Server
Expose `skill`'s functionality as an MCP server so that AI agents (Claude Code, etc.) can themselves search for, install, and manage skills programmatically. Built with `py2mcp` or `FastMCP`.

### 4. Claude Code Skill (meta-skill)
A skill *about* skill management — a `SKILL.md` that teaches Claude Code how to use the `skill` CLI to discover, install, and manage skills. Self-referential but practical.

### 5. HTTP API (future, via `qh`)
For web UIs, browser extensions, or remote integrations.

---

## Architectural Decisions

1. **Canonical format = Agent Skills spec (SKILL.md)** — all internal storage and operations use this format. Translation to other formats is a lossy export.
2. **Canonical storage = `skill`'s own app data folder** — skills are stored once, linked many times. This is the SSOT for skill content.
3. **`dol`-based Mapping stores** — both local and remote skill collections are accessed via `Mapping` protocol, enabling composition, caching, and the two-tier sourced-store pattern.
4. **`platformdirs` for cross-platform paths** — no hardcoded `~/.local/share/` etc.
5. **`argh` for CLI dispatch** — SSOT pattern where the same functions serve both the Python API and the CLI.
6. **Progressive disclosure in the package itself** — simple `search()` and `install()` for quick use, full `SkillStore` Mapping for power users.
7. **AI-optional** — core CRUD, search (keyword), install, and validate work without any AI API. Semantic search and agentic features require an AI service config.

---

## Package Structure (Preliminary)

```
skill/
├── pyproject.toml
├── skill/
│   ├── __init__.py          # Public API: search, install, create, list, ...
│   ├── base.py              # Core dataclasses: Skill, SkillInfo, SkillMeta
│   ├── stores.py            # Mapping-based stores (local, remote, sourced)
│   ├── install.py           # Installation logic (symlink, copy, agent targets)
│   ├── translate.py         # Format translators (SKILL.md ↔ .mdc, copilot, etc.)
│   ├── search.py            # Search facade (local index, remote backends)
│   ├── backends/            # Remote backend adapters
│   │   ├── __init__.py
│   │   ├── github.py        # GitHub API / git clone
│   │   ├── skills_sh.py     # skills.sh directory
│   │   └── agensi.py        # Agensi.io API
│   ├── create.py            # Scaffolding, validation, linting
│   ├── reuse.py             # MCP server gen, subagent gen, composition
│   ├── config.py            # Configuration management (platformdirs)
│   ├── ai.py                # AI service facade (for semantic search, agentic features)
│   ├── util.py              # Internal helpers
│   ├── __main__.py          # CLI entry point (argh dispatch)
│   └── data/                # Package resources (templates, etc.)
│       └── skill_template/
│           └── SKILL.md
├── tests/
│   └── ...
└── README.md
```

---

## Open Research Questions

These are addressed by the research plans in the accompanying files:

1. **What remote backends/registries exist?** What are their APIs, key formats, and how do we acquire skills from them? (Research Plan 1)
2. **How do we translate between agent-specific formats?** What's the current state of the Agent Skills spec? What are the semantic gaps? (Research Plan 2)
3. **What similar/related tools exist?** Can we facade/aggregate them? What can we learn from their design? (Research Plan 3)
4. **What surfaces/interfaces should we expose?** MCP server, Claude Code skill, HTTP API — what's the best strategy? (Research Plan 4)
5. **What's the best AI API facade?** How should we handle multi-provider AI service configuration? (Research Plan 5)
6. **What are the right storage and installation patterns?** Symlink strategies, platform differences, config standards. (Research Plan 6)
