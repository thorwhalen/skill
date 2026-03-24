# PYTHON_ARGCOMPLETE_OK
"""CLI entry point for the skill package.

Usage::

    python -m skill search "react best practices"
    python -m skill create my-skill --description "My custom skill"
    python -m skill validate ./my-skill/
    python -m skill list
    python -m skill link-skills /path/to/project
    python -m skill install-completion
"""

import argh

from skill import search, install, uninstall, create, list_skills, validate, show, link_skills
from skill.completion import install_completion, maybe_hint_completion


def main():
    maybe_hint_completion()
    argh.dispatch_commands(
        [
            search, install, uninstall, create, list_skills, validate, show,
            link_skills, install_completion,
        ]
    )


if __name__ == '__main__':
    main()
