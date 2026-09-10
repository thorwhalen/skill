# skill.search

### skill.search(query, , max_results=10, local_only=False, backends=None)

Search for skills across local index and remote backends.

With `local_only=True`, only searches locally installed skills.
Otherwise, searches both local and remote, with local results first.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`SkillInfo`](skill.base.html.md#skill.base.SkillInfo)]

```pycon
>>> isinstance(search('test', local_only=True, max_results=0), list)
True
```
