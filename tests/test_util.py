"""Tests for skill.util."""

import os
import pytest
from pathlib import Path

from skill.util import ParsedKey, resolve_env_vars, find_project_root, atomic_write


class TestParsedKey:
    def test_two_part(self):
        pk = ParsedKey.from_string('owner/my-skill')
        assert pk.owner == 'owner'
        assert pk.name == 'my-skill'

    def test_one_part_defaults_to_local(self):
        pk = ParsedKey.from_string('my-skill')
        assert pk.owner == '_local'
        assert pk.name == 'my-skill'

    def test_three_part_drops_repo(self):
        pk = ParsedKey.from_string('owner/repo/skill-name')
        assert pk.owner == 'owner'
        assert pk.name == 'skill-name'

    def test_case_normalization(self):
        pk = ParsedKey.from_string('Owner/Skill-Name')
        assert pk.owner == 'owner'
        assert pk.name == 'skill-name'

    def test_str_roundtrip(self):
        pk = ParsedKey(owner='owner', name='skill')
        assert str(pk) == 'owner/skill'

    def test_invalid_key_raises(self):
        with pytest.raises(ValueError, match="Invalid key format"):
            ParsedKey.from_string('a/b/c/d')

    def test_whitespace_stripped(self):
        pk = ParsedKey.from_string('  owner/name  ')
        assert pk.owner == 'owner'
        assert pk.name == 'name'


class TestResolveEnvVars:
    def test_dollar_syntax(self, monkeypatch):
        monkeypatch.setenv('MY_VAR', 'hello')
        assert resolve_env_vars('val=$MY_VAR') == 'val=hello'

    def test_brace_syntax(self, monkeypatch):
        monkeypatch.setenv('MY_VAR', 'world')
        assert resolve_env_vars('${MY_VAR}/path') == 'world/path'

    def test_no_vars(self):
        assert resolve_env_vars('plain text') == 'plain text'

    def test_missing_var_raises(self):
        with pytest.raises(KeyError, match='_NONEXISTENT_VAR_XYZ'):
            resolve_env_vars('$_NONEXISTENT_VAR_XYZ')

    def test_multiple_vars(self, monkeypatch):
        monkeypatch.setenv('A', '1')
        monkeypatch.setenv('B', '2')
        assert resolve_env_vars('$A-${B}') == '1-2'


class TestFindProjectRoot:
    def test_finds_git_root(self, tmp_path):
        (tmp_path / '.git').mkdir()
        sub = tmp_path / 'a' / 'b'
        sub.mkdir(parents=True)
        assert find_project_root(sub) == tmp_path

    def test_finds_pyproject(self, tmp_path):
        (tmp_path / 'pyproject.toml').touch()
        assert find_project_root(tmp_path) == tmp_path

    def test_returns_none_when_no_markers(self, tmp_path):
        sub = tmp_path / 'isolated'
        sub.mkdir()
        assert find_project_root(sub) is None


class TestAtomicWrite:
    def test_creates_file(self, tmp_path):
        p = tmp_path / 'test.txt'
        atomic_write(p, 'hello')
        assert p.read_text() == 'hello'

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / 'sub' / 'deep' / 'file.txt'
        atomic_write(p, 'content')
        assert p.read_text() == 'content'

    def test_overwrites_existing(self, tmp_path):
        p = tmp_path / 'test.txt'
        p.write_text('old')
        atomic_write(p, 'new')
        assert p.read_text() == 'new'
