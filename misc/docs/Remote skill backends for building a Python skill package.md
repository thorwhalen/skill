# Remote skill backends for building a Python `skill` package

**GitHub is the only backend you truly need for v1, but three adjacent registries offer high-value expansion paths.** The Agent Skills ecosystem lacks a centralized API-driven registry — skills.sh is telemetry-driven and browse-only, Agensi.io has no public API, and agentskills.io is purely a spec site. This means a Python `skill` package must treat GitHub as its primary backend (using the Contents, Trees, and Search APIs), with Smithery, Composio, and community-curated lists as secondary sources requiring format translation. Of the 11+ backends investigated, only **four** offer viable programmatic access to skill-like content in a format close enough to SKILL.md to justify integration effort.

The Agent Skills specification — published by Anthropic in December 2025 at agentskills.io — defines skills as folders containing a SKILL.md file (YAML frontmatter with `name` and `description`, plus a Markdown body of instructions), with optional `scripts/`, `references/`, and `assets/` subdirectories. The Vercel `skills` CLI (`npx skills add`) is the de facto package manager, adopted across **37+ agent platforms** including Claude Code, Codex CLI, Cursor, GitHub Copilot, and Gemini CLI. The canonical key format is `owner/repo/skill-name`, and skills are distributed as git repositories.

## Summary of all backends investigated

| Backend | URL | API | Auth | Native SKILL.md | Free | Status |
|---------|-----|-----|------|-----------------|------|--------|
| **GitHub** (Contents/Trees/Search) | api.github.com | REST ✅ | Token (optional for public) | ✅ Yes | Free tier | **Implemented** |
| **Smithery** | api.smithery.ai | REST ✅ | None for read, Bearer for write | ❌ MCP tools / skills | Free | **Implemented** |
| **Composio** | backend.composio.dev | REST + Python SDK ✅ | API key (`COMPOSIO_API_KEY`) | ❌ Tool definitions | 20K calls/mo free | **Implemented** |
| **awesome-claude-skills** | github.com/travisvn/awesome-claude-skills | Parseable README | None | ✅ Links to SKILL.md repos | Free | **Implemented** |
| **SkillsDirectory** | skillsdirectory.com | REST ✅ | API key (`SKILLSDIRECTORY_API_KEY`) | Mixed (some have content) | 100 req/day free | **Implemented** |
| skills.sh | skills.sh | ❌ None | None | ✅ (browse only) | Free | No — no API |
| Vercel skills CLI | github.com/vercel-labs/skills | CLI only | None | ✅ Yes | Free | Wrap via subprocess |
| Agensi.io | agensi.io | ❌ None | Account for purchases | ✅ Yes | Free + paid ($3–$30) | No — no API |
| agentskills.io | agentskills.io | ❌ None | None | N/A (spec only) | Free | No — not a registry |
| Anthropic skills repo | github.com/anthropics/skills | Via GitHub API | GitHub token | ✅ Yes | Free | Via GitHub backend |
| LangChain Hub | smith.langchain.com/hub | REST + SDK ✅ | API key | ❌ Prompt templates | Free tier | Low priority |
| PromptBase | promptbase.com | Limited | Account | ❌ Text prompts | Paid ($2.99+) | No |
| OpenRouter | openrouter.ai | REST ✅ | API key | ❌ Model metadata | Credits-based | No — not a skill registry |
| Official MCP Registry | registry.modelcontextprotocol.io | REST (preview) | TBD | ❌ MCP metadata | Free | Future — still in preview |
| skillsmp.com | skillsmp.com | ❌ 403 Cloudflare | Unknown | Unknown | Unknown | **Not viable** — blocked by Cloudflare |
| claudeskills.info | claudeskills.info | ❌ None | None | N/A (content site) | Free to browse | **Not viable** — no API |
| mcpmarket.com | mcpmarket.com | ❌ 403 Vercel | Unknown | Unknown | Unknown | **Not viable** — blocked |
| platform.claude.com tool-search | platform.claude.com | Docs only | Anthropic API key | N/A | N/A | **Not a registry** — docs about tool search feature |

## GitHub is the canonical skill backend

Since skills are distributed as git repos with no centralized registry, **GitHub's API suite is the primary programmatic interface** for discovering, listing, and fetching skills. The `skill` package needs three API layers.

**Discovery via Code Search API.** The endpoint `GET /search/code?q=filename:SKILL.md` finds SKILL.md files across all public repos. Authentication is required. The response returns up to **100 results per page** with repository metadata, file paths, and SHA hashes. Critical constraint: the Search API uses the legacy search engine, caps at **4,000 repositories scanned**, and enforces **10 requests per minute** for code search. Additional qualifiers like `user:anthropics` or `org:vercel-labs` narrow results effectively.

**Listing via Contents and Trees APIs.** To enumerate skills within a known repo, `GET /repos/{owner}/{repo}/contents/skills` returns a JSON array of directory entries. For repos with complex nesting, the Git Trees API (`GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1`) returns the full file tree in one call — filter for paths matching `*/SKILL.md` to find all skills. The Trees API handles up to **100,000 entries** per response.

**Fetching via raw content URLs.** For reading actual SKILL.md content, `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}/SKILL.md` returns raw markdown with no authentication required for public repos and no rate limiting. Alternatively, the Contents API with `Accept: application/vnd.github.raw+json` returns raw content directly (no base64 decoding needed). Standard rate limits apply: **60 requests/hour unauthenticated, 5,000/hour with a token**. Conditional requests via ETags return 304s that don't count against limits.

```
Backend: GitHub
URL: https://api.github.com
Auth: none (60 req/hr) | token (5,000 req/hr) | GitHub App (15,000 req/hr)
Search endpoint: GET /search/code?q=filename:SKILL.md
Search params: q (required), sort, order, per_page (max 100), page
Fetch endpoint: GET /repos/{owner}/{repo}/contents/{path}
Raw URL: https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}
Key format: "owner/repo/skill-name" (three-part hierarchy)
Skill format: Native SKILL.md
Rate limits: Code search 10/min; Core 5,000/hr (authenticated)
Python client: PyGithub, ghapi, or raw requests/httpx
Notes: Trees API is most efficient for full-repo skill enumeration
```

## The Vercel skills CLI reveals key architectural patterns

The open-source `skills` CLI (7.5K stars, MIT licensed, v1.4.3) is the de facto package manager. Its source code at `vercel-labs/skills` reveals the internal skill discovery logic that a Python package should replicate. The CLI searches **35+ paths** within any repo: root SKILL.md, `skills/`, `skills/.curated/`, `skills/.experimental/`, agent-specific paths (`.claude/skills/`, `.cursor/skills/`, `.agents/skills/`), and falls back to recursive search if nothing is found.

Resolution follows a clear pipeline: GitHub shorthand `owner/repo` maps to `https://github.com/owner/repo`, the repo is cloned or fetched, SKILL.md files are discovered in standard locations, YAML frontmatter is parsed for `name` and `description`, and the user selects which skills to install. The CLI communicates with a backend at `add-skill.vercel.sh` for two purposes only: **anonymous install telemetry** (`POST /t`) which feeds the skills.sh leaderboard, and **update checking** (`POST /check-updates`) using `skillFolderHash` (GitHub tree SHA) for cache invalidation.

For the Python `skill` package, the CLI can be wrapped via `subprocess.run(['npx', 'skills', 'add', source, '--yes', '--list'])` for quick integration, but reimplementing the discovery logic in Python is straightforward — it's essentially a directory walker that searches known paths for SKILL.md files and parses YAML frontmatter.

```
Backend: Vercel skills CLI (wrapper)
URL: N/A (local CLI)
Auth: none
Search: npx skills find <query>
List: npx skills add <source> --list
Key format: "owner/repo" (resolves to individual skills within)
Skill format: Native SKILL.md
Rate limits: Inherits GitHub rate limits
Python client: subprocess wrapper or reimplement discovery logic
Notes: --yes flag for non-interactive mode; supports GitHub, GitLab, local paths
```

## skills.sh is a leaderboard, not a registry

Despite being the most visible discovery surface, **skills.sh has no public API**. It is a server-rendered Next.js application that displays a leaderboard ranked by install count, fed entirely by anonymous telemetry from the `skills` CLI. Skills appear automatically when installed via `npx skills add` — there is no submission flow. The site supports tabs (All Time, Trending 24h, Hot), owner pages (`skills.sh/{owner}`), and repo pages (`skills.sh/{owner}/{repo}/{skill-name}`), but all data is rendered server-side with no JSON endpoints.

Top skills by install count include `find-skills` (580.7K installs), `vercel-react-best-practices` (217K), `frontend-design` (164.5K), and `azure-ai` (137.7K). The owner page for `vercel-labs` alone shows **29 sources, 182 skills, 1.3M total installs**. To consume this data programmatically, the only option is HTML scraping — making it unsuitable as a primary backend but potentially useful for popularity metadata.

## Anthropic's repo and community lists provide curated starting points

The `anthropics/skills` repo contains **17 official skills** organized in a flat `skills/` directory: `algorithmic-art`, `brand-guidelines`, `canvas-design`, `claude-api`, `doc-coauthoring`, `docx`, `frontend-design`, `internal-comms`, `mcp-builder`, `pdf`, `pptx`, `skill-creator`, `slack-gif-creator`, `theme-factory`, `web-artifacts-builder`, `webapp-testing`, and `xlsx`. The `skill-creator` meta-skill includes a sophisticated evaluation framework (`scripts/run_loop`) that splits test sets 60/40, runs queries 3× for reliability, iterates up to 5 times, and selects the best skill description by held-out test score.

The `awesome-claude-skills` list (7.5K stars, CC0 licensed) provides a parseable index of community skills in standard markdown link format. A regex like `\[([^\]]+)\]\((https://github\.com/[^\)]+)\)` extracts repo URLs reliably. Several parallel lists exist: `hesreallyhim/awesome-claude-code` (8.9K stars), `VoltAgent/awesome-claude-code-subagents` (83.2K stars), and the emerging **SkillsMP** (skillsmp.com) which claims **500,000+ indexed skills** via GitHub scraping.

## Smithery and Composio are the strongest adjacent backends

**Smithery** (registry.smithery.ai) offers a well-documented REST API for MCP server discovery. The `GET /servers` endpoint supports semantic search (`q` param), owner/repo filtering, and pagination. The detail endpoint `GET /servers/{qualifiedName}` returns a **`tools` array** where each tool has `name`, `description`, and `inputSchema` (JSON Schema) — fields that map almost directly to SKILL.md structure. Authentication requires a Bearer token from smithery.ai/account/api-keys. The key format is `owner/repository`, matching the skills ecosystem's conventions.

```
Backend: Smithery
URL: https://api.smithery.ai
Auth: None for read (GET /servers, GET /skills); Bearer token for write
Skills endpoint: GET /skills?q=<query>&pageSize=10&page=1
Servers endpoint: GET /servers?q=<query>&pageSize=10&page=1
Detail endpoint: GET /skills/{qualifiedName}
Key format: "owner/skill-name" (qualifiedName)
Skill format: Mixed — some link to GitHub SKILL.md repos, others are metadata-only
Response: JSON with skills[], pagination; includes gitUrl, categories, qualityScore
Python client: raw urllib (REST API is straightforward)
Notes: Has both /skills (agent skills) and /servers (MCP servers) endpoints.
       Skills often have gitUrl pointing to GitHub repos with SKILL.md.
       Implementation: skill.backends.smithery.SmitherySkillSource
```

**Composio** provides the broadest tool catalog: **11,000+ tools across 850+ toolkits** covering GitHub, Slack, Gmail, Notion, Jira, and hundreds more services. The REST API at `backend.composio.dev/api/v3` has full OpenAPI documentation. The Python SDK (`composio-core`) offers direct access: `composio.tools.get(toolkits=["GITHUB"])`. Tool definitions include structured input schemas that translate cleanly to SKILL.md. The free tier provides **20,000 calls/month**. The main complexity is authentication — many tools require per-user OAuth flows managed by Composio's connection system.

```
Backend: Composio
URL: https://backend.composio.dev/api/v3
Auth: x-api-key header (COMPOSIO_API_KEY env var)
Search endpoint: GET /api/v3/tools?query=<query>&limit=10
Detail endpoint: GET /api/v3/tools/{tool_slug}
Key format: "toolkit_slug/TOOL_SLUG" (e.g., github/GITHUB_CREATE_ISSUE)
Skill format: Tool definitions → translated to SKILL.md with parameters documented
Response: JSON with items[], total_items; includes input_parameters, output_parameters
Rate limits: 20K–100K requests/10min (plan-dependent)
Python client: composio (pip install composio) or raw urllib
Notes: 11K+ tools across 850+ toolkits. Cursor-based pagination.
       Sign up at platform.composio.dev for API key.
       Implementation: skill.backends.composio.ComposioSkillSource
```

**SkillsDirectory** (skillsdirectory.com) provides a curated directory of 36,000+ skills with a REST API. Free tier allows 100 requests/day. Some skills include full SKILL.md content, others provide metadata only. The API supports search, category filtering, and security scoring.

```
Backend: SkillsDirectory
URL: https://www.skillsdirectory.com/api/v1
Auth: x-api-key header (SKILLSDIRECTORY_API_KEY env var)
Search endpoint: GET /api/v1/skills?q=<query>&limit=10
Detail endpoint: GET /api/v1/skills/{slug}
Key format: "author/slug" (e.g., alice/python-linter)
Skill format: Mixed — some include full SKILL.md content, others metadata-only
Response: JSON with skills[]; detail may include content field
Rate limits: 100 req/day (free), 1000/day (Pro $29/mo), 10000/day (Enterprise $199/mo)
Python client: raw urllib
Notes: Sign up at skillsdirectory.com/login?next=/developer/keys for API key.
       Implementation: skill.backends.skillsdirectory.SkillsDirectorySource
```

## Sites investigated but not viable

**skillsmp.com** — Returns HTTP 403 (Cloudflare bot challenge). Cannot be accessed programmatically.

**claudeskills.info** — A Next.js content/blog site about Claude Skills. Has an `/explore` search page but no JSON API. Would require fragile SPA scraping.

**mcpmarket.com** — Returns HTTP 403 from Vercel (`x-vercel-mitigated: deny`). Entirely inaccessible.

**platform.claude.com tool-search-tool** — This is Anthropic's documentation for a feature that lets you search *your own* tool catalog at runtime (using `tool_search_tool_regex_20251119` or `tool_search_tool_bm25_20251119` within the Messages API). It's not a skill marketplace or registry.

**LangChain Hub** offers prompts via `langsmith` Python SDK (`client.pull_prompt("owner/name")`) with versioning and tags. However, prompts are passive text templates rather than tool definitions, making the SKILL.md translation less natural. The key format `owner/prompt_name:commit_hash` supports version pinning. Access requires a `LANGCHAIN_API_KEY`. This backend is lower priority because prompt-as-skill is a weaker abstraction than tool-as-skill.

## Translation from non-native formats follows clear patterns

For backends that don't serve native SKILL.md, a translator must produce a valid skill folder from structured metadata. The three viable translations share a common pattern: extract `name` (kebab-cased), `description` (with "Use when..." trigger clause), and structured content for the markdown body.

**MCP server → SKILL.md** has the highest fidelity. Each MCP tool's `name`, `description`, and `inputSchema` map directly to frontmatter and body sections. Transport configuration maps to the `compatibility` field. A single MCP server with multiple tools produces one SKILL.md with each tool documented as a markdown section with parameter tables.

**Composio tool → SKILL.md** follows a similar pattern but requires handling the auth layer. Toolkit names become skill names (e.g., `HACKERNEWS` → `hackernews-toolkit`), action descriptions become body sections, and input schemas become parameter documentation. The `compatibility` field captures auth requirements.

**LangChain prompt → SKILL.md** requires the most interpretation. Template text becomes the instruction body, `input_variables` become a "Required Inputs" section, and few-shot examples map to `references/examples.md`. The `metadata` field stores the original prompt ID and version hash for traceability.

No universal format translator exists today. The `skills-ref` CLI from agentskills/agentskills validates SKILL.md files but doesn't generate them. **Mintlify** auto-generates `/.well-known/skills/default/skill.md` for all documentation sites — a pattern worth noting but not directly useful as a registry. **Speakeasy** (speakeasy-api/skills) has released skills that convert OpenAPI specs into SKILL.md format, establishing a precedent for the OpenAPI → SKILL.md translation path.

## Implemented backends in the `skill` package

All five backends share the `SkillSource` protocol: `search(query, *, max_results) -> list[SkillInfo]`, `__getitem__(key) -> Skill`, `__contains__(key) -> bool`. They are registered lazily in `skill.search.backends` and can be enabled/disabled via config flags in `config.toml`.

**No auth needed (register automatically):**
- `GitHubSkillSource` — Primary backend. Searches via Code Search API, fetches raw SKILL.md.
- `SmitherySkillSource` — Searches `/skills` endpoint. Tries to fetch SKILL.md from linked git repos, falls back to synthesized skills.
- `AwesomeListSource` — Parses the curated README, caches entries. Fetches SKILL.md from linked GitHub repos.

**Auth needed (register if env var set):**
- `ComposioSkillSource` — Requires `COMPOSIO_API_KEY`. Translates tool definitions into SKILL.md format with parameter documentation.
- `SkillsDirectorySource` — Requires `SKILLSDIRECTORY_API_KEY`. Parses SKILL.md content from API response or synthesizes from metadata.

**Future consideration.** The official MCP Registry (registry.modelcontextprotocol.io) is still in preview but will likely become the canonical MCP discovery layer. LangChain Hub offers prompts but with weaker skill semantics. Agensi.io and skills.sh lack APIs entirely — monitor for API announcements.

## Conclusion

The Agent Skills ecosystem is deliberately decentralized — there is no npm-equivalent registry with a comprehensive API. This is by design: the spec is "deliciously tiny" (as Simon Willison noted), and distribution piggybacks on git. For the `skill` Python package, this means **GitHub is simultaneously the source of truth and the API layer**, supplemented by curated indexes for discovery and adjacent registries for breadth. The most impactful architectural decision is building a pluggable backend interface early: a `SkillBackend` abstract class with `search()`, `list()`, and `fetch()` methods, where `GitHubBackend` ships as default and `SmitheryBackend`/`ComposioBackend` are optional extras that include SKILL.md translators. The translation gap is real but tractable — MCP tool definitions and Composio's structured schemas map to SKILL.md with high fidelity, while prompt-based sources require more interpretive wrapping.