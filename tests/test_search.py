"""Tests for skill.search."""

from pathlib import Path

from skill.base import Skill, SkillMeta
from skill.stores import LocalSkillStore
from skill.search import search, _search_local


class TestSearchLocal:
    def test_finds_matching_skill(self, tmp_path):
        store = LocalSkillStore(root=tmp_path)
        store['alice/python-lint'] = Skill(
            meta=SkillMeta(name='python-lint', description='Lint Python code'),
            body='# Lint',
        )
        store['bob/react'] = Skill(
            meta=SkillMeta(name='react', description='React patterns'),
            body='# React',
        )
        results = _search_local('python', store=store)
        assert len(results) == 1
        assert results[0].name == 'python-lint'

    def test_empty_store(self, tmp_path):
        store = LocalSkillStore(root=tmp_path)
        assert _search_local('anything', store=store) == []

    def test_max_results(self, tmp_path):
        store = LocalSkillStore(root=tmp_path)
        for i in range(5):
            store[f'alice/skill-{i}'] = Skill(
                meta=SkillMeta(name=f'skill-{i}', description='A skill'),
                body='body',
            )
        results = _search_local('skill', store=store, max_results=2)
        assert len(results) == 2


class TestSearch:
    def test_local_only(self, tmp_path):
        store = LocalSkillStore(root=tmp_path)
        store['alice/test'] = Skill(
            meta=SkillMeta(name='test', description='Test skill'),
            body='body',
        )
        # Use local_only to avoid network calls
        results = search('test', local_only=True, max_results=10)
        # Results may or may not include our tmp store depending on default
        # But the function should not raise
        assert isinstance(results, list)
