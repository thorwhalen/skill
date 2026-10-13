# skill

AI Agent Skill Search and Management.

Simple usage:

```default
from skill import search, install, create, list_skills, validate

# Search for skills
results = search('react best practices', local_only=True)

# Create a new skill locally
skill = create('my-skill', description='My custom skill')

# Validate a skill
issues = validate('/path/to/skill-dir')
```

Plugin registries:

```default
from skill.install import agent_targets
from skill.translate import translators
from skill.search import backends
from skill.create import validators
```

### Functions

| [`list_skills`](#skill.list_skills)(\*[, agent_target, scope])   | List locally installed skills, optionally filtered by agent target.    |
|-------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| [`show`](#skill.show)(key)                                | Read and return a skill by its canonical key.                          |
| [`sources`](#skill.sources)()                                | List registered search backends with their name, homepage, and status. |

### skill.list_skills(, agent_target=None, scope='all')

List locally installed skills, optionally filtered by agent target.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`SkillInfo`](skill.base.md#skill.base.SkillInfo)]

```pycon
>>> isinstance(list_skills(), list)
True
```

### skill.show(key)

Read and return a skill by its canonical key.

Raises KeyError if the skill is not found locally.

* **Return type:**
  [`Skill`](skill.base.md#skill.base.Skill)

### skill.sources()

List registered search backends with their name, homepage, and status.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

```pycon
>>> isinstance(sources(), list)
True
```

### Modules

| [`ai`](skill.ai.md#module-skill.ai)                                             | Optional AI facade for semantic search and LLM-powered features.   |
|-----------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`backends`](skill.backends.md#module-skill.backends)                                 | Backend protocols and local filesystem backend.                    |
| [`base`](skill.base.md#module-skill.base)                                         | Core data model and SKILL.md parsing.                              |
| [`cli_format`](skill.cli_format.md#module-skill.cli_format)                             | Terminal-friendly formatting for CLI output.                       |
| [`completion`](skill.completion.md#module-skill.completion)                             | Shell completion setup and diagnostics.                            |
| [`config`](skill.config.md#module-skill.config)                                     | Configuration management via platformdirs and TOML.                |
| [`create`](skill.create.md#skill.create)(name, \*[, description, body, owner, ...]) | Create a new skill and store it locally.                           |
| [`install`](skill.install.md#skill.install)(key, \*[, agent_targets, scope, ...])    | Install a skill into one or more agent target directories.         |
| [`registry`](skill.registry.md#module-skill.registry)                                 | Generic plugin registry with entry point discovery.                |
| [`search`](skill.search.md#skill.search)(query, \*[, max_results, local_only, ...]) | Search for skills across local index and remote backends.          |
| [`stores`](skill.stores.md#module-skill.stores)                                     | Storage layer: LocalSkillStore and SourcedSkillStore via dol.      |
| [`translate`](skill.translate.md#module-skill.translate)                               | Format translators: SKILL.md <-> agent-specific formats.           |
| [`util`](skill.util.md#module-skill.util)                                         | Pure helpers with zero internal imports.                           |
