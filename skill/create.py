"""Skill scaffolding, validation, and creation."""

from collections.abc import Callable
from pathlib import Path

from skill.base import Skill, SkillMeta, parse_frontmatter
from skill.stores import LocalSkillStore
from skill.util import ParsedKey
from skill.registry import Registry


# ---------------------------------------------------------------------------
# Validator registry
# ---------------------------------------------------------------------------

validators: Registry[Callable[[Skill], list[str]]] = Registry('validators')
"""Registry of validation rules. Each validator is a ``(Skill) -> list[str]``
callable that returns a list of issue strings (empty = pass)."""


def _validate_required_fields(skill: Skill) -> list[str]:
    """Check that name and description are present.

    >>> from skill.base import SkillMeta
    >>> _validate_required_fields(Skill(meta=SkillMeta(name='', description='x'), body='y'))
    ["Missing or empty 'name' in frontmatter"]
    """
    issues = []
    if not skill.meta.name:
        issues.append("Missing or empty 'name' in frontmatter")
    if not skill.meta.description:
        issues.append("Missing or empty 'description' in frontmatter")
    return issues


validators.register('required_fields', _validate_required_fields)


def _validate_body(skill: Skill) -> list[str]:
    """Check that body is not empty.

    >>> from skill.base import SkillMeta
    >>> _validate_body(Skill(meta=SkillMeta(name='x', description='y'), body='  '))
    ['Skill body is empty']
    """
    if not skill.body.strip():
        return ['Skill body is empty']
    return []


validators.register('body', _validate_body)


def _validate_name_format(skill: Skill) -> list[str]:
    """Check that name matches the spec: ``^[a-z0-9]+(-[a-z0-9]+)*$``.

    >>> from skill.base import SkillMeta
    >>> _validate_name_format(Skill(meta=SkillMeta(name='BadName', description='x'), body='y'))
    ["Invalid name: 'BadName'. Must be lowercase alphanumeric with hyphens."]
    """
    if not skill.meta.name:
        return []  # Handled by required_fields validator
    if not _is_valid_name(skill.meta.name):
        return [
            f"Invalid name: {skill.meta.name!r}. "
            "Must be lowercase alphanumeric with hyphens."
        ]
    return []


validators.register('name_format', _validate_name_format)


def _validate_lengths(skill: Skill) -> list[str]:
    """Check name and description length limits.

    >>> from skill.base import SkillMeta
    >>> _validate_lengths(Skill(meta=SkillMeta(name='x' * 65, description='y'), body='z'))
    ['Name exceeds 64 characters (65)']
    """
    issues = []
    if len(skill.meta.name) > 64:
        issues.append(f"Name exceeds 64 characters ({len(skill.meta.name)})")
    if len(skill.meta.description) > 1024:
        issues.append(
            f"Description exceeds 1024 characters ({len(skill.meta.description)})"
        )
    return issues


validators.register('lengths', _validate_lengths)


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

_TEMPLATE_BODY = """\
# {name}

{description}

## Usage

<!-- Describe how this skill should be used -->

## Instructions

<!-- Add your skill instructions here -->
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create(
    name: str,
    *,
    description: str = '',
    body: str = '',
    owner: str = '_local',
    store: LocalSkillStore | None = None,
) -> Skill:
    """Create a new skill and store it locally.

    >>> import tempfile
    >>> from pathlib import Path
    >>> store = LocalSkillStore(root=Path(tempfile.mkdtemp()))
    >>> s = create('my-skill', description='Does things', store=store)
    >>> s.meta.name
    'my-skill'
    >>> '_local/my-skill' in store
    True
    """
    if store is None:
        store = LocalSkillStore()
    if not body:
        body = _TEMPLATE_BODY.format(name=name, description=description)
    meta = SkillMeta(name=name, description=description)
    skill = Skill(meta=meta, body=body)
    key = str(ParsedKey(owner=owner, name=name))
    store[key] = skill
    return skill


def scaffold(
    name: str,
    *,
    description: str | None = None,
    path: Path | None = None,
) -> Path:
    """Generate a new skill folder with boilerplate SKILL.md.

    >>> import tempfile
    >>> p = scaffold('demo-skill', path=Path(tempfile.mkdtemp()) / 'demo-skill')
    >>> (p / 'SKILL.md').exists()
    True
    """
    if path is None:
        path = Path.cwd() / name
    desc = description or f'A skill for {name}'
    body = _TEMPLATE_BODY.format(name=name, description=desc)
    skill = Skill(meta=SkillMeta(name=name, description=desc), body=body)
    skill.write_to(path)
    # Create optional resource subdirectories
    (path / 'scripts').mkdir(exist_ok=True)
    (path / 'references').mkdir(exist_ok=True)
    return path


def validate(path_or_key: str) -> list[str]:
    """Validate a skill, returning a list of issue strings (empty = valid).

    Runs all registered validators. Accepts a filesystem path to a skill
    directory, or a canonical key to look up in the local store.

    >>> import tempfile
    >>> from skill.base import Skill, SkillMeta
    >>> d = Path(tempfile.mkdtemp()) / 'test'
    >>> Skill(meta=SkillMeta(name='test', description='OK'), body='body').write_to(d)
    >>> validate(str(d))
    []
    >>> d2 = Path(tempfile.mkdtemp()) / 'bad'
    >>> Skill(meta=SkillMeta(name='', description=''), body='').write_to(d2)
    >>> issues = validate(str(d2))
    >>> any('name' in i for i in issues)
    True
    """
    # Resolve path or key to a Skill
    path = Path(path_or_key)
    if path.is_dir():
        skill_md = path / 'SKILL.md'
        if not skill_md.exists():
            return [f"Missing SKILL.md in {path}"]
        skill = Skill.from_path(path)
    else:
        store = LocalSkillStore()
        try:
            skill = store[path_or_key]
        except KeyError:
            return [f"Not a valid path or skill key: {path_or_key}"]

    return _validate_skill(skill)


def _validate_skill(skill: Skill) -> list[str]:
    """Run all registered validators against a Skill."""
    issues = []
    for validator in validators.values():
        issues.extend(validator(skill))
    return issues


def _is_valid_name(name: str) -> bool:
    """Check if a skill name matches the spec: ``^[a-z0-9]+(-[a-z0-9]+)*$``.

    >>> _is_valid_name('my-skill')
    True
    >>> _is_valid_name('MySkill')
    False
    >>> _is_valid_name('')
    False
    """
    import re
    return bool(re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name))
