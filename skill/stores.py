"""Storage layer: LocalSkillStore and SourcedSkillStore via dol."""

from collections.abc import MutableMapping, Iterator
from pathlib import Path

from skill.base import Skill, SkillInfo
from skill.config import skills_dir
from skill.util import ParsedKey


class LocalSkillStore(MutableMapping):
    """Filesystem-backed MutableMapping[str, Skill] over the canonical skills directory.

    Keys are canonical ``owner/name`` strings. Each skill is stored as a
    directory containing ``SKILL.md`` and optional resource subdirectories.

    >>> import tempfile
    >>> store = LocalSkillStore(root=Path(tempfile.mkdtemp()))
    >>> len(store)
    0
    >>> list(store)
    []
    """

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else skills_dir()
        self.root.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        pk = ParsedKey.from_string(key)
        return self.root / pk.owner / pk.name

    def __getitem__(self, key: str) -> Skill:
        path = self._key_to_path(key)
        if not (path / "SKILL.md").exists():
            raise KeyError(key)
        return Skill.from_path(path)

    def __setitem__(self, key: str, skill: Skill) -> None:
        path = self._key_to_path(key)
        skill.write_to(path)

    def __delitem__(self, key: str) -> None:
        import shutil

        path = self._key_to_path(key)
        if not path.exists():
            raise KeyError(key)
        shutil.rmtree(path)
        # Clean up empty owner directory
        owner_dir = path.parent
        if owner_dir.exists() and not any(owner_dir.iterdir()):
            owner_dir.rmdir()

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

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return (self._key_to_path(key) / "SKILL.md").exists()

    def list_info(self) -> list[SkillInfo]:
        """Return SkillInfo for all locally stored skills."""
        result = []
        for key in self:
            skill = self[key]
            pk = ParsedKey.from_string(key)
            result.append(
                SkillInfo(
                    canonical_key=key,
                    name=skill.meta.name,
                    description=skill.meta.description,
                    source="local",
                    owner=pk.owner,
                    installed=True,
                )
            )
        return result

    def __repr__(self) -> str:
        return f"{type(self).__name__}(root={self.root!r})"
