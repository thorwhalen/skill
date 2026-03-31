"""Composio backend for skill discovery and fetching."""

import json
import os
import urllib.request
import urllib.error
from collections.abc import Callable
from typing import Any

from skill.base import Skill, SkillInfo, SkillMeta

_COMPOSIO_API = "https://backend.composio.dev"


def _default_http_get(url: str, *, headers: dict | None = None) -> dict | str:
    """Perform an HTTP GET, returning parsed JSON or raw text."""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req) as resp:
        data = resp.read().decode("utf-8")
        content_type = resp.headers.get("Content-Type", "")
        if "json" in content_type:
            return json.loads(data)
        return data


class ComposioSkillSource:
    """SkillSource backed by the Composio API (v3).

    Requires a ``COMPOSIO_API_KEY`` environment variable or explicit *token*.

    >>> src = ComposioSkillSource(token="my-key")
    >>> src.name
    'composio'
    """

    name: str = "composio"
    homepage: str = "https://composio.dev"

    def __init__(
        self,
        *,
        token: str | None = None,
        http_get: Callable[..., Any] | None = None,
    ):
        self._token = token or os.environ.get("COMPOSIO_API_KEY")
        if not self._token:
            raise ValueError(
                "Composio requires an API key. "
                "Set COMPOSIO_API_KEY or pass token= to ComposioSkillSource."
            )
        self._http_get = http_get or _default_http_get

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self._token}

    def _get(self, url: str) -> Any:
        return self._http_get(url, headers=self._headers())

    # -- SkillSource interface ------------------------------------------------

    def search(self, query: str, *, max_results: int = 10) -> list[SkillInfo]:
        """Search Composio for tools matching *query*."""
        q = urllib.request.quote(query, safe="")
        url = f"{_COMPOSIO_API}/api/v3/tools?query={q}&limit={max_results}"
        try:
            data = self._get(url)
        except urllib.error.HTTPError:
            return []
        results = []
        for item in data.get("items", []):
            slug = item.get("slug", "")
            toolkit = item.get("toolkit", {})
            toolkit_slug = toolkit.get("slug", "")
            canonical_key = f"{toolkit_slug}/{slug}" if toolkit_slug else slug
            results.append(
                SkillInfo(
                    canonical_key=canonical_key,
                    name=item.get("name", slug),
                    description=item.get("description", ""),
                    source="composio",
                    url=f"https://composio.dev/tools/{toolkit_slug}",
                    owner=toolkit_slug or None,
                )
            )
        return results[:max_results]

    def __getitem__(self, key: str) -> Skill:
        """Fetch a tool as a Skill by key (e.g. ``github/GITHUB_CREATE_ISSUE``).

        The key format is ``toolkit_slug/tool_slug``.
        """
        # Parse tool_slug from key
        parts = key.split("/", 1)
        tool_slug = parts[-1]
        url = f"{_COMPOSIO_API}/api/v3/tools/{tool_slug}"
        try:
            data = self._get(url)
        except (urllib.error.HTTPError, Exception):
            raise KeyError(key)

        return self._tool_to_skill(data)

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
    def _tool_to_skill(data: dict) -> Skill:
        """Convert a Composio tool response into a Skill object."""
        name = data.get("name", data.get("slug", "unknown"))
        description = data.get("human_description") or data.get("description", "")
        toolkit = data.get("toolkit", {})

        body_parts = [f"# {name}", ""]
        if description:
            body_parts.append(description)
            body_parts.append("")

        # Document input parameters
        input_params = data.get("input_parameters", {})
        props = input_params.get("properties", {})
        required = set(input_params.get("required", []))
        if props:
            body_parts.append("## Parameters")
            body_parts.append("")
            for pname, pschema in props.items():
                req_mark = " (required)" if pname in required else ""
                pdesc = pschema.get("description", pschema.get("type", ""))
                body_parts.append(f"- **{pname}**{req_mark}: {pdesc}")
            body_parts.append("")

        # Document output parameters
        output_params = data.get("output_parameters", {})
        out_props = output_params.get("properties", {})
        if out_props:
            body_parts.append("## Output")
            body_parts.append("")
            for pname, pschema in out_props.items():
                pdesc = pschema.get("description", pschema.get("type", ""))
                body_parts.append(f"- **{pname}**: {pdesc}")
            body_parts.append("")

        if toolkit.get("name"):
            body_parts.append(f"**Toolkit:** {toolkit['name']}")

        return Skill(
            meta=SkillMeta(name=name, description=description),
            body="\n".join(body_parts),
        )

    def __repr__(self) -> str:
        return f"ComposioSkillSource(token=***)"
