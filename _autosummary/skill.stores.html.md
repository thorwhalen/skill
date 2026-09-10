# skill.stores

Storage layer: LocalSkillStore and SourcedSkillStore via dol.

### Classes

| [`LocalSkillStore`](#skill.stores.LocalSkillStore)([root])   | Filesystem-backed MutableMapping[str, Skill] over the canonical skills directory.   |
|----------------------------------------------------------------------------|-------------------------------------------------------------------------------------|

### *class* skill.stores.LocalSkillStore(root=None)

Bases: [`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping)

Filesystem-backed MutableMapping[str, Skill] over the canonical skills directory.

Keys are canonical `owner/name` strings. Each skill is stored as a
directory containing `SKILL.md` and optional resource subdirectories.

```pycon
>>> import tempfile
>>> store = LocalSkillStore(root=Path(tempfile.mkdtemp()))
>>> len(store)
0
>>> list(store)
[]
```

#### get_source_meta(key)

Read source metadata for a skill, or empty dict if none.

* **Return type:**
  [`dict`](https://docs.python.org/3/library/stdtypes.html#dict)

#### list_info()

Return SkillInfo for all locally stored skills.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`SkillInfo`](skill.base.html.md#skill.base.SkillInfo)]

#### set_source_meta(key, , url=None, source=None)

Store source metadata (URL, origin) alongside a skill.

* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)
