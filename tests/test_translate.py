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

    def test_description_is_yaml_escaped(self):
        desc = 'Lint: style rules\n> and more'
        mdc = to_mdc(_make_skill(description=desc))
        assert from_mdc(mdc).meta.description == desc

    def test_globs_stay_unquoted_on_one_line(self):
        s = _make_skill(metadata={'cursor.globs': ['**/*.ts', '**/*.tsx']})
        assert 'globs: **/*.ts, **/*.tsx\n' in to_mdc(s)

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

    def test_cursor_native_unquoted_globs(self):
        content = "---\ndescription: Py rules\nglobs: **/*.py, **/*.ts\nalwaysApply: false\n---\n# Rules"
        s = from_mdc(content)
        assert s.meta.metadata['cursor.globs'] == '**/*.py, **/*.ts'
        assert s.meta.metadata['cursor.alwaysApply'] == 'False'
        assert s.meta.description == 'Py rules'

    def test_globs_block_list(self):
        content = "---\ndescription: d\nglobs:\n  - '*.ts'\n  - '*.tsx'\n---\nbody"
        assert from_mdc(content).meta.metadata['cursor.globs'] == '*.ts, *.tsx'

    def test_globs_line_in_body_is_ignored(self):
        content = "---\ndescription: d\n---\nglobs: **/*.py\n"
        s = from_mdc(content)
        assert 'cursor.globs' not in s.meta.metadata
        assert 'globs: **/*.py' in s.body

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

    def test_roundtrip_globs_starting_with_star(self):
        original = _make_skill(metadata={'cursor.globs': ['**/*.py', '**/*.ts']})
        imported = from_mdc(to_mdc(original))
        assert imported.meta.metadata['cursor.globs'] == '**/*.py, **/*.ts'


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


def test_every_translated_format_declares_its_losses():
    from skill.install import agent_targets
    from skill.translate import translation_losses

    for target in agent_targets.values():
        if target.needs_translation:
            assert target.format in translation_losses, target.name


def test_lost_fields_matches_the_warning():
    import warnings as _w

    from skill.base import Skill, SkillMeta
    from skill.translate import lost_fields, translate

    s = Skill(meta=SkillMeta(name='t', description='d', license='MIT', allowed_tools=['Bash']), body='x')
    for fmt in ('mdc', 'windsurf_md', 'clinerules_md', 'gemini_md', 'copilot_md'):
        with _w.catch_warnings(record=True) as caught:
            _w.simplefilter('always')
            translate(s, target_format=fmt)
        lost = lost_fields(s, target_format=fmt)
        assert lost and all(f in str(caught[0].message) for f in lost)


def test_new_frontmatter_is_valid_yaml_for_hostile_values():
    import yaml

    from skill.base import Skill, SkillMeta
    from skill.translate import to_cline_rule, to_windsurf_rule

    desc = 'Use when: a > b\nsecond line'
    s = Skill(meta=SkillMeta(name='t', description=desc, metadata={'windsurf.globs': '**/*.py', 'cline.paths': '*.md'}), body='x')
    ws = yaml.safe_load(to_windsurf_rule(s).split('---')[1])
    assert ws['description'] == desc and ws['globs'] == '**/*.py'
    assert yaml.safe_load(to_cline_rule(s).split('---')[1])['paths'] == '*.md'
    assert '> second line' in to_cline_rule(s)
