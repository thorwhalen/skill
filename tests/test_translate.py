"""Tests for skill.translate."""

import warnings
import pytest

from skill.base import Skill, SkillMeta
from skill.translate import to_mdc, from_mdc, to_copilot_instructions, translate


def _make_skill(**kwargs):
    defaults = dict(name='test', description='A test skill')
    defaults.update(kwargs)
    meta = SkillMeta(**defaults)
    return Skill(meta=meta, body='# Instructions\n\nDo stuff.\n')


class TestToMdc:
    def test_basic(self):
        mdc = to_mdc(_make_skill())
        assert 'description: A test skill' in mdc
        assert 'alwaysApply: false' in mdc
        assert 'Do stuff.' in mdc

    def test_with_cursor_metadata(self):
        s = _make_skill(metadata={'cursor.globs': '*.py', 'cursor.alwaysApply': 'true'})
        mdc = to_mdc(s)
        assert 'globs: *.py' in mdc
        assert 'alwaysApply: true' in mdc

    def test_warns_on_lossy_fields(self):
        s = _make_skill(allowed_tools=['Read'], license='MIT')
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            to_mdc(s)
            assert len(w) == 1
            assert 'allowed-tools' in str(w[0].message)
            assert 'license' in str(w[0].message)


class TestFromMdc:
    def test_basic(self):
        content = "---\ndescription: Do things\nglobs: '*.py'\nalwaysApply: false\n---\n# Rules"
        s = from_mdc(content)
        assert s.meta.description == 'Do things'
        assert s.meta.metadata['cursor.globs'] == '*.py'
        assert '# Rules' in s.body

    def test_derives_name(self):
        content = "---\ndescription: React best practices\n---\nbody"
        s = from_mdc(content)
        assert s.meta.name == 'react-best-practices'


class TestMdcRoundTrip:
    def test_roundtrip(self):
        original = _make_skill(metadata={'cursor.globs': 'src/**/*.ts'})
        mdc = to_mdc(original)
        imported = from_mdc(mdc)
        assert imported.meta.description == original.meta.description
        assert imported.meta.metadata.get('cursor.globs') == 'src/**/*.ts'


class TestToCopilotInstructions:
    def test_basic(self):
        md = to_copilot_instructions(_make_skill(name='lint', description='Lint rules'))
        assert '## lint' in md
        assert 'Lint rules' in md
        assert 'Do stuff.' in md


class TestTranslateDispatcher:
    def test_mdc(self):
        result = translate(_make_skill(), target_format='mdc')
        assert 'alwaysApply' in result

    def test_copilot(self):
        result = translate(_make_skill(), target_format='copilot_md')
        assert '## test' in result

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match='Unknown target format'):
            translate(_make_skill(), target_format='nonexistent')
