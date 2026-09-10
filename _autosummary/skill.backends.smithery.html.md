# skill.backends.smithery

Smithery backend for skill discovery and fetching.

### Classes

| [`SmitherySkillSource`](#skill.backends.smithery.SmitherySkillSource)(\*[, token, http_get])   | SkillSource backed by the Smithery API.   |
|-----------------------------------------------------------------------------------------------|-------------------------------------------|

### *class* skill.backends.smithery.SmitherySkillSource(, token=None, http_get=None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

SkillSource backed by the Smithery API.

Searches the `/skills` endpoint for agent skills.  No authentication
is required for read operations.

```pycon
>>> src = SmitherySkillSource()
>>> src.name
'smithery'
```

#### search(query, , max_results=10)

Search Smithery for skills matching *query*.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`SkillInfo`](skill.base.html.md#skill.base.SkillInfo)]
