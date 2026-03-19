"""GitHub backend for skill discovery and fetching."""

import json
import os
import urllib.request
import urllib.error
from collections.abc import Callable
from typing import Any

from skill.base import Skill, SkillInfo, parse_skill_md


_GITHUB_API = 'https://api.github.com'


def _default_http_get(url: str, *, headers: dict | None = None) -> dict | str:
    """Perform an HTTP GET, returning parsed JSON or raw text."""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        data = resp.read().decode('utf-8')
        content_type = resp.headers.get('Content-Type', '')
        if 'json' in content_type:
            return json.loads(data)
        return data


class GitHubSkillSource:
    """SkillSource backed by the GitHub API.

    Searches for SKILL.md files via the Code Search API and fetches
    skill content via the Contents API.

    >>> src = GitHubSkillSource()
    >>> src.name
    'github'
    >>> isinstance(src, GitHubSkillSource)
    True
    """

    name: str = 'github'

    def __init__(
        self,
        *,
        token: str | None = None,
        http_get: Callable[..., Any] | None = None,
    ):
        self._token = token or os.environ.get('GITHUB_TOKEN')
        self._http_get = http_get or _default_http_get

    def _headers(self) -> dict[str, str]:
        h = {'Accept': 'application/vnd.github.v3+json'}
        if self._token:
            h['Authorization'] = f'token {self._token}'
        return h

    def _get(self, url: str) -> Any:
        return self._http_get(url, headers=self._headers())

    def _raw_url(self, owner: str, repo: str, path: str, *, ref: str = 'HEAD') -> str:
        return f'https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}'

    def search(self, query: str, *, max_results: int = 10) -> list[SkillInfo]:
        """Search GitHub for SKILL.md files matching query.

        Uses the Code Search API: ``filename:SKILL.md {query}``.
        """
        q = urllib.request.quote(f'{query} filename:SKILL.md', safe='')
        url = f'{_GITHUB_API}/search/code?q={q}&per_page={max_results}'
        try:
            data = self._get(url)
        except urllib.error.HTTPError:
            return []
        results = []
        for item in data.get('items', []):
            repo = item.get('repository', {})
            owner = repo.get('owner', {}).get('login', '')
            repo_name = repo.get('name', '')
            # Derive skill name from the path
            path = item.get('path', '')
            skill_name = _skill_name_from_path(path) or repo_name
            key = f'{owner}/{skill_name}'
            results.append(
                SkillInfo(
                    canonical_key=key,
                    name=skill_name,
                    description=repo.get('description', '') or '',
                    source='github',
                    url=repo.get('html_url', ''),
                    owner=owner,
                )
            )
        return results

    def __getitem__(self, key: str) -> Skill:
        """Fetch a skill by canonical key.

        Supports ``owner/name`` (assumes repo == name, skill at root) and
        ``owner/repo/name`` (skill in ``skills/{name}/`` or at root).
        """
        parts = key.split('/')
        if len(parts) == 2:
            owner, name = parts
            repo = name
            paths_to_try = ['SKILL.md', f'skills/{name}/SKILL.md']
        elif len(parts) == 3:
            owner, repo, name = parts
            paths_to_try = [
                f'skills/{name}/SKILL.md',
                'SKILL.md',
            ]
        else:
            raise KeyError(f"Invalid key: {key}")

        for path in paths_to_try:
            url = self._raw_url(owner, repo, path)
            try:
                content = self._http_get(url, headers=self._headers())
                if isinstance(content, str):
                    return Skill.from_string(content)
            except urllib.error.HTTPError:
                continue
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        try:
            self[key]
            return True
        except (KeyError, urllib.error.HTTPError):
            return False

    def list_repo_skills(self, owner: str, repo: str) -> list[SkillInfo]:
        """List all skills in a GitHub repo using the Trees API."""
        url = f'{_GITHUB_API}/repos/{owner}/{repo}/git/trees/HEAD?recursive=1'
        try:
            data = self._get(url)
        except urllib.error.HTTPError:
            return []
        results = []
        for item in data.get('tree', []):
            path = item.get('path', '')
            if path.endswith('/SKILL.md') or path == 'SKILL.md':
                name = _skill_name_from_path(path) or repo
                results.append(
                    SkillInfo(
                        canonical_key=f'{owner}/{name}',
                        name=name,
                        description='',
                        source='github',
                        url=f'https://github.com/{owner}/{repo}',
                        owner=owner,
                    )
                )
        return results

    def __repr__(self) -> str:
        return f"{type(self).__name__}(token={'***' if self._token else None})"


def _skill_name_from_path(path: str) -> str | None:
    """Extract skill name from a SKILL.md file path.

    >>> _skill_name_from_path('skills/my-skill/SKILL.md')
    'my-skill'
    >>> _skill_name_from_path('SKILL.md') is None
    True
    >>> _skill_name_from_path('.claude/skills/foo/SKILL.md')
    'foo'
    """
    parts = path.replace('\\', '/').split('/')
    if len(parts) >= 2 and parts[-1] == 'SKILL.md':
        return parts[-2]
    return None
