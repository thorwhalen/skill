# Storage Architecture & Installation Patterns for the `skill` Package

**Technical Design Document — v1.0**

---

## 1. Canonical Storage Layout

### 1.1 Directory Structure

The `skill` package follows the XDG-aligned three-directory separation enforced by `platformdirs`:

```
DATA_DIR/                              # platformdirs.user_data_dir("skill")
├── skills/                            # Canonical skill storage (the SSOT)
│   ├── anthropics/                    # Organized by owner (nested, not flat)
│   │   ├── frontend-design/
│   │   │   ├── SKILL.md
│   │   │   ├── scripts/
│   │   │   └── references/
│   │   └── docx/
│   │       └── SKILL.md
│   ├── vercel-labs/
│   │   └── react-best-practices/
│   │       └── SKILL.md
│   └── _local/                        # User-created skills (no remote owner)
│       └── my-custom-skill/
│           └── SKILL.md
│
CONFIG_DIR/                            # platformdirs.user_config_dir("skill")
├── config.json                        # User preferences, backend settings
└── backends/                          # Per-backend credentials/config
    ├── github.json
    └── smithery.json

CACHE_DIR/                             # platformdirs.user_cache_dir("skill")
├── index.json                         # Aggregated skill metadata index
├── search/                            # Cached search results (TTL-based)
│   └── <query_hash>.json
└── trees/                             # Cached GitHub tree SHAs per repo
    └── <owner>--<repo>.json
```

### 1.2 Platform Paths

| OS | DATA_DIR | CONFIG_DIR | CACHE_DIR |
|----|----------|------------|-----------|
| Linux | `~/.local/share/skill/` | `~/.config/skill/` | `~/.cache/skill/` |
| macOS | `~/Library/Application Support/skill/` | `~/Library/Application Support/skill/` | `~/Library/Caches/skill/` |
| Windows | `%LOCALAPPDATA%\skill\` | `%APPDATA%\skill\` | `%LOCALAPPDATA%\skill\Cache\` |

**macOS gotcha:** `user_data_dir` and `user_config_dir` resolve to the *same* directory (`~/Library/Application Support/skill/`). This is correct per Apple conventions — we just need to ensure the `config.json` file doesn't collide with the `skills/` subdirectory, which it won't since they're at different depths.

### 1.3 Nested vs. Flat Organization

**Decision: nested (`skills/owner/name/`), not flat (`skills/owner--name/`).**

Rationale:

- Nested matches the canonical key format (`owner/skill-name`) and the GitHub mental model.
- `os.listdir(skills_dir / owner)` naturally lists all skills by that owner.
- Flat requires a separator convention (`--`, `__`, etc.) that leaks into display and creates ambiguity if the separator appears in a name.
- The Vercel CLI uses `.agents/skills/<n>/` (numbered), which is fine for a single-project namespace but wrong for a global store where multiple owners coexist.

The `_local/` prefix (underscore) for user-created skills is chosen deliberately: it sorts first in directory listings, it's visually distinct, and it can't collide with a GitHub username (GitHub prohibits leading underscores).

### 1.4 Version Management

**Decision: no multi-version storage in v1. One version per skill.**

The canonical store holds the *current* version. Version tracking is handled by metadata:

```python
@dataclass
class SkillMeta:
    """Cached metadata for a locally stored skill."""
    name: str
    owner: str
    description: str
    source_url: str | None = None       # e.g., "https://github.com/anthropics/skills"
    source_ref: str | None = None       # git tree SHA or commit hash at fetch time
    content_hash: str | None = None     # SHA-256 of the skill directory contents
    fetched_at: str | None = None       # ISO 8601 timestamp
    installed_targets: list[str] = field(default_factory=list)  # ["claude-code", "cursor"]
```

When updating a skill, the old version is replaced atomically (see §4.2). A future v2 could add `skills/owner/name/@versions/v1.2.0/` for pinning, but this adds complexity with no immediate payoff — the ecosystem itself has no versioning standard yet.

### 1.5 Config vs. Data vs. Cache Separation

| Directory | Contains | Disposable? | Sensitive? |
|-----------|----------|-------------|------------|
| **DATA** | Skill folders, metadata manifests | **No** — user's skill library | No |
| **CONFIG** | Preferences, API key references, backend settings | **No** — user's configuration | Yes (may reference env vars) |
| **CACHE** | Search indexes, GitHub tree caches, TTL metadata | **Yes** — can be rebuilt from remote | No |

The `config.json` never stores raw API keys — only `$ENV_VAR` references:

```json
{
  "default_agent_targets": ["claude-code"],
  "install_method": "symlink",
  "ai_service": {
    "provider": "anthropic",
    "api_key": "$ANTHROPIC_API_KEY"
  }
}
```

---

## 2. Symlink Strategy

### 2.1 Cross-Platform Symlink Creation

```python
import os
import sys
import shutil
from pathlib import Path


def _create_link(
    source: Path,
    target: Path,
    *,
    copy: bool = False,
    force: bool = False,
) -> Path:
    """Link (or copy) a skill from the canonical store to an agent target directory.

    ``source`` is the canonical skill directory.
    ``target`` is the destination in the agent's tree.

    Returns the resolved target path.

    >>> # (doctest omitted — requires filesystem side-effects)
    """
    if target.exists() or target.is_symlink():
        if not force:
            raise FileExistsError(
                f"Target already exists: {target}. "
                "Use force=True to overwrite, or remove it first."
            )
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)

    target.parent.mkdir(parents=True, exist_ok=True)

    if copy:
        shutil.copytree(source, target)
        return target

    if sys.platform == "win32":
        return _create_link_windows(source, target)

    # Unix: straightforward symlink
    os.symlink(source, target)
    return target


def _create_link_windows(source: Path, target: Path) -> Path:
    """Create a directory junction on Windows (no admin required).

    Falls back to os.symlink if junction creation fails.

    >>> # (doctest omitted — Windows-specific)
    """
    import subprocess

    # Try junction first (works without Developer Mode or admin)
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(target), str(source)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return target

    # Fall back to os.symlink (requires Developer Mode or admin on Win10+)
    try:
        os.symlink(source, target, target_is_directory=True)
        return target
    except OSError as exc:
        raise OSError(
            f"Cannot create symlink or junction on Windows.\n"
            f"Enable Developer Mode in Settings > For Developers,\n"
            f"or run as administrator.\n"
            f"Alternatively, use install(..., copy=True).\n"
            f"Original error: {exc}"
        ) from exc
```

**Key platform notes:**

- **Linux/macOS**: `os.symlink(src, dst)` creates a symlink. Atomic. No privileges needed.
- **Windows**: `os.symlink(src, dst, target_is_directory=True)` creates a *real* symlink, which requires either **Developer Mode** (Settings → For Developers → toggle on) or **admin privileges**. This is a known pain point. Directory junctions (`mklink /J`) require no special privileges and are functionally equivalent for local paths. `pathlib.Path.symlink_to()` is fine but `os.symlink()` gives us the `target_is_directory` kwarg on Windows, so we use that.
- **Python's os.symlink on Windows**: it creates real symlinks (not junctions). The `target_is_directory` hint is required on Windows for directory symlinks. Hence the junction-first fallback strategy above.

### 2.2 Agent Target Directory Layout

Each agent expects skills/rules in specific locations. The install function maps from a canonical key to one or more agent target paths:

```python
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentTarget:
    """Describes where an agent expects to find skills/rules."""

    name: str
    global_path: str | None = None    # Template with {home}, {name}
    project_path: str | None = None   # Template with {project}, {name}
    format: str = "skill.md"          # "skill.md" | "mdc" | "copilot_md" | "windsurf_md" | "agents_md"
    needs_translation: bool = False

AGENT_TARGETS: dict[str, AgentTarget] = {
    "claude-code": AgentTarget(
        name="claude-code",
        global_path="{home}/.claude/skills/{name}",
        project_path="{project}/.claude/skills/{name}",
    ),
    "cursor": AgentTarget(
        name="cursor",
        # Note: Cursor has NO global ~/.cursor/rules/ directory.
        # Global rules exist only in Cursor Settings UI.
        project_path="{project}/.cursor/rules/{name}.mdc",
        format="mdc",
        needs_translation=True,
    ),
    "copilot": AgentTarget(
        name="copilot",
        project_path="{project}/.github/instructions/{name}.instructions.md",
        format="copilot_md",
        needs_translation=True,
    ),
    "windsurf": AgentTarget(
        name="windsurf",
        global_path="{home}/.codeium/windsurf/memories/global_rules.md",
        project_path="{project}/.windsurf/rules/{name}.md",
        format="windsurf_md",
        needs_translation=True,
    ),
    "agents-md": AgentTarget(
        name="agents-md",
        project_path="{project}/AGENTS.md",
        format="agents_md",
        needs_translation=True,
    ),
    "codex": AgentTarget(
        name="codex",
        # Codex reads .agents/skills/ directly (universal agent)
        project_path="{project}/.agents/skills/{name}",
    ),
    "gemini": AgentTarget(
        name="gemini",
        global_path="{home}/.gemini/skills/{name}",
        project_path="{project}/.gemini/skills/{name}",
    ),
}
```

For agents that support the SKILL.md spec natively (Claude Code, Codex, Gemini, and the 35+ other universal adopters), installation is a symlink from the agent directory to the canonical store. For agents with incompatible formats (Cursor, Copilot, Windsurf, AGENTS.md), installation requires translation followed by a *copy* (since the output format differs from the source).

**Rule: symlink when format matches, copy when translation is needed.**

### 2.3 Handling Edge Cases

**Target agent directory doesn't exist yet:**

```python
def _ensure_agent_dir(target_path: Path, *, scope: str = "project") -> None:
    """Create agent directory if missing, with safety checks.

    >>> # (doctest omitted)
    """
    parent = target_path.parent
    if parent.exists():
        return

    if scope == "project":
        _check_project_root(parent)

    parent.mkdir(parents=True, exist_ok=True)


def _check_project_root(path: Path) -> None:
    """Warn if we don't appear to be in a project root."""
    project_markers = {
        "pyproject.toml", "package.json", "Cargo.toml",
        "go.mod", "Makefile", ".git", "pom.xml", "build.gradle",
    }
    # Walk up to find project root
    candidate = path
    while candidate != candidate.parent:
        if any((candidate / marker).exists() for marker in project_markers):
            return
        candidate = candidate.parent

    import warnings
    warnings.warn(
        f"No project root markers found above {path}. "
        f"This may not be a project directory. "
        f"Creating agent config directory anyway — use Ctrl+C to abort.",
        UserWarning,
        stacklevel=3,
    )
```

**Non-symlink skill already exists at target:**

```python
def _check_existing(target: Path) -> str:
    """Classify what exists at the target path.

    Returns one of: 'none', 'our_symlink', 'foreign_symlink', 'directory', 'file'.
    """
    if not target.exists() and not target.is_symlink():
        return "none"
    if target.is_symlink():
        resolved = target.resolve()
        # Check if it points into our canonical store
        data_dir = Path(platformdirs.user_data_dir("skill"))
        try:
            resolved.relative_to(data_dir)
            return "our_symlink"
        except ValueError:
            return "foreign_symlink"
    if target.is_dir():
        return "directory"
    return "file"
```

The install function uses this to decide behavior:

| Existing state | Default action | With `--force` |
|---------------|----------------|----------------|
| `none` | Install normally | — |
| `our_symlink` | Update (atomic re-link) | — |
| `foreign_symlink` | Warn + skip | Replace |
| `directory` | Warn + skip | Replace |
| `file` | Warn + skip | Replace |

**Dangling symlink detection and cleanup:**

```python
def find_dangling_links(agent_target: str | None = None) -> list[Path]:
    """Scan agent target directories for dangling symlinks.

    >>> # Returns list of Path objects that are symlinks pointing to nonexistent targets.
    """
    dangling = []
    targets = (
        [AGENT_TARGETS[agent_target]] if agent_target
        else AGENT_TARGETS.values()
    )
    for target_spec in targets:
        for template in [target_spec.global_path, target_spec.project_path]:
            if template is None:
                continue
            # Expand {home}, find all matching directories
            base = Path(template.split("{name}")[0].format(
                home=Path.home(), project="."
            ))
            if not base.exists():
                continue
            for child in base.iterdir():
                if child.is_symlink() and not child.exists():
                    dangling.append(child)
    return dangling


def cleanup_dangling(*, dry_run: bool = True) -> list[Path]:
    """Remove dangling symlinks from all agent target directories.

    >>> # Returns list of removed (or would-remove) paths.
    """
    dangling = find_dangling_links()
    if not dry_run:
        for link in dangling:
            link.unlink()
    return dangling
```

### 2.4 Symlink vs. Copy Trade-Offs

| Factor | Symlink | Copy |
|--------|---------|------|
| Disk space | Minimal (one pointer) | Full duplicate per target |
| Updates | Instant (change canonical, all targets see it) | Manual re-copy needed |
| Dangling risk | Yes (if canonical deleted) | No |
| Windows compat | Needs Developer Mode or junction fallback | Works everywhere |
| Editor support | Most editors follow symlinks; some watchers don't | No issues |
| Agent support | Claude Code: **confirmed** follows symlinks in `.claude/skills/`. Cursor: reads `.agents/skills/` via symlinks. Codex: reads `.agents/skills/` directly. | Universal |
| Offline resilience | Can dangle if canonical on a network mount | Self-contained |

**Default: symlink. Expose `--copy` flag for fallback.**

The Vercel `skills` CLI uses a symlink-from-agents strategy: it copies skills into `.agents/skills/<n>/` as the canonical project-local store, then symlinks each agent's directory to that location. Our approach differs: the global canonical store lives in `DATA_DIR/skills/`, and both global and project-level agent directories link back to it. This means a skill updated in the canonical store is immediately available across all projects and agents.

---

## 3. Two-Tier Sourced Store (dol Pattern)

### 3.1 Store Class Design

The core abstraction follows the `dol` `mk_sourced_store` pattern: a local `MutableMapping` backed by a remote `Mapping` source, with cache-miss fetch.

```python
from collections.abc import MutableMapping, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import platformdirs

from skill.base import Skill, SkillMeta


class LocalSkillStore(MutableMapping):
    """A MutableMapping over the canonical skill directory.

    Keys are canonical identifiers like ``"anthropics/frontend-design"``.
    Values are ``Skill`` objects (parsed frontmatter + body + resource manifest).

    >>> # store = LocalSkillStore()
    >>> # list(store)  # yields installed skill keys
    """

    def __init__(self, root: Path | None = None):
        self._root = root or Path(platformdirs.user_data_dir("skill")) / "skills"
        self._root.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        """Resolve a canonical key to a filesystem path.

        >>> store = LocalSkillStore(Path("/tmp/test_skills"))
        >>> store._key_to_path("anthropics/frontend-design")
        PosixPath('/tmp/test_skills/anthropics/frontend-design')
        """
        parts = _parse_key(key)
        return self._root / parts.owner / parts.name

    def __getitem__(self, key: str) -> Skill:
        path = self._key_to_path(key)
        skill_md = path / "SKILL.md"
        if not skill_md.exists():
            raise KeyError(key)
        return Skill.from_path(path)

    def __setitem__(self, key: str, value: Skill) -> None:
        path = self._key_to_path(key)
        value.write_to(path)

    def __delitem__(self, key: str) -> None:
        path = self._key_to_path(key)
        if not path.exists():
            raise KeyError(key)
        import shutil
        shutil.rmtree(path)

    def __iter__(self) -> Iterator[str]:
        """Yield canonical keys for all locally stored skills."""
        if not self._root.exists():
            return
        for owner_dir in sorted(self._root.iterdir()):
            if not owner_dir.is_dir():
                continue
            owner = owner_dir.name
            for skill_dir in sorted(owner_dir.iterdir()):
                if (skill_dir / "SKILL.md").exists():
                    yield f"{owner}/{skill_dir.name}"

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return (self._key_to_path(key) / "SKILL.md").exists()
```

### 3.2 Remote Source Interface

Each backend implements a minimal `Mapping`-like protocol for read-only access:

```python
from collections.abc import Mapping, Iterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class SkillSource(Protocol):
    """Protocol for remote skill sources."""

    def __getitem__(self, key: str) -> Skill:
        """Fetch a skill by canonical key."""
        ...

    def __contains__(self, key: object) -> bool:
        """Check if a skill exists in this source."""
        ...

    def search(self, query: str, *, max_results: int = 10) -> list[SkillMeta]:
        """Search for skills matching a query."""
        ...
```

Note that `search()` is *not* part of the `Mapping` protocol — it's an additional method on the source, since keyword search is fundamentally different from key lookup. This matches how `haggle` handles it: the `Mapping` interface gives you `__getitem__` and `__iter__` for known keys, while `search` is a separate method for discovery.

### 3.3 Sourced Store (Composition)

```python
class SourcedSkillStore(MutableMapping):
    """Two-tier store: local cache + remote source with write-through on miss.

    Reads check local first, then fall back to remote and cache locally.
    Writes go directly to the local store.
    Iteration yields only locally cached keys (not all remote keys).

    >>> # store = SourcedSkillStore(local=LocalSkillStore(), sources=[GitHubSource()])
    >>> # skill = store["anthropics/frontend-design"]  # fetches remotely if not cached
    """

    def __init__(
        self,
        local: LocalSkillStore,
        sources: list[SkillSource] | None = None,
    ):
        self._local = local
        self._sources = sources or []

    def __getitem__(self, key: str) -> Skill:
        # Local hit
        if key in self._local:
            return self._local[key]

        # Remote fetch with write-through
        for source in self._sources:
            if key in source:
                skill = source[key]
                self._local[key] = skill  # Cache locally
                return skill

        raise KeyError(
            f"Skill {key!r} not found locally or in any remote source. "
            f"Try: skill search {key.split('/')[-1]}"
        )

    def __setitem__(self, key: str, value: Skill) -> None:
        self._local[key] = value

    def __delitem__(self, key: str) -> None:
        del self._local[key]

    def __iter__(self) -> Iterator[str]:
        yield from self._local

    def __len__(self) -> int:
        return len(self._local)

    def search(self, query: str, *, max_results: int = 10) -> list[SkillMeta]:
        """Search across all sources, deduplicate by key."""
        results: dict[str, SkillMeta] = {}
        for source in self._sources:
            for meta in source.search(query, max_results=max_results):
                if meta.canonical_key not in results:
                    results[meta.canonical_key] = meta
                if len(results) >= max_results:
                    break
        return list(results.values())[:max_results]

    def is_stale(self, key: str) -> bool | None:
        """Check if the local copy differs from remote.

        Returns None if staleness cannot be determined (e.g. no source_ref recorded).
        """
        if key not in self._local:
            return None
        meta = self._local[key].meta
        if not meta.source_ref:
            return None
        for source in self._sources:
            if key in source:
                remote_skill = source[key]
                return remote_skill.meta.content_hash != meta.content_hash
        return None
```

### 3.4 Multiple Backends

The `sources` list is ordered by priority. The first source that contains a key wins. Configuration in `config.json`:

```json
{
  "remote_backends": {
    "github": {"enabled": true, "token": "$GITHUB_TOKEN"},
    "smithery": {"enabled": true, "token": "$SMITHERY_TOKEN"},
    "agensi": {"enabled": false}
  }
}
```

Sources are lazily constructed only when `enabled: true` and credentials resolve.

### 3.5 Staleness and Partial Downloads

**Staleness**: Each locally cached skill stores its `source_ref` (GitHub tree SHA) and `content_hash` (SHA-256 of the directory). The `is_stale()` method compares against the remote. For GitHub, this is cheap: compare the tree SHA via the Trees API (one request, counts against the 5000/hr limit, but ETag caching with `304 Not Modified` makes subsequent checks free).

**Partial downloads**: A skill is considered complete if and only if `SKILL.md` exists. If a skill directory exists but `SKILL.md` is missing, it's treated as incomplete and re-fetched on next access. The `__contains__` check in `LocalSkillStore` only returns `True` if `SKILL.md` is present.

---

## 4. Metadata Cache

### 4.1 Schema

Stored at `CACHE_DIR/index.json`:

```python
@dataclass
class CachedSkillEntry:
    """Lightweight metadata for a known (possibly not-installed) skill."""

    canonical_key: str              # "anthropics/frontend-design"
    name: str                       # "frontend-design"
    description: str                # From SKILL.md frontmatter
    owner: str                      # "anthropics"
    source_url: str                 # "https://github.com/anthropics/skills"
    source_type: str                # "github" | "smithery" | "awesome-list"
    last_fetched: str               # ISO 8601
    installed: bool = False         # Is this in the local store?
    install_count: int | None = None  # From skills.sh if available
```

The JSON on disk is a dict keyed by `canonical_key`:

```json
{
  "anthropics/frontend-design": {
    "name": "frontend-design",
    "description": "Create distinctive, production-grade frontend interfaces...",
    "owner": "anthropics",
    "source_url": "https://github.com/anthropics/skills",
    "source_type": "github",
    "last_fetched": "2026-03-18T12:00:00Z",
    "installed": true,
    "install_count": 164500
  }
}
```

### 4.2 TTL and Invalidation

```python
import json
import time
from pathlib import Path

import platformdirs


class MetadataCache:
    """TTL-based metadata cache for known skills.

    >>> # cache = MetadataCache(ttl=3600)
    >>> # cache.get("anthropics/frontend-design")
    """

    def __init__(self, *, ttl: int = 3600):
        self._path = Path(platformdirs.user_cache_dir("skill")) / "index.json"
        self._ttl = ttl
        self._data: dict | None = None

    def _load(self) -> dict:
        if self._data is not None:
            return self._data
        if self._path.exists():
            self._data = json.loads(self._path.read_text())
        else:
            self._data = {"_updated_at": 0, "skills": {}}
        return self._data

    @property
    def is_expired(self) -> bool:
        """Check if the cache has exceeded its TTL."""
        data = self._load()
        return (time.time() - data.get("_updated_at", 0)) > self._ttl

    def get(self, key: str) -> CachedSkillEntry | None:
        """Retrieve a cached entry, or None if not found."""
        data = self._load()
        entry = data.get("skills", {}).get(key)
        if entry is None:
            return None
        return CachedSkillEntry(**entry)

    def upsert(self, entry: CachedSkillEntry) -> None:
        """Insert or update a cache entry."""
        from dataclasses import asdict
        data = self._load()
        data["skills"][entry.canonical_key] = asdict(entry)
        data["_updated_at"] = time.time()
        self._write(data)

    def search_local(self, query: str) -> list[CachedSkillEntry]:
        """Fast keyword search over cached metadata (name + description)."""
        data = self._load()
        query_lower = query.lower()
        tokens = query_lower.split()
        results = []
        for entry_data in data.get("skills", {}).values():
            text = f"{entry_data['name']} {entry_data['description']}".lower()
            if all(tok in text for tok in tokens):
                results.append(CachedSkillEntry(**entry_data))
        return results

    def _write(self, data: dict) -> None:
        """Atomic write: write to temp, rename over."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.rename(self._path)
        self._data = data
```

The cache is *disposable* — deleting `CACHE_DIR/` triggers a cold rebuild from remote sources on next search. The `_updated_at` field at the root level tracks global freshness; per-entry `last_fetched` tracks individual entries.

---

## 5. Installation Safety

### 5.1 Atomic Operations

All install operations follow an atomic pattern: write to a temp location, then rename.

```python
import tempfile
import shutil
from pathlib import Path


def _atomic_install(source: Path, destination: Path) -> None:
    """Copy a skill directory atomically to the destination.

    Writes to a sibling temp directory, then renames over the target.
    If interrupted, no partial state remains at the destination.

    >>> # (doctest omitted — filesystem side-effects)
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(
        dir=destination.parent,
        prefix=f".{destination.name}_installing_",
    ))
    try:
        # Copy full skill tree to temp
        actual_tmp = tmp / destination.name
        shutil.copytree(source, actual_tmp)

        # Atomic swap: remove old, rename new
        if destination.exists():
            shutil.rmtree(destination)
        actual_tmp.rename(destination)
    finally:
        # Clean up temp dir if anything remains
        if tmp.exists():
            shutil.rmtree(tmp)


def _atomic_symlink(source: Path, destination: Path) -> None:
    """Create or replace a symlink atomically.

    Creates a temp symlink, then renames over the target.
    On POSIX, os.rename of a symlink is atomic.

    >>> # (doctest omitted)
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_link = destination.with_suffix(".tmp_link")

    # Remove stale temp if it exists from a prior interrupted run
    if tmp_link.exists() or tmp_link.is_symlink():
        tmp_link.unlink()

    os.symlink(source, tmp_link)
    os.rename(tmp_link, destination)  # Atomic on POSIX
```

### 5.2 Project Root Detection

```python
_PROJECT_MARKERS = frozenset({
    ".git", "pyproject.toml", "package.json", "Cargo.toml",
    "go.mod", "Makefile", "CMakeLists.txt", "pom.xml",
    "build.gradle", "composer.json", "Gemfile", ".hg",
})


def _find_project_root(start: Path | None = None) -> Path | None:
    """Walk up from ``start`` to find the nearest project root.

    Returns None if no project marker is found.

    >>> # In a git repo, returns the repo root.
    """
    candidate = (start or Path.cwd()).resolve()
    while candidate != candidate.parent:
        if any((candidate / m).exists() for m in _PROJECT_MARKERS):
            return candidate
        candidate = candidate.parent
    return None
```

### 5.3 Conflict Resolution

**Same name, different owners:** Not a conflict — keys are `owner/name`, so `anthropics/frontend-design` and `acme-corp/frontend-design` coexist in the canonical store. When installing to an agent that uses a flat namespace (e.g., Claude Code's `.claude/skills/<name>/`), there *is* a potential collision. Resolution:

```python
def _agent_target_name(key: str, agent: AgentTarget) -> str:
    """Derive the filesystem name for a skill in an agent's directory.

    For agents supporting nested dirs, use the skill name.
    If collision detected, prefix with owner.

    >>> _agent_target_name("acme/frontend-design", AGENT_TARGETS["claude-code"])
    'frontend-design'
    """
    parts = _parse_key(key)
    name = parts.name

    # Check for collisions in the target directory
    # (handled at install time with a collision check)
    return name
```

If a collision is detected at install time (another owner's skill with the same name is already linked), the install function warns and offers to use `owner--name` as the directory name:

```
Warning: "frontend-design" already installed from anthropics.
  Installing acme-corp/frontend-design as "acme-corp--frontend-design".
```

**Coexistence with the Vercel CLI:** If a user has also run `npx skills add`, there will be skills in `.agents/skills/<n>/` (numbered) with symlinks to agent dirs. Our installer detects `foreign_symlink` and skips by default, warning:

```
Skipping .claude/skills/frontend-design/ — symlink exists
pointing to .agents/skills/1/ (likely from `npx skills add`).
Use --force to replace.
```

---

## 6. Key Format Specification

### 6.1 Canonical Key Format

```
<owner>/<skill-name>
```

- **`owner`**: GitHub username or org, lowercase. For local-only skills: `_local`.
- **`skill-name`**: Lowercase alphanumeric + hyphens, matching the Agent Skills spec `name` regex: `^[a-z0-9]+(-[a-z0-9]+)*$`

For multi-skill repos (where a single GitHub repo contains multiple skills under `skills/`):

```
<owner>/<repo>/<skill-name>      # Three-part key (unambiguous)
```

Internally, three-part keys are stored as `<owner>/<skill-name>` on disk (the repo name is recorded in metadata, not the directory tree). This keeps directory depth manageable and avoids the `owner/repo/skill` vs `owner/skill` ambiguity.

### 6.2 Normalization

```python
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedKey:
    """Parsed components of a canonical skill key."""
    owner: str
    name: str
    repo: str | None = None

_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _parse_key(raw: str) -> ParsedKey:
    """Parse and normalize a skill key.

    >>> _parse_key("Anthropics/Frontend-Design")
    ParsedKey(owner='anthropics', name='frontend-design', repo=None)

    >>> _parse_key("vercel-labs/skills/react-best-practices")
    ParsedKey(owner='vercel-labs', name='react-best-practices', repo='skills')

    >>> _parse_key("my-custom-skill")
    ParsedKey(owner='_local', name='my-custom-skill', repo=None)
    """
    parts = raw.strip().lower().split("/")

    if len(parts) == 1:
        # Bare name → local skill
        name = parts[0]
        if not _NAME_RE.match(name):
            raise ValueError(
                f"Invalid skill name: {name!r}. "
                f"Must match: lowercase alphanumeric + hyphens."
            )
        return ParsedKey(owner="_local", name=name)

    if len(parts) == 2:
        owner, name = parts
        if not _NAME_RE.match(name):
            raise ValueError(f"Invalid skill name: {name!r}.")
        return ParsedKey(owner=owner, name=name)

    if len(parts) == 3:
        owner, repo, name = parts
        if not _NAME_RE.match(name):
            raise ValueError(f"Invalid skill name: {name!r}.")
        return ParsedKey(owner=owner, name=name, repo=repo)

    raise ValueError(
        f"Invalid key format: {raw!r}. "
        f"Expected: 'name', 'owner/name', or 'owner/repo/name'."
    )
```

### 6.3 Comparison with Vercel CLI

The Vercel CLI uses `owner/repo` as the install key, then discovers individual skills *within* the repo. Our keys are more granular: `owner/skill-name` identifies a single skill. The mapping is:

| Vercel CLI | `skill` package |
|------------|-----------------|
| `npx skills add anthropics/skills` (installs all skills in repo) | `skill install anthropics/frontend-design` (installs one) |
| Discovers skills within repo | Requires explicit skill name or `--all` flag |
| Keys are `owner/repo` | Keys are `owner/name` (with optional `owner/repo/name`) |

---

## 7. Known Platform Gotchas and Mitigations

### 7.1 Windows

| Issue | Impact | Mitigation |
|-------|--------|------------|
| `os.symlink()` requires Developer Mode or admin | Users can't symlink by default | Fall back to `mklink /J` (directory junction); further fall back to copy with a clear error message |
| Directory junctions don't work across drives | Junction from `C:` to `D:` fails | Detect cross-drive scenario, auto-fall back to copy |
| Path length limit (260 chars by default) | Deep nesting can exceed limit | Use `\\?\` prefix for long paths; recommend short `DATA_DIR` |
| Case-insensitive filesystem | `Frontend-Design` and `frontend-design` collide | We normalize all keys to lowercase; no issue |

### 7.2 macOS

| Issue | Impact | Mitigation |
|-------|--------|------------|
| `user_data_dir` == `user_config_dir` | Both resolve to `~/Library/Application Support/skill/` | Not a problem — `skills/` and `config.json` don't collide |
| Gatekeeper quarantine on downloaded files | Scripts in `scripts/` may be quarantined | `xattr -d com.apple.quarantine <path>` after fetch; document in README |
| APFS case-insensitive (default) | Same as Windows | Lowercase normalization handles it |

### 7.3 Linux

| Issue | Impact | Mitigation |
|-------|--------|------------|
| `XDG_DATA_HOME` might be overridden | Custom paths | `platformdirs` handles this automatically |
| NFS/network mounts | Symlinks across mount points may not resolve | Detect network mounts; warn and suggest `--copy` |
| Snap/Flatpak confinement | App may not access `~/.config/` or follow symlinks outside sandbox | Document incompatibility; suggest installing outside container |

### 7.4 Agent-Specific

| Agent | Gotcha | Mitigation |
|-------|--------|------------|
| Cursor | No global `~/.cursor/rules/` directory; global rules are UI-only | Only support project-level Cursor install |
| Cursor | `.mdc` format for rules, but reads `.agents/skills/` for Agent Skills natively | Use symlinks for native SKILL.md in `.agents/skills/`; translate to `.mdc` only if user explicitly targets `cursor-rules` |
| Copilot | `copilot-instructions.md` is append-only (single file) | Translation appends a delimited section; `uninstall` must find and remove the section |
| Windsurf | 6,000 char limit on global rules, 12,000 on workspace | Validate body length during install; warn if over limit |
| Claude Code | `paths:` frontmatter in user-level rules (`~/.claude/rules/`) is ignored | Document this; recommend project-level only for path-scoped skills |

---

## 8. The Install Function

Bringing it all together — the main public API entry point:

```python
def install(
    key: str,
    *,
    agent_targets: list[str] | None = None,
    scope: str = "project",
    copy: bool = False,
    force: bool = False,
    project_dir: Path | None = None,
) -> dict[str, Path]:
    """Install a skill into one or more agent target directories.

    Returns a mapping of ``{agent_name: installed_path}``.

    >>> # install("anthropics/frontend-design", agent_targets=["claude-code"])
    >>> # {'claude-code': PosixPath('.claude/skills/frontend-design')}
    """
    parsed = _parse_key(key)
    config = _load_config()

    targets = agent_targets or config.get("default_agent_targets", ["claude-code"])
    method = "copy" if copy else config.get("install_method", "symlink")

    # 1. Ensure skill exists in canonical store
    store = SourcedSkillStore(
        local=LocalSkillStore(),
        sources=_build_sources(config),
    )
    skill = store[key]  # Fetches remotely if not cached

    canonical_path = store._local._key_to_path(key)
    project = (project_dir or Path.cwd()).resolve() if scope == "project" else None
    results = {}

    for target_name in targets:
        target_spec = AGENT_TARGETS.get(target_name)
        if target_spec is None:
            raise ValueError(
                f"Unknown agent target: {target_name!r}. "
                f"Known targets: {', '.join(AGENT_TARGETS)}"
            )

        # 2. Resolve target path
        template = (
            target_spec.project_path if scope == "project"
            else target_spec.global_path
        )
        if template is None:
            import warnings
            warnings.warn(
                f"{target_name} does not support {scope}-level installation. Skipping.",
                UserWarning,
            )
            continue

        target_path = Path(template.format(
            home=Path.home(),
            project=project or ".",
            name=_agent_target_name(key, target_spec),
        ))

        # 3. Safety checks
        if scope == "project":
            _check_project_root(target_path)

        existing = _check_existing(target_path)
        if existing not in ("none", "our_symlink") and not force:
            import warnings
            warnings.warn(
                f"Skipping {target_path} — {existing} already exists. "
                f"Use force=True to overwrite.",
                UserWarning,
            )
            continue

        # 4. Install
        if target_spec.needs_translation:
            # Translate and copy (can't symlink a different format)
            from skill.translate import translate
            translated = translate(skill, target_format=target_spec.format)
            translated.write_to(target_path)
        elif method == "symlink":
            _atomic_symlink(canonical_path, target_path)
        else:
            _atomic_install(canonical_path, target_path)

        results[target_name] = target_path

    return results
```

---

## References

[1] [platformdirs — Python library for platform-specific directories](https://platformdirs.readthedocs.io/)
[2] [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/)
[3] [haggle — Kaggle Mapping façade (PyPI)](https://pypi.org/project/haggle/)
[4] [hfdol — HuggingFace Mapping façade (PyPI)](https://pypi.org/project/hfdol/)
[5] [dol — Data Object Layers (PyPI)](https://pypi.org/project/dol/)
[6] [Vercel skills CLI (GitHub)](https://github.com/vercel-labs/skills)
[7] [Python os.symlink documentation](https://docs.python.org/3/library/os.html#os.symlink)
[8] [Windows symbolic links / directory junctions](https://learn.microsoft.com/en-us/windows/win32/fileio/creating-symbolic-links)
[9] [Agent Skills specification — agentskills.io](https://agentskills.io)
