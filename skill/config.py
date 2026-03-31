"""Configuration management via platformdirs and TOML."""

import sys
from dataclasses import dataclass, field, fields, asdict
from pathlib import Path

import platformdirs

from skill.util import resolve_env_vars, atomic_write

_APP_NAME = "skill"


def data_dir() -> Path:
    """Return the platform-specific data directory for skill.

    >>> isinstance(data_dir(), Path)
    True
    """
    return Path(platformdirs.user_data_dir(_APP_NAME))


def config_dir() -> Path:
    """Return the platform-specific config directory for skill.

    >>> isinstance(config_dir(), Path)
    True
    """
    return Path(platformdirs.user_config_dir(_APP_NAME))


def cache_dir() -> Path:
    """Return the platform-specific cache directory for skill.

    >>> isinstance(cache_dir(), Path)
    True
    """
    return Path(platformdirs.user_cache_dir(_APP_NAME))


def skills_dir() -> Path:
    """Return the canonical skills storage directory.

    >>> skills_dir().name
    'skills'
    """
    return data_dir() / "skills"


def config_path() -> Path:
    """Return the path to the config TOML file.

    >>> config_path().name
    'config.toml'
    """
    return config_dir() / "config.toml"


@dataclass
class SkillConfig:
    """Root configuration schema with sensible defaults for zero-config first run.

    >>> c = SkillConfig()
    >>> c.default_agent_targets
    ['claude-code']
    >>> c.install_method
    'symlink'
    """

    default_agent_targets: list[str] = field(default_factory=lambda: ["claude-code"])
    default_scope: str = "project"
    install_method: str = "symlink"
    ai_provider_model: str = "anthropic:claude-sonnet-4-20250514"
    ai_api_key: str = "$ANTHROPIC_API_KEY"
    github_enabled: bool = True
    smithery_enabled: bool = True
    composio_enabled: bool = True
    awesome_list_enabled: bool = True
    skillsdirectory_enabled: bool = True
    search_cache_ttl: int = 3600


def _load_toml(path: Path) -> dict:
    """Load a TOML file, returning an empty dict if it doesn't exist."""
    if not path.exists():
        return {}
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib
    with open(path, "rb") as f:
        return tomllib.load(f)


def _serialize_toml(data: dict) -> str:
    """Serialize a flat dict to minimal TOML."""
    lines = []
    for k, v in data.items():
        if isinstance(v, bool):
            lines.append(f"{k} = {str(v).lower()}")
        elif isinstance(v, int):
            lines.append(f"{k} = {v}")
        elif isinstance(v, str):
            lines.append(f"{k} = {v!r}")
        elif isinstance(v, list):
            items = ", ".join(repr(i) for i in v)
            lines.append(f"{k} = [{items}]")
    return "\n".join(lines) + "\n"


def load_config(path: Path | None = None) -> SkillConfig:
    """Load config from TOML, falling back to defaults for missing fields.

    >>> c = load_config(Path('/nonexistent/config.toml'))
    >>> c.default_scope
    'project'
    """
    raw = _load_toml(path or config_path())
    # Flatten nested tables (e.g., [defaults] -> prefix with section name)
    flat = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                flat[sub_k] = sub_v
        else:
            flat[k] = v
    # Build config from defaults, overriding with file values
    kwargs = {}
    valid_fields = {f.name for f in fields(SkillConfig)}
    for k, v in flat.items():
        if k in valid_fields:
            kwargs[k] = v
    return SkillConfig(**kwargs)


def save_config(config: SkillConfig, *, path: Path | None = None) -> None:
    """Save config to TOML.

    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as d:
    ...     p = Path(d) / 'config.toml'
    ...     save_config(SkillConfig(), path=p)
    ...     p.exists()
    True
    """
    atomic_write(path or config_path(), _serialize_toml(asdict(config)))
