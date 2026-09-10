# skill.cli_format

Terminal-friendly formatting for CLI output.

### Functions

| [`format_path_dict`](#skill.cli_format.format_path_dict)(d, \*[, verb])              | Format a {name: path} dict as readable output.            |
|-----------------------------------------------------------------------------------------------|-----------------------------------------------------------|
| [`format_skill`](#skill.cli_format.format_skill)(skill, \*[, url, dep_warnings]) | Format a full Skill for terminal display.                 |
| [`format_skill_info`](#skill.cli_format.format_skill_info)(info)                      | Format a single SkillInfo as a compact one-liner.         |
| [`format_skill_info_table`](#skill.cli_format.format_skill_info_table)(items)               | Format a list of SkillInfo as an aligned, readable table. |
| [`format_sources`](#skill.cli_format.format_sources)(sources)                      | Format a list of source dicts for terminal display.       |

### skill.cli_format.format_path_dict(d, , verb='Installed')

Format a {name: path} dict as readable output.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> from pathlib import Path
>>> out = format_path_dict({'claude-code': Path('/a/b')}, verb='Installed')
>>> 'claude-code' in out
True
```

### skill.cli_format.format_skill(skill, , url=None, dep_warnings=None)

Format a full Skill for terminal display.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> from skill.base import SkillMeta
>>> s = Skill(meta=SkillMeta(name='test', description='A test'), body='# Hello')
>>> 'Name:' in format_skill(s)
True
>>> 'WARNING' in format_skill(s, dep_warnings=['Missing dependencies: alice/foo'])
True
```

### skill.cli_format.format_skill_info(info)

Format a single SkillInfo as a compact one-liner.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> si = SkillInfo('owner/test', 'test', 'A test skill', 'local', installed=True)
>>> '✓' in format_skill_info(si)
True
```

### skill.cli_format.format_skill_info_table(items)

Format a list of SkillInfo as an aligned, readable table.

Shows URL on a second line when available.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> items = [
...     SkillInfo('alice/lint', 'lint', 'Lint Python code', 'local', installed=True),
...     SkillInfo('bob/react-tips', 'react-tips', 'React best practices guide', 'github',
...               url='https://github.com/bob/react-tips'),
... ]
>>> out = format_skill_info_table(items)
>>> '✓' in out and 'alice/lint' in out
True
>>> 'https://github.com/bob/react-tips' in out
True
```

### skill.cli_format.format_sources(sources)

Format a list of source dicts for terminal display.

* **Return type:**
  [`str`](https://docs.python.org/3/library/stdtypes.html#str)

```pycon
>>> out = format_sources([{'name': 'github', 'homepage': 'https://github.com', 'enabled': True}])
>>> 'github' in out and 'https://github.com' in out
True
```
