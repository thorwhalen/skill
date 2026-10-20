# skill.translate

Format translators: SKILL.md <-> agent-specific formats.

### Module Attributes

| [`translators`](#skill.translate.translators)        | Registry of format translators (Skill -> target format string).                  |
|---------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`translation_losses`](#skill.translate.translation_losses) | Registry of what each lossy format drops (Skill -> lost field names), by format. |

### Functions

| [`from_mdc`](#skill.translate.from_mdc)(content)                     | Import a Cursor `.mdc` file as a Skill.                                          |
|----------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| [`lost_fields`](#skill.translate.lost_fields)(skill, \*, target_format) | What translating *skill* to *target_format* drops; `[]` for a lossless format.   |
| [`to_cline_rule`](#skill.translate.to_cline_rule)(skill)                  | Translate a Skill to a Cline rule file (Markdown; always active).                |
| [`to_copilot_instructions`](#skill.translate.to_copilot_instructions)(skill)        | Translate a Skill to GitHub Copilot instructions format.                         |
| [`to_gemini_md`](#skill.translate.to_gemini_md)(skill)                   | Translate a Skill to a section of Gemini CLI's `GEMINI.md`.                      |
| [`to_mdc`](#skill.translate.to_mdc)(skill)                         | Translate a Skill to Cursor `.mdc` format.                                       |
| [`to_windsurf_rule`](#skill.translate.to_windsurf_rule)(skill)               | Translate a Skill to a Windsurf rule, applied when the model judges it relevant. |
| [`translate`](#skill.translate.translate)(skill, \*, target_format)   | Translate a Skill to the specified target format.                                |

### skill.translate.from_mdc(content)

Import a Cursor `.mdc` file as a Skill.

```pycon
>>> content = "---\ndescription: Do things\nglobs: '*.py'\nalwaysApply: false\n---\n# Rules"
>>> s = from_mdc(content)
>>> s.meta.description
'Do things'
>>> s.meta.metadata.get('cursor.globs')
'*.py'
```

* **Return type:**
  [`Skill`](skill.base.html.md#skill.base.Skill)

### skill.translate.lost_fields(skill, , target_format)

What translating *skill* to *target_format* drops; `[]` for a lossless format.

```pycon
>>> from skill.base import SkillMeta
>>> s = Skill(meta=SkillMeta(name='t', description='d', license='MIT'), body='x')
>>> lost_fields(s, target_format='mdc')
['license']
>>> lost_fields(s, target_format='skill.md')
[]
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### skill.translate.to_cline_rule(skill)

Translate a Skill to a Cline rule file (Markdown; always active).

`metadata` key `cline.paths` becomes the `paths` frontmatter that makes the
rule conditional. Lossy: no progressive disclosure, and `allowed-tools`,
`license` and bundled resources are dropped.

```pycon
>>> from skill.base import SkillMeta
>>> s = Skill(meta=SkillMeta(name='lint', description='Lint rules'), body='Use ruff.')
>>> to_cline_rule(s).splitlines()[:3]
['# lint', '', '> Lint rules']
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### skill.translate.to_copilot_instructions(skill)

Translate a Skill to GitHub Copilot instructions format.

Produces a Markdown section suitable for appending to
`.github/copilot-instructions.md`. Lossy: no frontmatter support
beyond `applyTo`, no progressive disclosure, no resources.

```pycon
>>> from skill.base import SkillMeta
>>> s = Skill(meta=SkillMeta(name='lint', description='Lint rules'), body='Use ruff.')
>>> md = to_copilot_instructions(s)
>>> '## lint' in md
True
>>> 'Use ruff.' in md
True
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### skill.translate.to_gemini_md(skill)

Translate a Skill to a section of Gemini CLI’s `GEMINI.md`.

Lossy: the file is always loaded (no progressive disclosure), and
`allowed-tools`, `license` and bundled resources are dropped.

```pycon
>>> from skill.base import SkillMeta
>>> s = Skill(meta=SkillMeta(name='lint', description='Lint rules'), body='Use ruff.')
>>> to_gemini_md(s).splitlines()[0]
'## lint'
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### skill.translate.to_mdc(skill)

Translate a Skill to Cursor `.mdc` format.

Lossy: `allowed-tools`, `license`, bundled resources, and progressive
disclosure semantics are lost.

```pycon
>>> from skill.base import SkillMeta
>>> s = Skill(meta=SkillMeta(name='test', description='Test skill'), body='Do stuff.')
>>> mdc = to_mdc(s)
>>> 'description: Test skill' in mdc
True
>>> 'Do stuff.' in mdc
True
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### skill.translate.to_windsurf_rule(skill)

Translate a Skill to a Windsurf rule, applied when the model judges it relevant.

`metadata` keys `windsurf.trigger` (default `model_decision`) and
`windsurf.globs` pass through. Lossy: `allowed-tools`, `license` and
bundled resources are dropped.

```pycon
>>> from skill.base import SkillMeta
>>> s = Skill(meta=SkillMeta(name='lint', description='Lint rules'), body='Use ruff.')
>>> print(to_windsurf_rule(s))
---
trigger: model_decision
description: Lint rules
---

Use ruff.
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### skill.translate.translate(skill, , target_format)

Translate a Skill to the specified target format.

```pycon
>>> from skill.base import SkillMeta
>>> s = Skill(meta=SkillMeta(name='x', description='y'), body='z')
>>> 'alwaysApply' in translate(s, target_format='mdc')
True
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### skill.translate.translation_losses *: [Registry](skill.registry.html.md#skill.registry.Registry)[[Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[Skill](skill.base.html.md#skill.base.Skill)], [list](https://docs.python.org/3/builtins/stdtypes.html#list)[[str](https://docs.python.org/3/builtins/stdtypes.html#str)]]]* *= Registry('translation_losses', keys=['mdc', 'copilot_md', 'gemini_md', 'windsurf_md', 'clinerules_md'])*

Registry of what each lossy format drops (Skill -> lost field names), by format.

The SSOT for lossy down-casts: translators warn from it, and linters (opsward’s
portability check) read it without translating anything.

### skill.translate.translators *: [Registry](skill.registry.html.md#skill.registry.Registry)[[Callable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[Skill](skill.base.html.md#skill.base.Skill)], [str](https://docs.python.org/3/builtins/stdtypes.html#str)]]* *= Registry('translators', keys=['mdc', 'copilot_md', 'gemini_md', 'windsurf_md', 'clinerules_md'])*

Registry of format translators (Skill -> target format string).
