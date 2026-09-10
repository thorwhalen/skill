# skill.backends

Backend protocols and local filesystem backend.

### Classes

| [`LocalDirSource`](#skill.backends.LocalDirSource)(root)            | SkillSource backed by an arbitrary local directory of skills.   |
|----------------------------------------------------------------------------------|-----------------------------------------------------------------|
| [`SkillSource`](#skill.backends.SkillSource)(\*args, \*\*kwargs) | Read-only source of skills (e.g., GitHub, local directory).     |

### *class* skill.backends.LocalDirSource(root)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

SkillSource backed by an arbitrary local directory of skills.

Useful for testing and for local skill packages (e.g. a git checkout).
The directory should contain `owner/name/SKILL.md` structure.

```pycon
>>> import tempfile
>>> from skill.base import Skill, SkillMeta
>>> d = Path(tempfile.mkdtemp())
>>> (d / 'alice' / 'greet').mkdir(parents=True)
>>> Skill(meta=SkillMeta(name='greet', description='Say hi'), body='Hi!').write_to(d / 'alice' / 'greet')
>>> src = LocalDirSource(d)
>>> src.name
'local'
>>> 'alice/greet' in src
True
>>> src['alice/greet'].meta.name
'greet'
```

#### search(query, , max_results=10)

Keyword search over skill names and descriptions.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`SkillInfo`](skill.base.html.md#skill.base.SkillInfo)]

```pycon
>>> import tempfile
>>> from skill.base import Skill, SkillMeta
>>> d = Path(tempfile.mkdtemp())
>>> (d / 'bob' / 'python-lint').mkdir(parents=True)
>>> Skill(meta=SkillMeta(name='python-lint', description='Lint Python code'), body='...').write_to(d / 'bob' / 'python-lint')
>>> src = LocalDirSource(d)
>>> results = src.search('python')
>>> len(results) > 0
True
>>> results[0].name
'python-lint'
```

### *class* skill.backends.SkillSource(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Read-only source of skills (e.g., GitHub, local directory).

`__iter__` and `__len__` are deliberately omitted — remote sources
may not support enumeration.

### Modules

| [`awesome_list`](skill.backends.awesome_list.html.md#module-skill.backends.awesome_list)       | Awesome-claude-skills curated list backend for skill discovery.   |
|--------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| [`composio`](skill.backends.composio.html.md#module-skill.backends.composio)               | Composio backend for skill discovery and fetching.                |
| [`github`](skill.backends.github.html.md#module-skill.backends.github)                   | GitHub backend for skill discovery and fetching.                  |
| [`skillsdirectory`](skill.backends.skillsdirectory.html.md#module-skill.backends.skillsdirectory) | SkillsDirectory backend for skill discovery and fetching.         |
| [`smithery`](skill.backends.smithery.html.md#module-skill.backends.smithery)               | Smithery backend for skill discovery and fetching.                |
