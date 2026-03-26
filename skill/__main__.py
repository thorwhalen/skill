# PYTHON_ARGCOMPLETE_OK
"""CLI entry point for the skill package.

Usage::

    python -m skill search "react best practices"
    python -m skill create my-skill --description "My custom skill"
    python -m skill validate ./my-skill/
    python -m skill list
    python -m skill link-skills /path/to/project
    python -m skill install-completion
    python -m skill sources
"""

import argh

from skill import search as _search
from skill import install as _install
from skill import uninstall as _uninstall
from skill import create as _create
from skill import list_skills as _list_skills
from skill import validate
from skill import show as _show
from skill import link_skills as _link_skills
from skill import sources as _sources
from skill import check_dependencies
from skill.stores import LocalSkillStore
from skill.completion import install_completion, maybe_hint_completion
from skill.cli_format import (
    format_skill_info_table,
    format_skill,
    format_path_dict,
    format_sources,
)


# ---------------------------------------------------------------------------
# CLI wrappers — call the real function, then format for terminal output
# ---------------------------------------------------------------------------


def search(
    query: str,
    *,
    max_results: int = 10,
    local_only: bool = False,
    backends: list[str] | None = None,
) -> str:
    """Search for skills across local index and remote backends."""
    results = _search(
        query,
        max_results=max_results,
        local_only=local_only,
        backends=backends,
    )
    return format_skill_info_table(results)


def list_skills(
    *,
    agent_target: str | None = None,
    scope: str = "all",
) -> str:
    """List locally installed skills."""
    results = _list_skills(agent_target=agent_target, scope=scope)
    return format_skill_info_table(results)


def show(key: str) -> str:
    """Read and display a skill by its canonical key."""
    skill = _show(key)
    store = LocalSkillStore()
    source_meta = store.get_source_meta(key)
    url = source_meta.get("url")
    dep_warnings = check_dependencies(skill, store=store)
    return format_skill(skill, url=url, dep_warnings=dep_warnings)


def sources() -> str:
    """List registered search backends and their status."""
    return format_sources(_sources())


def install(
    key: str,
    *,
    agent_targets: list[str] | None = None,
    scope: str = "project",
    copy: bool = False,
    force: bool = False,
    project_dir: str | None = None,
) -> str:
    """Install a skill into one or more agent target directories."""
    result = _install(
        key,
        agent_targets=agent_targets,
        scope=scope,
        copy=copy,
        force=force,
        project_dir=project_dir,
    )
    return format_path_dict(result, verb="Installed")


def uninstall(
    key: str,
    *,
    agent_targets: list[str] | None = None,
    scope: str = "project",
    project_dir: str | None = None,
) -> str:
    """Uninstall a skill from agent target directories."""
    result = _uninstall(
        key,
        agent_targets=agent_targets,
        scope=scope,
        project_dir=project_dir,
    )
    return format_path_dict(result, verb="Removed")


def create(
    name: str,
    *,
    description: str = "",
    body: str = "",
    owner: str = "_local",
) -> str:
    """Create a new skill locally."""
    skill = _create(name, description=description, body=body, owner=owner)
    return format_skill(skill)


def link_skills(
    source: str,
    *,
    target: str = "",
    copy: bool = False,
    force: bool = False,
) -> str:
    """Link skills from a directory into agent target directories."""
    result = _link_skills(
        source,
        target=target,
        copy=copy,
        force=force,
    )
    return format_path_dict(result, verb="Linked")


def main():
    maybe_hint_completion()
    argh.dispatch_commands(
        [
            search,
            install,
            uninstall,
            create,
            list_skills,
            validate,
            show,
            link_skills,
            sources,
            install_completion,
        ]
    )


if __name__ == "__main__":
    main()
