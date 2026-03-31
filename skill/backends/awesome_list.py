"""Awesome-claude-skills curated list backend for skill discovery."""

import re
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from skill.base import Skill, SkillInfo

_README_URL = (
    "https://raw.githubusercontent.com/travisvn/awesome-claude-skills/main/README.md"
)

# Patterns for parsing the two listing formats in the README.
_BULLET_RE = re.compile(r"- \*\*\[(.+?)\]\((.+?)\)\*\*\s*[-–]\s*(.+)")
_TABLE_RE = re.compile(r"\|\s*\*\*\[(.+?)\]\((.+?)\)\*\*\s*\|\s*(.+?)\s*\|")


def _default_http_get(url: str, *, headers: dict | None = None) -> str:
    """Fetch raw text from a URL."""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


class AwesomeListSource:
    """SkillSource backed by the awesome-claude-skills curated list.

    Fetches and parses the README from
    ``github.com/travisvn/awesome-claude-skills``.

    >>> src = AwesomeListSource()
    >>> src.name
    'awesome-list'
    """

    name: str = "awesome-list"
    homepage: str = "https://github.com/travisvn/awesome-claude-skills"

    def __init__(
        self,
        *,
        http_get: Callable[..., Any] | None = None,
    ):
        self._http_get = http_get or _default_http_get
        self._cache: list[SkillInfo] | None = None

    def _fetch_entries(self) -> list[SkillInfo]:
        """Fetch and parse all entries from the README."""
        if self._cache is not None:
            return self._cache
        try:
            text = self._http_get(_README_URL, headers={})
        except (urllib.error.HTTPError, Exception):
            return []
        entries: list[SkillInfo] = []
        seen: set[str] = set()
        for pattern in (_BULLET_RE, _TABLE_RE):
            for m in pattern.finditer(text):
                name, url, description = m.group(1), m.group(2), m.group(3).strip()
                canonical_key = _canonical_key_from_url(url, name)
                if canonical_key in seen:
                    continue
                seen.add(canonical_key)
                owner = canonical_key.split("/")[0] if "/" in canonical_key else None
                entries.append(
                    SkillInfo(
                        canonical_key=canonical_key,
                        name=name,
                        description=description,
                        source="awesome-list",
                        url=url,
                        owner=owner,
                    )
                )
        self._cache = entries
        return entries

    # -- SkillSource interface ------------------------------------------------

    def search(self, query: str, *, max_results: int = 10) -> list[SkillInfo]:
        """Search the curated list for skills matching *query*."""
        entries = self._fetch_entries()
        if not entries:
            return []
        q = query.lower()
        results = [
            e
            for e in entries
            if q in e.name.lower() or q in e.description.lower() or not q
        ]
        return results[:max_results]

    def __getitem__(self, key: str) -> Skill:
        """Fetch a skill by canonical key.

        Attempts to fetch SKILL.md from the linked GitHub repository.
        """
        # Parse owner/repo/skill_name from key
        parts = key.split("/")
        if len(parts) >= 3:
            owner, repo, skill_name = parts[0], parts[1], "/".join(parts[2:])
        elif len(parts) == 2:
            owner, repo = parts
            skill_name = repo
        else:
            raise KeyError(key)

        # Try common SKILL.md locations
        paths_to_try = [
            f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/SKILL.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/skills/{skill_name}/SKILL.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/main/SKILL.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/main/skills/{skill_name}/SKILL.md",
        ]
        for url in paths_to_try:
            try:
                content = self._http_get(url, headers={})
                if isinstance(content, str):
                    return Skill.from_string(content)
            except (urllib.error.HTTPError, Exception):
                continue
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        try:
            self[key]
            return True
        except KeyError:
            return False

    def __repr__(self) -> str:
        return "AwesomeListSource()"


def _canonical_key_from_url(url: str, name: str) -> str:
    """Derive a canonical key like ``owner/repo/skill`` from a GitHub URL.

    Examples:
        >>> _canonical_key_from_url(
        ...     "https://github.com/anthropics/skills/tree/main/skills/pdf",
        ...     "pdf",
        ... )
        'anthropics/skills/pdf'
        >>> _canonical_key_from_url("https://github.com/bob/react-tips", "react-tips")
        'bob/react-tips'
    """
    # Strip trailing slash and fragment
    url = url.rstrip("/").split("#")[0]
    parts = url.split("/")
    # github.com/owner/repo[/tree/branch/skills/name]
    if "github.com" in url and len(parts) >= 5:
        owner, repo = parts[3], parts[4]
        # If URL points into a subdirectory, extract the skill name from the end
        if len(parts) > 6 and "tree" in parts[5]:
            # e.g. .../tree/main/skills/pdf -> pdf
            skill_name = parts[-1]
            return f"{owner}/{repo}/{skill_name}"
        return f"{owner}/{repo}"
    # Non-GitHub URL: just use the name
    return name
