# The AI agent skills ecosystem: a complete landscape survey

**The agent skills ecosystem is experiencing its "npm moment"** — at least 30 tools now compete to manage, distribute, create, or convert the instruction packages that guide AI coding agents. The Vercel Skills CLI dominates installation (10.6K GitHub stars, 594K installs for its top skill), built atop the open Agent Skills specification maintained by Anthropic and adopted by **26+ platforms** including Claude Code, OpenAI Codex, GitHub Copilot, Gemini CLI, and Cursor. Yet critical gaps remain: no versioning or dependency resolution, no security review process, no standardized testing framework, and deep fragmentation across competing tools. For a Python `skill` package, the opportunity is clear — become the programmatic backbone that the ecosystem's CLI-centric, Node.js-dominated tools lack.

---

## 1. Landscape map: every tool in the ecosystem

### Skill installation and management

| Tool | What it does | Language | Adoption |
|------|-------------|----------|----------|
| **Vercel `skills` CLI** | Package manager for Agent Skills across 40+ agents; symlink-based central store | TypeScript | 10.6K stars, 594K top-skill installs |
| **skild.sh** | Alternative skills CLI ("the npm for Agent Skills") | — | Early stage |
| **skillpm** | Maps Agent Skills onto npm's actual registry with dependency resolution | JS | ~630 LOC, experimental |
| **skills-npm** (antfu) | Ships skills inside npm packages; symlinks on `npm install` | JS | Experimental |
| **OpenSkills** | Universal skills loader with Claude Code–compatible prompt format | JS | Early stage |
| **Ruler** | Centralized rule management; `.ruler/` → distributes to 30+ agents | — | Active development |
| **PRPM** | Universal prompt package manager with cross-format conversion engine | JS | Early stage |
| **prmp** | CLI to manage Cursor rules and Claude sub-agent files from URLs | JS | promptpm.dev |
| **localskills.sh** | SaaS platform for team skill sharing with SSO/SCIM, SHA-256 versioning | Web | Commercial |
| **skillshare** (runkids) | CLI to sync skills across all AI CLI tools from `~/.config/skillshare/` | — | Early stage |
| **agent-skills-nix** | Declarative skill management via Nix flakes + home-manager | Nix | Niche |

### Skill creation and authoring

| Tool | What it does | Language | Adoption |
|------|-------------|----------|----------|
| **Anthropic skill-creator** | Meta-skill that creates other skills via define→draft→test→evaluate→refine loop | Python/MD | Official, in anthropics/skills (69K+ stars) |
| **Skill Seekers** | Converts docs, GitHub repos, PDFs, videos into structured skills for 16 targets | Python | ~800 stars |
| **agentrulegen.com** | Web UI generating agent rules from 10K+ community-contributed rules for 8 agents | Next.js | Free web service |
| **awesome-claude-skills** | Curated list of Claude skills with quality gates | Markdown | 3.6K–7.5K stars |

### Format conversion and linting

| Tool | What it does | Language | Adoption |
|------|-------------|----------|----------|
| **rule-porter** | Bidirectional converter: Cursor .mdc ↔ CLAUDE.md, AGENTS.md, Copilot, Windsurf | JS (zero-dep) | Low stars, active npm |
| **cursor-doctor** | Linter/diagnostic for Cursor rules: 100+ checks, conflict detection, auto-fix | JS (zero-dep) | 4,791 npm downloads |
| **Ultracite** | Zero-config linter preset that generates synchronized rule files for 20+ agents | Rust | Active |

### Broader agent tool ecosystem

| Tool | What it does | Language | Relationship |
|------|-------------|----------|-------------|
| **FastMCP** | Standard Python MCP server framework; 70% of MCP servers across all languages | Python | Complementary — tools vs. instructions |
| **Smithery.ai** | MCP server + skills registry with CLI (`smithery skill search/add`) | TypeScript | Integrate — has skill registry concept |
| **mcp.run** | Hosted MCP servers via WebAssembly with profile-based tool bundles | Multi | Complement — execution layer |
| **LangSmith / LangChain Hub** | Prompt versioning, playground, evaluation with commit-hash versioning | Python/TS | Learn from — best versioning model |
| **Composio** | 1,000+ pre-built tool integrations with managed auth for AI agents | Python/TS | Integrate — tool layer below skills |
| **promptfoo** | Test-driven prompt evaluation, red teaming, security scanning (acquired by OpenAI) | TypeScript | Integrate — testing layer for skills |
| **ell** | Prompt engineering library treating prompts as versioned Python functions | Python | Learn from — best prompts-as-code design |

### Registries and directories

| Registry | Model | Scale |
|----------|-------|-------|
| **skills.sh** (Vercel) | Install-telemetry-populated leaderboard | 500K+ tracked installs |
| **SkillsMP** (skillsmp.com) | GitHub scraper, min 2 stars filter | Claims 500K+ skills |
| **SkillHub** (skillhub.club) | AI-evaluated skills with playground | 7,000+ skills |
| **Smithery.ai** | Curated MCP + skills registry | Growing |
| **agentskills.so** | Skill directory/browser | Browse by repo |
| **cursor.directory** | Community Cursor rules | Active |

### PyPI packages for skill management

| Package | Focus |
|---------|-------|
| `skills-cli` | CLI with validate, zip, push-to-Anthropic, to-prompt conversion |
| `agent-skills-sdk` | Production Agent Skills spec implementation with framework integrations |
| `open-skills` | Framework-agnostic skills subsystem for Python agents |
| `agent-skill` | TUI + MCP server for skill management |
| `pydantic-ai-skills` | Lightweight skills for Pydantic AI |
| `adk-skills-agent` | Google ADK agent skills loader |
| `skillnet-ai` | SkillNet SDK with search, install, create, evaluate |
| `clawhub` | Agent skill registry with Python API |
| `aider-skills` | Agent Skills integration for aider |
| `agent-skills` | Skills as Python files composing MCP tools |

---

## 2. The Vercel Skills CLI sets the standard

The most important tool in this ecosystem is the Vercel `skills` CLI, which functions as the de facto package manager for the Agent Skills specification. Released January 20, 2026, it has achieved **10.6K GitHub stars** and supports **40 agents** through a sophisticated agent detection system defined in ~540 lines of TypeScript.

The architecture follows a canonical-store-plus-symlinks pattern. When a developer runs `npx skills add owner/repo`, the CLI clones the GitHub repository, discovers SKILL.md files via a three-tier search strategy (direct path → priority directories like `skills/` → recursive fallback), and copies skill files to `.agents/skills/<name>/`. It then creates symlinks from each detected agent's directory (`.claude/skills/`, `.cursor/skills/`, `.github/skills/`) pointing to the canonical location. **Universal agents** like Codex and OpenCode read directly from `.agents/skills/` without symlinks.

The skill format itself is deliberately minimal. A SKILL.md file requires only two frontmatter fields — `name` (lowercase alphanumeric with hyphens, 1–64 characters) and `description` (1–1,024 characters) — plus a markdown body. Optional fields include `license`, `compatibility`, `metadata` (arbitrary key-value pairs), and experimental fields like `allowed-tools`. The specification enforces progressive disclosure: **~100 tokens** for metadata scanning at startup, **<5,000 tokens** for full instructions on activation, and resources (scripts, references, assets) loaded on demand. This three-tier loading is critical for context window management.

The skills.sh directory uses a novel passive-registration model. **No submission flow exists** — install telemetry automatically surfaces packages. This eliminates gatekeeping but means new skills remain invisible until someone installs them. The leaderboard ranks by total installs, with Vercel's own packages dominating (react-best-practices at 220K, web-design-guidelines at 175K).

Key weaknesses define the opportunity space for a Python package. The CLI provides **no semantic versioning** — skills pull from HEAD of the default branch, with only git tree SHAs for change detection. There is **no dependency management** between skills, **no security review** beyond manual inspection (skills with `scripts/` can execute arbitrary code), **no conflict resolution** when skills share names, and **no private registry support** for enterprise teams. The lock file (`skills-lock.json`) tracks installed skills but cannot pin to specific versions or tags.

---

## 3. Anthropic's skill-creator defines the quality bar

The official Anthropic skills repository (69K+ stars) contains **17 skills** spanning creative, technical, and enterprise categories. The crown jewel is the **skill-creator** — a meta-skill that creates other skills through a rigorous iterative cycle.

The development loop works as follows. In the **define** phase, the skill-creator extracts intent from conversation, probing edge cases, I/O formats, and success criteria. During **draft**, it writes SKILL.md with "pushy" descriptions — the documentation explicitly notes that Claude tends to "undertrigger" skills, so descriptions should aggressively enumerate triggering scenarios. The **test** phase spawns parallel subagents: one with the skill loaded, one without (baseline), generating structured output in `<skill-name>-workspace/iteration-<N>/eval-<ID>/`. **Evaluation** uses three specialized subagents:

- **Grader**: evaluates assertions as PASS/FAIL with cited evidence; critically, it also critiques the evaluation criteria themselves, flagging weak assertions that create false confidence
- **Comparator**: performs blind A/B comparison without revealing which version is which
- **Analyzer**: determines why the winner won, feeding insights back into refinement

The evaluation framework includes Python scripts for the full lifecycle: `run_eval.py` runs test suites, `generate_review.py` creates interactive HTML reports, `improve_description.py` tests description triggering accuracy against 20 eval queries, and `package_skill.py` creates distributable `.skill` files. The system adapts across environments — Claude Code gets full parallel testing, Claude.ai runs sequentially (no subagents), and Cowork falls between.

Two design principles stand out as lessons. First, **description optimization is its own discipline** — the skill-creator dedicates an entire script to testing whether descriptions correctly trigger skill activation. Second, the **grader's self-critique** ("a passing grade on a weak assertion is worse than useless") establishes an evaluation philosophy that any skill testing framework should adopt.

---

## 4. Format conversion tools reveal the fragmentation problem

The ecosystem suffers from a format fragmentation problem that several tools attempt to solve. **Cursor's .mdc format** is the only one with real structure (YAML frontmatter with `globs` and `alwaysApply` fields). Every other format — CLAUDE.md, AGENTS.md, `.github/copilot-instructions.md`, `.windsurfrules` — is essentially flat markdown, creating lossy conversions.

**rule-porter** handles this honestly. Its three-layer architecture (parser → splitter → format writers) uses an intermediate representation with five fields: name, description, globs, alwaysApply, and body. When converting Cursor .mdc to CLAUDE.md, glob patterns become markdown comments (information preserved but not machine-readable), and alwaysApply flags map to structural placement. The tool's "no silent data loss" policy — explicitly warning about every non-1:1 conversion — is a UX pattern worth adopting. Built with **zero dependencies** and 242 tests, it demonstrates that focused tools can be highly reliable.

**cursor-doctor** addresses the quality problem. Its diagnostic engine runs **100+ lint rules** across six categories (syntax, conflicts, token budget, globs, prompt quality, structure) and detects **48 semantic conflict patterns** by extracting directives ("use X," "prefer X," "never X") and cross-comparing across files. A study of 50 public repos found **60% scored C or lower** on its health grading system, confirming that broken and conflicting rules are endemic. The tool ships as a CLI, VS Code extension, MCP server, and GitHub Action — comprehensive delivery surface for a validation tool.

**PRPM** (Prompt Package Manager) takes the most ambitious approach, implementing a full cross-format conversion engine that parses each format into a canonical intermediate representation and converts to any target. Its install syntax — `npx prpm install @anthropic/typescript-best-practices --as cursor` — makes format a parameter rather than a constraint. **Ruler** solves the same problem differently: store rules once in `.ruler/`, run `ruler apply`, and it distributes to 30+ agent config files simultaneously.

---

## 5. MCP and skills occupy complementary layers

A persistent question in this ecosystem is where MCP servers end and skills begin. The boundary is clean in principle but blurring in practice.

**Skills control how agents think.** They are instruction packages — markdown documents with behavioral guidance, decision-making patterns, and domain expertise. They consume ~100 tokens at rest and <5,000 tokens when active. **MCP servers control what agents can do.** They expose tools, resources, and data access via JSON-RPC, with auto-generated schemas from type hints.

**FastMCP** dominates the MCP implementation space, powering **70% of MCP servers across all languages** and downloaded over a million times a day. Version 3.0 introduced a "Skills" provider type, signaling convergence. **Smithery.ai** has already merged both concepts, offering a CLI with both `smithery mcp search/add` and `smithery skill search/add` commands — the only platform combining a tool registry with a skill registry.

The convergence point is MCP's **Prompts** primitive — reusable templates for LLM interactions that are essentially lightweight skills attached to a server. A Python skill management package should treat MCP integration as a first-class concern: skills reference MCP tools in their instructions, and MCP servers can expose skills through the Prompts primitive. **Composio** (1,000+ tool integrations with managed auth) sits at the tool layer beneath skills — skills tell agents when and how to use Composio's integrations.

---

## 6. Prompt versioning insights from LangSmith and ell

Two tools offer the strongest versioning models to learn from. **LangSmith** uses commit-hash versioning where every push creates a unique hash, with human-readable tags ("dev," "staging," "prod") pointing to specific commits. Its API (`push_prompt()`, `pull_prompt()`) supports full lifecycle management, and its playground enables side-by-side model comparison with token/cost tracking. The tracing integration — recording which prompt version produced each execution — is particularly powerful for debugging skill regressions.

**ell** takes a more radical approach, treating prompts as Python functions decorated with `@ell.simple()` or `@ell.complex()`. Versioning is automatic: on first invocation, ell computes the lexical closure of the function's source plus all dependencies, hashes it, and creates a version. No manual commits. The Ell Studio provides local visualization with version diffs, I/O traces, and dependency graphs. With **5.8K GitHub stars**, ell proves that the "prompts as code" paradigm resonates.

For a Python `skill` package, the optimal versioning strategy borrows from both: **semantic versioning for published skills** (like npm packages) combined with **automatic hash-based change detection** (like ell) for local development, with **commit-hash based immutable versions** (like LangSmith) for the registry.

---

## 7. The PyPI ecosystem is surprisingly active but fragmented

At least **10 distinct Python packages** target agent skill management on PyPI, but none has achieved dominance. `agent-skills-sdk` offers the most complete Agent Skills spec implementation with framework integrations (Agno, LangChain, CrewAI) and progressive disclosure achieving **84–95% token savings**. `skills-cli` provides the closest Python equivalent to the Vercel CLI with validate, zip, push-to-Anthropic, and format conversion commands. `open-skills` takes a framework-agnostic approach supporting OpenAI, Anthropic, LangChain, and LlamaIndex.

The fragmentation itself is the signal. No Python package has yet assembled the complete skill lifecycle — **creation** (like Anthropic's skill-creator), **validation** (like cursor-doctor), **format conversion** (like rule-porter), **distribution** (like the Vercel CLI), **versioning** (like LangSmith), and **testing** (like promptfoo) — into a single coherent tool. This is the gap a well-designed `skill` package should fill.

Distribution models split into three camps. The **npm/GitHub model** (Vercel's approach) uses git repos as the unit of distribution with telemetry-based discovery. Anthony Fu's `skills-npm` variant proposes shipping skills inside npm packages so they arrive automatically with `npm install`. The **PyPI model** offers familiar tooling and dependency resolution but adds overhead for what are essentially markdown files. The **dotfiles model** — managing CLAUDE.md and .cursorrules via GNU Stow, chezmoi, or Nix flakes — is organically popular and represents how power users actually sync configs today, often with selective encryption via chezmoi + age for sensitive API keys in commands.

---

## 8. Feature gap analysis: what the ecosystem still lacks

Five critical gaps emerge from this survey.

**Versioning and pinning.** The Vercel CLI tracks git tree SHAs but cannot pin to a specific tag, branch, or semantic version. Skills pull from HEAD, making reproducible builds impossible. No tool provides `package-lock.json`-style deterministic resolution for skills.

**Security and trust.** Skills with `scripts/` directories execute arbitrary code. No tool implements signing, sandboxing, vulnerability scanning, or supply-chain verification. The Vercel FAQ warns users to "treat them like any other code you run." Promptfoo's red-teaming capabilities could address prompt injection risks but no integration exists. **This is the most dangerous gap** as skill adoption scales.

**Dependency management.** Skills cannot declare dependencies on other skills. No transitive resolution, no conflict detection at the dependency level, no shared-dependency deduplication. This limits skill composability.

**Testing integration.** Anthropic's skill-creator has a sophisticated evaluation framework, but it is embedded in a skill, not a standalone library. No tool provides `skill test my-skill` out of the box with configurable evaluation backends. The promptfoo integration pathway (auto-generating YAML test configs from skill metadata) is obvious but unbuilt.

**Private registries.** Enterprise teams need internal skill registries with access control. localskills.sh offers SSO/SCIM but is a SaaS dependency. No self-hosted, open-source private registry exists.

---

## 9. Recommendations for the Python `skill` package

### Wrap or facade these tools (don't rebuild)

- **Vercel Skills CLI** — call `npx skills add/remove/list` via subprocess for installation; don't reimplement the 40-agent detection logic
- **promptfoo** — generate test configs and delegate evaluation; it has 10M+ users and is battle-tested
- **rule-porter** — wrap via subprocess for format conversion; its 242-test parser is robust
- **cursor-doctor** — call for validation of Cursor-format outputs; consider porting its lint rules to Python for native integration

### Build from scratch (no adequate tool exists)

- **Skill versioning engine** — semantic versioning + hash-based change detection + lock file with deterministic resolution
- **Dependency resolver** — skills declaring dependencies on other skills with transitive resolution
- **Python-native SKILL.md parser/validator** — the reference implementation is TypeScript; a Python equivalent with Pydantic models is the foundation
- **Description optimizer** — programmatic testing of whether descriptions correctly trigger skill activation (inspired by Anthropic's `improve_description.py`)
- **Private registry server** — lightweight HTTP server compatible with the skills.sh API surface

### Integrate with (complementary tools)

- **FastMCP** — expose skill management as MCP tools (`load_skill`, `validate_skill`, `search_skills`)
- **Smithery.ai** — publish skills to and pull from Smithery's skill registry
- **LangSmith** — import/export prompt versions; adopt their commit-hash + tags versioning model
- **ell** — study its automatic versioning via source analysis for development-mode skill tracking

### Ignore (low value or wrong layer)

- **agentrulegen.com** — closed-source web-only; no integration path
- **mcp.run** — WebAssembly execution layer; orthogonal to skill management
- **Composio** — tool integrations layer; skills reference Composio tools but don't manage them

---

## 10. Design ideas borrowed from the ecosystem

**Progressive disclosure from the Agent Skills spec.** Implement three-tier loading: metadata dict (~100 tokens) → full instructions (<5K tokens) → resources on demand. This is the single most important architectural pattern.

**Intermediate representation from rule-porter.** Define a canonical `Skill` dataclass with `name`, `description`, `globs`, `triggers`, `body`, and `metadata`. All format conversions route through this IR. Pydantic models are the natural Python implementation.

**Health grading from cursor-doctor.** Every skill gets a quality score (A–F) based on automated checks: frontmatter completeness, description quality (flag vague phrases like "try to" or "consider"), instruction length, script security, and cross-skill conflict detection.

**Evaluation framework from Anthropic's skill-creator.** Expose grader, comparator, and analyzer as composable Python functions. The key insight: always test with-skill vs. without-skill (baseline), and always critique the evaluation criteria themselves.

**Telemetry-based discovery from skills.sh.** Install events passively populate a registry. No submission flow. This eliminates gatekeeping friction while still enabling discovery.

**Dotfiles-native from the community.** Support `chezmoi` and `stow` workflows natively. Provide `skill export --dotfiles` that outputs a structure ready for GNU Stow symlinking. Support selective encryption markers for skills containing sensitive configuration.

**Lock files from Vercel + npm patterns.** Two files: `skill-lock.json` (committed, team-reproducible) and `.skill-lock.json` (global, machine-specific). Track source URL, commit SHA, installed version, target agents, and content hash.

---

## Conclusion

The agent skills ecosystem has coalesced around the SKILL.md format as an open standard with remarkable speed — from Anthropic's December 2025 specification to adoption by 26+ platforms in under four months. The Vercel Skills CLI dominates distribution, Anthropic's skill-creator sets the quality bar for authoring, and a constellation of conversion tools (rule-porter, PRPM, Ruler) address format fragmentation. Yet the ecosystem remains strikingly immature in versioning, security, dependency management, and testing — the exact capabilities that a well-designed Python package manager provides.

The strategic position for a Python `skill` package is not to compete with the Vercel CLI on installation breadth (40 agents is hard to replicate) but to own the **programmatic layer**: Pydantic-modeled skill objects, a versioning engine with deterministic resolution, a validation pipeline porting cursor-doctor's 100+ lint rules, integration with promptfoo for evaluation, and a registry protocol supporting both public (skills.sh–compatible) and private (enterprise) deployment. The tools to wrap exist; the tools to build are clearly defined; the gap is wide open.