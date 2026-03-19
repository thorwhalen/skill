"""Tests for skill.registry and the plugin registration system."""

import pytest
from collections.abc import MutableMapping

from skill.registry import Registry


class TestRegistry:
    def test_register_and_get(self):
        r = Registry('test')
        r.register('foo', 42)
        assert r['foo'] == 42

    def test_setitem_getitem(self):
        r = Registry('test')
        r['bar'] = 99
        assert r['bar'] == 99

    def test_delitem(self):
        r = Registry('test')
        r['x'] = 1
        del r['x']
        assert 'x' not in r

    def test_iter(self):
        r = Registry('test')
        r['a'] = 1
        r['b'] = 2
        assert sorted(r) == ['a', 'b']

    def test_len(self):
        r = Registry('test')
        assert len(r) == 0
        r['x'] = 1
        assert len(r) == 1

    def test_contains(self):
        r = Registry('test')
        r['x'] = 1
        assert 'x' in r
        assert 'y' not in r

    def test_mutable_mapping_protocol(self):
        assert isinstance(Registry('test'), MutableMapping)

    def test_register_returns_item(self):
        """register() returns the item, enabling decorator-factory usage."""
        r = Registry('test')
        item = r.register('fn', lambda: 1)
        assert item() == 1

    def test_repr(self):
        r = Registry('demo')
        r['a'] = 1
        assert 'demo' in repr(r)
        assert 'a' in repr(r)

    def test_name_property(self):
        assert Registry('myname').name == 'myname'

    def test_entry_point_group_default(self):
        r = Registry('agents')
        assert r._entry_point_group == 'skill.agents'

    def test_entry_point_group_custom(self):
        r = Registry('agents', entry_point_group='custom.group')
        assert r._entry_point_group == 'custom.group'

    def test_missing_key_raises(self):
        r = Registry('test')
        with pytest.raises(KeyError):
            r['nonexistent']

    def test_overwrite(self):
        r = Registry('test')
        r['x'] = 1
        r['x'] = 2
        assert r['x'] == 2

    def test_items(self):
        r = Registry('test')
        r['a'] = 1
        r['b'] = 2
        assert dict(r.items()) == {'a': 1, 'b': 2}


class TestAgentTargetRegistration:
    """Test that agent targets can be registered and used."""

    def test_builtin_targets_registered(self):
        from skill.install import agent_targets
        assert 'claude-code' in agent_targets
        assert 'cursor' in agent_targets
        assert 'copilot' in agent_targets

    def test_register_custom_target(self):
        from skill.install import agent_targets, AgentTarget
        target = AgentTarget(
            name='windsurf',
            project_path='{project}/.windsurf/rules/{name}.md',
            format='skill.md',
        )
        agent_targets.register('windsurf', target)
        assert 'windsurf' in agent_targets
        assert agent_targets['windsurf'].name == 'windsurf'
        # Cleanup
        del agent_targets['windsurf']

    def test_backward_compat_alias(self):
        from skill.install import AGENT_TARGETS, agent_targets
        assert AGENT_TARGETS is agent_targets


class TestTranslatorRegistration:
    def test_builtin_translators_registered(self):
        from skill.translate import translators
        assert 'mdc' in translators
        assert 'copilot_md' in translators

    def test_register_custom_translator(self):
        from skill.translate import translators, translate
        from skill.base import Skill, SkillMeta

        def to_windsurf(skill: Skill) -> str:
            return f"# {skill.meta.name}\n{skill.body}"

        translators.register('windsurf_md', to_windsurf)
        s = Skill(meta=SkillMeta(name='test', description='Test'), body='body')
        result = translate(s, target_format='windsurf_md')
        assert '# test' in result
        # Cleanup
        del translators['windsurf_md']


class TestBackendRegistration:
    def test_register_custom_backend(self):
        from skill.search import backends
        from skill.backends import LocalDirSource
        from pathlib import Path
        import tempfile

        d = Path(tempfile.mkdtemp())
        src = LocalDirSource(d)
        backends.register('test_local', src)
        assert 'test_local' in backends
        # Cleanup
        del backends['test_local']


class TestValidatorRegistration:
    def test_builtin_validators_registered(self):
        from skill.create import validators
        assert 'required_fields' in validators
        assert 'body' in validators
        assert 'name_format' in validators
        assert 'lengths' in validators

    def test_register_custom_validator(self):
        from skill.create import validators, validate
        from skill.base import Skill, SkillMeta
        from pathlib import Path
        import tempfile

        def check_no_todo(skill: Skill) -> list[str]:
            if 'TODO' in skill.body:
                return ['Body contains TODO items']
            return []

        validators.register('no_todo', check_no_todo)

        # Validate a skill with TODO in body
        d = Path(tempfile.mkdtemp()) / 'test'
        Skill(
            meta=SkillMeta(name='test', description='Test'),
            body='# TODO: fix this',
        ).write_to(d)
        issues = validate(str(d))
        assert any('TODO' in i for i in issues)

        # Cleanup
        del validators['no_todo']

    def test_custom_validator_no_issues(self):
        from skill.create import validators, validate
        from skill.base import Skill, SkillMeta
        from pathlib import Path
        import tempfile

        def check_no_todo(skill: Skill) -> list[str]:
            if 'TODO' in skill.body:
                return ['Body contains TODO items']
            return []

        validators.register('no_todo', check_no_todo)

        d = Path(tempfile.mkdtemp()) / 'test'
        Skill(
            meta=SkillMeta(name='test', description='Test'),
            body='# Good body',
        ).write_to(d)
        issues = validate(str(d))
        assert not any('TODO' in i for i in issues)

        # Cleanup
        del validators['no_todo']
