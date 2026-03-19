"""CLI entry point for the skill package.

Usage::

    python -m skill search "react best practices"
    python -m skill create my-skill --description "My custom skill"
    python -m skill validate ./my-skill/
    python -m skill list
"""

import argh

from skill import search, install, uninstall, create, list_skills, validate, show


def main():
    argh.dispatch_commands(
        [search, install, uninstall, create, list_skills, validate, show]
    )


if __name__ == '__main__':
    main()
