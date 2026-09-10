# skill.backends.composio

Composio backend for skill discovery and fetching.

### Classes

| [`ComposioSkillSource`](#skill.backends.composio.ComposioSkillSource)(\*[, token, http_get])   | SkillSource backed by the Composio API (v3).   |
|-----------------------------------------------------------------------------------------------|------------------------------------------------|

### *class* skill.backends.composio.ComposioSkillSource(, token=None, http_get=None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

SkillSource backed by the Composio API (v3).

Requires a `COMPOSIO_API_KEY` environment variable or explicit *token*.

```pycon
>>> src = ComposioSkillSource(token="my-key")
>>> src.name
'composio'
```

#### search(query, , max_results=10)

Search Composio for tools matching *query*.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`SkillInfo`](skill.base.html.md#skill.base.SkillInfo)]
