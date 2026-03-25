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
from skill.create import create, scaffold, validate
from skill.base import Skill, SkillMeta, SkillInfo
from skill.stores import LocalSkillStore
from skill.registry import Registry


def list_skills(
    *,
    agent_target: str | None = None,
    scope: str = 'all',
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
