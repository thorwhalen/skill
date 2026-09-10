# skill.translate

Format translators: SKILL.md <-> agent-specific formats.

### Module Attributes

| [`translators`](#skill.translate.translators)   | Registry of format translators (Skill -> target format string).   |
|----------------------------------------------------------------|-------------------------------------------------------------------|

### Functions

| [`from_mdc`](#skill.translate.from_mdc)(content)                   | Import a Cursor `.mdc` file as a Skill.                  |
|--------------------------------------------------------------------------------------|----------------------------------------------------------|
| [`to_copilot_instructions`](#skill.translate.to_copilot_instructions)(skill)      | Translate a Skill to GitHub Copilot instructions format. |
| [`to_mdc`](#skill.translate.to_mdc)(skill)                       | Translate a Skill to Cursor `.mdc` format.               |
| [`translate`](#skill.translate.translate)(skill, \*, target_format) | Translate a Skill to the specified target format.        |

### skill.translate.from_mdc(content)

Import a Cursor `.mdc` file as a Skill.

* **Return type:**
  [`Skill`](skill.base.html.md#skill.base.Skill)

```pycon
>>> content = "---\ndescription: Do things\nglobs: '*.py'\nalwaysApply: false\n---\n# Rules"
>>> s = from_mdc(content)
>>> s.meta.description
'Do things'
>>> s.meta.metadata.get('cursor.globs')
'*.py'
```

### skill.translate.to_copilot_instructions(skill)

Translate a Skill to GitHub Copilot instructions format.

Produces a Markdown section suitable for appending to
`.github/copilot-instructions.md`. Lossy: no frontmatter support
beyond `applyTo`, no progressive disclosure, no resources.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> from skill.base import SkillMeta
>>> s = Skill(meta=SkillMeta(name='lint', description='Lint rules'), body='Use ruff.')
>>> md = to_copilot_instructions(s)
>>> '## lint' in md
True
>>> 'Use ruff.' in md
True
```

### skill.translate.to_mdc(skill)

Translate a Skill to Cursor `.mdc` format.

Lossy: `allowed-tools`, `license`, bundled resources, and progressive
disclosure semantics are lost.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> from skill.base import SkillMeta
>>> s = Skill(meta=SkillMeta(name='test', description='Test skill'), body='Do stuff.')
>>> mdc = to_mdc(s)
>>> 'description: Test skill' in mdc
True
>>> 'Do stuff.' in mdc
True
```

### skill.translate.translate(skill, , target_format)

Translate a Skill to the specified target format.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> from skill.base import SkillMeta
>>> s = Skill(meta=SkillMeta(name='x', description='y'), body='z')
>>> 'alwaysApply' in translate(s, target_format='mdc')
True
```

### skill.translate.translators *: [Registry](skill.registry.html.md#skill.registry.Registry)[[Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[Skill](skill.base.html.md#skill.base.Skill)], [str](https://docs.python.org/3/library/stdtypes.html#str)]]* *= Registry('translators', keys=['mdc', 'copilot_md'])*

Registry of format translators (Skill -> target format string).
