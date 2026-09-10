# skill.backends.github

GitHub backend for skill discovery and fetching.

### Classes

| [`GitHubSkillSource`](#skill.backends.github.GitHubSkillSource)(\*[, token, http_get])   | SkillSource backed by the GitHub API.   |
|---------------------------------------------------------------------------------------------|-----------------------------------------|

### *class* skill.backends.github.GitHubSkillSource(, token=None, http_get=None)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

SkillSource backed by the GitHub API.

Searches for SKILL.md files via the Code Search API and fetches
skill content via the Contents API.

```pycon
>>> src = GitHubSkillSource()
>>> src.name
'github'
>>> isinstance(src, GitHubSkillSource)
True
```

#### list_repo_skills(owner, repo)

List all skills in a GitHub repo using the Trees API.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`SkillInfo`](skill.base.html.md#skill.base.SkillInfo)]

#### search(query, , max_results=10)

Search GitHub for SKILL.md files matching query.

Uses the Code Search API: `filename:SKILL.md {query}`.

* **Return type:**
  [`list`](https://docs.python.org/3/library/stdtypes.html#list)[[`SkillInfo`](skill.base.html.md#skill.base.SkillInfo)]
