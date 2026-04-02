---
name: skill-manage
description: >-
  Skill management tooling for the skill package. Search, list, inspect, and
  manage AI agent skills across agents and projects. Use this skill when the
  user wants to find skills, see what skills are installed, check where skills
  are linked, inspect a skill's contents, install or uninstall skills, compare
  skills across agents (Claude Code, Cursor, Copilot), or says things like
  "what skills do I have", "find a skill for X", "show me the skill", "where
  are my skills", "install this skill", "remove that skill", "list skills", or
  "search skills". Trigger on any skill inventory, discovery, or housekeeping
  request.
---

# Skill Manager

Search, list, inspect, and manage AI agent skills.

## Core operations

### Search for skills

Find skills across local store and remote backends (GitHub, Smithery, Composio,
and more):

```python
from skill import search

# Local + remote search
results = search('react best practices', max_results=10)

# Local only (faster, no network)
results = search('testing', local_only=True)

# Specific backends only
results = search('deployment', backends=['github', 'smithery'])
```

CLI:
```bash
skill search "react best practices"
skill search "testing" --local-only
skill search "deployment" --max-results 20
```

Each result is a `SkillInfo` with:
- `canonical_key` — e.g., `"thorwhalen/skill-search"` (owner/name)
- `name`, `description` — what it does
- `source` — where it came from (`"local"`, `"github"`, `"smithery"`, etc.)
- `url` — link to the source (for remote results)
- `installed` — whether it's already in the local store

### List installed skills

```python
from skill import list_skills

skills = list_skills()
for s in skills:
    print(f"{'✓' if s.installed else ' '} {s.canonical_key}: {s.description}")
```

CLI:
```bash
skill list-skills
```

### Inspect a skill

Read the full contents of an installed skill:

```python
from skill import show

s = show('owner/skill-name')
print(s.meta.name)        # 'skill-name'
print(s.meta.description)  # one-liner
print(s.body)              # full instructions
print(s.resources)         # {'scripts': ['run.py'], 'references': ['guide.md']}
```

CLI:
```bash
skill show owner/skill-name
```

### Install a skill

Install from the local store into an agent target:

```python
from skill import install

# Install into project-local Claude Code skills
paths = install('owner/skill-name', scope='project')

# Install globally
paths = install('owner/skill-name', scope='global')

# Install into multiple agents
paths = install('owner/skill-name', agent_targets=['claude-code', 'cursor'])

# Copy instead of symlink
paths = install('owner/skill-name', copy=True)
```

CLI:
```bash
skill install owner/skill-name
skill install owner/skill-name --scope global
skill install owner/skill-name --agent-targets claude-code cursor
```

### Uninstall a skill

```python
from skill import uninstall

removed = uninstall('owner/skill-name')
```

CLI:
```bash
skill uninstall owner/skill-name
```

### Link skills from a project

Bulk-link all skills from a project or directory:

```python
from skill import link_skills

# From a project root (auto-discovers .claude/skills/ or {pkg}/data/skills/)
linked = link_skills('/path/to/project')

# Into a specific target
linked = link_skills('/path/to/project', target='~/.claude/skills')

# Force overwrite existing
linked = link_skills('/path/to/project', target='.claude/skills', force=True)
```

CLI:
```bash
skill link-skills /path/to/project
skill link-skills /path/to/project --target ~/.claude/skills --force
```

### Check available search backends

```python
from skill import sources

for src in sources():
    status = "enabled" if src['enabled'] else "disabled"
    print(f"{src['name']}: {status} ({src.get('homepage', 'N/A')})")
```

CLI:
```bash
skill sources
```

## Where skills live

Skills can exist in several places:

| Location | Purpose | Scope |
|----------|---------|-------|
| `~/.local/share/skill/skills/` | Local skill store (downloaded/created) | User-wide |
| `~/.claude/skills/` | Claude Code global skills | All projects |
| `.claude/skills/` | Claude Code project skills | This project |
| `.cursor/rules/` | Cursor rules (translated from SKILL.md) | This project |
| `.github/copilot-instructions.md` | Copilot instructions (appended) | This project |
| `{pkg}/data/skills/` | Package-shipped skills | Distributed |

When helping the user understand their skill landscape, check all relevant
locations. Use `ls` or `glob` to see what's actually on disk, since symlinks
may point to different locations.

## Common workflows

**"I want to find and use a skill":**
1. `search('topic')` to find candidates
2. Review the results — check descriptions and sources
3. `install(key)` to link it into the current project
4. The agent can now use it automatically

**"What skills do I have?":**
1. `list_skills()` for the local store inventory
2. Check `.claude/skills/` for project-local skills
3. Check `~/.claude/skills/` for global skills
4. Report which are symlinks vs copies, and where they point

**"Something's wrong with a skill":**
1. `show(key)` to read the full skill
2. `validate(path)` to check for structural issues
3. Check if it's a symlink pointing to a moved/deleted source
4. Use the `skill-sync` skill if the issue is code drift

## Gotchas

- **`install()` requires the skill to be in the local store first.** If you
  searched remotely, you need to fetch/create it locally before installing.
  The `create()` function can be used to add a skill to the store.
- **Cursor and Copilot need format translation.** When installing to these
  targets, the skill is automatically converted — but some metadata is lost
  (Cursor doesn't support all frontmatter fields, Copilot appends to a
  single file).
- **Symlinks break if the source moves.** If a user reorganizes their project,
  skill symlinks may dangle. Check with `ls -la` and re-link if needed.
- **`scope='project'` requires being in a project.** If `find_project_root()`
  can't detect a project (no `.git`, `pyproject.toml`, etc.), it will raise
  `RuntimeError`. Pass `project_dir` explicitly in that case.
