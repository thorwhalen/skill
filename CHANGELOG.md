# Changelog

## [0.1.9] - 2026-06-13

### Added

- feat(skills): adopt canonical gh-skill layout; skill-package-setup as authority ([#5](https://github.com/thorwhalen/skill/pull/5))

## [0.1.8] - 2026-06-04

### Added

- feat(base): preserve unknown/namespaced frontmatter keys on round-trip ([#3](https://github.com/thorwhalen/skill/pull/3))

## [0.1.7] - 2026-05-14

- chore(ci): bump action pins to checkout@v6, setup-uv@v7

## [0.1.6] - 2026-04-14

### Added

- feat: Add audience field to distinguish consumer vs developer skills

## [0.1.5] - 2026-04-02

### Added

- feat: Add 5 AI agent skills for the skill package

## [0.1.4] - 2026-03-31

### Added

- feat: Add new skill backends for Smithery, Composio, Awesome List, and SkillsDirectory

## [0.1.3] - 2026-03-26

### Added

- feat: add sources command, URL display, and dependency checking

## [0.1.2] - 2026-03-26

### Added

- feat: add terminal-friendly formatting for CLI output

## [0.1.1] - 2026-03-26

- added homepage in pyproject
- 0.0.7:
- add docs/* to .gitignore
- 0.0.6:
- 0.0.5:
- None: fix: *.ipynb linguist-documentation in .gitattributes
- 0.0.3
- .gitignore
- 0.0.2

### Added

- feat: add link-skills command and shell completion ([#1](https://github.com/thorwhalen/skill/pull/1))
- feat: full skill package implementation with plugin registry system
- feat: added docs and a convenient  class

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
