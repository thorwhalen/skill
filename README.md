
# skill

AI Agent Skill Search and Management

Manage [Agent Skills](https://agentskills.io) (SKILL.md files) across multiple AI coding agents — Claude Code, Cursor, GitHub Copilot, Windsurf, and more.

## Install

```
pip install skill
```

## Quick Start

```python
from skill import search, create, install, validate

# Create a skill locally
skill = create('my-skill', description='My custom coding rules')

# Validate it
issues = validate('/path/to/skill-dir')

# Search for skills
results = search('react best practices', local_only=True)

# Install to an agent target
install('_local/my-skill', agent_targets=['claude-code'], scope='project')
```

### CLI

```
python -m skill create my-skill --description "My custom coding rules"
python -m skill search "react best practices" --local-only
python -m skill validate ./my-skill/
python -m skill list-skills
python -m skill install _local/my-skill --agent-targets claude-code
```

## Plugin System

`skill` has a registry-based plugin architecture with four extension points:

| Registry | What it holds | Import |
|----------|--------------|--------|
| **Agent targets** | Where agents expect skills installed | `from skill.install import agent_targets` |
| **Translators** | SKILL.md → target format converters | `from skill.translate import translators` |
| **Backends** | Remote skill sources for search | `from skill.search import backends` |
| **Validators** | Pluggable validation rules | `from skill.create import validators` |

Register at runtime:

```python
from skill.install import agent_targets, AgentTarget

agent_targets.register('windsurf', AgentTarget(
    name='windsurf',
    project_path='{project}/.windsurf/rules/{name}.md',
    format='skill.md',
))
```

Or via entry points in your `pyproject.toml`:

```toml
[project.entry-points."skill.agent_targets"]
windsurf = "my_package:windsurf_target"
```

See [Plugin System Documentation](misc/docs/plugin_system.md) for full details on contracts, interfaces, and built-in registrations.
