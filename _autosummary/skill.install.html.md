# skill.install

### skill.install(key, , agent_targets=None, scope='project', copy=False, force=False, project_dir=None, store=None)

Install a skill into one or more agent target directories.

Returns a dict mapping agent target names to the paths where the skill
was installed.

* **Parameters:**
  * **key** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – Canonical skill key (e.g., `'owner/skill-name'`).
  * **agent_targets** ([`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`str`](https://docs.python.org/3/library/stdtypes.html#str)] | [`None`](https://docs.python.org/3/library/constants.html#None)) – Agent targets to install into. Defaults to config’s `default_agent_targets`.
  * **scope** ([`str`](https://docs.python.org/3/library/stdtypes.html#str)) – `'project'` (default) or `'global'`.
  * **copy** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – If True, copy instead of symlink.
  * **force** ([`bool`](https://docs.python.org/3/library/functions.html#bool)) – If True, overwrite existing files/links.
  * **project_dir** ([`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path) | [`str`](https://docs.python.org/3/library/stdtypes.html#str) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Project root. Auto-detected if None.
  * **store** ([`LocalSkillStore`](skill.stores.html.md#skill.stores.LocalSkillStore) | [`None`](https://docs.python.org/3/library/constants.html#None)) – Skill store to read from. Uses default if None.
* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)[[`str`](https://docs.python.org/3/library/stdtypes.html#str), [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]
