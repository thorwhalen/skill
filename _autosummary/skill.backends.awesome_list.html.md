# skill.backends.awesome_list

Awesome-claude-skills curated list backend for skill discovery.

### Classes

| [`AwesomeListSource`](#skill.backends.awesome_list.AwesomeListSource)(\*[, http_get])   | SkillSource backed by the awesome-claude-skills curated list.   |
|--------------------------------------------------------------------------------------|-----------------------------------------------------------------|

### *class* skill.backends.awesome_list.AwesomeListSource(, http_get=None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

SkillSource backed by the awesome-claude-skills curated list.

Fetches and parses the README from
`github.com/travisvn/awesome-claude-skills`.

```pycon
>>> src = AwesomeListSource()
>>> src.name
'awesome-list'
```

#### search(query, , max_results=10)

Search the curated list for skills matching *query*.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`SkillInfo`](skill.base.html.md#skill.base.SkillInfo)]
