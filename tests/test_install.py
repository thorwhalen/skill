"""Tests for skill.install."""

import os
import pytest
from pathlib import Path

from skill.base import Skill, SkillMeta
from skill.stores import LocalSkillStore
from skill.install import (
    install,
    uninstall,
    _check_existing,
    _create_link,
    AgentTarget,
    AGENT_TARGETS,
)


def _setup_store_and_project(tmp_path):
    """Create a store with one skill and a fake project directory."""
    store_root = tmp_path / 'store'
    project = tmp_path / 'project'
    (project / '.git').mkdir(parents=True)

    store = LocalSkillStore(root=store_root)
    store['alice/greet'] = Skill(
        meta=SkillMeta(name='greet', description='Say hello'),
        body='# Greet\n\nSay hello to the user.\n',
    )
    return store, project


class TestCheckExisting:
    def test_none(self, tmp_path):
        assert _check_existing(tmp_path / 'nope') == 'none'

    def test_directory(self, tmp_path):
        d = tmp_path / 'existing'
        d.mkdir()
        assert _check_existing(d) == 'directory'

    def test_file(self, tmp_path):
        f = tmp_path / 'file.txt'
        f.write_text('hello')
        assert _check_existing(f) == 'file'

    def test_symlink(self, tmp_path):
        src = tmp_path / 'src'
        src.mkdir()
        link = tmp_path / 'link'
        os.symlink(src, link)
        assert _check_existing(link) == 'foreign_symlink'


class TestCreateLink:
    def test_symlink(self, tmp_path):
        src = tmp_path / 'source'
        src.mkdir()
        target = tmp_path / 'target'
        result = _create_link(src, target)
        assert result.is_symlink()
        assert result.resolve() == src.resolve()

    def test_copy(self, tmp_path):
        src = tmp_path / 'source'
        src.mkdir()
        (src / 'file.txt').write_text('content')
        target = tmp_path / 'target'
        _create_link(src, target, copy=True)
        assert target.is_dir()
        assert (target / 'file.txt').read_text() == 'content'

    def test_force_overwrites(self, tmp_path):
        src = tmp_path / 'source'
        src.mkdir()
        target = tmp_path / 'target'
        target.write_text('existing')
        _create_link(src, target, force=True)
        assert target.is_symlink()

    def test_existing_raises_without_force(self, tmp_path):
        src = tmp_path / 'source'
        src.mkdir()
        target = tmp_path / 'target'
        target.mkdir()
        with pytest.raises(FileExistsError):
            _create_link(src, target)


class TestInstall:
    def test_install_claude_code(self, tmp_path):
        store, project = _setup_store_and_project(tmp_path)
        result = install(
            'alice/greet',
            agent_targets=['claude-code'],
            scope='project',
            project_dir=project,
            store=store,
        )
        assert 'claude-code' in result
        installed_path = result['claude-code']
        assert installed_path.is_symlink() or installed_path.is_dir()

    def test_install_cursor(self, tmp_path):
        store, project = _setup_store_and_project(tmp_path)
        result = install(
            'alice/greet',
            agent_targets=['cursor'],
            scope='project',
            project_dir=project,
            store=store,
        )
        assert 'cursor' in result
        content = result['cursor'].read_text()
        assert 'description: Say hello' in content
        assert 'alwaysApply' in content

    def test_install_copilot(self, tmp_path):
        store, project = _setup_store_and_project(tmp_path)
        result = install(
            'alice/greet',
            agent_targets=['copilot'],
            scope='project',
            project_dir=project,
            store=store,
        )
        assert 'copilot' in result
        content = result['copilot'].read_text()
        assert '## greet' in content
        assert 'skill:greet' in content  # marker

    def test_install_missing_skill_raises(self, tmp_path):
        store, project = _setup_store_and_project(tmp_path)
        with pytest.raises(KeyError, match='nonexistent'):
            install('alice/nonexistent', store=store, project_dir=project)


class TestUninstall:
    def test_uninstall_claude_code(self, tmp_path):
        store, project = _setup_store_and_project(tmp_path)
        install(
            'alice/greet',
            agent_targets=['claude-code'],
            scope='project',
            project_dir=project,
            store=store,
        )
        result = uninstall(
            'alice/greet',
            agent_targets=['claude-code'],
            scope='project',
            project_dir=project,
            store=store,
        )
        assert 'claude-code' in result
        assert not result['claude-code'].exists()

    def test_uninstall_copilot(self, tmp_path):
        store, project = _setup_store_and_project(tmp_path)
        install(
            'alice/greet',
            agent_targets=['copilot'],
            scope='project',
            project_dir=project,
            store=store,
        )
        uninstall(
            'alice/greet',
            agent_targets=['copilot'],
            scope='project',
            project_dir=project,
            store=store,
        )
        instructions = project / '.github' / 'copilot-instructions.md'
        if instructions.exists():
            assert 'skill:greet' not in instructions.read_text()


class TestAgentTargets:
    def test_claude_code_exists(self):
        assert 'claude-code' in AGENT_TARGETS

    def test_cursor_exists(self):
        assert 'cursor' in AGENT_TARGETS
        assert AGENT_TARGETS['cursor'].needs_translation

    def test_copilot_exists(self):
        assert 'copilot' in AGENT_TARGETS
