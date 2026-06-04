"""Tests for skill.base."""

import pytest
from pathlib import Path

from skill.base import (
    parse_frontmatter,
    parse_skill_md,
    render_skill_md,
    render_frontmatter,
    discover_resources,
    Skill,
    SkillMeta,
    SkillInfo,
    _meta_from_dict,
)


class TestParseFrontmatter:
    def test_basic(self):
        meta, body = parse_frontmatter("---\nname: test\n---\n# Hello")
        assert meta['name'] == 'test'
        assert body.strip() == '# Hello'

    def test_no_frontmatter(self):
        meta, body = parse_frontmatter("just text")
        assert meta == {}
        assert body == 'just text'

    def test_empty_frontmatter(self):
        meta, body = parse_frontmatter("---\n---\nbody")
        assert meta == {}
        assert body == 'body'

    def test_multiline_body(self):
        content = "---\nname: x\n---\nline1\nline2"
        meta, body = parse_frontmatter(content)
        assert 'line1' in body
        assert 'line2' in body


class TestRoundTrip:
    def test_parse_render_roundtrip(self):
        original_meta = SkillMeta(name='foo', description='A foo skill')
        original_body = '# Usage\n\nDo stuff.\n'
        rendered = render_skill_md(original_meta, original_body)
        parsed_meta, parsed_body = parse_skill_md(rendered)
        assert parsed_meta.name == original_meta.name
        assert parsed_meta.description == original_meta.description
        assert parsed_body == original_body

    def test_roundtrip_with_optional_fields(self):
        meta = SkillMeta(
            name='bar',
            description='desc',
            license='MIT',
            allowed_tools=['Read', 'Write'],
        )
        rendered = render_skill_md(meta, 'body')
        parsed, _ = parse_skill_md(rendered)
        assert parsed.license == 'MIT'
        assert parsed.allowed_tools == ['Read', 'Write']

    def test_roundtrip_preserves_unknown_namespaced_keys(self):
        # an additive namespaced block (e.g. another tool's `coact:` section) must
        # survive parse -> render rather than being silently dropped (issue #2).
        src = (
            "---\n"
            "name: ux\n"
            "description: Analyze.\n"
            "coact:\n"
            "  model: sonnet\n"
            "  tools: [Read, Grep]\n"
            "vendor-x:\n"
            "  flag: true\n"
            "---\n"
            "# body\n"
        )
        meta, body = parse_skill_md(src)
        assert meta.extra['coact'] == {'model': 'sonnet', 'tools': ['Read', 'Grep']}
        assert meta.extra['vendor-x'] == {'flag': True}

        rendered = render_skill_md(meta, body)
        reparsed, _ = parse_skill_md(rendered)
        assert reparsed.extra == meta.extra
        assert 'coact:' in rendered and 'vendor-x:' in rendered

    def test_named_fields_are_not_captured_as_extra(self):
        meta, _ = parse_skill_md(
            "---\nname: x\ndescription: y\naudience: developer\n"
            "license: MIT\nallowed-tools: [Bash]\n---\nbody"
        )
        assert meta.extra == {}
        assert meta.audience == 'developer' and meta.allowed_tools == ['Bash']

    def test_no_extra_means_no_change_to_output(self):
        meta = SkillMeta(name='x', description='y')
        assert 'extra' not in render_skill_md(meta, 'b')


class TestExtraKeys:
    def test_default_extra_is_empty(self):
        assert SkillMeta(name='x', description='y').extra == {}

    def test_to_dict_emits_extra_after_named_fields(self):
        d = SkillMeta(name='x', description='y', license='MIT',
                      extra={'coact': {'model': 'sonnet'}}).to_dict()
        keys = list(d)
        assert keys[:3] == ['name', 'description', 'license']
        assert d['coact'] == {'model': 'sonnet'}

    def test_extra_cannot_shadow_named_frontmatter_keys(self):
        # a stray 'name' in extra must not override the real field on render
        d = SkillMeta(name='real', description='y', extra={'name': 'evil'}).to_dict()
        assert d['name'] == 'real'


class TestMetaFromDict:
    def test_minimal(self):
        m = _meta_from_dict({'name': 'x', 'description': 'y'})
        assert m.name == 'x'
        assert m.license is None

    def test_with_extras(self):
        m = _meta_from_dict({
            'name': 'x',
            'description': 'y',
            'allowed-tools': ['Bash'],
            'metadata': {'cursor.globs': '*.py'},
        })
        assert m.allowed_tools == ['Bash']
        assert m.metadata == {'cursor.globs': '*.py'}


class TestDiscoverResources:
    def test_finds_scripts(self, tmp_path):
        (tmp_path / 'scripts').mkdir()
        (tmp_path / 'scripts' / 'run.py').touch()
        (tmp_path / 'scripts' / 'build.sh').touch()
        r = discover_resources(tmp_path)
        assert sorted(r['scripts']) == ['build.sh', 'run.py']

    def test_empty_when_no_resource_dirs(self, tmp_path):
        assert discover_resources(tmp_path) == {}

    def test_ignores_non_files(self, tmp_path):
        (tmp_path / 'scripts').mkdir()
        (tmp_path / 'scripts' / 'subdir').mkdir()
        r = discover_resources(tmp_path)
        assert r['scripts'] == []


class TestSkill:
    def test_from_string(self):
        s = Skill.from_string("---\nname: x\ndescription: y\n---\nbody")
        assert s.meta.name == 'x'
        assert s.body == 'body'
        assert s.resources == {}

    def test_from_path(self, tmp_path):
        (tmp_path / 'SKILL.md').write_text(
            "---\nname: demo\ndescription: A demo\n---\n# Demo"
        )
        (tmp_path / 'scripts').mkdir()
        (tmp_path / 'scripts' / 'run.sh').touch()
        s = Skill.from_path(tmp_path)
        assert s.meta.name == 'demo'
        assert s.resources['scripts'] == ['run.sh']
        assert s.source_path == tmp_path

    def test_from_path_missing_skill_md(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            Skill.from_path(tmp_path)

    def test_write_to(self, tmp_path):
        s = Skill(
            meta=SkillMeta(name='test', description='Test skill'),
            body='# Test\n',
        )
        out = tmp_path / 'test-skill'
        s.write_to(out)
        assert (out / 'SKILL.md').exists()
        loaded = Skill.from_path(out)
        assert loaded.meta.name == 'test'

    def test_to_string(self):
        s = Skill(meta=SkillMeta(name='x', description='y'), body='hello')
        text = s.to_string()
        assert 'name: x' in text
        assert 'hello' in text


class TestSkillInfo:
    def test_creation(self):
        si = SkillInfo(
            canonical_key='owner/test',
            name='test',
            description='desc',
            source='github',
        )
        assert si.installed is False
        assert si.url is None
