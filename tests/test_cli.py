"""Tests for skill CLI (__main__.py)."""

import subprocess
import sys

import pytest


def _run_cli(*args):
    result = subprocess.run(
        [sys.executable, '-m', 'skill', *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result


class TestCLI:
    def test_help(self):
        result = _run_cli('--help')
        assert result.returncode == 0
        assert 'search' in result.stdout
        assert 'create' in result.stdout
        assert 'validate' in result.stdout

    def test_search_help(self):
        result = _run_cli('search', '--help')
        assert result.returncode == 0
        assert 'query' in result.stdout.lower() or 'max-results' in result.stdout.lower()

    def test_create_and_validate(self, tmp_path):
        """End-to-end: create a skill via CLI scaffolding, then validate it."""
        skill_path = tmp_path / 'test-skill'
        # Scaffold manually (CLI create writes to store, scaffold writes to path)
        from skill.create import scaffold
        scaffold('test-skill', description='Test skill', path=skill_path)

        result = _run_cli('validate', str(skill_path))
        # Should succeed with no issues
        assert result.returncode == 0

    def test_list_skills(self):
        result = _run_cli('list-skills')
        assert result.returncode == 0
