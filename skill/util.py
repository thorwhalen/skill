"""Pure helpers with zero internal imports."""

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParsedKey:
    """A normalized skill key.

    >>> ParsedKey.from_string('owner/skill-name')
    ParsedKey(owner='owner', name='skill-name')
    >>> ParsedKey.from_string('Owner/Skill-Name')
    ParsedKey(owner='owner', name='skill-name')
    >>> ParsedKey.from_string('my-skill')
    ParsedKey(owner='_local', name='my-skill')
    >>> ParsedKey.from_string('owner/repo/skill-name')
    ParsedKey(owner='owner', name='skill-name')
    >>> str(ParsedKey(owner='owner', name='skill-name'))
    'owner/skill-name'
    """

    owner: str
    name: str

    @classmethod
    def from_string(cls, raw: str) -> 'ParsedKey':
        """Parse a raw key string into a normalized ParsedKey.

        Supports 1-part (name only), 2-part (owner/name), and 3-part
        (owner/repo/name) keys. All parts are lowercased.
        """
        parts = raw.strip().split('/')
        if len(parts) == 1:
            return cls(owner='_local', name=parts[0].lower())
        elif len(parts) == 2:
            return cls(owner=parts[0].lower(), name=parts[1].lower())
        elif len(parts) == 3:
            # owner/repo/name -> we keep owner and name, drop repo
            return cls(owner=parts[0].lower(), name=parts[2].lower())
        else:
            raise ValueError(f"Invalid key format: {raw!r} (expected 1-3 parts)")

    def __str__(self):
        return f"{self.owner}/{self.name}"


_ENV_VAR_PATTERN = re.compile(r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)')


def resolve_env_vars(value: str) -> str:
    """Resolve ``$VAR`` and ``${VAR}`` references from environment variables.

    >>> import os; os.environ['_SKILL_TEST'] = 'hello'
    >>> resolve_env_vars('key=$_SKILL_TEST')
    'key=hello'
    >>> resolve_env_vars('${_SKILL_TEST}/world')
    'hello/world'
    >>> resolve_env_vars('no vars here')
    'no vars here'
    """

    def _replace(match):
        var_name = match.group(1) or match.group(2)
        val = os.environ.get(var_name)
        if val is None:
            raise KeyError(
                f"Environment variable {var_name!r} is not set. "
                f"Set it with: export {var_name}=<value>"
            )
        return val

    return _ENV_VAR_PATTERN.sub(_replace, value)


_PROJECT_MARKERS = frozenset({
    '.git',
    'pyproject.toml',
    'setup.py',
    'setup.cfg',
    'package.json',
    'Cargo.toml',
    'go.mod',
    'Makefile',
    'pom.xml',
})


def find_project_root(start: Path | None = None) -> Path | None:
    """Walk up from ``start`` looking for a project root marker.

    >>> import tempfile
    >>> d = Path(tempfile.mkdtemp()).resolve()
    >>> p = d / 'sub' / 'deep'
    >>> p.mkdir(parents=True)
    >>> (d / '.git').mkdir()
    >>> find_project_root(p) == d
    True
    >>> find_project_root(Path('/nonexistent/path/that/does/not/exist')) is None
    True
    """
    current = (start or Path.cwd()).resolve()
    while True:
        if any((current / marker).exists() for marker in _PROJECT_MARKERS):
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def atomic_write(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically via temp-then-rename.

    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as d:
    ...     p = Path(d) / 'test.txt'
    ...     atomic_write(p, 'hello')
    ...     p.read_text()
    'hello'
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise
