"""Terminal-friendly formatting for CLI output."""

import os
import shutil

from skill.base import Skill, SkillInfo


def _terminal_width(default: int = 80) -> int:
    """Get terminal width, with a sensible fallback."""
    return shutil.get_terminal_size((default, 24)).columns


def _truncate(text: str, width: int) -> str:
    """Truncate text to width, adding ellipsis if needed."""
    if len(text) <= width:
        return text
    return text[: width - 1] + '…'


# ---------------------------------------------------------------------------
# SkillInfo formatting
# ---------------------------------------------------------------------------

def format_skill_info(info: SkillInfo) -> str:
    """Format a single SkillInfo as a compact one-liner.

    >>> si = SkillInfo('owner/test', 'test', 'A test skill', 'local', installed=True)
    >>> '✓' in format_skill_info(si)
    True
    """
    marker = '✓' if info.installed else ' '
    return f"{marker} {info.canonical_key}  {info.description}  ({info.source})"


def format_skill_info_table(items: list[SkillInfo]) -> str:
    """Format a list of SkillInfo as an aligned, readable table.

    Returns an empty string if items is empty.

    >>> items = [
    ...     SkillInfo('alice/lint', 'lint', 'Lint Python code', 'local', installed=True),
    ...     SkillInfo('bob/react-tips', 'react-tips', 'React best practices guide', 'github',
    ...               url='https://github.com/bob/react-tips'),
    ... ]
    >>> out = format_skill_info_table(items)
    >>> '✓' in out and 'alice/lint' in out
    True
    """
    if not items:
        return '  (no results)'

    term_width = _terminal_width()

    # Compute column widths from data
    key_width = max(len(i.canonical_key) for i in items)
    source_width = max(len(i.source) for i in items)

    # Description gets whatever space remains
    #   layout: "M KEY  DESC  (SOURCE)"
    #   M = 1 char marker, 1 space, KEY, 2 spaces, DESC, 2 spaces, (SOURCE)
    fixed = 1 + 1 + key_width + 2 + 2 + source_width + 2  # parens
    desc_width = max(20, term_width - fixed)

    lines = []
    for info in items:
        marker = '✓' if info.installed else ' '
        key = info.canonical_key.ljust(key_width)
        desc = _truncate(info.description, desc_width).ljust(desc_width)
        source = info.source
        lines.append(f"{marker} {key}  {desc}  ({source})")

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Skill (show) formatting
# ---------------------------------------------------------------------------

def format_skill(skill: Skill) -> str:
    """Format a full Skill for terminal display."""
    m = skill.meta
    lines = [
        f"Name:          {m.name}",
        f"Description:   {m.description}",
    ]
    if m.license:
        lines.append(f"License:       {m.license}")
    if m.compatibility:
        lines.append(f"Compatibility: {m.compatibility}")
    if skill.source_path:
        lines.append(f"Path:          {skill.source_path}")
    if skill.resources:
        res_parts = ', '.join(
            f"{k} ({len(v)})" for k, v in skill.resources.items()
        )
        lines.append(f"Resources:     {res_parts}")
    if m.allowed_tools:
        lines.append(f"Tools:         {', '.join(m.allowed_tools)}")

    # Body preview
    body = skill.body.strip()
    if body:
        lines.append('')
        lines.append(body)

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Dict[str, Path] formatting (install / uninstall / link_skills)
# ---------------------------------------------------------------------------

def format_path_dict(d: dict, *, verb: str = 'Installed') -> str:
    """Format a {name: path} dict as readable output.

    >>> from pathlib import Path
    >>> out = format_path_dict({'claude-code': Path('/a/b')}, verb='Installed')
    >>> 'claude-code' in out
    True
    """
    if not d:
        return '  (none)'

    key_width = max(len(k) for k in d)
    lines = []
    for name, path in d.items():
        lines.append(f"  {name.ljust(key_width)}  → {path}")
    return '\n'.join(lines)
