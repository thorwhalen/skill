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


class TestCLIGrammar:
    """Characterization tests pinning the CLI grammar across the argh -> cw move.

    The expected values here were recorded from the previous ``argh``
    implementation and must not be relaxed to match new behaviour without a
    deliberate decision to change the published command line.
    """

    COMMANDS = (
        'search',
        'install',
        'uninstall',
        'create',
        'list-skills',
        'validate',
        'show',
        'link-skills',
        'sources',
        'install-completion',
    )

    def test_every_command_is_listed(self):
        result = _run_cli('--help')
        assert result.returncode == 0
        for name in self.COMMANDS:
            assert name in result.stdout, f'{name} missing from --help'

    @pytest.mark.parametrize('command', COMMANDS)
    def test_every_command_has_help(self, command):
        result = _run_cli(command, '--help')
        assert result.returncode == 0
        assert result.stdout.startswith('usage:')

    def test_no_arguments_prints_usage_to_stdout_and_exits_zero(self):
        """argh's behaviour, which plain argparse with a required subparser lacks.

        Bare ``skill`` prints usage on STDOUT and exits 0, rather than erroring
        on a missing subcommand.
        """
        result = _run_cli()
        assert result.returncode == 0
        assert result.stdout.startswith('usage:')
        assert result.stderr == ''

    def test_unknown_command_exits_two(self):
        """A non-zero-exit vector.

        ``cw.dispatch`` RETURNS an exit code where argh exited by itself, so
        ``main`` must ``raise SystemExit`` with it. Every other test in this
        file passes whether or not it does.
        """
        result = _run_cli('no-such-command')
        assert result.returncode == 2
        assert 'invalid choice' in result.stderr

    def test_missing_required_argument_exits_two(self):
        result = _run_cli('search')
        assert result.returncode == 2

    @pytest.mark.parametrize(
        'command,flag',
        [('search', '--backends'), ('install', '--agent-targets')],
    )
    def test_list_valued_flags_accept_zero_values(self, command, flag):
        """``list[str] | None`` parameters take ``nargs='*'``, as they did under argh.

        Passing the flag with no values must parse rather than error; it yields
        an empty list.
        """
        result = _run_cli(command, '--help')
        assert result.returncode == 0
        # argparse renders an nargs='*' option as `[FLAG [VALUE ...]]` in usage.
        assert f'{flag} [' in result.stdout
