"""Tests for skill.backends."""

import pytest
from pathlib import Path

from skill.base import Skill, SkillInfo, SkillMeta
from skill.backends import LocalDirSource, SkillSource
from skill.backends.github import GitHubSkillSource, _skill_name_from_path


def _populate_source(root: Path):
    """Create a test skill directory structure."""
    for owner, name, desc in [
        ('alice', 'python-lint', 'Lint Python code'),
        ('alice', 'react-best', 'React best practices'),
        ('bob', 'docker-setup', 'Docker setup guide'),
    ]:
        path = root / owner / name
        path.mkdir(parents=True)
        Skill(
            meta=SkillMeta(name=name, description=desc),
            body=f'# {name}\n',
        ).write_to(path)


class TestLocalDirSource:
    def test_getitem(self, tmp_path):
        _populate_source(tmp_path)
        src = LocalDirSource(tmp_path)
        s = src['alice/python-lint']
        assert s.meta.name == 'python-lint'

    def test_contains(self, tmp_path):
        _populate_source(tmp_path)
        src = LocalDirSource(tmp_path)
        assert 'alice/python-lint' in src
        assert 'alice/nonexistent' not in src

    def test_iter(self, tmp_path):
        _populate_source(tmp_path)
        src = LocalDirSource(tmp_path)
        keys = sorted(src)
        assert keys == ['alice/python-lint', 'alice/react-best', 'bob/docker-setup']

    def test_len(self, tmp_path):
        _populate_source(tmp_path)
        src = LocalDirSource(tmp_path)
        assert len(src) == 3

    def test_search(self, tmp_path):
        _populate_source(tmp_path)
        src = LocalDirSource(tmp_path)
        results = src.search('python')
        assert len(results) == 1
        assert results[0].name == 'python-lint'

    def test_search_max_results(self, tmp_path):
        _populate_source(tmp_path)
        src = LocalDirSource(tmp_path)
        results = src.search('a', max_results=1)  # matches alice's skills
        assert len(results) == 1

    def test_protocol_conformance(self, tmp_path):
        src = LocalDirSource(tmp_path)
        assert isinstance(src, SkillSource)


class TestGitHubSkillSource:
    def test_search_with_mock(self):
        """GitHub search dispatches to the Code Search API."""
        def mock_get(url, *, headers=None):
            return {
                'items': [
                    {
                        'path': 'skills/react-rules/SKILL.md',
                        'repository': {
                            'name': 'skills',
                            'owner': {'login': 'anthropics'},
                            'description': 'Official skills',
                            'html_url': 'https://github.com/anthropics/skills',
                        },
                    }
                ]
            }

        src = GitHubSkillSource(http_get=mock_get)
        results = src.search('react')
        assert len(results) == 1
        assert results[0].canonical_key == 'anthropics/react-rules'
        assert results[0].source == 'github'

    def test_getitem_with_mock(self):
        """GitHub getitem fetches raw SKILL.md content."""
        skill_content = "---\nname: test\ndescription: A test\n---\n# Hello"

        def mock_get(url, *, headers=None):
            if 'raw.githubusercontent.com' in url:
                return skill_content
            raise Exception(f"Unexpected URL: {url}")

        src = GitHubSkillSource(http_get=mock_get)
        skill = src['owner/test']
        assert skill.meta.name == 'test'

    def test_getitem_missing_raises(self):
        """Missing skill raises KeyError."""
        import urllib.error

        def mock_get(url, *, headers=None):
            raise urllib.error.HTTPError(url, 404, 'Not Found', {}, None)

        src = GitHubSkillSource(http_get=mock_get)
        with pytest.raises(KeyError):
            src['owner/nonexistent']

    def test_contains_with_mock(self):
        def mock_get(url, *, headers=None):
            return "---\nname: x\ndescription: y\n---\nbody"

        src = GitHubSkillSource(http_get=mock_get)
        assert 'owner/skill' in src

    def test_list_repo_skills_with_mock(self):
        def mock_get(url, *, headers=None):
            return {
                'tree': [
                    {'path': 'skills/foo/SKILL.md'},
                    {'path': 'skills/bar/SKILL.md'},
                    {'path': 'README.md'},
                ]
            }

        src = GitHubSkillSource(http_get=mock_get)
        results = src.list_repo_skills('owner', 'repo')
        assert len(results) == 2
        names = {r.name for r in results}
        assert names == {'foo', 'bar'}


class TestSkillNameFromPath:
    def test_nested(self):
        assert _skill_name_from_path('skills/my-skill/SKILL.md') == 'my-skill'

    def test_root(self):
        assert _skill_name_from_path('SKILL.md') is None

    def test_deep_nested(self):
        assert _skill_name_from_path('.claude/skills/foo/SKILL.md') == 'foo'


# ---------------------------------------------------------------------------
# Mock HTTP helpers for new backends
# ---------------------------------------------------------------------------


def _make_mock_http(responses: dict):
    """Return a callable that maps URL substrings to canned responses.

    ``responses`` maps a URL substring to the value that should be returned.
    If the value is a dict/list it is returned as-is (simulating parsed JSON).
    If it is a string it is returned as raw text.
    Raises ``urllib.error.HTTPError`` for unmatched URLs.
    """
    import urllib.error

    def mock_get(url, *, headers=None):
        for pattern, value in responses.items():
            if pattern in url:
                return value
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    return mock_get


# ===========================================================================
# Smithery
# ===========================================================================

_SMITHERY_SEARCH_RESPONSE = {
    "skills": [
        {
            "qualifiedName": "shubhamsaboo/python-expert",
            "displayName": "python-expert",
            "description": "Expert Python coding assistant",
            "categories": ["Coding"],
            "gitUrl": "https://github.com/shubhamsaboo/python-expert",
            "qualityScore": 0.87,
            "totalActivations": 144,
        },
        {
            "qualifiedName": "anthropics/skills/claude-api",
            "displayName": "claude-api",
            "description": "Build apps with the Claude API",
            "categories": ["Development"],
            "gitUrl": "https://github.com/anthropics/skills",
            "qualityScore": 0.95,
            "totalActivations": 500,
        },
    ],
    "pagination": {
        "currentPage": 1,
        "pageSize": 10,
        "totalPages": 1,
        "totalCount": 2,
    },
}


class TestSmitherySkillSource:
    def _make_source(self, responses):
        from skill.backends.smithery import SmitherySkillSource

        return SmitherySkillSource(http_get=_make_mock_http(responses))

    def test_name_and_homepage(self):
        from skill.backends.smithery import SmitherySkillSource

        src = SmitherySkillSource(http_get=_make_mock_http({}))
        assert src.name == "smithery"
        assert "smithery" in src.homepage

    def test_search_returns_skill_infos(self):
        src = self._make_source({"/skills": _SMITHERY_SEARCH_RESPONSE})
        results = src.search("python")
        assert len(results) == 2
        assert all(isinstance(r, SkillInfo) for r in results)
        assert results[0].name == "python-expert"
        assert results[0].source == "smithery"
        assert results[0].canonical_key == "shubhamsaboo/python-expert"

    def test_search_max_results(self):
        src = self._make_source({"/skills": _SMITHERY_SEARCH_RESPONSE})
        results = src.search("python", max_results=1)
        assert len(results) == 1

    def test_search_returns_empty_on_http_error(self):
        src = self._make_source({})
        results = src.search("anything")
        assert results == []

    def test_contains(self):
        detail = {
            "qualifiedName": "shubhamsaboo/python-expert",
            "displayName": "python-expert",
            "description": "Expert Python coding",
            "gitUrl": "https://github.com/shubhamsaboo/python-expert",
        }
        raw_skill_md = "---\nname: python-expert\ndescription: Expert Python coding\n---\n# Usage\nBe an expert."
        src = self._make_source({
            "/skills/shubhamsaboo/python-expert": detail,
            "raw.githubusercontent.com": raw_skill_md,
        })
        assert "shubhamsaboo/python-expert" in src

    def test_getitem_fetches_skill_via_git_url(self):
        raw_skill_md = "---\nname: python-expert\ndescription: Expert Python\n---\n# Hello"
        detail = {
            "qualifiedName": "shubhamsaboo/python-expert",
            "displayName": "python-expert",
            "description": "Expert Python",
            "gitUrl": "https://github.com/shubhamsaboo/python-expert",
        }
        src = self._make_source({
            "/skills/shubhamsaboo/python-expert": detail,
            "raw.githubusercontent.com": raw_skill_md,
        })
        skill = src["shubhamsaboo/python-expert"]
        assert isinstance(skill, Skill)
        assert skill.meta.name == "python-expert"

    def test_getitem_synthesizes_when_no_git_url(self):
        detail = {
            "qualifiedName": "someone/my-skill",
            "displayName": "my-skill",
            "description": "A great skill for things",
        }
        src = self._make_source({
            "/skills/someone/my-skill": detail,
        })
        skill = src["someone/my-skill"]
        assert isinstance(skill, Skill)
        assert skill.meta.name == "my-skill"
        assert skill.meta.description == "A great skill for things"

    def test_getitem_missing_raises_keyerror(self):
        src = self._make_source({})
        with pytest.raises(KeyError):
            src["nonexistent/skill"]

    def test_repr(self):
        from skill.backends.smithery import SmitherySkillSource

        src = SmitherySkillSource(http_get=_make_mock_http({}))
        assert "Smithery" in repr(src)

    def test_protocol_conformance(self):
        from skill.backends.smithery import SmitherySkillSource

        src = SmitherySkillSource(http_get=_make_mock_http({}))
        assert isinstance(src, SkillSource)


# ===========================================================================
# Composio
# ===========================================================================

_COMPOSIO_SEARCH_RESPONSE = {
    "items": [
        {
            "slug": "GITHUB_CREATE_ISSUE",
            "name": "Create Issue",
            "description": "Create a new issue in a GitHub repository",
            "toolkit": {"slug": "github", "name": "GitHub", "logo": ""},
            "input_parameters": {"type": "object", "properties": {"title": {"type": "string"}}},
            "tags": ["issues", "github"],
        },
        {
            "slug": "SLACK_SEND_MESSAGE",
            "name": "Send Message",
            "description": "Send a message to a Slack channel",
            "toolkit": {"slug": "slack", "name": "Slack", "logo": ""},
            "input_parameters": {"type": "object", "properties": {}},
            "tags": ["messaging"],
        },
    ],
    "total_items": 2,
}

_COMPOSIO_TOOL_DETAIL = {
    "slug": "GITHUB_CREATE_ISSUE",
    "name": "Create Issue",
    "description": "Create a new issue in a GitHub repository",
    "human_description": "Creates an issue on GitHub with title, body, and labels.",
    "toolkit": {"slug": "github", "name": "GitHub", "logo": ""},
    "input_parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Issue title"},
            "body": {"type": "string", "description": "Issue body"},
        },
        "required": ["title"],
    },
    "output_parameters": {"type": "object", "properties": {}},
    "tags": ["issues"],
}


class TestComposioSkillSource:
    def _make_source(self, responses):
        from skill.backends.composio import ComposioSkillSource

        return ComposioSkillSource(
            token="test-key", http_get=_make_mock_http(responses)
        )

    def test_name_and_homepage(self):
        from skill.backends.composio import ComposioSkillSource

        src = ComposioSkillSource(token="k", http_get=_make_mock_http({}))
        assert src.name == "composio"
        assert "composio" in src.homepage

    def test_search_returns_skill_infos(self):
        src = self._make_source({"/api/v3/tools": _COMPOSIO_SEARCH_RESPONSE})
        results = src.search("github")
        assert len(results) == 2
        assert results[0].name == "Create Issue"
        assert results[0].source == "composio"
        assert results[0].canonical_key == "github/GITHUB_CREATE_ISSUE"

    def test_search_max_results(self):
        src = self._make_source({"/api/v3/tools": _COMPOSIO_SEARCH_RESPONSE})
        results = src.search("github", max_results=1)
        assert len(results) == 1

    def test_search_returns_empty_on_http_error(self):
        src = self._make_source({})
        assert src.search("anything") == []

    def test_getitem_fetches_tool_as_skill(self):
        src = self._make_source({
            "/api/v3/tools/GITHUB_CREATE_ISSUE": _COMPOSIO_TOOL_DETAIL,
        })
        skill = src["github/GITHUB_CREATE_ISSUE"]
        assert isinstance(skill, Skill)
        assert skill.meta.name == "Create Issue"
        assert "title" in skill.body

    def test_getitem_missing_raises_keyerror(self):
        src = self._make_source({})
        with pytest.raises(KeyError):
            src["nonexistent/TOOL"]

    def test_contains(self):
        src = self._make_source({
            "/api/v3/tools/GITHUB_CREATE_ISSUE": _COMPOSIO_TOOL_DETAIL,
        })
        assert "github/GITHUB_CREATE_ISSUE" in src
        assert "missing/TOOL" not in src

    def test_requires_token(self):
        from skill.backends.composio import ComposioSkillSource

        with pytest.raises(ValueError):
            ComposioSkillSource(http_get=_make_mock_http({}))

    def test_repr_masks_token(self):
        from skill.backends.composio import ComposioSkillSource

        src = ComposioSkillSource(token="secret123", http_get=_make_mock_http({}))
        assert "secret123" not in repr(src)
        assert "***" in repr(src)

    def test_protocol_conformance(self):
        from skill.backends.composio import ComposioSkillSource

        src = ComposioSkillSource(token="k", http_get=_make_mock_http({}))
        assert isinstance(src, SkillSource)


# ===========================================================================
# Awesome Claude Skills (curated list)
# ===========================================================================

_AWESOME_README = """\
# Awesome Claude Skills

## Official Skills

### Document Skills
- **[docx](https://github.com/anthropics/skills/tree/main/skills/docx)** - Create and edit Word documents
- **[pdf](https://github.com/anthropics/skills/tree/main/skills/pdf)** - Generate and manipulate PDF files

### Development
- **[frontend-design](https://github.com/anthropics/skills/tree/main/skills/frontend-design)** - Frontend design best practices

## Community Skills

### Individual Skills

| Skill | Description |
|-------|-------------|
| **[python-lint](https://github.com/conorluddy/python-lint)** | Lint Python code with style |
| **[react-tips](https://github.com/bob/react-tips)** | React best practices guide |
"""


class TestAwesomeListSource:
    def _make_source(self, responses):
        from skill.backends.awesome_list import AwesomeListSource

        return AwesomeListSource(http_get=_make_mock_http(responses))

    def test_name_and_homepage(self):
        from skill.backends.awesome_list import AwesomeListSource

        src = AwesomeListSource(http_get=_make_mock_http({}))
        assert src.name == "awesome-list"
        assert "github.com" in src.homepage

    def test_search_parses_bullet_and_table_entries(self):
        src = self._make_source({"raw.githubusercontent.com": _AWESOME_README})
        results = src.search("python")
        assert len(results) >= 1
        names = [r.name for r in results]
        assert "python-lint" in names

    def test_search_finds_official_skills(self):
        src = self._make_source({"raw.githubusercontent.com": _AWESOME_README})
        results = src.search("pdf")
        assert any(r.name == "pdf" for r in results)

    def test_search_max_results(self):
        src = self._make_source({"raw.githubusercontent.com": _AWESOME_README})
        results = src.search("", max_results=2)
        assert len(results) <= 2

    def test_search_returns_empty_on_http_error(self):
        src = self._make_source({})
        assert src.search("anything") == []

    def test_getitem_fetches_from_github(self):
        raw_skill_md = "---\nname: pdf\ndescription: PDF generation\n---\n# PDF"
        src = self._make_source({
            "raw.githubusercontent.com": raw_skill_md,
        })
        skill = src["anthropics/skills/pdf"]
        assert isinstance(skill, Skill)
        assert skill.meta.name == "pdf"

    def test_getitem_missing_raises_keyerror(self):
        src = self._make_source({})
        with pytest.raises(KeyError):
            src["nonexistent/skill"]

    def test_protocol_conformance(self):
        from skill.backends.awesome_list import AwesomeListSource

        src = AwesomeListSource(http_get=_make_mock_http({}))
        assert isinstance(src, SkillSource)


# ===========================================================================
# SkillsDirectory
# ===========================================================================

_SKILLSDIR_SEARCH_RESPONSE = {
    "skills": [
        {
            "slug": "python-linter",
            "name": "Python Linter",
            "description": "Lint Python code for style and correctness",
            "author": "alice",
            "tags": ["python", "linting"],
            "stars": 42,
            "url": "https://www.skillsdirectory.com/skills/python-linter",
        },
        {
            "slug": "react-helper",
            "name": "React Helper",
            "description": "React component patterns and tips",
            "author": "bob",
            "tags": ["react", "frontend"],
            "stars": 15,
            "url": "https://www.skillsdirectory.com/skills/react-helper",
        },
    ],
}

_SKILLSDIR_DETAIL = {
    "slug": "python-linter",
    "name": "Python Linter",
    "description": "Lint Python code for style and correctness",
    "author": "alice",
    "content": "---\nname: Python Linter\ndescription: Lint Python code\n---\n# Python Linter\n\nUse this skill to lint your code.",
    "tags": ["python"],
    "stars": 42,
}


class TestSkillsDirectorySource:
    def _make_source(self, responses):
        from skill.backends.skillsdirectory import SkillsDirectorySource

        return SkillsDirectorySource(
            token="test-api-key", http_get=_make_mock_http(responses)
        )

    def test_name_and_homepage(self):
        from skill.backends.skillsdirectory import SkillsDirectorySource

        src = SkillsDirectorySource(token="k", http_get=_make_mock_http({}))
        assert src.name == "skillsdirectory"
        assert "skillsdirectory" in src.homepage

    def test_search_returns_skill_infos(self):
        src = self._make_source({"/api/v1/skills": _SKILLSDIR_SEARCH_RESPONSE})
        results = src.search("python")
        assert len(results) == 2
        assert results[0].name == "Python Linter"
        assert results[0].source == "skillsdirectory"
        assert results[0].canonical_key == "alice/python-linter"

    def test_search_max_results(self):
        src = self._make_source({"/api/v1/skills": _SKILLSDIR_SEARCH_RESPONSE})
        results = src.search("python", max_results=1)
        assert len(results) == 1

    def test_search_returns_empty_on_http_error(self):
        src = self._make_source({})
        assert src.search("anything") == []

    def test_getitem_with_content(self):
        src = self._make_source({
            "/api/v1/skills/python-linter": _SKILLSDIR_DETAIL,
        })
        skill = src["alice/python-linter"]
        assert isinstance(skill, Skill)
        assert skill.meta.name == "Python Linter"

    def test_getitem_without_content_synthesizes_skill(self):
        detail_no_content = {
            "slug": "react-helper",
            "name": "React Helper",
            "description": "React tips",
            "author": "bob",
        }
        src = self._make_source({
            "/api/v1/skills/react-helper": detail_no_content,
        })
        skill = src["bob/react-helper"]
        assert isinstance(skill, Skill)
        assert skill.meta.name == "React Helper"

    def test_getitem_missing_raises_keyerror(self):
        src = self._make_source({})
        with pytest.raises(KeyError):
            src["nonexistent/skill"]

    def test_contains(self):
        src = self._make_source({
            "/api/v1/skills/python-linter": _SKILLSDIR_DETAIL,
        })
        assert "alice/python-linter" in src
        assert "missing/thing" not in src

    def test_requires_token(self):
        from skill.backends.skillsdirectory import SkillsDirectorySource

        with pytest.raises(ValueError):
            SkillsDirectorySource(http_get=_make_mock_http({}))

    def test_repr_masks_token(self):
        from skill.backends.skillsdirectory import SkillsDirectorySource

        src = SkillsDirectorySource(token="secret", http_get=_make_mock_http({}))
        assert "secret" not in repr(src)

    def test_protocol_conformance(self):
        from skill.backends.skillsdirectory import SkillsDirectorySource

        src = SkillsDirectorySource(token="k", http_get=_make_mock_http({}))
        assert isinstance(src, SkillSource)
