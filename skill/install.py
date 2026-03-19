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
    format: str = 'skill.md'
    needs_translation: bool = False

    def format_global_path(self, name: str) -> Path | None:
        if self.global_path is None:
            return None
        return Path(self.global_path.format(home=Path.home(), name=name))

    def format_project_path(self, project: str | Path, name: str) -> Path | None:
        if self.project_path is None:
            return None
        return Path(self.project_path.format(project=project, name=name))


agent_targets: Registry[AgentTarget] = Registry('agent_targets')
"""Registry of agent targets (e.g., claude-code, cursor, copilot)."""

agent_targets.register(
    'claude-code',
    AgentTarget(
        name='claude-code',
        global_path='{home}/.claude/skills/{name}',
        project_path='{project}/.claude/skills/{name}',
        format='skill.md',
    ),
)
agent_targets.register(
    'cursor',
    AgentTarget(
        name='cursor',
        project_path='{project}/.cursor/rules/{name}.mdc',
        format='mdc',
        needs_translation=True,
    ),
)
agent_targets.register(
    'copilot',
    AgentTarget(
        name='copilot',
        project_path='{project}/.github/copilot-instructions.md',
        format='copilot_md',
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
        return 'none'
    if target.is_symlink():
        # Check if it points into our skills dir
        link_target = str(target.resolve())
        from skill.config import skills_dir
        if str(skills_dir()) in link_target:
            return 'our_symlink'
        return 'foreign_symlink'
    if target.is_dir():
        return 'directory'
    return 'file'


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
    if existing == 'our_symlink':
        # Already linked by us — update if source changed
        target.unlink()
    elif existing != 'none':
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
    scope: str = 'project',
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

    if scope == 'project':
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

        if scope == 'project':
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
            if target.format == 'copilot_md':
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
    marker = f'<!-- skill:{skill_name} -->'
    end_marker = f'<!-- /skill:{skill_name} -->'

    if path.exists():
        existing = path.read_text()
        if marker in existing:
            # Replace existing section
            start = existing.index(marker)
            end = existing.index(end_marker) + len(end_marker)
            existing = existing[:start] + existing[end:]
            existing = existing.rstrip() + '\n\n'
        else:
            existing = existing.rstrip() + '\n\n'
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = ''

    path.write_text(f'{existing}{marker}\n{content}\n{end_marker}\n')


def uninstall(
    key: str,
    *,
    agent_targets: list[str] | None = None,
    scope: str = 'project',
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

    if scope == 'project':
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
        if scope == 'project':
            dest = target.format_project_path(project_dir, skill_name)
        else:
            dest = target.format_global_path(skill_name)

        if dest is None:
            continue

        if target.format == 'copilot_md' and dest.exists():
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


def _remove_section(path: Path, skill_name: str) -> None:
    """Remove a skill section from a copilot instructions file."""
    marker = f'<!-- skill:{skill_name} -->'
    end_marker = f'<!-- /skill:{skill_name} -->'
    content = path.read_text()
    if marker in content and end_marker in content:
        start = content.index(marker)
        end = content.index(end_marker) + len(end_marker)
        content = content[:start] + content[end:]
        content = content.strip() + '\n' if content.strip() else ''
        path.write_text(content)
