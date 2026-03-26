"""Installation logic: symlink/copy skills into agent target directories."""

import os
import shutil
import warnings
from dataclasses import dataclass
from pathlib import Path

from skill.base import Skill
from skill.stores import LocalSkillStore
from skill.translate import translators
from skill.util import find_project_root
from skill.config import load_config
from skill.registry import Registry
from skill.create import _validate_skill


# ---------------------------------------------------------------------------
# Agent target registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentTarget:
    """Describes where an agent expects skills to be installed.

    Path templates support ``{home}``, ``{project}``, and ``{name}`` placeholders.

    >>> str(AgentTarget(name='test', project_path='{project}/.test/{name}').format_project_path('/proj', 'my-skill'))
    '/proj/.test/my-skill'
    """

    name: str
    global_path: str | None = None
    project_path: str | None = None
    format: str = "skill.md"
    needs_translation: bool = False

    def format_global_path(self, name: str) -> Path | None:
        if self.global_path is None:
            return None
        return Path(self.global_path.format(home=Path.home(), name=name))

    def format_project_path(self, project: str | Path, name: str) -> Path | None:
        if self.project_path is None:
            return None
        return Path(self.project_path.format(project=project, name=name))


agent_targets: Registry[AgentTarget] = Registry("agent_targets")
"""Registry of agent targets (e.g., claude-code, cursor, copilot)."""

agent_targets.register(
    "claude-code",
    AgentTarget(
        name="claude-code",
        global_path="{home}/.claude/skills/{name}",
        project_path="{project}/.claude/skills/{name}",
        format="skill.md",
    ),
)
agent_targets.register(
    "cursor",
    AgentTarget(
        name="cursor",
        project_path="{project}/.cursor/rules/{name}.mdc",
        format="mdc",
        needs_translation=True,
    ),
)
agent_targets.register(
    "copilot",
    AgentTarget(
        name="copilot",
        project_path="{project}/.github/copilot-instructions.md",
        format="copilot_md",
        needs_translation=True,
    ),
)

# Keep AGENT_TARGETS as a backward-compatible alias
AGENT_TARGETS = agent_targets


# ---------------------------------------------------------------------------
# Link/copy helpers
# ---------------------------------------------------------------------------


def _check_existing(target: Path) -> str:
    """Classify what currently exists at ``target``.

    Returns one of: ``'none'``, ``'our_symlink'``, ``'foreign_symlink'``,
    ``'directory'``, ``'file'``.

    >>> _check_existing(Path('/nonexistent/path/abc'))
    'none'
    """
    if not target.exists() and not target.is_symlink():
        return "none"
    if target.is_symlink():
        # Check if it points into our skills dir
        link_target = str(target.resolve())
        from skill.config import skills_dir

        if str(skills_dir()) in link_target:
            return "our_symlink"
        return "foreign_symlink"
    if target.is_dir():
        return "directory"
    return "file"


def _create_link(
    source: Path,
    target: Path,
    *,
    copy: bool = False,
    force: bool = False,
) -> Path:
    """Create a symlink (or copy) from ``target`` pointing to ``source``.

    On Windows, uses a directory junction instead of symlink.
    """
    existing = _check_existing(target)
    if existing == "our_symlink":
        # Already linked by us — update if source changed
        target.unlink()
    elif existing != "none":
        if not force:
            raise FileExistsError(
                f"Target already exists ({existing}): {target}. "
                f"Use force=True to overwrite."
            )
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)

    target.parent.mkdir(parents=True, exist_ok=True)

    if copy:
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    else:
        os.symlink(source, target)

    return target


# ---------------------------------------------------------------------------
# Install / uninstall
# ---------------------------------------------------------------------------


def install(
    key: str,
    *,
    agent_targets: list[str] | None = None,
    scope: str = "project",
    copy: bool = False,
    force: bool = False,
    project_dir: Path | str | None = None,
    store: LocalSkillStore | None = None,
) -> dict[str, Path]:
    """Install a skill into one or more agent target directories.

    Returns a dict mapping agent target names to the paths where the skill
    was installed.

    Parameters
    ----------
    key : str
        Canonical skill key (e.g., ``'owner/skill-name'``).
    agent_targets : list[str] | None
        Agent targets to install into. Defaults to config's ``default_agent_targets``.
    scope : str
        ``'project'`` (default) or ``'global'``.
    copy : bool
        If True, copy instead of symlink.
    force : bool
        If True, overwrite existing files/links.
    project_dir : Path | str | None
        Project root. Auto-detected if None.
    store : LocalSkillStore | None
        Skill store to read from. Uses default if None.
    """
    if store is None:
        store = LocalSkillStore()

    if key not in store:
        raise KeyError(f"Skill {key!r} not found in local store. Fetch it first.")

    skill = store[key]
    config = load_config()
    targets = agent_targets or config.default_agent_targets

    if scope == "project":
        if project_dir is None:
            project_dir = find_project_root()
        if project_dir is None:
            raise RuntimeError(
                "Could not detect project root. Pass project_dir explicitly "
                "or run from within a project directory."
            )
        project_dir = Path(project_dir)

    installed = {}
    for target_name in targets:
        target = AGENT_TARGETS.get(target_name)
        if target is None:
            warnings.warn(f"Unknown agent target: {target_name!r}", stacklevel=2)
            continue

        skill_name = skill.meta.name

        if scope == "project":
            dest = target.format_project_path(project_dir, skill_name)
        else:
            dest = target.format_global_path(skill_name)

        if dest is None:
            warnings.warn(
                f"Agent target {target_name!r} has no {scope} path",
                stacklevel=2,
            )
            continue

        if target.needs_translation:
            # Write translated content as a file
            translator = translators.get(target.format)
            if translator is None:
                warnings.warn(
                    f"No translator for format {target.format!r}", stacklevel=2
                )
                continue
            content = translator(skill)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if target.format == "copilot_md":
                # Copilot: append to the instructions file
                _append_or_create(dest, content, skill_name)
            else:
                dest.write_text(content)
            installed[target_name] = dest
        else:
            # Symlink/copy the skill directory
            source = skill.source_path or store._key_to_path(key)
            _create_link(source, dest, copy=copy, force=force)
            installed[target_name] = dest

    return installed


def _append_or_create(path: Path, content: str, skill_name: str) -> None:
    """Append content to a file, or create it. Avoids duplicates by skill name."""
    marker = f"<!-- skill:{skill_name} -->"
    end_marker = f"<!-- /skill:{skill_name} -->"

    if path.exists():
        existing = path.read_text()
        if marker in existing:
            # Replace existing section
            start = existing.index(marker)
            end = existing.index(end_marker) + len(end_marker)
            existing = existing[:start] + existing[end:]
            existing = existing.rstrip() + "\n\n"
        else:
            existing = existing.rstrip() + "\n\n"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = ""

    path.write_text(f"{existing}{marker}\n{content}\n{end_marker}\n")


def uninstall(
    key: str,
    *,
    agent_targets: list[str] | None = None,
    scope: str = "project",
    project_dir: Path | str | None = None,
    store: LocalSkillStore | None = None,
) -> dict[str, Path]:
    """Remove a skill's installation from agent target directories.

    Returns a dict mapping agent target names to the paths that were removed.
    """
    if store is None:
        store = LocalSkillStore()

    if key not in store:
        raise KeyError(f"Skill {key!r} not found in local store.")

    skill = store[key]
    config = load_config()
    targets = agent_targets or config.default_agent_targets

    if scope == "project":
        if project_dir is None:
            project_dir = find_project_root()
        if project_dir is None:
            raise RuntimeError("Could not detect project root.")
        project_dir = Path(project_dir)

    removed = {}
    for target_name in targets:
        target = AGENT_TARGETS.get(target_name)
        if target is None:
            continue

        skill_name = skill.meta.name
        if scope == "project":
            dest = target.format_project_path(project_dir, skill_name)
        else:
            dest = target.format_global_path(skill_name)

        if dest is None:
            continue

        if target.format == "copilot_md" and dest.exists():
            # Remove the section from copilot instructions
            _remove_section(dest, skill_name)
            removed[target_name] = dest
        elif dest.exists() or dest.is_symlink():
            if dest.is_symlink() or dest.is_file():
                dest.unlink()
            elif dest.is_dir():
                shutil.rmtree(dest)
            removed[target_name] = dest

    return removed


# ---------------------------------------------------------------------------
# Link skills from a source directory
# ---------------------------------------------------------------------------

_SKILL_MARKER = "SKILL.md"


def _has_skills(directory: Path) -> bool:
    """Return True if ``directory`` contains at least one skill subdirectory."""
    if not directory.is_dir():
        return False
    return any(
        child.is_dir() and (child / _SKILL_MARKER).exists()
        for child in directory.iterdir()
    )


def _resolve_skills_source(source: Path) -> Path:
    """Find the actual skills directory given a path that might be a project root.

    Resolution order:

    1. If ``source`` itself contains skill subdirectories, use it directly.
    2. If ``source/.claude/skills`` exists and contains skills, use that.
    3. If ``source/{pkg}/data/skills`` exists for some package ``pkg`` (detected
       via ``pyproject.toml``), use that.
    4. Fall back to ``source`` as-is (will yield nothing if no skills found).
    """
    # 1. Direct: source already contains skill subdirs
    if _has_skills(source):
        return source

    # 2. .claude/skills convention
    claude_skills = source / ".claude" / "skills"
    if _has_skills(claude_skills):
        return claude_skills

    # 3. {pkg}/data/skills convention (Python projects)
    pyproject = source / "pyproject.toml"
    if pyproject.exists():
        # Infer package name from the directory name (common convention)
        pkg_name = source.name.replace("-", "_")
        pkg_skills = source / pkg_name / "data" / "skills"
        if _has_skills(pkg_skills):
            return pkg_skills

    return source


def _iter_skill_dirs(source: Path):
    """Yield ``(name, path)`` for each skill directory found under ``source``.

    A skill directory is any immediate subdirectory containing a ``SKILL.md``.
    """
    if not source.is_dir():
        raise NotADirectoryError(f"Not a directory: {source}")
    for child in sorted(source.iterdir()):
        if child.is_dir() and (child / _SKILL_MARKER).exists():
            yield child.name, child


# ---------------------------------------------------------------------------
# Target validation
# ---------------------------------------------------------------------------


def _known_target_parents() -> set[Path]:
    """Return the set of resolved parent directories for all known agent targets.

    For example, ``~/.claude/skills`` for claude-code global,
    ``.cursor/rules`` for cursor project, etc.
    """
    parents = set()
    home = str(Path.home())
    for target in AGENT_TARGETS.values():
        if target.global_path is not None:
            # Format with a dummy name, then take the parent
            p = Path(target.global_path.format(home=home, name="_dummy"))
            parents.add(p.parent)
    return parents


def _is_recognized_target(target_path: Path) -> bool:
    """Check whether ``target_path`` is a recognized skills target directory.

    Recognized if:
    - It matches a known agent target parent directory (e.g. ~/.claude/skills).
    - It already contains at least one skill subdirectory (existing skills dir).
    - It is empty or does not yet exist (fresh target — allow it).
    """
    resolved = target_path.resolve()

    # Known agent target directories
    if resolved in _known_target_parents():
        return True

    # Doesn't exist yet or is empty — safe to create into
    if not resolved.exists():
        return True
    if resolved.is_dir() and not any(resolved.iterdir()):
        return True

    # Already contains skills — it's a skills directory
    if _has_skills(resolved):
        return True

    return False


def link_skills(
    source: str,
    *,
    target: str = "",
    copy: bool = False,
    force: bool = False,
) -> dict[str, Path]:
    """Symlink (or copy) every skill found under ``source`` into ``target``.

    ``source`` can be a skills directory directly, a project root (will look
    for ``.claude/skills/`` or ``{pkg}/data/skills/``), or any directory
    containing skill subdirectories (each with a ``SKILL.md``).

    Each candidate skill is validated before linking. Skills with validation
    errors are skipped and a warning is emitted.

    The ``target`` directory is checked against known agent target directories.
    If it doesn't match a recognized target, a ``ValueError`` is raised (unless
    it's empty or already contains skills).

    Returns a dict mapping skill names to their installed paths.

    Parameters
    ----------
    source : str
        A skills directory, or a project root containing skills.
    target : str
        Destination directory. Defaults to ``~/.claude/skills``.
    copy : bool
        If True, copy instead of symlink.
    force : bool
        If True, overwrite existing files/links at the destination.
    """
    source_path = _resolve_skills_source(Path(source).resolve())
    if target:
        target_path = Path(target).expanduser().resolve()
    else:
        target_path = Path.home() / ".claude" / "skills"

    if not _is_recognized_target(target_path):
        raise ValueError(
            f"Target directory {target_path} is not a recognized skills "
            f"target. Known targets: "
            f"{', '.join(str(p) for p in sorted(_known_target_parents()))}. "
            f"The target must be a known agent skills directory, an empty "
            f"directory, or a directory already containing skills."
        )

    installed = {}
    for name, skill_dir in _iter_skill_dirs(source_path):
        skill = Skill.from_path(skill_dir)
        issues = _validate_skill(skill)
        if issues:
            warnings.warn(
                f"Skipping invalid skill {name!r} at {skill_dir}: " + "; ".join(issues),
                stacklevel=2,
            )
            continue
        dest = target_path / name
        _create_link(skill_dir, dest, copy=copy, force=force)
        installed[name] = dest

    return installed


def _remove_section(path: Path, skill_name: str) -> None:
    """Remove a skill section from a copilot instructions file."""
    marker = f"<!-- skill:{skill_name} -->"
    end_marker = f"<!-- /skill:{skill_name} -->"
    content = path.read_text()
    if marker in content and end_marker in content:
        start = content.index(marker)
        end = content.index(end_marker) + len(end_marker)
        content = content[:start] + content[end:]
        content = content.strip() + "\n" if content.strip() else ""
        path.write_text(content)
