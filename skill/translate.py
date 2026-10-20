"""Format translators: SKILL.md <-> agent-specific formats."""

import json
import warnings
from collections.abc import Callable

from skill.base import Skill, SkillMeta, parse_frontmatter, _meta_from_dict
from skill.registry import Registry


# ---------------------------------------------------------------------------
# Translator registry
# ---------------------------------------------------------------------------

translators: Registry[Callable[[Skill], str]] = Registry("translators")
"""Registry of format translators (Skill -> target format string)."""

translation_losses: Registry[Callable[[Skill], list[str]]] = Registry(
    "translation_losses"
)
"""Registry of what each lossy format drops (Skill -> lost field names), by format.

The SSOT for lossy down-casts: translators warn from it, and linters (opsward's
portability check) read it without translating anything.
"""


def _dropped(skill: Skill, *, fields: tuple[str, ...]) -> list[str]:
    """Which of *fields* (``allowed-tools``, ``license``, ``resources``) *skill* uses."""
    used = {
        "allowed-tools": bool(skill.meta.allowed_tools),
        "license": bool(skill.meta.license),
        "resources": bool(skill.resources),
    }
    return [
        f"bundled resources ({', '.join(skill.resources)})" if f == "resources" else f
        for f in fields
        if used[f]
    ]


def lost_fields(skill: Skill, *, target_format: str) -> list[str]:
    """What translating *skill* to *target_format* drops; ``[]`` for a lossless format.

    >>> from skill.base import SkillMeta
    >>> s = Skill(meta=SkillMeta(name='t', description='d', license='MIT'), body='x')
    >>> lost_fields(s, target_format='mdc')
    ['license']
    >>> lost_fields(s, target_format='skill.md')
    []
    """
    losses = translation_losses.get(target_format)
    return losses(skill) if losses else []


def _yaml_scalar(value: object) -> str:
    """*value* as a one-line YAML scalar: plain when safe, else a JSON (= YAML) string.

    >>> _yaml_scalar('Lint rules'), _yaml_scalar('a: b'), _yaml_scalar('**/*.py')
    ('Lint rules', '"a: b"', '"**/*.py"')
    """
    text = str(value)
    unsafe = (
        not text
        or text != text.strip()
        or "\n" in text
        or ": " in text
        or " #" in text
        or text[0] in "!&*[]{}|>'\"%@`#,?-:"
    )
    return json.dumps(text) if unsafe else text


def _warn_lossy(skill: Skill, *, target_format: str, label: str) -> None:
    lost = lost_fields(skill, target_format=target_format)
    if lost:
        warnings.warn(
            f"Lossy translation to {label}: dropping {', '.join(lost)}",
            stacklevel=3,
        )


# ---------------------------------------------------------------------------
# SKILL.md -> Cursor .mdc
# ---------------------------------------------------------------------------


def _mdc_globs(globs: object) -> str:
    """*globs* as Cursor writes them: one line, comma-separated, never quoted.

    Cursor's ``.mdc`` frontmatter is not parsed as strict YAML for ``globs``, and
    quoted or bracketed globs are reported not to match, so this field is left
    unquoted (unlike ``description``) and only flattened onto one line.

    >>> _mdc_globs('**/*.py'), _mdc_globs(['*.ts', '*.tsx']), _mdc_globs('*.md,\\n*.txt')
    ('**/*.py', '*.ts, *.tsx', '*.md, *.txt')
    """
    if isinstance(globs, str):
        parts = globs.replace("\n", ",").split(",")
    else:
        parts = [str(g) for g in globs]
    return ", ".join(p.strip() for p in parts if p.strip())


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
    _warn_lossy(skill, target_format="mdc", label=".mdc")

    # Build .mdc frontmatter
    lines = ["---"]
    lines.append(f"description: {_yaml_scalar(skill.meta.description)}")
    # Check for cursor-specific metadata
    globs = skill.meta.metadata.get("cursor.globs")
    if globs:
        lines.append(f"globs: {_mdc_globs(globs)}")
    always_apply = skill.meta.metadata.get("cursor.alwaysApply", "false")
    lines.append(f"alwaysApply: {always_apply}")
    lines.append("---")
    lines.append("")
    lines.append(skill.body)
    return "\n".join(lines)


translators.register("mdc", to_mdc)
translation_losses.register(
    "mdc", lambda s: _dropped(s, fields=("allowed-tools", "license", "resources"))
)


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
    if "globs" in raw_meta:
        metadata["cursor.globs"] = str(raw_meta["globs"])
    if "alwaysApply" in raw_meta:
        metadata["cursor.alwaysApply"] = str(raw_meta["alwaysApply"])

    # Derive name from description (first few words, slugified)
    desc = raw_meta.get("description", "")
    name = "-".join(desc.lower().split()[:3]) or "imported-rule"
    # Clean name to valid chars
    name = "".join(c if c.isalnum() or c == "-" else "-" for c in name).strip("-")

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
    _warn_lossy(skill, target_format="copilot_md", label="copilot-instructions")
    return _md_section(skill)


def _md_section(skill: Skill) -> str:
    """A skill as one ``## name`` section of a shared instructions file."""
    quoted = "\n".join(f"> {line}" for line in skill.meta.description.splitlines())
    return "\n".join([f"## {skill.meta.name}", "", quoted or ">", "", skill.body])


translators.register("copilot_md", to_copilot_instructions)
translation_losses.register(
    "copilot_md", lambda s: _dropped(s, fields=("allowed-tools", "resources"))
)


# ---------------------------------------------------------------------------
# SKILL.md -> Gemini CLI (a section of GEMINI.md)
# ---------------------------------------------------------------------------


def to_gemini_md(skill: Skill) -> str:
    """Translate a Skill to a section of Gemini CLI's ``GEMINI.md``.

    Lossy: the file is always loaded (no progressive disclosure), and
    ``allowed-tools``, ``license`` and bundled resources are dropped.

    >>> from skill.base import SkillMeta
    >>> s = Skill(meta=SkillMeta(name='lint', description='Lint rules'), body='Use ruff.')
    >>> to_gemini_md(s).splitlines()[0]
    '## lint'
    """
    _warn_lossy(skill, target_format="gemini_md", label="GEMINI.md")
    return _md_section(skill)


translators.register("gemini_md", to_gemini_md)
translation_losses.register(
    "gemini_md",
    lambda s: _dropped(s, fields=("allowed-tools", "license", "resources")),
)


# ---------------------------------------------------------------------------
# SKILL.md -> Windsurf rule (.windsurf/rules/<name>.md)
# ---------------------------------------------------------------------------


def to_windsurf_rule(skill: Skill) -> str:
    """Translate a Skill to a Windsurf rule, applied when the model judges it relevant.

    ``metadata`` keys ``windsurf.trigger`` (default ``model_decision``) and
    ``windsurf.globs`` pass through. Lossy: ``allowed-tools``, ``license`` and
    bundled resources are dropped.

    >>> from skill.base import SkillMeta
    >>> s = Skill(meta=SkillMeta(name='lint', description='Lint rules'), body='Use ruff.')
    >>> print(to_windsurf_rule(s))
    ---
    trigger: model_decision
    description: Lint rules
    ---
    <BLANKLINE>
    Use ruff.
    """
    _warn_lossy(skill, target_format="windsurf_md", label="a Windsurf rule")
    meta = skill.meta.metadata
    trigger = meta.get("windsurf.trigger", "model_decision")
    lines = ["---", f"trigger: {_yaml_scalar(trigger)}"]
    lines.append(f"description: {_yaml_scalar(skill.meta.description)}")
    if globs := meta.get("windsurf.globs"):
        lines.append(f"globs: {_yaml_scalar(globs)}")
    lines += ["---", "", skill.body]
    return "\n".join(lines)


translators.register("windsurf_md", to_windsurf_rule)
translation_losses.register(
    "windsurf_md",
    lambda s: _dropped(s, fields=("allowed-tools", "license", "resources")),
)


# ---------------------------------------------------------------------------
# SKILL.md -> Cline rule (.clinerules/<name>.md)
# ---------------------------------------------------------------------------


def to_cline_rule(skill: Skill) -> str:
    """Translate a Skill to a Cline rule file (Markdown; always active).

    ``metadata`` key ``cline.paths`` becomes the ``paths`` frontmatter that makes the
    rule conditional. Lossy: no progressive disclosure, and ``allowed-tools``,
    ``license`` and bundled resources are dropped.

    >>> from skill.base import SkillMeta
    >>> s = Skill(meta=SkillMeta(name='lint', description='Lint rules'), body='Use ruff.')
    >>> to_cline_rule(s).splitlines()[:3]
    ['# lint', '', '> Lint rules']
    """
    _warn_lossy(skill, target_format="clinerules_md", label="a Cline rule")
    body = _md_section(skill).replace("## ", "# ", 1)
    if paths := skill.meta.metadata.get("cline.paths"):
        return f"---\npaths: {_yaml_scalar(paths)}\n---\n\n{body}"
    return body


translators.register("clinerules_md", to_cline_rule)
translation_losses.register(
    "clinerules_md",
    lambda s: _dropped(s, fields=("allowed-tools", "license", "resources")),
)


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
        available = ", ".join(sorted(translators))
        raise ValueError(
            f"Unknown target format: {target_format!r}. Available: {available}"
        )
    return translator(skill)
