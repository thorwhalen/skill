
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

### Link skills from a project

If a project ships skills (in `.claude/skills/`, `{pkg}/data/skills/`, or a
dedicated folder), you can symlink them all into your agent's skills directory
in one shot:

```python
from skill import link_skills

# Point at a project root — it finds the skills automatically
link_skills('/path/to/my-project')

# Or point at the skills folder directly
link_skills('/path/to/my-project/my_pkg/data/skills')

# Symlink into a specific target instead of ~/.claude/skills
link_skills('/path/to/my-project', target='/other/project/.claude/skills')
```

Each skill is validated before linking — invalid skills are skipped with a
warning. The target directory is also checked to ensure it's a recognized
skills directory.

### CLI

```
skill create my-skill --description "My custom coding rules"
skill search "react best practices" --local-only
skill validate ./my-skill/
skill list-skills
skill install _local/my-skill --agent-targets claude-code
skill link-skills /path/to/project
skill link-skills /path/to/project --target ~/.claude/skills --force
```

### Shell completion

Enable tab completion for all `skill` commands:

```bash
skill install-completion
```

This detects your shell (bash/zsh) and adds the registration line to your
shell config (`~/.bashrc` or `~/.zshrc`). Restart your shell or `source` the
config file to activate.

If you prefer to set it up manually:

```bash
# Add to your shell config:
eval "$(register-python-argcomplete skill)"
```

The first time you run any `skill` command without completion set up, you'll
see a one-time hint reminding you to run `skill install-completion`.

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
