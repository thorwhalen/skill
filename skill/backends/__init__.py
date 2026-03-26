"""Backend protocols and local filesystem backend."""

from collections.abc import Iterator
from pathlib import Path
from typing import Protocol, runtime_checkable

from skill.base import Skill, SkillInfo


@runtime_checkable
class SkillSource(Protocol):
    """Read-only source of skills (e.g., GitHub, local directory).

    ``__iter__`` and ``__len__`` are deliberately omitted — remote sources
    may not support enumeration.
    """

    name: str

    def __getitem__(self, key: str) -> Skill: ...

    def __contains__(self, key: object) -> bool: ...

    def search(self, query: str, *, max_results: int = 10) -> list[SkillInfo]: ...


class LocalDirSource:
    """SkillSource backed by an arbitrary local directory of skills.

    Useful for testing and for local skill packages (e.g. a git checkout).
    The directory should contain ``owner/name/SKILL.md`` structure.

    >>> import tempfile
    >>> from skill.base import Skill, SkillMeta
    >>> d = Path(tempfile.mkdtemp())
    >>> (d / 'alice' / 'greet').mkdir(parents=True)
    >>> Skill(meta=SkillMeta(name='greet', description='Say hi'), body='Hi!').write_to(d / 'alice' / 'greet')
    >>> src = LocalDirSource(d)
    >>> src.name
    'local'
    >>> 'alice/greet' in src
    True
    >>> src['alice/greet'].meta.name
    'greet'
    """

    name: str = "local"

    def __init__(self, root: Path):
        self.root = Path(root)

    def __getitem__(self, key: str) -> Skill:
        parts = key.split("/")
        if len(parts) == 2:
            path = self.root / parts[0] / parts[1]
        elif len(parts) == 1:
            path = self.root / parts[0]
        else:
            raise KeyError(key)
        if not (path / "SKILL.md").exists():
            raise KeyError(key)
        return Skill.from_path(path)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        try:
            self[key]
            return True
        except KeyError:
            return False

    def __iter__(self) -> Iterator[str]:
        if not self.root.exists():
            return
        for owner_dir in sorted(self.root.iterdir()):
            if not owner_dir.is_dir():
                continue
            for skill_dir in sorted(owner_dir.iterdir()):
                if (skill_dir / "SKILL.md").exists():
                    yield f"{owner_dir.name}/{skill_dir.name}"

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def search(self, query: str, *, max_results: int = 10) -> list[SkillInfo]:
        """Keyword search over skill names and descriptions.

        >>> import tempfile
        >>> from skill.base import Skill, SkillMeta
        >>> d = Path(tempfile.mkdtemp())
        >>> (d / 'bob' / 'python-lint').mkdir(parents=True)
        >>> Skill(meta=SkillMeta(name='python-lint', description='Lint Python code'), body='...').write_to(d / 'bob' / 'python-lint')
        >>> src = LocalDirSource(d)
        >>> results = src.search('python')
        >>> len(results) > 0
        True
        >>> results[0].name
        'python-lint'
        """
        query_lower = query.lower()
        results = []
        for key in self:
            skill = self[key]
            text = f"{skill.meta.name} {skill.meta.description}".lower()
            if query_lower in text:
                owner = key.split("/")[0] if "/" in key else None
                results.append(
                    SkillInfo(
                        canonical_key=key,
                        name=skill.meta.name,
                        description=skill.meta.description,
                        source=self.name,
                        owner=owner,
                    )
                )
                if len(results) >= max_results:
                    break
        return results

    def __repr__(self) -> str:
        return f"{type(self).__name__}(root={self.root!r})"
