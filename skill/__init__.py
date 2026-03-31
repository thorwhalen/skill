"""AI Agent Skill Search and Management.

Simple usage::

    from skill import search, install, create, list_skills, validate

    # Search for skills
    results = search('react best practices', local_only=True)

    # Create a new skill locally
    skill = create('my-skill', description='My custom skill')

    # Validate a skill
    issues = validate('/path/to/skill-dir')

Plugin registries::

    from skill.install import agent_targets
    from skill.translate import translators
    from skill.search import backends
    from skill.create import validators
"""

from skill.search import search
from skill.install import install, uninstall, link_skills
from skill.create import create, scaffold, validate, check_dependencies
from skill.base import Skill, SkillMeta, SkillInfo
from skill.stores import LocalSkillStore
from skill.registry import Registry


def list_skills(
    *,
    agent_target: str | None = None,
    scope: str = "all",
) -> list[SkillInfo]:
    """List locally installed skills, optionally filtered by agent target.

    >>> isinstance(list_skills(), list)
    True
    """
    store = LocalSkillStore()
    infos = store.list_info()
    # Filtering by agent_target is a future enhancement — for now, return all
    return infos


def show(key: str) -> Skill:
    """Read and return a skill by its canonical key.

    Raises KeyError if the skill is not found locally.
    """
    store = LocalSkillStore()
    return store[key]


def sources() -> list[dict]:
    """List registered search backends with their name, homepage, and status.

    >>> isinstance(sources(), list)
    True
    """
    from skill.search import backends, _ensure_default_backends
    from skill.config import load_config

    _ensure_default_backends()
    config = load_config()

    _enable_flags = {
        "github": "github_enabled",
        "smithery": "smithery_enabled",
        "composio": "composio_enabled",
        "awesome-list": "awesome_list_enabled",
        "skillsdirectory": "skillsdirectory_enabled",
    }

    result = []
    for name, source in backends.items():
        flag = _enable_flags.get(name)
        enabled = getattr(config, flag, True) if flag else True
        result.append(
            {
                "name": name,
                "homepage": getattr(source, "homepage", None),
                "enabled": enabled,
            }
        )
    return result
