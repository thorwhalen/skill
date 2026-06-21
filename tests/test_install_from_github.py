"""Tests for skill.install.install_from_github (gh skill CLI wrapper)."""

import subprocess

import pytest

import importlib

from skill import install_from_github

# Note: ``skill.install`` the attribute is the install *function* (re-exported in
# skill/__init__.py), so import the submodule explicitly to patch its globals.
install_mod = importlib.import_module("skill.install")


def _patch_which(monkeypatch, fn):
    """Patch ``shutil.which`` as seen by the install module."""
    monkeypatch.setattr(install_mod.shutil, "which", fn)


def _patch_run(monkeypatch, fn):
    """Patch ``subprocess.run`` as seen by the install module."""
    monkeypatch.setattr(install_mod.subprocess, "run", fn)


def test_gh_missing_raises(monkeypatch):
    """If `gh` isn't on PATH, raise a RuntimeError pointing to cli.github.com."""
    _patch_which(monkeypatch, lambda _: None)
    with pytest.raises(RuntimeError) as exc:
        install_from_github("thorwhalen/skill", "skill-package-setup")
    assert "cli.github.com" in str(exc.value)


def test_success_path_calls_gh_with_right_argv(monkeypatch):
    """The success path shells out to gh with the expected argv."""
    _patch_which(monkeypatch, lambda _: "/usr/bin/gh")

    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    _patch_run(monkeypatch, fake_run)

    results = install_from_github(
        "thorwhalen/skill", "skill-package-setup", agent="claude-code"
    )

    assert calls == [
        [
            "gh",
            "skill",
            "install",
            "thorwhalen/skill",
            "skill-package-setup",
            "--agent",
            "claude-code",
        ]
    ]
    assert results[0]["name"] == "skill-package-setup"
    assert results[0]["returncode"] == 0


def test_preview_uses_preview_verb_and_no_agent(monkeypatch):
    """preview=True runs `gh skill preview` without an --agent flag."""
    _patch_which(monkeypatch, lambda _: "/usr/bin/gh")

    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    _patch_run(monkeypatch, fake_run)

    install_from_github("thorwhalen/skill", ["a", "b"], preview=True)

    assert calls == [
        ["gh", "skill", "preview", "thorwhalen/skill", "a"],
        ["gh", "skill", "preview", "thorwhalen/skill", "b"],
    ]


def test_gh_skill_unavailable_raises_pointing_to_docs(monkeypatch):
    """An 'unknown command' error from gh raises a RuntimeError to the gh_skill docs."""
    _patch_which(monkeypatch, lambda _: "/usr/bin/gh")

    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(
            argv, 1, stdout="", stderr="unknown command \"skill\" for \"gh\""
        )

    _patch_run(monkeypatch, fake_run)

    with pytest.raises(RuntimeError) as exc:
        install_from_github("thorwhalen/skill", "x")
    assert "gh_skill" in str(exc.value)


def test_subprocess_filenotfound_raises(monkeypatch):
    """If subprocess raises FileNotFoundError, surface the install-gh message."""
    _patch_which(monkeypatch, lambda _: "/usr/bin/gh")

    def fake_run(argv, **kwargs):
        raise FileNotFoundError(argv[0])

    _patch_run(monkeypatch, fake_run)

    with pytest.raises(RuntimeError) as exc:
        install_from_github("thorwhalen/skill", "x")
    assert "cli.github.com" in str(exc.value)
