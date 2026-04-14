"""Core data model and SKILL.md parsing."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Parsing helpers (pure functions)
# ---------------------------------------------------------------------------


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter delimited by ``---`` from markdown content.

    >>> meta, body = parse_frontmatter("---\\nname: test\\ndescription: A test\\n---\\n# Hello")
    >>> meta['name']
    'test'
    >>> body.strip()
    '# Hello'
    >>> parse_frontmatter("no frontmatter here")
    ({}, 'no frontmatter here')
    """
    content = content.lstrip()
    if not content.startswith("---"):
        return {}, content
    # Find the closing ---
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    yaml_str = content[3:end].strip()
    body = content[end + 3 :]
    if body.startswith("\n"):
        body = body[1:]
    meta = yaml.safe_load(yaml_str) or {}
    return meta, body


def render_frontmatter(meta: dict) -> str:
    """Render a dict as YAML frontmatter block.

    >>> print(render_frontmatter({'name': 'test', 'description': 'A test'}))
    ---
    name: test
    description: A test
    ---
    <BLANKLINE>
    """
    yaml_str = yaml.dump(meta, default_flow_style=False, sort_keys=False).rstrip()
    return f"---\n{yaml_str}\n---\n"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SkillMeta:
    """Parsed YAML frontmatter from a SKILL.md file.

    >>> m = SkillMeta(name='test', description='A test skill')
    >>> m.name
    'test'
    """

    name: str
    description: str
    audience: str | None = None
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    allowed_tools: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to a dict suitable for YAML frontmatter, omitting None values."""
        d = {"name": self.name, "description": self.description}
        if self.audience is not None:
            d["audience"] = self.audience
        if self.license is not None:
            d["license"] = self.license
        if self.compatibility is not None:
            d["compatibility"] = self.compatibility
        if self.metadata:
            d["metadata"] = self.metadata
        if self.allowed_tools:
            d["allowed-tools"] = self.allowed_tools
        return d


def _meta_from_dict(d: dict) -> SkillMeta:
    """Construct a SkillMeta from a frontmatter dict.

    >>> m = _meta_from_dict({'name': 'x', 'description': 'y', 'license': 'MIT'})
    >>> m.license
    'MIT'
    """
    return SkillMeta(
        name=d.get("name", ""),
        description=d.get("description", ""),
        audience=d.get("audience"),
        license=d.get("license"),
        compatibility=d.get("compatibility"),
        metadata=d.get("metadata", {}),
        allowed_tools=d.get("allowed-tools", []),
    )


def parse_skill_md(content: str) -> tuple[SkillMeta, str]:
    """Parse a SKILL.md string into (SkillMeta, body).

    >>> meta, body = parse_skill_md("---\\nname: foo\\ndescription: bar\\n---\\nHello")
    >>> meta.name
    'foo'
    >>> body
    'Hello'
    """
    raw_meta, body = parse_frontmatter(content)
    return _meta_from_dict(raw_meta), body


def render_skill_md(meta: SkillMeta, body: str) -> str:
    """Render a SKILL.md string from meta and body.

    >>> s = render_skill_md(SkillMeta(name='x', description='y'), 'Hello')
    >>> 'name: x' in s and 'Hello' in s
    True
    """
    return render_frontmatter(meta.to_dict()) + body


# ---------------------------------------------------------------------------
# Resource discovery
# ---------------------------------------------------------------------------

_RESOURCE_DIRS = ("scripts", "references", "assets")


def discover_resources(path: Path) -> dict[str, list[str]]:
    """Scan a skill directory for bundled resource subdirectories.

    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as d:
    ...     p = Path(d)
    ...     (p / 'scripts').mkdir()
    ...     (p / 'scripts' / 'run.py').touch()
    ...     r = discover_resources(p)
    ...     r['scripts']
    ['run.py']
    """
    resources = {}
    for dirname in _RESOURCE_DIRS:
        subdir = path / dirname
        if subdir.is_dir():
            resources[dirname] = sorted(f.name for f in subdir.iterdir() if f.is_file())
    return resources


# ---------------------------------------------------------------------------
# Skill and SkillInfo
# ---------------------------------------------------------------------------


@dataclass
class Skill:
    """A fully parsed skill: frontmatter + body + resource manifest.

    >>> s = Skill(meta=SkillMeta(name='test', description='A test'), body='# Hello')
    >>> s.meta.name
    'test'
    """

    meta: SkillMeta
    body: str
    resources: dict[str, list[str]] = field(default_factory=dict)
    source_path: Path | None = None

    @classmethod
    def from_path(cls, path: Path) -> "Skill":
        """Load a Skill from a directory containing SKILL.md.

        ``path`` should be the skill directory (containing SKILL.md).
        """
        skill_md = path / "SKILL.md"
        if not skill_md.exists():
            raise FileNotFoundError(f"No SKILL.md found in {path}")
        meta, body = parse_skill_md(skill_md.read_text())
        resources = discover_resources(path)
        return cls(meta=meta, body=body, resources=resources, source_path=path)

    @classmethod
    def from_string(cls, content: str) -> "Skill":
        """Parse a Skill from a SKILL.md string (no resource discovery).

        >>> s = Skill.from_string("---\\nname: x\\ndescription: y\\n---\\nbody")
        >>> s.meta.name
        'x'
        """
        meta, body = parse_skill_md(content)
        return cls(meta=meta, body=body)

    def to_string(self) -> str:
        """Render this skill as a SKILL.md string."""
        return render_skill_md(self.meta, self.body)

    def write_to(self, path: Path) -> None:
        """Write this skill to a directory, creating SKILL.md and resource dirs."""
        path.mkdir(parents=True, exist_ok=True)
        (path / "SKILL.md").write_text(self.to_string())
        for dirname, files in self.resources.items():
            (path / dirname).mkdir(exist_ok=True)


@dataclass
class SkillInfo:
    """Lightweight metadata for search results (no body).

    >>> si = SkillInfo(canonical_key='owner/test', name='test', description='A test', source='local')
    >>> si.canonical_key
    'owner/test'
    """

    canonical_key: str
    name: str
    description: str
    source: str
    url: str | None = None
    owner: str | None = None
    installed: bool = False

    def __str__(self) -> str:
        marker = "✓" if self.installed else " "
        return f"{marker} {self.canonical_key}  {self.description}  ({self.source})"
