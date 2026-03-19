"""Tests for skill.config."""

import pytest
from pathlib import Path

from skill.config import SkillConfig, load_config, save_config, _serialize_toml


class TestSkillConfig:
    def test_defaults(self):
        c = SkillConfig()
        assert c.default_agent_targets == ['claude-code']
        assert c.default_scope == 'project'
        assert c.install_method == 'symlink'
        assert c.github_enabled is True
        assert c.search_cache_ttl == 3600


class TestLoadConfig:
    def test_nonexistent_file_returns_defaults(self):
        c = load_config(Path('/nonexistent/config.toml'))
        assert c == SkillConfig()

    def test_loads_from_toml(self, tmp_path):
        p = tmp_path / 'config.toml'
        p.write_text('default_scope = "global"\nsearch_cache_ttl = 600\n')
        c = load_config(p)
        assert c.default_scope == 'global'
        assert c.search_cache_ttl == 600
        # Other fields keep defaults
        assert c.install_method == 'symlink'

    def test_ignores_unknown_keys(self, tmp_path):
        p = tmp_path / 'config.toml'
        p.write_text('unknown_field = "value"\n')
        c = load_config(p)
        assert c == SkillConfig()


class TestSaveConfig:
    def test_roundtrip(self, tmp_path):
        p = tmp_path / 'config.toml'
        original = SkillConfig(default_scope='global', search_cache_ttl=120)
        save_config(original, path=p)
        loaded = load_config(p)
        assert loaded.default_scope == 'global'
        assert loaded.search_cache_ttl == 120


class TestSerializeToml:
    def test_string(self):
        assert "key = 'value'" in _serialize_toml({'key': 'value'})

    def test_int(self):
        assert 'key = 42' in _serialize_toml({'key': 42})

    def test_bool(self):
        assert 'key = true' in _serialize_toml({'key': True})
        assert 'key = false' in _serialize_toml({'key': False})

    def test_list(self):
        result = _serialize_toml({'key': ['a', 'b']})
        assert "key = ['a', 'b']" in result
