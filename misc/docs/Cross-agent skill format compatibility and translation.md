# Cross-agent skill format compatibility and translation

**The Agent Skills specification (SKILL.md) has emerged as the dominant open standard for AI coding agent instructions, with 41+ agents adopting it natively — but critical translation gaps remain for agents with incompatible legacy formats.** Anthropic released the spec in December 2025, and Vercel's `skills` CLI now installs SKILL.md files across all 41 adopters via symlinks, eliminating the need for format conversion in most cases. However, Cursor's `.mdc` frontmatter, Copilot's `applyTo` globs, and Windsurf's `trigger` field each encode scoping semantics that SKILL.md lacks, making bidirectional translation inherently lossy. A `skill` package should use **symlinks for the 41 native adopters** and **lossy translation for the 3-4 incompatible formats**, with clear metadata annotations to preserve round-trip fidelity where possible.

---

## The Agent Skills specification is the canonical format

The Agent Skills spec, released December 18, 2025 at agentskills.io, defines a directory-based skill format with a `SKILL.md` entrypoint containing YAML frontmatter and Markdown instructions [1]. Anthropic created it for Claude Code, then open-sourced it under Apache 2.0 (code) and CC-BY-4.0 (docs) [2].

Each skill is a **directory** (not a single file), with the directory name matching the `name` frontmatter field:

```
my-skill/
├── SKILL.md          # Required: YAML frontmatter + Markdown body
├── scripts/          # Optional: executable Python/Bash scripts
├── references/       # Optional: documentation loaded on demand
├── assets/           # Optional: templates, binary files
└── examples/         # Optional: example output
```

The complete frontmatter schema has **six fields**, only two required:

| Field | Required | Constraints |
|-------|----------|-------------|
| `name` | **Yes** | Max 64 chars. Lowercase alphanumeric + hyphens. Regex: `^[a-z0-9]+(-[a-z0-9]+)*$` |
| `description` | **Yes** | Max 1024 chars. Describes what the skill does AND when to use it — this is the primary routing trigger |
| `license` | No | License name or reference to bundled LICENSE file |
| `compatibility` | No | Max 500 chars. Environment requirements (tools, packages, network) |
| `metadata` | No | Arbitrary string→string map. Common keys: `author`, `version`, `internal` |
| `allowed-tools` | No | Space-delimited pre-approved tools. **Experimental** — support varies by agent |

**The spec deliberately omits versioning and dependency fields.** Version is expressed through `metadata.version` as a convention, and skills are designed to be self-contained with no inter-skill dependency mechanism. Resource bundling follows a convention of `scripts/`, `references/`, and `assets/` subdirectories, with agents loading these on demand during the third stage of progressive disclosure.

The progressive disclosure model works in three stages: (1) at startup, only `name` + `description` are loaded (~100 tokens per skill); (2) when activated, the full SKILL.md body is injected (~5000 tokens recommended max); (3) during execution, bundled resources are read as needed. This keeps context efficient across large skill libraries.

**41 agents now support the spec natively**, including Claude Code, OpenAI Codex, GitHub Copilot, Cursor, Windsurf, Gemini CLI, Roo Code, Goose, Trae, Kiro CLI, Cline, Continue, Augment, JetBrains Junie, Amp, Qwen Code, OpenHands, Mistral Vibe, and many more [3].

---

## Agent-specific format specifications

### Claude Code: the reference implementation

Claude Code implements the richest superset of the Agent Skills spec, adding **seven Claude-specific frontmatter fields** beyond the base spec [4][5]:

| Claude-specific field | Type | Purpose |
|----------------------|------|---------|
| `disable-model-invocation` | boolean | Only user can invoke via `/skill-name`; agent cannot auto-trigger |
| `user-invocable` | boolean | If false, hides from slash menu; only agent can invoke |
| `context` | string | Set to `fork` to run in a forked subagent context |
| `agent` | string | Subagent type when forked: `Explore`, `Plan`, or custom agent name |
| `model` | string | Override model ID when skill is active |
| `mode` | boolean | Surfaces skill in "Mode Commands" section |
| `hooks` | object | Lifecycle hooks (PreToolUse, PostToolUse, Stop) scoped to skill |

Claude Code uses three instruction mechanisms with distinct semantics. **CLAUDE.md** at the project root (and in a hierarchy of parent/child directories) provides always-loaded project context via plain Markdown with `@path` import syntax for referencing other files. **Rules** in `.claude/rules/*.md` are modular instructions with an optional `paths:` frontmatter field for glob-based file scoping — rules without `paths:` load unconditionally, while path-scoped rules activate when Claude reads matching files. **Skills** in `.claude/skills/<name>/SKILL.md` are the most sophisticated: directory-based packages with progressive disclosure, bundled resources, and on-demand loading via the `Skill` tool.

The `Skill` tool is injected into Claude's system prompt with an `<available_skills>` XML block listing all discovered skill names and descriptions. Skill selection is **pure LLM reasoning** — no regex, keyword matching, or ML classifiers. When Claude determines a skill is relevant, it calls the Skill tool with the skill name, and the system injects the full SKILL.md body plus the skill's base directory path into the conversation as a tool result [6].

Key gotchas: `paths:` frontmatter in user-level rules (`~/.claude/rules/`) is currently ignored (only project-level works). Path-scoped rules only fire on Read operations, not Write/Create. The `allowed-tools` field is CLI-only — not respected by the Agent SDK.

### Cursor: MDC format with inferred activation modes

Cursor uses `.cursor/rules/*.mdc` files (Markdown with Components) containing exactly **three frontmatter fields** [7]:

```yaml
---
description: "When to apply this rule"   # string, default ""
globs: "src/**/*.ts,src/**/*.tsx"         # string or string[], default ""
alwaysApply: false                        # boolean, default false
---
```

The activation mode is **inferred from the combination of fields**, not declared explicitly:

- **Always Apply**: `alwaysApply: true` → loaded every conversation
- **Auto Attached**: `globs` set, `alwaysApply: false` → loaded when user references a matching file in chat
- **Agent Requested**: `description` set, no `globs`, `alwaysApply: false` → description shown to agent, which decides whether to load the full content (two-phase progressive disclosure, similar to skills)
- **Manual**: all fields empty → only loaded via `@rule-name` mention in chat

The legacy `.cursorrules` single file at project root is deprecated but still functional. A newer `RULE.md` folder-based format was documented for v2.2+ but remains non-functional as of v2.3.x per multiple bug reports. Global rules exist only in Cursor Settings UI as plain text — there is no `~/.cursor/rules/` directory. Cursor natively reads from `.agents/skills/` for Agent Skills spec support.

### Windsurf: explicit trigger field

Windsurf uses `.windsurf/rules/*.md` files with standard `.md` extension and an explicit `trigger` field [8]:

```yaml
---
trigger: always_on | model_decision | glob | manual
globs: "**/*.test.ts"        # required when trigger is "glob"
description: "When to use"   # required when trigger is "model_decision"
---
```

**Windsurf's explicit `trigger` field is the key differentiator** — where Cursor infers the mode from field combinations, Windsurf declares it. Character limits are **12,000 per workspace rule file** and **6,000 for global rules** (`~/.codeium/windsurf/memories/global_rules.md`). Discovery spans workspace directories, subdirectories, and parent directories up to git root.

### GitHub Copilot: dual-file system with applyTo globs

Copilot uses two file types [9]. Repository-wide instructions in `.github/copilot-instructions.md` are plain Markdown with no frontmatter, applied to all chat requests. Path-scoped instructions in `.github/instructions/*.instructions.md` use YAML frontmatter:

```yaml
---
applyTo: "**/*.py"
description: "Python coding conventions"
excludeAgent: "code-review"    # optional: exclude from code review or coding agent
---
```

Priority order is confirmed as **personal > repository > organization**, with all levels combined and priority resolving conflicts. Copilot also reads `AGENTS.md` natively since August 2025. The `chat.instructionsFilesLocations` VS Code setting can be configured to scan additional directories including `.claude/rules/`.

### AGENTS.md: the minimal cross-agent standard

AGENTS.md is a **plain Markdown file with no frontmatter, no schema, and no dependencies** — just free-form text with conventional heading structure [10]. Now stewarded by the **Agentic AI Foundation (AAIF)** under the Linux Foundation, with OpenAI, Anthropic, Google, AWS, and others as members. Over **60,000 open-source repos** include AGENTS.md files. Subdirectory scoping is supported — agents walk the directory tree and the closest AGENTS.md to the edited file wins. OpenAI's own Codex repo has 88 AGENTS.md files across subdirectories.

### Gemini CLI and Codex

**Gemini CLI** uses `GEMINI.md` files with the same hierarchical loading as AGENTS.md — global (`~/.gemini/GEMINI.md`), project root, and subdirectories. Supports `@file.md` import syntax. Configurable via `.gemini/settings.json` to read alternative filenames including AGENTS.md [11].

**Codex** uses `AGENTS.md` exclusively as its primary instruction mechanism, with a unique `AGENTS.override.md` file that takes priority at any directory level. Configuration lives in `~/.codex/config.toml` (TOML format). The `project_doc_fallback_filenames` setting allows specifying alternative instruction filenames. There is no `CODEX.md` or `codex.md` file [12].

### Other agents at a glance

| Agent | Config path | Format | Frontmatter | Glob support |
|-------|------------|--------|-------------|-------------|
| **Roo Code** | `.roo/rules/`, `.roo/rules-{mode}/` | Markdown | None required | No |
| **Goose** | `.goosehints` | Plain text/MD + Jinja2 | None | No |
| **Kiro** | `.kiro/steering/*.md` | Markdown | Optional (`title`, `inclusion: always\|manual`) | No |
| **Trae** | `.trae/rules/*.md` | Markdown | Optional (`description`, `globs`, `alwaysApply`, `priority`) | Yes |
| **Augment** | `.augment/rules/*.md` | Markdown | Optional (type: always/manual/auto) | No |
| **Aider** | `.aider.conf.yml` + `CONVENTIONS.md` | YAML config + MD | None | No |
| **Cline** | `.clinerules/` directory | Markdown | Optional (`description`, `globs`) | Yes |
| **Continue** | `.continue/rules/*.md` | Markdown | Optional (`name`, `globs`, `regex`, `alwaysApply`) | Yes |

Roo Code is notable for its **mode-specific rules** (`.roo/rules-code/`, `.roo/rules-architect/`, etc.) — a concept no other agent supports. Kiro uses **spec-driven development** with auto-generated steering files and a unique `inclusion: always|manual` toggle. Trae adds a `priority: 1-4` field unique to its system.

---

## Format comparison matrix

| Feature | SKILL.md (Spec) | Claude Code | Cursor (.mdc) | Windsurf (.md) | Copilot | AGENTS.md | Gemini CLI |
|---------|----------------|-------------|---------------|----------------|---------|-----------|------------|
| **File extension** | `.md` (SKILL.md) | `.md` | `.mdc` | `.md` | `.md` | `.md` | `.md` |
| **Frontmatter** | YAML (6 fields) | YAML (13+ fields) | YAML (3 fields) | YAML (3 fields) | YAML (3 fields) | None | None |
| **Name field** | `name` ✅ | `name` ✅ | — (filename) | — (filename) | `name` (optional) | — | — |
| **Description** | `description` ✅ | `description` ✅ | `description` | `description` | `description` | — | — |
| **Glob scoping** | ❌ | `paths:` (rules only) | `globs` | `globs` | `applyTo` | Subdirectory | Subdirectory |
| **Always-apply** | Via description | Via description | `alwaysApply` | `trigger: always_on` | Default behavior | Default | Default |
| **On-demand loading** | Progressive disclosure | Progressive disclosure | Agent Requested mode | `model_decision` | — | — | — |
| **Allowed tools** | `allowed-tools` | `allowed-tools` | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Resource bundling** | `scripts/`, `references/`, `assets/` | Same + `examples/` | ❌ single file | ❌ single file | ❌ single file | ❌ single file | `@file.md` imports |
| **Directory-based** | ✅ (skill = directory) | ✅ | ❌ (flat files) | ❌ (flat files) | ❌ (flat files) | ❌ (flat file) | ❌ (flat file) |
| **Global location** | `~/.agents/skills/` | `~/.claude/skills/` | Settings UI only | `~/.codeium/windsurf/memories/` | GitHub UI | — | `~/.gemini/GEMINI.md` |
| **Import syntax** | Relative paths | `@path` imports | `@filename` refs | — | Markdown links | — | `@file.md` imports |
| **Hooks/lifecycle** | ❌ | `hooks:` field | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Model override** | ❌ | `model:` field | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## Translation feasibility: what survives, what doesn't

### SKILL.md → other formats

| Target | Lossless fields | Lossy fields | Lost entirely |
|--------|----------------|--------------|---------------|
| **Cursor .mdc** | Body → Markdown content; `description` → `description` | `name` → filename only; progressive disclosure → Agent Requested mode (partial) | `allowed-tools`, `license`, `compatibility`, `metadata`, bundled resources (scripts/refs/assets), hooks, model override, forked context |
| **Windsurf .md** | Body → Markdown content; `description` → `description` | Progressive disclosure → `trigger: model_decision` (partial) | `allowed-tools`, bundled resources, all Claude-specific fields |
| **Copilot .instructions.md** | Body → Markdown content; `description` → `description` | No glob equivalent in SKILL.md (Copilot's `applyTo` has no source data) | `allowed-tools`, bundled resources, progressive disclosure |
| **AGENTS.md** | Body → Markdown content | `name` → heading; `description` → opening paragraph | All frontmatter semantics, bundled resources, scoping |
| **Claude Code (native)** | Everything | — | — |
| **41 Agent Skills adopters** | Everything the agent supports | Agent-specific extensions may not apply | `context: fork`, `hooks` (Claude-only features) |

### Other formats → SKILL.md

| Source | Translates cleanly | Requires enrichment | Cannot represent |
|--------|-------------------|--------------------|-----------------| 
| **Cursor .mdc** | Body → Markdown; `description` → `description`; filename → `name` | `globs` → no native SKILL.md equivalent (store in `metadata`?); `alwaysApply` → no equivalent (use description wording) | Cursor's activation mode inference logic |
| **Windsurf .md** | Body → Markdown; `description` → `description` | `trigger` field → no SKILL.md equivalent; `globs` → store in `metadata` | Windsurf's character limits, auto-memory system |
| **Copilot .instructions.md** | Body → Markdown; `description` → `description` | `applyTo` → store in `metadata`; `excludeAgent` → no equivalent | Copilot's personal/org instruction layers |
| **AGENTS.md** | Full content → SKILL.md body | Need to extract/infer `name` and `description` from headings | Nothing lost (AGENTS.md has less structure) |

The fundamental translation challenge is **scoping semantics**. SKILL.md uses description-based routing (the LLM reads the description and decides when to invoke), while Cursor uses `globs` (file pattern matching), Copilot uses `applyTo` (file pattern matching), and Windsurf uses an explicit `trigger` enum. These are philosophically different approaches: **SKILL.md is agent-decided, while globs are rule-decided**. Translation between them is inherently lossy because the routing mechanism itself differs.

---

## Existing translation tools inventory

### rule-porter: the bidirectional format converter

rule-porter (`npx rule-porter`) is a zero-dependency Node.js CLI that converts bidirectionally between **five formats**: Cursor `.mdc` ↔ CLAUDE.md ↔ AGENTS.md ↔ Copilot ↔ Windsurf, plus legacy `.cursorrules` import [13][14]. It has 242 automated tests and handles edge cases including empty files, broken frontmatter, and non-ASCII content. For lossy conversions, glob patterns are preserved as human-readable Markdown comments with warnings. It does **not** support SKILL.md, Roo Code, Goose, Kiro, Trae, Augment, Cline, or Continue formats.

### Ruler: the single-source distributor

Ruler (`@intellectronica/ruler`) takes a different approach — instead of converting between formats, it maintains a single source of truth in `.ruler/` and **distributes the same content** to 30+ agent-specific locations [15]. Configured via `ruler.toml`, it writes to Claude Code's `CLAUDE.md`, Cursor's `.cursor/rules/`, Copilot's `.github/copilot-instructions.md`, Windsurf's `.windsurfrules`, and many more. It also propagates skills to agents with native skills support. However, it does not translate scoping semantics — it concatenates Markdown and writes it everywhere.

### Vercel skills CLI: symlink-based multi-agent installer

The `skills` CLI (`npx skills`) installs SKILL.md skills to **41 agents** via a canonical `.agents/skills/` directory with symlinks to each agent's skill path [3]. It does **not** translate formats — all 41 agents read SKILL.md natively. Installation creates symlinks (default) or copies (`--copy` flag). The CLI also handles source parsing from GitHub/GitLab URLs, local paths, and git shorthand, plus a lock file for update tracking.

### Other tools

- **cursor-doctor** (`npx cursor-doctor`): Linter for Cursor rules with 100+ checks and 34 auto-fixers. Validates frontmatter, detects vague language, finds contradictions between rules, and grades rule health A-F [16].
- **agentrulegen.com**: Free web-based generator that creates rules from tech stack presets, exporting to Cursor, CLAUDE.md, Copilot, and Windsurf formats. Not a converter — it generates from templates [17].
- **rule-gen** (`npx rulegen-ai`): Generates Cursor rules from source code analysis via Gemini.
- **roomode**: Converts Markdown+Frontmatter to Roo Code's `.roomodes` JSON format.

| Tool | Type | Supports SKILL.md | Agent coverage | Handles scoping | Direction |
|------|------|-------------------|----------------|-----------------|-----------|
| **Vercel skills CLI** | Installer | ✅ (native) | 41 agents | N/A (same format) | One-way (install) |
| **rule-porter** | Converter | ❌ | 5 formats | Lossy (comments) | Bidirectional |
| **Ruler** | Distributor | ✅ (propagates) | 30+ agents | ❌ (same content) | One-to-many |
| **cursor-doctor** | Linter | ❌ | Cursor only | N/A | N/A |
| **agentrulegen** | Generator | ❌ | 4 formats | N/A | Generate only |

---

## Design recommendations for a `skill` package

### Use symlinks for the 41 native adopters, translate for the rest

The Vercel `skills` CLI has proven the symlink approach works at scale. For agents that natively read SKILL.md from their designated skills directory, a `skill` package should copy to `.agents/skills/<name>/` and create symlinks to each agent's path. The full agent-to-path mapping from the `skills` CLI source covers all 41 agents — Claude Code at `.claude/skills/`, Cursor at `.agents/skills/`, Windsurf at `.windsurf/skills/`, Copilot at `.agents/skills/`, Roo Code at `.roo/skills/`, and so on.

**Translation is only needed for three scenarios:**

- **Cursor `.mdc` rules** (`.cursor/rules/`): When a user wants a skill to appear as a native Cursor rule with glob scoping, translate SKILL.md → `.mdc` with `description` mapped to `description`, body mapped to content, and `alwaysApply: false` to trigger Agent Requested mode. Glob patterns cannot be derived from SKILL.md and must be user-supplied or omitted.
- **Copilot `.instructions.md`** (`.github/instructions/`): Map `description` → `description`, body → content, and require user-supplied `applyTo` globs for path scoping.
- **Legacy flat-file agents** (`.windsurfrules`, `.cursorrules`, `.goosehints`, `.clinerules`): Concatenate skill body into the single flat file, prefixed with a `# Skill: {name}` heading and `> {description}` blockquote.

### Preserve round-trip metadata in `metadata` field

For bidirectional translation, store source-format-specific fields in SKILL.md's `metadata` map:

```yaml
metadata:
  cursor.globs: "src/**/*.ts"
  cursor.alwaysApply: "true"
  copilot.applyTo: "**/*.py"
  windsurf.trigger: "glob"
  source_format: "cursor-mdc"
```

This enables lossless round-tripping: when exporting back to Cursor, the `cursor.globs` value can be restored to the `.mdc` frontmatter. Without this, glob scoping information is permanently lost.

### Import strategy for existing rules

Importing Cursor rules as SKILL.md skills is straightforward: filename becomes `name`, `description` maps directly, body maps to body. The `globs` and `alwaysApply` values should be stored in `metadata` for round-trip fidelity. Copilot `.instructions.md` files import similarly, with `applyTo` stored in `metadata`. AGENTS.md files require extracting a `name` (from the first heading or filename) and a `description` (from the first paragraph or user input).

### The translation hierarchy should be explicit

A `skill` package should expose three installation strategies per agent:

- **Native** (symlink/copy): For the 41 Agent Skills adopters. No translation. Maximum fidelity.
- **Translated** (format conversion): For Cursor rules, Copilot instructions, Windsurf rules. Lossy but functional. Warnings emitted for lost fields.
- **Injected** (flat-file append): For legacy single-file formats. Most lossy. Skill content concatenated into the target file.

This three-tier approach matches what the ecosystem already does — the Vercel CLI handles native, rule-porter handles translated, and Ruler handles injected — but unifies them under a single package with consistent metadata preservation.

---

## Conclusion

The AI coding agent instruction landscape has consolidated faster than expected. **The Agent Skills specification covers 41 agents natively**, making symlink-based installation the dominant strategy. The remaining translation problem is narrow: only Cursor's `.mdc` rules, Copilot's `.instructions.md` files, and a handful of legacy single-file formats require actual format conversion. The critical insight for a `skill` package is that **scoping semantics are the hardest translation problem** — SKILL.md's description-based routing is fundamentally different from glob-based file matching, and no automated translation can bridge that gap without user-supplied metadata. The recommended approach is to store source-specific scoping data in SKILL.md's `metadata` field, enabling round-trip fidelity while keeping the canonical format clean. With Ruler handling distribution, rule-porter handling conversion, and the Vercel CLI handling installation, the tooling ecosystem is maturing — but a unified `skill` package that combines all three strategies with consistent metadata preservation would fill the remaining gap.

---

## References

[1] [Agent Skills Specification](https://agentskills.io) — Official specification website

[2] [Agent Skills GitHub Repository](https://github.com/agentskills/agentskills) — Spec source, reference SDK, Apache 2.0 + CC-BY-4.0

[3] [Vercel Skills CLI](https://github.com/vercel-labs/skills) — CLI source code, 41 agent definitions, symlink installer

[4] [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills) — Official Anthropic docs

[5] [Claude Code Skills Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) — Anthropic platform docs

[6] [Inside Claude Code Skills](https://mikhail.io/2025/10/claude-code-skills/) — Reverse-engineered internals of the Skill tool

[7] [Cursor Rules Documentation](https://docs.cursor.com) — Official Cursor docs on rules and MDC format

[8] [Windsurf Rules Documentation](https://docs.windsurf.com/windsurf/cascade/memories) — Official Windsurf/Codeium docs

[9] [GitHub Copilot Custom Instructions](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot) — Official GitHub docs

[10] [AGENTS.md Official Website](https://agents.md/) — Cross-agent standard, AAIF governance

[11] [Gemini CLI Documentation](https://google-gemini.github.io/gemini-cli/docs/cli/gemini-md.html) — GEMINI.md format and configuration

[12] [OpenAI Codex AGENTS.md Guide](https://developers.openai.com/codex/guides/agents-md) — Codex instruction system

[13] [rule-porter GitHub](https://github.com/nedcodes/rule-porter) — Bidirectional format converter

[14] [rule-porter Blog Post](https://dev.to/nedcodes/rule-porter-convert-cursor-rules-to-claudemd-agentsmd-and-copilot-4hjc) — Conversion approach and examples

[15] [Ruler GitHub](https://github.com/intellectronica/ruler) — Single-source rule distributor for 30+ agents

[16] [cursor-doctor GitHub](https://github.com/nedcodes-ok/cursor-doctor) — Cursor rule linter with 100+ checks

[17] [agentrulegen.com](https://www.agentrulegen.com) — Web-based AI coding rules generator

[18] [Claude Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/) — Progressive disclosure analysis

[19] [Cursor Rules vs CLAUDE.md vs Copilot Comparison](https://www.agentrulegen.com/guides/cursorrules-vs-claude-md) — Format comparison guide

[20] [Gemini CLI GitHub Repository](https://github.com/google-gemini/gemini-cli) — Source code and configuration reference