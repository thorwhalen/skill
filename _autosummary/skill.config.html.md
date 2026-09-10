# skill.config

Configuration management via platformdirs and TOML.

### Functions

| [`cache_dir`](#skill.config.cache_dir)()                     | Return the platform-specific cache directory for skill.             |
|----------------------------------------------------------------------------------|---------------------------------------------------------------------|
| [`config_dir`](#skill.config.config_dir)()                    | Return the platform-specific config directory for skill.            |
| [`config_path`](#skill.config.config_path)()                   | Return the path to the config TOML file.                            |
| [`data_dir`](#skill.config.data_dir)()                      | Return the platform-specific data directory for skill.              |
| [`load_config`](#skill.config.load_config)([path])             | Load config from TOML, falling back to defaults for missing fields. |
| [`save_config`](#skill.config.save_config)(config, \*[, path]) | Save config to TOML.                                                |
| [`skills_dir`](#skill.config.skills_dir)()                    | Return the canonical skills storage directory.                      |

### Classes

| [`SkillConfig`](#skill.config.SkillConfig)([default_agent_targets, ...])   | Root configuration schema with sensible defaults for zero-config first run.   |
|----------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|

### *class* skill.config.SkillConfig(default_agent_targets=<factory>, default_scope='project', install_method='symlink', ai_provider_model='anthropic:claude-sonnet-4-20250514', ai_api_key='$ANTHROPIC_API_KEY', github_enabled=True, smithery_enabled=True, composio_enabled=True, awesome_list_enabled=True, skillsdirectory_enabled=True, search_cache_ttl=3600)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Root configuration schema with sensible defaults for zero-config first run.

```pycon
>>> c = SkillConfig()
>>> c.default_agent_targets
['claude-code']
>>> c.install_method
'symlink'
```

### skill.config.cache_dir()

Return the platform-specific cache directory for skill.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

```pycon
>>> isinstance(cache_dir(), Path)
True
```

### skill.config.config_dir()

Return the platform-specific config directory for skill.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

```pycon
>>> isinstance(config_dir(), Path)
True
```

### skill.config.config_path()

Return the path to the config TOML file.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

```pycon
>>> config_path().name
'config.toml'
```

### skill.config.data_dir()

Return the platform-specific data directory for skill.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

```pycon
>>> isinstance(data_dir(), Path)
True
```

### skill.config.load_config(path=None)

Load config from TOML, falling back to defaults for missing fields.

* **Return type:**
  [`SkillConfig`](#skill.config.SkillConfig)

```pycon
>>> c = load_config(Path('/nonexistent/config.toml'))
>>> c.default_scope
'project'
```

### skill.config.save_config(config, , path=None)

Save config to TOML.

* **Return type:**
  [`None`](https://docs.python.org/3/library/constants.html#None)

```pycon
>>> import tempfile
>>> with tempfile.TemporaryDirectory() as d:
...     p = Path(d) / 'config.toml'
...     save_config(SkillConfig(), path=p)
...     p.exists()
True
```

### skill.config.skills_dir()

Return the canonical skills storage directory.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

```pycon
>>> skills_dir().name
'skills'
```
