"""Smithery backend for skill discovery and fetching."""

import json
import os
import urllib.request
import urllib.error
from collections.abc import Callable
from typing import Any

from skill.base import Skill, SkillInfo, SkillMeta

_SMITHERY_API = "https://api.smithery.ai"


def _default_http_get(url: str, *, headers: dict | None = None) -> dict | str:
    """Perform an HTTP GET, returning parsed JSON or raw text."""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        data = resp.read().decode("utf-8")
        content_type = resp.headers.get("Content-Type", "")
        if "json" in content_type:
            return json.loads(data)
        return data


class SmitherySkillSource:
    """SkillSource backed by the Smithery API.

    Searches the ``/skills`` endpoint for agent skills.  No authentication
    is required for read operations.

    >>> src = SmitherySkillSource()
    >>> src.name
    'smithery'
    """

    name: str = "smithery"
    homepage: str = "https://smithery.ai"

    def __init__(
        self,
        *,
        token: str | None = None,
        http_get: Callable[..., Any] | None = None,
    ):
        self._token = token or os.environ.get("SMITHERY_API_KEY")
        self._http_get = http_get or _default_http_get

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def _get(self, url: str) -> Any:
        return self._http_get(url, headers=self._headers())

    # -- SkillSource interface ------------------------------------------------

    def search(self, query: str, *, max_results: int = 10) -> list[SkillInfo]:
        """Search Smithery for skills matching *query*."""
        q = urllib.request.quote(query, safe="")
        url = f"{_SMITHERY_API}/skills?q={q}&pageSize={max_results}"
        try:
            data = self._get(url)
        except urllib.error.HTTPError:
            return []
        results = []
        for item in data.get("skills", []):
            qname = item.get("qualifiedName", "")
            results.append(
                SkillInfo(
                    canonical_key=qname,
                    name=item.get("displayName", qname.split("/")[-1]),
                    description=item.get("description", ""),
                    source="smithery",
                    url=item.get("gitUrl") or f"https://smithery.ai/skills/{qname}",
                    owner=qname.split("/")[0] if "/" in qname else None,
                )
            )
        return results[:max_results]

    def __getitem__(self, key: str) -> Skill:
        """Fetch a skill by its qualified name (e.g. ``owner/skill-name``).

        Tries to fetch the SKILL.md from the linked git URL first; if that
        fails (or no git URL exists), synthesizes a Skill from API metadata.
        """
        url = f"{_SMITHERY_API}/skills/{key}"
        try:
            data = self._get(url)
        except (urllib.error.HTTPError, Exception):
            raise KeyError(key)

        # Try fetching native SKILL.md from git URL
        git_url = data.get("gitUrl", "")
        if git_url and "github.com" in git_url:
            skill = self._try_fetch_from_github(git_url, key)
            if skill is not None:
                return skill

        # Fall back to synthesized skill from API metadata
        return self._synthesize_skill(data)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        try:
            self[key]
            return True
        except KeyError:
            return False

    # -- Helpers --------------------------------------------------------------

    def _try_fetch_from_github(self, git_url: str, key: str) -> Skill | None:
        """Attempt to fetch SKILL.md from a GitHub repo."""
        # Parse owner/repo from git_url like https://github.com/owner/repo
        parts = git_url.rstrip("/").split("/")
        if len(parts) < 5:
            return None
        owner, repo = parts[3], parts[4]
        # Derive skill name from the key
        skill_name = key.split("/")[-1]
        paths_to_try = [
            f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/SKILL.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/skills/{skill_name}/SKILL.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/main/SKILL.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/main/skills/{skill_name}/SKILL.md",
        ]
        for raw_url in paths_to_try:
            try:
                content = self._http_get(raw_url, headers={})
                if isinstance(content, str):
                    return Skill.from_string(content)
            except (urllib.error.HTTPError, Exception):
                continue
        return None

    @staticmethod
    def _synthesize_skill(data: dict) -> Skill:
        """Create a Skill object from Smithery API metadata."""
        name = data.get("displayName", data.get("qualifiedName", "unknown"))
        description = data.get("description", "")
        body_parts = [f"# {name}", ""]
        if description:
            body_parts.append(description)
            body_parts.append("")
        categories = data.get("categories", [])
        if categories:
            body_parts.append(f"**Categories:** {', '.join(categories)}")
        git_url = data.get("gitUrl")
        if git_url:
            body_parts.append(f"**Source:** {git_url}")
        return Skill(
            meta=SkillMeta(name=name, description=description),
            body="\n".join(body_parts),
        )

    def __repr__(self) -> str:
        return f"SmitherySkillSource(token={'***' if self._token else None})"
