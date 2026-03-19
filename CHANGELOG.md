# Changelog

## 0.1.0 (2026-03-19)

Initial implementation of the `skill` package.

### Added

- **Core data model** (`skill.base`): `Skill`, `SkillMeta`, `SkillInfo` dataclasses and SKILL.md parsing/rendering.
- **Storage layer** (`skill.stores`): `LocalSkillStore` — filesystem-backed `MutableMapping[str, Skill]`.
- **Plugin registry** (`skill.registry`): Generic `Registry[T]` class (a `MutableMapping` with lazy entry point discovery) powering four extension points:
  - `skill.install.agent_targets` — agent target definitions (Claude Code, Cursor, Copilot built-in)
  - `skill.translate.translators` — format translators (`.mdc`, `copilot-instructions.md` built-in)
  - `skill.search.backends` — remote skill sources (GitHub built-in)
  - `skill.create.validators` — pluggable validation rules (4 built-in validators)
- **Installation** (`skill.install`): Symlink/copy skills into agent target directories with format translation. Supports project and global scope.
- **Translation** (`skill.translate`): SKILL.md ↔ Cursor `.mdc` and SKILL.md → Copilot instructions, with lossy-field warnings.
- **Search** (`skill.search`): Local keyword search + remote GitHub Code Search API.
- **Backends** (`skill.backends`): `SkillSource` protocol, `LocalDirSource`, and `GitHubSkillSource` with injectable HTTP client.
- **Creation & validation** (`skill.create`): `create()`, `scaffold()`, `validate()` with registry-based validators.
- **Configuration** (`skill.config`): TOML config via `platformdirs`, zero-config first run, `$ENV_VAR` resolution.
- **AI facade** (`skill.ai`): Optional, lazy-loading AI provider facade (aisuite → anthropic → openai).
- **CLI** (`skill.__main__`): `argh`-based CLI exposing the same functions as the Python API.
- **Entry point support**: Third-party packages can register plugins via `pyproject.toml` entry points under `skill.*` groups.
