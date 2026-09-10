# skill.util

Pure helpers with zero internal imports.

### Functions

| [`atomic_write`](#skill.util.atomic_write)(path, content)   | Write `content` to `path` atomically via temp-then-rename.         |
|--------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`find_project_root`](#skill.util.find_project_root)([start])    | Walk up from `start` looking for a project root marker.            |
| [`resolve_env_vars`](#skill.util.resolve_env_vars)(value)       | Resolve `$VAR` and `${VAR}` references from environment variables. |

### Classes

| [`ParsedKey`](#skill.util.ParsedKey)(owner, name)   | A normalized skill key.   |
|---------------------------------------------------------------------------|---------------------------|

### *class* skill.util.ParsedKey(owner, name)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A normalized skill key.

```pycon
>>> ParsedKey.from_string('owner/skill-name')
ParsedKey(owner='owner', name='skill-name')
>>> ParsedKey.from_string('Owner/Skill-Name')
ParsedKey(owner='owner', name='skill-name')
>>> ParsedKey.from_string('my-skill')
ParsedKey(owner='_local', name='my-skill')
>>> ParsedKey.from_string('owner/repo/skill-name')
ParsedKey(owner='owner', name='skill-name')
>>> str(ParsedKey(owner='owner', name='skill-name'))
'owner/skill-name'
```

#### *classmethod* from_string(raw)

Parse a raw key string into a normalized ParsedKey.

Supports 1-part (name only), 2-part (owner/name), and 3-part
(owner/repo/name) keys. All parts are lowercased.

* **Return type:**
  [`ParsedKey`](#skill.util.ParsedKey)

### skill.util.atomic_write(path, content)

Write `content` to `path` atomically via temp-then-rename.

* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)

```pycon
>>> import tempfile
>>> with tempfile.TemporaryDirectory() as d:
...     p = Path(d) / 'test.txt'
...     atomic_write(p, 'hello')
...     p.read_text()
'hello'
```

### skill.util.find_project_root(start=None)

Walk up from `start` looking for a project root marker.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`None`](https://docs.python.org/3/library/constants.html#None)

```pycon
>>> import tempfile
>>> d = Path(tempfile.mkdtemp()).resolve()
>>> p = d / 'sub' / 'deep'
>>> p.mkdir(parents=True)
>>> (d / '.git').mkdir()
>>> find_project_root(p) == d
True
>>> find_project_root(Path('/nonexistent/path/that/does/not/exist')) is None
True
```

### skill.util.resolve_env_vars(value)

Resolve `$VAR` and `${VAR}` references from environment variables.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> import os; os.environ['_SKILL_TEST'] = 'hello'
>>> resolve_env_vars('key=$_SKILL_TEST')
'key=hello'
>>> resolve_env_vars('${_SKILL_TEST}/world')
'hello/world'
>>> resolve_env_vars('no vars here')
'no vars here'
```
