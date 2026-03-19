"""Format translators: SKILL.md <-> agent-specific formats."""

import warnings
from collections.abc import Callable

from skill.base import Skill, SkillMeta, parse_frontmatter, _meta_from_dict
from skill.registry import Registry


# ---------------------------------------------------------------------------
# Translator registry
# ---------------------------------------------------------------------------

translators: Registry[Callable[[Skill], str]] = Registry('translators')
"""Registry of format translators (Skill -> target format string)."""


# ---------------------------------------------------------------------------
# SKILL.md -> Cursor .mdc
# ---------------------------------------------------------------------------

def to_mdc(skill: Skill) -> str:
    """Translate a Skill to Cursor ``.mdc`` format.

    Lossy: ``allowed-tools``, ``license``, bundled resources, and progressive
    disclosure semantics are lost.

    >>> from skill.base import SkillMeta
    >>> s = Skill(meta=SkillMeta(name='test', description='Test skill'), body='Do stuff.')
    >>> mdc = to_mdc(s)
    >>> 'description: Test skill' in mdc
    True
    >>> 'Do stuff.' in mdc
    True
    """
    lost = []
    if skill.meta.allowed_tools:
        lost.append('allowed-tools')
    if skill.meta.license:
        lost.append('license')
    if skill.resources:
        lost.append(f"bundled resources ({', '.join(skill.resources)})")
    if lost:
        warnings.warn(
            f"Lossy translation to .mdc: dropping {', '.join(lost)}",
            stacklevel=2,
        )

    # Build .mdc frontmatter
    lines = ['---']
    lines.append(f'description: {skill.meta.description}')
    # Check for cursor-specific metadata
    globs = skill.meta.metadata.get('cursor.globs')
    if globs:
        lines.append(f'globs: {globs}')
    always_apply = skill.meta.metadata.get('cursor.alwaysApply', 'false')
    lines.append(f'alwaysApply: {always_apply}')
    lines.append('---')
    lines.append('')
    lines.append(skill.body)
    return '\n'.join(lines)


translators.register('mdc', to_mdc)


def from_mdc(content: str) -> Skill:
    """Import a Cursor ``.mdc`` file as a Skill.

    >>> content = "---\\ndescription: Do things\\nglobs: '*.py'\\nalwaysApply: false\\n---\\n# Rules"
    >>> s = from_mdc(content)
    >>> s.meta.description
    'Do things'
    >>> s.meta.metadata.get('cursor.globs')
    '*.py'
    """
    raw_meta, body = parse_frontmatter(content)
    metadata = {}
    if 'globs' in raw_meta:
        metadata['cursor.globs'] = str(raw_meta['globs'])
    if 'alwaysApply' in raw_meta:
        metadata['cursor.alwaysApply'] = str(raw_meta['alwaysApply'])

    # Derive name from description (first few words, slugified)
    desc = raw_meta.get('description', '')
    name = '-'.join(desc.lower().split()[:3]) or 'imported-rule'
    # Clean name to valid chars
    name = ''.join(c if c.isalnum() or c == '-' else '-' for c in name).strip('-')

    meta = SkillMeta(
        name=name,
        description=desc,
        metadata=metadata,
    )
    return Skill(meta=meta, body=body)


# ---------------------------------------------------------------------------
# SKILL.md -> Copilot instructions
# ---------------------------------------------------------------------------

def to_copilot_instructions(skill: Skill) -> str:
    """Translate a Skill to GitHub Copilot instructions format.

    Produces a Markdown section suitable for appending to
    ``.github/copilot-instructions.md``. Lossy: no frontmatter support
    beyond ``applyTo``, no progressive disclosure, no resources.

    >>> from skill.base import SkillMeta
    >>> s = Skill(meta=SkillMeta(name='lint', description='Lint rules'), body='Use ruff.')
    >>> md = to_copilot_instructions(s)
    >>> '## lint' in md
    True
    >>> 'Use ruff.' in md
    True
    """
    lost = []
    if skill.meta.allowed_tools:
        lost.append('allowed-tools')
    if skill.resources:
        lost.append(f"bundled resources ({', '.join(skill.resources)})")
    if lost:
        warnings.warn(
            f"Lossy translation to copilot-instructions: dropping {', '.join(lost)}",
            stacklevel=2,
        )

    lines = [f'## {skill.meta.name}', '']
    lines.append(f'> {skill.meta.description}')
    lines.append('')
    lines.append(skill.body)
    return '\n'.join(lines)


translators.register('copilot_md', to_copilot_instructions)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def translate(skill: Skill, *, target_format: str) -> str:
    """Translate a Skill to the specified target format.

    >>> from skill.base import SkillMeta
    >>> s = Skill(meta=SkillMeta(name='x', description='y'), body='z')
    >>> 'alwaysApply' in translate(s, target_format='mdc')
    True
    """
    translator = translators.get(target_format)
    if translator is None:
        available = ', '.join(sorted(translators))
        raise ValueError(
            f"Unknown target format: {target_format!r}. "
            f"Available: {available}"
        )
    return translator(skill)
