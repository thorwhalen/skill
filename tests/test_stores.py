"""Tests for skill.stores."""

import pytest
from pathlib import Path

from skill.base import Skill, SkillMeta
from skill.stores import LocalSkillStore


class TestLocalSkillStore:
    def _make_skill(self, name='test', description='A test skill'):
        return Skill(meta=SkillMeta(name=name, description=description), body=f'# {name}\n')

    def test_setitem_getitem(self, tmp_path):
        store = LocalSkillStore(root=tmp_path)
        skill = self._make_skill()
        store['alice/test'] = skill
        loaded = store['alice/test']
        assert loaded.meta.name == 'test'

    def test_contains(self, tmp_path):
        store = LocalSkillStore(root=tmp_path)
        assert 'alice/test' not in store
        store['alice/test'] = self._make_skill()
        assert 'alice/test' in store

    def test_iter(self, tmp_path):
        store = LocalSkillStore(root=tmp_path)
        store['alice/foo'] = self._make_skill('foo')
        store['bob/bar'] = self._make_skill('bar')
        keys = list(store)
        assert sorted(keys) == ['alice/foo', 'bob/bar']

    def test_len(self, tmp_path):
        store = LocalSkillStore(root=tmp_path)
        assert len(store) == 0
        store['alice/test'] = self._make_skill()
        assert len(store) == 1

    def test_delitem(self, tmp_path):
        store = LocalSkillStore(root=tmp_path)
        store['alice/test'] = self._make_skill()
        del store['alice/test']
        assert 'alice/test' not in store
        assert len(store) == 0

    def test_delitem_cleans_empty_owner(self, tmp_path):
        store = LocalSkillStore(root=tmp_path)
        store['alice/test'] = self._make_skill()
        del store['alice/test']
        assert not (tmp_path / 'alice').exists()

    def test_delitem_missing_raises(self, tmp_path):
        store = LocalSkillStore(root=tmp_path)
        with pytest.raises(KeyError):
            del store['alice/nonexistent']

    def test_getitem_missing_raises(self, tmp_path):
        store = LocalSkillStore(root=tmp_path)
        with pytest.raises(KeyError):
            store['alice/nonexistent']

    def test_list_info(self, tmp_path):
        store = LocalSkillStore(root=tmp_path)
        store['alice/greet'] = self._make_skill('greet', 'Say hello')
        infos = store.list_info()
        assert len(infos) == 1
        assert infos[0].canonical_key == 'alice/greet'
        assert infos[0].source == 'local'

    def test_overwrite(self, tmp_path):
        store = LocalSkillStore(root=tmp_path)
        store['alice/test'] = self._make_skill('test', 'v1')
        store['alice/test'] = self._make_skill('test', 'v2')
        assert store['alice/test'].meta.description == 'v2'

    def test_mutable_mapping_protocol(self, tmp_path):
        """LocalSkillStore satisfies the MutableMapping ABC."""
        from collections.abc import MutableMapping
        store = LocalSkillStore(root=tmp_path)
        assert isinstance(store, MutableMapping)
