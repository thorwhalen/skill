# Plugin System

`skill` uses a registry-based plugin architecture. There are four registries, each holding a different category of extensible component. You can register custom components at runtime (via the Python API) or via entry points (for third-party packages).

## Registries Overview

| Registry | Import path | Key type | Value type | Entry point group |
|----------|-------------|----------|------------|-------------------|
| Agent targets | `skill.install.agent_targets` | `str` | `AgentTarget` | `skill.agent_targets` |
| Translators | `skill.translate.translators` | `str` | `Callable[[Skill], str]` | `skill.translators` |
| Backends | `skill.search.backends` | `str` | `SkillSource` | `skill.backends` |
| Validators | `skill.create.validators` | `str` | `Callable[[Skill], list[str]]` | `skill.validators` |

All registries are instances of `skill.registry.Registry`, a `MutableMapping[str, T]` with lazy entry point discovery.

---

## Registering at Runtime

### Agent Targets

An `AgentTarget` describes where an AI agent expects skills to be installed.

**Contract**: `AgentTarget` dataclass with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Human-readable name |
| `global_path` | `str \| None` | Template for global install path. Supports `{home}`, `{name}`. |
| `project_path` | `str \| None` | Template for project install path. Supports `{project}`, `{name}`. |
| `format` | `str` | Output format key (must match a translator if `needs_translation=True`). Default: `'skill.md'`. |
| `needs_translation` | `bool` | Whether the skill must be translated before installation. Default: `False`. |

**Example**:

```python
from skill.install import agent_targets, AgentTarget

agent_targets.register('windsurf', AgentTarget(
    name='windsurf',
    global_path='{home}/.windsurf/rules/{name}.md',
    project_path='{project}/.windsurf/rules/{name}.md',
    format='skill.md',  # native SKILL.md, no translation needed
))
```

If `format` is something other than `'skill.md'`, set `needs_translation=True` and ensure a matching translator is registered.

### Translators

A translator converts a `Skill` object to a target-format string.

**Contract**: `Callable[[Skill], str]`

The function receives a `Skill` and returns the translated content as a string. If the translation is lossy, emit a `warnings.warn()` describing what was dropped.

**Example**:

```python
from skill.translate import translators
from skill.base import Skill

def to_windsurf(skill: Skill) -> str:
    """Translate SKILL.md to Windsurf rule format."""
    lines = [
        '---',
        f'trigger: model_decision',
        f'description: {skill.meta.description}',
        '---',
        '',
        skill.body,
    ]
    return '\n'.join(lines)

translators.register('windsurf_md', to_windsurf)
```

### Backends (Skill Sources)

A backend is a read-only source of skills for remote search and fetching.

**Contract**: Must satisfy the `SkillSource` protocol:

```python
class SkillSource(Protocol):
    name: str

    def __getitem__(self, key: str) -> Skill:
        """Fetch a skill by canonical key. Raises KeyError if not found."""
        ...

    def __contains__(self, key: object) -> bool:
        """Check if a skill exists in this source."""
        ...

    def search(self, query: str, *, max_results: int = 10) -> list[SkillInfo]:
        """Search for skills matching the query string."""
        ...
```

`__iter__` and `__len__` are deliberately omitted — remote sources may not support enumeration.

**Example**:

```python
from skill.search import backends

class SmitherySource:
    name = 'smithery'

    def __getitem__(self, key):
        # Fetch from Smithery API...
        ...

    def __contains__(self, key):
        ...

    def search(self, query, *, max_results=10):
        # Search Smithery API...
        ...

backends.register('smithery', SmitherySource())
```

### Validators

A validator checks a `Skill` for issues and returns a list of problem descriptions.

**Contract**: `Callable[[Skill], list[str]]`

Returns an empty list if the skill passes the check. Each string in the returned list describes one issue.

**Example**:

```python
from skill.create import validators
from skill.base import Skill

def check_body_length(skill: Skill) -> list[str]:
    word_count = len(skill.body.split())
    if word_count > 5000:
        return [f'Body exceeds 5000 words ({word_count})']
    return []

validators.register('body_length', check_body_length)
```

---

## Registering via Entry Points

Third-party packages can register plugins without requiring any code changes in `skill`. Add an entry point to your package's `pyproject.toml`:

```toml
[project.entry-points."skill.agent_targets"]
windsurf = "my_package.targets:windsurf_target"

[project.entry-points."skill.translators"]
windsurf_md = "my_package.translators:to_windsurf"

[project.entry-points."skill.backends"]
smithery = "my_package.backends:smithery_source"

[project.entry-points."skill.validators"]
body_length = "my_package.validators:check_body_length"
```

Each entry point should resolve to the object to register (an `AgentTarget` instance, a callable, a `SkillSource` instance, etc.). Entry points are discovered lazily on first registry access.

---

## Built-in Registrations

### Agent targets

| Name | Format | Translation | Scope |
|------|--------|-------------|-------|
| `claude-code` | `skill.md` | No | Global + Project |
| `cursor` | `mdc` | Yes | Project only |
| `copilot` | `copilot_md` | Yes | Project only |

### Translators

| Name | Direction | Notes |
|------|-----------|-------|
| `mdc` | SKILL.md → Cursor .mdc | Lossy: drops `allowed-tools`, `license`, resources |
| `copilot_md` | SKILL.md → Copilot instructions | Lossy: drops resources, appends as section |

### Backends

| Name | Source | Notes |
|------|--------|-------|
| `github` | GitHub API | Code Search + Contents API, lazily registered |

### Validators

| Name | Checks |
|------|--------|
| `required_fields` | `name` and `description` are present |
| `body` | Body is not empty |
| `name_format` | Name matches `^[a-z0-9]+(-[a-z0-9]+)*$` |
| `lengths` | Name ≤ 64 chars, description ≤ 1024 chars |

---

## The Registry Class

`skill.registry.Registry[T]` is a `MutableMapping[str, T]` with these extras:

- **`register(name, item)`**: Register an item. Returns the item (usable as a decorator factory).
- **Entry point discovery**: On first read access (`__getitem__`, `__iter__`, `__contains__`, `__len__`), loads plugins from the `skill.<registry_name>` entry point group.
- **Explicit registration takes precedence**: If you `register()` a name before entry points load, the explicit registration wins.
