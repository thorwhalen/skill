# skill.backends.skillsdirectory

SkillsDirectory backend for skill discovery and fetching.

### Classes

| [`SkillsDirectorySource`](#skill.backends.skillsdirectory.SkillsDirectorySource)(\*[, token, http_get])   | SkillSource backed by skillsdirectory.com.   |
|-------------------------------------------------------------------------------------------------|----------------------------------------------|

### *class* skill.backends.skillsdirectory.SkillsDirectorySource(, token=None, http_get=None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

SkillSource backed by skillsdirectory.com.

Requires a `SKILLSDIRECTORY_API_KEY` environment variable or explicit *token*.
Free tier: 100 requests/day.

```pycon
>>> src = SkillsDirectorySource(token="my-key")
>>> src.name
'skillsdirectory'
```

#### search(query, , max_results=10)

Search SkillsDirectory for skills matching *query*.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`SkillInfo`](skill.base.html.md#skill.base.SkillInfo)]
