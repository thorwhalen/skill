---
name: skill-docs
description: >-
  Skill documentation tooling for the skill package. Document a project's AI
  agent skills in the README and other formats. Use this skill when the user
  wants to add skills documentation to a README, explain what skills a project
  offers, write a "Skills" section, generate skill installation instructions,
  or when asked things like "document the skills", "add skills to the README",
  "how should I present skills to users", or "write skill usage examples".
  Also trigger when updating a README for a package that has skills in
  .claude/skills/ or {pkg}/data/skills/.
---

# Skill Docs

Document a project's skills so users know they exist and how to use them.

## Philosophy

Skills are the AI-native interface to a package. The future of developer tools
involves some form of AI agency — whether you're pair-programming with Claude,
using Cursor, or asking Copilot for help. Skills are how packages teach these
agents to actually be useful, rather than hallucinating API calls.

So: put the Skills section **early** in the README. Before the detailed API
reference, after the install/quick-start. The message is simple — this package
comes with built-in AI superpowers. Of course, developers who prefer direct API
calls are welcome to scroll past. We don't judge the artisanal, hand-crafted
approach. Much.

## Process

### 1. Discover skills

Find all skills the project offers:

```bash
# Project-local skills
ls .claude/skills/

# Shipped skills (for pip-installable packages)
ls {pkg_name}/data/skills/ 2>/dev/null
```

Read each skill's SKILL.md to understand what it does.

### 2. Classify skills

Sort skills into two categories:

- **Consumer skills** — Help users *use* the package. These are what most users
  care about. Example: "a skill that helps you search for and install AI agent
  skills."
- **Producer skills** — Help developers *extend* the package. Relevant for
  contributors. Example: "a skill that guides you through adding a new search
  backend."

### 3. Write the README section

Place this section after "Install" / "Quick Start" and before detailed API docs.

**Template:**

````markdown
## Skills (AI Agent Integration)

This package ships with [AI agent skills](https://agentskills.io) —
structured instructions that make AI coding assistants (Claude Code, Cursor,
GitHub Copilot, etc.) genuinely effective at using `{pkg_name}`.

> The future is agentic. Skills are how your tools teach your AI to actually
> help, instead of confidently guessing wrong. But if you prefer typing
> everything yourself, the [API docs](#api) await you below. No judgment.
> (Okay, a little judgment.)

### Available skills

| Skill | What it does |
|-------|-------------|
| `{skill-name}` | {one-liner from description} |
| ... | ... |

### Using skills

**With Claude Code** (skills auto-trigger based on your request):
```
> I need to {describe a task that matches a consumer skill's trigger}
# Claude automatically consults the relevant skill and follows its guidance
```

Or invoke explicitly:
```
> /skill-name
```

**Installing skills in your project:**
```bash
# Symlink from this package into your project (keeps SSOT in the package)
skill link-skills /path/to/{pkg_name} --target .claude/skills

# Or into your global skills (available everywhere)
skill link-skills /path/to/{pkg_name} --target ~/.claude/skills
```

> **Tip:** Symlinking keeps the single source of truth in the package repo.
> When the package updates its skills, your linked copies update too.
> See the [`skill` package docs](https://github.com/thorwhalen/skill) for
> more on managing skills, scoping, and multi-agent support.

**After `pip install {pkg_name}`:**
```bash
# If the package ships skills in its distribution
skill link-skills $(python -c "import {pkg_name}; print({pkg_name}.__path__[0])")/data/skills
```
````

### 4. Adapt the template

The template above is a starting point. Adapt it:

- **Use real skill names and descriptions** from the project's actual skills.
- **Pick 2-3 concrete examples** of consumer skill usage — show realistic
  prompts that a user might type, and what the AI would do. Favor consumer
  skills (things users do) over producer skills (things contributors do).
- **Mention both kinds of skills** but keep producer skills brief — a sentence
  or a link to CONTRIBUTING.md.
- **Link to further reading:**
  - [Agent Skills spec](https://agentskills.io)
  - [skill package](https://github.com/thorwhalen/skill) for managing skills
  - The project's own skill files for the full instructions

### 5. Other documentation surfaces

Beyond the README, consider:

- **CONTRIBUTING.md** — Mention producer skills here. "Before adding a new
  backend, consult the `add-backend` skill in `.claude/skills/`."
- **Package docstring** (`__init__.py`) — A one-liner like "This package ships
  AI agent skills. See .claude/skills/ or run `skill list-skills`."
- **Release notes** — When skills change, mention it. "Updated: `skill-search`
  skill now covers the new Smithery backend."
- **pyproject.toml metadata** — Add a `"Skills"` keyword/classifier so the
  package is discoverable by skill-aware tools.

## Example: skill package README section

Here's what the skills section might look like for the `skill` package itself:

````markdown
## Skills

This package eats its own cooking — it ships skills that teach AI agents how
to work with AI agent skills. Recursive? Yes. Useful? Also yes.

| Skill | Kind | What it does |
|-------|------|-------------|
| `skill-builder` | Producer | Analyze a package and create skills for it |
| `skill-manager` | Consumer | Search, list, and inspect installed skills |
| `skill-docs` | Producer | Document skills in README and other formats |
| `skill-sync` | Producer | Keep skills in sync when code changes |
| `skill-enablement` | Producer | Ship skills with pip-installable packages |

### Quick examples

**Find and install a skill** (auto-triggered by your request):
```
> I want to find a skill for writing React components and install it
```

**List what you have:**
```
> /skill-manager
> What skills do I have installed?
```

**Build skills for your own package:**
```
> /skill-builder
> Analyze my-package and suggest skills to create
```

### Installation

```bash
# Symlink into your project
skill link-skills /path/to/skill --target .claude/skills

# Or globally
skill link-skills /path/to/skill --target ~/.claude/skills
```
````
