"""Tests for skill.backends."""

import pytest
from pathlib import Path

from skill.base import Skill, SkillMeta
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
