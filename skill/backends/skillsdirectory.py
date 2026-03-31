"""SkillsDirectory backend for skill discovery and fetching."""

import json
import os
import urllib.request
import urllib.error
from collections.abc import Callable
from typing import Any

from skill.base import Skill, SkillInfo, SkillMeta

_SKILLSDIR_API = "https://www.skillsdirectory.com"


def _default_http_get(url: str, *, headers: dict | None = None) -> dict | str:
    """Perform an HTTP GET, returning parsed JSON or raw text."""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        data = resp.read().decode("utf-8")
        content_type = resp.headers.get("Content-Type", "")
        if "json" in content_type:
            return json.loads(data)
        return data


class SkillsDirectorySource:
    """SkillSource backed by skillsdirectory.com.

    Requires a ``SKILLSDIRECTORY_API_KEY`` environment variable or explicit *token*.
    Free tier: 100 requests/day.

    >>> src = SkillsDirectorySource(token="my-key")
    >>> src.name
    'skillsdirectory'
    """

    name: str = "skillsdirectory"
    homepage: str = "https://www.skillsdirectory.com"

    def __init__(
        self,
        *,
        token: str | None = None,
        http_get: Callable[..., Any] | None = None,
    ):
        self._token = token or os.environ.get("SKILLSDIRECTORY_API_KEY")
        if not self._token:
            raise ValueError(
                "SkillsDirectory requires an API key. "
                "Set SKILLSDIRECTORY_API_KEY or pass token= to SkillsDirectorySource. "
                "Sign up at https://www.skillsdirectory.com/login?next=/developer/keys"
            )
        self._http_get = http_get or _default_http_get

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self._token}

    def _get(self, url: str) -> Any:
        return self._http_get(url, headers=self._headers())

    # -- SkillSource interface ------------------------------------------------

    def search(self, query: str, *, max_results: int = 10) -> list[SkillInfo]:
        """Search SkillsDirectory for skills matching *query*."""
        q = urllib.request.quote(query, safe="")
        url = f"{_SKILLSDIR_API}/api/v1/skills?q={q}&limit={max_results}"
        try:
            data = self._get(url)
        except urllib.error.HTTPError:
            return []
        results = []
        for item in data.get("skills", []):
            slug = item.get("slug", "")
            author = item.get("author", "")
            canonical_key = f"{author}/{slug}" if author else slug
            results.append(
                SkillInfo(
                    canonical_key=canonical_key,
                    name=item.get("name", slug),
                    description=item.get("description", ""),
                    source="skillsdirectory",
                    url=item.get("url", f"{_SKILLSDIR_API}/skills/{slug}"),
                    owner=author or None,
                )
            )
        return results[:max_results]

    def __getitem__(self, key: str) -> Skill:
        """Fetch a skill by key (e.g. ``author/slug``).

        If the API response includes a ``content`` field (SKILL.md text),
        it is parsed directly.  Otherwise a Skill is synthesized from metadata.
        """
        parts = key.split("/", 1)
        slug = parts[-1]
        url = f"{_SKILLSDIR_API}/api/v1/skills/{slug}"
        try:
            data = self._get(url)
        except (urllib.error.HTTPError, Exception):
            raise KeyError(key)

        # If content is available, parse it as SKILL.md
        content = data.get("content")
        if content:
            return Skill.from_string(content)

        # Otherwise synthesize from metadata
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

    @staticmethod
    def _synthesize_skill(data: dict) -> Skill:
        """Create a Skill object from SkillsDirectory metadata."""
        name = data.get("name", data.get("slug", "unknown"))
        description = data.get("description", "")
        body_parts = [f"# {name}", ""]
        if description:
            body_parts.append(description)
            body_parts.append("")
        author = data.get("author")
        if author:
            body_parts.append(f"**Author:** {author}")
        tags = data.get("tags", [])
        if tags:
            body_parts.append(f"**Tags:** {', '.join(tags)}")
        return Skill(
            meta=SkillMeta(name=name, description=description),
            body="\n".join(body_parts),
        )

    def __repr__(self) -> str:
        return f"SkillsDirectorySource(token=***)"
