"""Search facade: local keyword search + remote backend dispatch."""

from skill.base import SkillInfo
from skill.stores import LocalSkillStore
from skill.config import load_config
from skill.registry import Registry
from skill.backends import SkillSource


backends: Registry[SkillSource] = Registry('backends')
"""Registry of remote skill backends (e.g., github, local directories)."""


def _ensure_default_backends() -> None:
    """Lazily register built-in backends on first use."""
    if 'github' not in backends._items and not backends._entry_points_loaded:
        try:
            from skill.backends.github import GitHubSkillSource
            backends.register('github', GitHubSkillSource())
        except Exception:
            pass


def _search_local(
    query: str,
    *,
    max_results: int = 10,
    store: LocalSkillStore | None = None,
) -> list[SkillInfo]:
    """Keyword search over locally installed skills.

    >>> import tempfile; from pathlib import Path
    >>> _search_local('nonexistent', store=LocalSkillStore(root=Path(tempfile.mkdtemp())))
    []
    """
    if store is None:
        store = LocalSkillStore()
    query_lower = query.lower()
    results = []
    for info in store.list_info():
        text = f"{info.name} {info.description}".lower()
        if query_lower in text:
            results.append(info)
            if len(results) >= max_results:
                break
    return results


def _search_remote(
    query: str,
    *,
    backend_names: list[str] | None = None,
    max_results: int = 10,
) -> list[SkillInfo]:
    """Dispatch search to configured remote backends."""
    _ensure_default_backends()
    config = load_config()
    results = []

    for name, source in backends.items():
        if backend_names is not None and name not in backend_names:
            continue
        # Check config for github-specific enable flag
        if name == 'github' and not config.github_enabled:
            continue
        try:
            results.extend(source.search(query, max_results=max_results))
        except Exception:
            pass  # Graceful degradation on network errors

    return results[:max_results]


def search(
    query: str,
    *,
    max_results: int = 10,
    local_only: bool = False,
    backends: list[str] | None = None,
) -> list[SkillInfo]:
    """Search for skills across local index and remote backends.

    With ``local_only=True``, only searches locally installed skills.
    Otherwise, searches both local and remote, with local results first.

    >>> isinstance(search('test', local_only=True, max_results=0), list)
    True
    """
    results = _search_local(query, max_results=max_results)

    if not local_only and len(results) < max_results:
        remaining = max_results - len(results)
        remote = _search_remote(
            query, backend_names=backends, max_results=remaining
        )
        # Deduplicate by canonical_key
        seen = {r.canonical_key for r in results}
        for r in remote:
            if r.canonical_key not in seen:
                results.append(r)
                seen.add(r.canonical_key)
    return results[:max_results]
