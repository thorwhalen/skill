"""Shell completion setup and diagnostics."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from skill.config import config_dir

_COMPLETION_HINTED_MARKER = config_dir() / ".completion_hinted"

_SHELL_CONFIGS = {
    "zsh": Path.home() / ".zshrc",
    "bash": Path.home() / ".bashrc",
}

_REGISTER_LINE = 'eval "$(register-python-argcomplete skill)"'
_REGISTER_COMMENT = (
    "# Shell completion for the skill CLI (added by `skill install-completion`)"
)


def _detect_shell() -> str:
    """Detect the current shell from the SHELL environment variable.

    >>> _detect_shell() in ('bash', 'zsh', 'fish', 'unknown')
    True
    """
    shell_path = os.environ.get("SHELL", "")
    shell_name = Path(shell_path).name
    if shell_name in ("bash", "zsh", "fish"):
        return shell_name
    return "unknown"


def is_completion_registered() -> bool:
    """Check whether shell completion for ``skill`` appears to be set up.

    Looks for the ``register-python-argcomplete skill`` line in the
    user's shell config, or checks if argcomplete global activation is present.
    """
    shell = _detect_shell()
    config_file = _SHELL_CONFIGS.get(shell)
    if config_file and config_file.exists():
        content = config_file.read_text()
        if "register-python-argcomplete skill" in content:
            return True
        # Global activation: the user has run activate-global-python-argcomplete
        if "activate-global-python-argcomplete" in content:
            return True
        if "python-argcomplete-check-easy-install-script" in content:
            return True
    # Also check if the global completion script is installed
    for d in ("/etc/bash_completion.d", "/usr/local/etc/bash_completion.d"):
        if (Path(d) / "_python-argcomplete").exists():
            return True
    return False


def install_completion() -> str:
    """Register shell completion for ``skill`` in the user's shell config.

    Returns a status message describing what was done.
    """
    if shutil.which("register-python-argcomplete") is None:
        return (
            "argcomplete is not installed or register-python-argcomplete is "
            "not on PATH. Install it with: pip install argcomplete"
        )

    shell = _detect_shell()
    config_file = _SHELL_CONFIGS.get(shell)

    if config_file is None:
        # Unsupported shell — give manual instructions
        result = subprocess.run(
            ["register-python-argcomplete", "skill"],
            capture_output=True,
            text=True,
        )
        return (
            f"Could not detect a supported shell (got {shell!r}). "
            f"Add the following to your shell config manually:\n\n"
            f"  {_REGISTER_LINE}\n\n"
            f"Or use the output of: register-python-argcomplete skill"
        )

    if config_file.exists():
        content = config_file.read_text()
        if "register-python-argcomplete skill" in content:
            return f"Completion already registered in {config_file}."
    else:
        content = ""

    # Append the registration line
    addition = f"\n{_REGISTER_COMMENT}\n{_REGISTER_LINE}\n"
    config_file.write_text(content.rstrip() + "\n" + addition)
    _mark_hinted()
    return (
        f"Completion registered in {config_file}.\n"
        f"Restart your shell or run: source {config_file}"
    )


def maybe_hint_completion() -> None:
    """Print a one-time hint about shell completion if it isn't set up.

    Called on first CLI invocation. Writes a marker file so the hint
    is only shown once.
    """
    if _COMPLETION_HINTED_MARKER.exists():
        return
    if is_completion_registered():
        _mark_hinted()
        return
    print(
        "Tip: Enable tab completion for skill commands by running:\n"
        "\n"
        "  skill install-completion\n",
        file=sys.stderr,
    )
    _mark_hinted()


def _mark_hinted() -> None:
    """Write the marker file so the completion hint is not shown again."""
    _COMPLETION_HINTED_MARKER.parent.mkdir(parents=True, exist_ok=True)
    _COMPLETION_HINTED_MARKER.touch()
