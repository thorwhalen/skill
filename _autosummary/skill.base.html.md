# skill.base

Core data model and SKILL.md parsing.

### Module Attributes

| [`KNOWN_FRONTMATTER_KEYS`](#skill.base.KNOWN_FRONTMATTER_KEYS)   | Top-level frontmatter keys `SkillMeta` models as named fields.   |
|---------------------------------------------------------------------------|------------------------------------------------------------------|

### Functions

| [`discover_resources`](#skill.base.discover_resources)(path)    | Scan a skill directory for bundled resource subdirectories.      |
|------------------------------------------------------------------------------|------------------------------------------------------------------|
| [`parse_frontmatter`](#skill.base.parse_frontmatter)(content)  | Parse YAML frontmatter delimited by `---` from markdown content. |
| [`parse_skill_md`](#skill.base.parse_skill_md)(content)     | Parse a SKILL.md string into (SkillMeta, body).                  |
| [`render_frontmatter`](#skill.base.render_frontmatter)(meta)    | Render a dict as YAML frontmatter block.                         |
| [`render_skill_md`](#skill.base.render_skill_md)(meta, body) | Render a SKILL.md string from meta and body.                     |

### Classes

| [`Skill`](#skill.base.Skill)(meta, body[, resources, source_path])      | A fully parsed skill: frontmatter + body + resource manifest.   |
|---------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| [`SkillInfo`](#skill.base.SkillInfo)(canonical_key, name, description, ...) | Lightweight metadata for search results (no body).              |
| [`SkillMeta`](#skill.base.SkillMeta)(name, description[, audience, ...])    | Parsed YAML frontmatter from a SKILL.md file.                   |

### skill.base.KNOWN_FRONTMATTER_KEYS *= frozenset({'allowed-tools', 'audience', 'compatibility', 'description', 'license', 'metadata', 'name'})*

Top-level frontmatter keys `SkillMeta` models as named fields. Anything else
is an unknown/namespaced key (e.g. another tool’s `coact:` block) and is kept
verbatim in [`SkillMeta.extra`](#skill.base.SkillMeta.extra) so it survives a parse→render round-trip.

### *class* skill.base.Skill(meta, body, resources=<factory>, source_path=None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A fully parsed skill: frontmatter + body + resource manifest.

```pycon
>>> s = Skill(meta=SkillMeta(name='test', description='A test'), body='# Hello')
>>> s.meta.name
'test'
```

#### *classmethod* from_path(path)

Load a Skill from a directory containing SKILL.md.

`path` should be the skill directory (containing SKILL.md).

* **Return type:**
  [`Skill`](#skill.base.Skill)

#### *classmethod* from_string(content)

Parse a Skill from a SKILL.md string (no resource discovery).

* **Return type:**
  [`Skill`](#skill.base.Skill)

```pycon
>>> s = Skill.from_string("---\nname: x\ndescription: y\n---\nbody")
>>> s.meta.name
'x'
```

#### to_string()

Render this skill as a SKILL.md string.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

#### write_to(path)

Write this skill to a directory, creating SKILL.md and resource dirs.

* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)

### *class* skill.base.SkillInfo(canonical_key, name, description, source, url=None, owner=None, installed=False)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Lightweight metadata for search results (no body).

```pycon
>>> si = SkillInfo(canonical_key='owner/test', name='test', description='A test', source='local')
>>> si.canonical_key
'owner/test'
```

### *class* skill.base.SkillMeta(name, description, audience=None, license=None, compatibility=None, metadata=<factory>, allowed_tools=<factory>, extra=<factory>)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Parsed YAML frontmatter from a SKILL.md file.

```pycon
>>> m = SkillMeta(name='test', description='A test skill')
>>> m.name
'test'
```

Unknown/namespaced top-level keys are preserved in [`extra`](#skill.base.SkillMeta.extra) and re-emitted
on render, so a tool’s additive frontmatter block isn’t silently dropped:

```pycon
>>> m = SkillMeta(name='t', description='d', extra={'coact': {'model': 'sonnet'}})
>>> m.to_dict()['coact']
{'model': 'sonnet'}
```

#### extra *: [dict](https://docs.python.org/3/library/stdtypes.html#dict)[[str](https://docs.python.org/3/library/stdtypes.html#str), [Any](https://docs.python.org/3/library/typing.html#typing.Any)]*

Unknown/namespaced top-level frontmatter keys, kept verbatim for round-trip.

#### to_dict()

Convert to a dict suitable for YAML frontmatter, omitting None values.

Named fields render first (stable order); preserved [`extra`](#skill.base.SkillMeta.extra) keys
follow, so namespaced blocks survive `parse_skill_md` → `render_skill_md`.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)

### skill.base.discover_resources(path)

Scan a skill directory for bundled resource subdirectories.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)]]

```pycon
>>> import tempfile
>>> with tempfile.TemporaryDirectory() as d:
...     p = Path(d)
...     (p / 'scripts').mkdir()
...     (p / 'scripts' / 'run.py').touch()
...     r = discover_resources(p)
...     r['scripts']
['run.py']
```

### skill.base.parse_frontmatter(content)

Parse YAML frontmatter delimited by `---` from markdown content.

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`dict`](https://docs.python.org/3/library/stdtypes.html#dict), [`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> meta, body = parse_frontmatter("---\nname: test\ndescription: A test\n---\n# Hello")
>>> meta['name']
'test'
>>> body.strip()
'# Hello'
>>> parse_frontmatter("no frontmatter here")
({}, 'no frontmatter here')
```

### skill.base.parse_skill_md(content)

Parse a SKILL.md string into (SkillMeta, body).

* **Return type:**
  [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple)[[`SkillMeta`](#skill.base.SkillMeta), [`str`](https://docs.python.org/3/library/stdtypes.html#str)]

```pycon
>>> meta, body = parse_skill_md("---\nname: foo\ndescription: bar\n---\nHello")
>>> meta.name
'foo'
>>> body
'Hello'
```

### skill.base.render_frontmatter(meta)

Render a dict as YAML frontmatter block.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> print(render_frontmatter({'name': 'test', 'description': 'A test'}))
---
name: test
description: A test
---
```

### skill.base.render_skill_md(meta, body)

Render a SKILL.md string from meta and body.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> s = render_skill_md(SkillMeta(name='x', description='y'), 'Hello')
>>> 'name: x' in s and 'Hello' in s
True
```
