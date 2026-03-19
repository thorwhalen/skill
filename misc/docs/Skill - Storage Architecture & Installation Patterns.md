# Skill: Storage Architecture & Installation Patterns

## Technical Design Document for the `skill` Package

---

## Executive Summary

This document finalizes the storage architecture, symlink strategy, two-tier sourced store design, metadata cache schema, installation safety checks, and key format specification for the `skill` Python package. The design is informed by research into `platformdirs` cross-platform behavior, Windows symlink/junction mechanics, the Vercel `skills` CLI's canonical directory architecture, and the `haggle`/`dol` Mapping-based store patterns.

The central principle is **store once, link many times**: skills live canonically in a single `skill`-managed data directory, and installation into agent-specific directories is done via symlinks (with copy as fallback). This mirrors the architecture the Vercel `skills` CLI has already adopted — `.agents/skills/` as canonical, symlinks to `.claude/skills/`, `.cursor/skills/`, etc. — but wraps it in a Python `Mapping` protocol with transparent two-tier caching for remote skills.

---

## A. Canonical Storage Layout

### A1. Directory Structure

The `skill` package manages three distinct directory categories, following the XDG Base Directory Specification [2] via `platformdirs` [1]:

```
DATA_DIR/                              # platformdirs.user_data_dir("skill")
├── skills/                            # Canonical skill storage (SSOT)
│   ├── anthropics/                    # Owner namespace (from GitHub owner)
│   │   └── frontend-design/           # Skill folder
│   │       ├── SKILL.md               # Frontmatter + body
│   │       ├── scripts/               # Optional executable code
│   │       ├── references/            # Optional docs loaded on demand
│   │       └── assets/                # Optional templates, icons
│   ├── vercel-labs/
│   │   └── react-best-practices/
│   └── _local/                        # Locally-created skills (no remote owner)
│       └── my-custom-skill/
│
CONFIG_DIR/                            # platformdirs.user_config_dir("skill")
├── config.json                        # User preferences, API keys, backend settings
│
CACHE_DIR/                             # platformdirs.user_cache_dir("skill")
├── index.json                         # Merged metadata index of all known skills
├── backends/                          # Per-backend cached metadata
│   ├── github.json
│   ├── skills_sh.json
│   └── agensi.json
└── git/                               # Temporary clones for fetching remote skills
```

**Concrete paths per platform:**

| Directory | Linux | macOS | Windows |
|-----------|-------|-------|---------|
| `DATA_DIR` | `~/.local/share/skill/` | `~/Library/Application Support/skill/` | `%LOCALAPPDATA%\skill\` |
| `CONFIG_DIR` | `~/.config/skill/` | `~/Library/Application Support/skill/` | `%LOCALAPPDATA%\skill\` |
| `CACHE_DIR` | `~/.cache/skill/` | `~/Library/Caches/skill/` | `%LOCALAPPDATA%\skill\Cache\` |

### A2. Nested vs. Flat Layout

**Decision: Nested (`skills/owner/name/`)**

Rationale:

- Mirrors GitHub's `owner/repo` URL structure, which is already the de facto identifier scheme used by the Vercel `skills` CLI and `skills.sh` [6].
- Allows listing all skills by a given owner via simple directory iteration (`os.listdir(data_dir / "skills" / owner)`).
- Avoids the visual noise and ambiguity of delimiter-based flat keys like `owner--name`.
- Consistent with the `haggle` pattern, which uses `owner/dataset` keys mapped to `rootdir/owner/dataset/` on disk [3].

The `_local/` prefix (with leading underscore) is reserved for locally-created skills that have no remote owner. The underscore signals "internal" — consistent with the package's own naming conventions — and avoids collision with any GitHub username.

### A3. Config vs. Data vs. Cache Separation

The three-way separation follows XDG conventions precisely:

- **Config** (`CONFIG_DIR/config.json`): User preferences, API keys (via `$ENV_VAR` references), default agent targets, remote backend toggles. Small, human-editable, version-controllable. On macOS and Windows, `user_config_dir` and `user_data_dir` return the same path [1], so config and data coexist under one parent — this is expected and harmless because we use distinct filenames (`config.json` vs. the `skills/` subdirectory).

- **Data** (`DATA_DIR/skills/`): Actual skill content. This is the SSOT for skill files. Deleting the cache doesn't affect installed skills. Deleting data *does* break symlinks (they become dangling).

- **Cache** (`CACHE_DIR/`): Disposable metadata indices, remote search results, temporary git clones. Safe to delete at any time — the system rebuilds on next access.

### A4. Version Management

**Decision: No multi-version storage in v1.**

Rationale: Skills are not libraries — they don't have dependency resolution or semver compatibility requirements. The Vercel CLI tracks freshness via `skillFolderHash` (a GitHub tree SHA), not versions [6]. For v1, `install` always fetches the latest and overwrites. A future v2 could add a `versions/` subdirectory if needed, but premature version management adds significant complexity (which version do you symlink? how do you pin?) without clear benefit.

The lock file (Section D) tracks the source commit hash, enabling `check` and `update` operations without multi-version storage.

---

## B. Symlink Strategy

### B1. Cross-Platform Symlink Creation

**Primary mechanism: `os.symlink()` with fallback to `_winapi.CreateJunction()` on Windows, then copy as last resort.**

Platform-specific behavior:

| Platform | `os.symlink()` | Requirements | Fallback |
|----------|----------------|--------------|----------|
| Linux | Creates POSIX symlinks | None (works for all users) | Copy |
| macOS | Creates POSIX symlinks | None (works for all users) | Copy |
| Windows ≥ 10 (Developer Mode) | Creates true NTFS symlinks | Developer Mode enabled OR admin | Junction, then copy |
| Windows (no Developer Mode) | Raises `OSError` | N/A | Junction, then copy |

**Windows junction fallback**: Python's `_winapi.CreateJunction()` is a CPython internal that creates NTFS directory junctions without requiring admin privileges or Developer Mode [7][8]. Junctions have two limitations: (a) they only work for directories (not files — fine for us, since skills are directories), and (b) they require absolute paths [8]. Since our canonical paths are absolute, this constraint is acceptable.

**Code sketch:**

```python
import os
import sys
from pathlib import Path

def _create_link(source: Path, target: Path) -> str:
    """Create a symlink (or junction) from target to source.

    Returns 'symlink', 'junction', or 'copy' indicating the method used.
    """
    target.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing link/directory at target
    if target.is_symlink() or (sys.platform == 'win32' and target.is_junction()):
        target.unlink()
    elif target.is_dir():
        # Non-symlink directory exists — don't clobber it silently
        raise FileExistsError(
            f"A non-symlink directory already exists at {target}. "
            "Use --copy to overwrite, or remove it manually."
        )

    # Try symlink first
    try:
        os.symlink(source, target, target_is_directory=True)
        return 'symlink'
    except OSError:
        if sys.platform != 'win32':
            raise  # On Unix, symlink failure is a real error

    # Windows fallback: directory junction (no admin required)
    try:
        import _winapi
        _winapi.CreateJunction(str(source), str(target))
        return 'junction'
    except (ImportError, OSError):
        pass

    # Last resort: full copy
    import shutil
    shutil.copytree(source, target, dirs_exist_ok=True)
    return 'copy'
```

**`pathlib` vs `os` choice**: We use `os.symlink()` directly because `pathlib.Path.symlink_to()` has an inverted argument order that was a source of confusion (it was even deprecated in Python 3.12 in favor of `Path.symlink_to(target)` being renamed). Using `os.symlink(src, dst)` is clearer and consistent with the `os` module's well-documented semantics [7].

Note: `Path.is_junction()` was added in Python 3.12. For Python 3.10–3.11 compatibility, we detect junctions via `os.path.isdir(p) and not os.path.islink(p) and os.readlink(p) != str(p)` (or simply catch the error).

### B2. Symlink Topology

**Global scope** (skills available to the user across all projects):

```
DATA_DIR/skills/anthropics/frontend-design/     # Canonical (SSOT)
    ├── SKILL.md
    └── scripts/

~/.claude/skills/frontend-design/               # Symlink → DATA_DIR/skills/anthropics/frontend-design/
~/.cursor/skills/frontend-design/               # Symlink → DATA_DIR/skills/anthropics/frontend-design/
```

**Project scope** (skills available only within a specific project):

```
DATA_DIR/skills/anthropics/frontend-design/     # Canonical (SSOT) — still here
    ├── SKILL.md
    └── scripts/

./project/.claude/skills/frontend-design/       # Symlink → DATA_DIR/skills/anthropics/frontend-design/
./project/.cursor/skills/frontend-design/       # Symlink → DATA_DIR/skills/anthropics/frontend-design/
```

Note that even for project-scope installations, the canonical source remains in `DATA_DIR`. The symlink simply points from the project's agent directory to the global canonical store. This means:

- Updating a skill in the canonical store propagates instantly to all linked projects.
- Uninstalling from a project just removes the symlink.
- The canonical store is the only place where skill content is written.

### B3. Edge Cases and Safety

**Target directory doesn't exist yet**: Create it with `mkdir(parents=True, exist_ok=True)`. This is safe because we're creating agent-specific subdirectories (like `.claude/skills/`) within directories that the agent tooling already manages (like `.claude/`). If `.claude/` itself doesn't exist, we still create it — but only after the project-root safety check (Section D1).

**Non-symlink skill already exists at target**: Raise `FileExistsError` with a clear message. Never silently overwrite a directory that might contain user-customized content. The `--force` flag can override this.

**Dangling symlinks** (canonical skill deleted, symlinks remain): Detect and clean up via a `skill doctor` command:

```python
def find_dangling_links(agent_skills_dir: Path) -> 'Iterator[Path]':
    """Yield dangling symlinks in an agent's skills directory."""
    if not agent_skills_dir.exists():
        return
    for entry in agent_skills_dir.iterdir():
        if entry.is_symlink() and not entry.resolve().exists():
            yield entry
```

**Vercel CLI compatibility**: The Vercel `skills` CLI uses `~/.agents/skills/` as its canonical store and symlinks from there to agent directories [6]. Our canonical store is `DATA_DIR/skills/` instead. If both tools are used, skills installed by the Vercel CLI live under `~/.agents/skills/` and skills installed by `skill` (Python) live under `DATA_DIR/skills/`. Agent directories may have symlinks pointing to either location. The `skill list` command should detect and report both.

### B4. Symlink vs. Copy Trade-offs

| Aspect | Symlink | Copy |
|--------|---------|------|
| Disk usage | Single copy | N × copies for N agents |
| Updates | Instant propagation | Must reinstall to each agent |
| Dangling risk | Yes (if canonical deleted) | No |
| Windows compatibility | Needs Dev Mode or junction | Always works |
| Tool compatibility | Most tools follow symlinks | Guaranteed |
| `.gitignore` | Symlink itself is a tiny file | Full directory |

**Claude Code and Cursor both follow symlinks** in their skills directories. The Vercel CLI defaults to symlink mode and has been used in production with 40+ agents [6]. Copy mode is provided as a fallback for environments where symlinks are problematic.

---

## C. Two-Tier Sourced Store (`dol` Pattern)

### C1. Architecture

Following the `haggle` pattern [3]: a local `Mapping` (skill files on disk) backed by a remote `Source` (GitHub, skills.sh, etc.), with cache-miss fetch and local write-through.

```python
from collections.abc import MutableMapping, Mapping, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class Skill:
    """Parsed representation of a skill folder."""
    name: str
    description: str
    body: str                          # Markdown body of SKILL.md
    path: Path                         # Canonical path on disk
    owner: Optional[str] = None        # GitHub owner or '_local'
    frontmatter: dict = field(default_factory=dict)  # Full YAML frontmatter
    has_scripts: bool = False
    has_references: bool = False
    has_assets: bool = False


@dataclass
class SkillInfo:
    """Lightweight metadata for search results (no body content)."""
    id: str                            # Canonical key: "owner/skill-name"
    name: str
    description: str
    source: str                        # 'github', 'skills_sh', 'agensi', 'local'
    url: Optional[str] = None          # Remote URL (for fetch)
    author: Optional[str] = None
    last_fetched: Optional[str] = None # ISO datetime


class LocalSkillStore(MutableMapping):
    """Mapping over skill folders in DATA_DIR/skills/.

    Keys: 'owner/skill-name' (e.g., 'anthropics/frontend-design')
    Values: Skill objects (parsed from SKILL.md)
    """

    def __init__(self, root: Path):
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        """Convert 'owner/name' to DATA_DIR/skills/owner/name/."""
        parts = key.split('/', 1)
        if len(parts) == 1:
            return self._root / '_local' / parts[0]
        return self._root / parts[0] / parts[1]

    def _path_to_key(self, path: Path) -> str:
        """Convert DATA_DIR/skills/owner/name/ to 'owner/name'."""
        rel = path.relative_to(self._root)
        return str(rel)

    def __getitem__(self, key: str) -> Skill:
        path = self._key_to_path(key)
        skill_md = path / 'SKILL.md'
        if not skill_md.exists():
            raise KeyError(key)
        return _parse_skill(path)

    def __setitem__(self, key: str, value: Skill) -> None:
        path = self._key_to_path(key)
        _write_skill(path, value)

    def __delitem__(self, key: str) -> None:
        path = self._key_to_path(key)
        if not path.exists():
            raise KeyError(key)
        import shutil
        shutil.rmtree(path)

    def __iter__(self) -> Iterator[str]:
        for owner_dir in sorted(self._root.iterdir()):
            if not owner_dir.is_dir():
                continue
            for skill_dir in sorted(owner_dir.iterdir()):
                if (skill_dir / 'SKILL.md').exists():
                    yield self._path_to_key(skill_dir)

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def __contains__(self, key) -> bool:
        return (self._key_to_path(key) / 'SKILL.md').exists()


class RemoteSkillSource(Mapping):
    """Read-only facade over remote skill backends.

    __getitem__ fetches a skill from the first backend that has it.
    __iter__ yields keys from the metadata cache (not a full remote listing).
    search() performs cross-backend search (not part of Mapping protocol).
    """

    def __init__(self, backends: dict):
        self._backends = backends  # {'github': GitHubBackend, ...}

    def __getitem__(self, key: str) -> Skill:
        for name, backend in self._backends.items():
            try:
                return backend.fetch(key)
            except KeyError:
                continue
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        # Yield from metadata cache, not live remote listing
        return iter(self._load_cached_index())

    def __len__(self) -> int:
        return len(self._load_cached_index())

    def search(self, query: str, *, max_results: int = 10) -> list[SkillInfo]:
        """Cross-backend search. Not part of Mapping protocol."""
        results = []
        for name, backend in self._backends.items():
            results.extend(backend.search(query, max_results=max_results))
        # Deduplicate by id, keeping first occurrence
        seen = set()
        deduped = []
        for r in results:
            if r.id not in seen:
                seen.add(r.id)
                deduped.append(r)
        return deduped[:max_results]

    def _load_cached_index(self) -> dict:
        # Load from CACHE_DIR/index.json
        ...


class SkillStore(MutableMapping):
    """Two-tier sourced store: local + remote with write-through.

    __getitem__: local first, then remote (with automatic local caching).
    __setitem__: writes to local only.
    __delitem__: deletes from local only.
    __iter__: yields local keys only.
    search(): delegates to remote source.
    """

    def __init__(self, local: LocalSkillStore, remote: RemoteSkillSource):
        self._local = local
        self._remote = remote

    def __getitem__(self, key: str) -> Skill:
        try:
            return self._local[key]
        except KeyError:
            pass
        # Cache-miss: fetch from remote and write through
        skill = self._remote[key]
        self._local[key] = skill
        return skill

    def __setitem__(self, key: str, value: Skill) -> None:
        self._local[key] = value

    def __delitem__(self, key: str) -> None:
        del self._local[key]

    def __iter__(self) -> Iterator[str]:
        yield from self._local

    def __len__(self) -> int:
        return len(self._local)

    def search(self, query: str, **kwargs) -> list[SkillInfo]:
        """Delegate search to remote source."""
        return self._remote.search(query, **kwargs)
```

### C2. Multiple Remote Backends

The `RemoteSkillSource` composes multiple backends behind a single `Mapping` interface. Each backend is a simple class with two methods:

```python
class GitHubBackend:
    """Fetch skills from GitHub repositories."""

    def fetch(self, key: str) -> Skill:
        """Clone repo, locate skill, parse and return."""
        ...

    def search(self, query: str, *, max_results: int = 10) -> list[SkillInfo]:
        """Search GitHub for skill repositories."""
        ...
```

Backend resolution order for `__getitem__` is deterministic (dict insertion order). For search, results from all backends are merged and deduplicated.

### C3. Freshness Checking

Following the Vercel CLI's `skillFolderHash` pattern [6], we store a content hash alongside each cached skill:

```python
import hashlib

def _skill_folder_hash(path: Path) -> str:
    """Compute a content hash over all files in a skill folder."""
    hasher = hashlib.sha256()
    for file in sorted(path.rglob('*')):
        if file.is_file():
            hasher.update(str(file.relative_to(path)).encode())
            hasher.update(file.read_bytes())
    return hasher.hexdigest()[:16]
```

The lock file stores this hash (Section D). The `check` command compares local hashes against remote to detect staleness.

---

## D. Lock File & Metadata Cache

### D1. Lock File Schema

Located at `DATA_DIR/skill-lock.json`. Tracks all installed skills and their installation targets:

```json
{
  "version": 1,
  "skills": {
    "anthropics/frontend-design": {
      "source": "github",
      "source_url": "https://github.com/anthropics/skills",
      "source_ref": "main",
      "content_hash": "a1b2c3d4e5f60718",
      "installed_at": "2026-03-15T10:30:00Z",
      "installations": [
        {
          "agent": "claude-code",
          "scope": "global",
          "path": "~/.claude/skills/frontend-design",
          "method": "symlink"
        },
        {
          "agent": "cursor",
          "scope": "project",
          "path": "/home/user/project/.cursor/skills/frontend-design",
          "method": "symlink"
        }
      ]
    }
  }
}
```

### D2. Metadata Cache Schema

Located at `CACHE_DIR/index.json`. A lightweight index built from remote search results, enabling fast local keyword search without network access:

```json
{
  "version": 1,
  "updated_at": "2026-03-15T10:30:00Z",
  "ttl_seconds": 3600,
  "skills": {
    "anthropics/frontend-design": {
      "name": "frontend-design",
      "description": "Create distinctive, production-grade frontend interfaces...",
      "source": "github",
      "url": "https://github.com/anthropics/skills/tree/main/skills/frontend-design",
      "author": "Anthropic",
      "last_fetched": "2026-03-15T10:30:00Z"
    }
  }
}
```

TTL-based invalidation: if `now - updated_at > ttl_seconds`, the index is considered stale and rebuilt on next `search()` call. The stale index is still used for fast results while the fresh one is being fetched in the background (stale-while-revalidate pattern).

---

## E. Installation Safety

### E1. Project-Root Detection

Before creating any agent directory (`.claude/`, `.cursor/`, etc.) in a project, verify we're at a plausible project root:

```python
_PROJECT_MARKERS = {
    '.git', 'pyproject.toml', 'setup.py', 'setup.cfg',
    'package.json', 'Cargo.toml', 'go.mod', 'Makefile',
    'CMakeLists.txt', 'pom.xml', 'build.gradle',
    'Gemfile', 'requirements.txt', '.hg', '.svn',
}

def _is_project_root(path: Path) -> bool:
    """Heuristic: does this directory look like a project root?"""
    return any((path / marker).exists() for marker in _PROJECT_MARKERS)

def _ensure_project_root(path: Path, *, force: bool = False) -> None:
    """Raise or warn if path doesn't look like a project root."""
    if _is_project_root(path):
        return
    if force:
        return  # User explicitly asked to proceed
    raise ValueError(
        f"'{path}' doesn't look like a project root "
        f"(no {', '.join(sorted(_PROJECT_MARKERS)[:5])}...). "
        f"Use --force to create agent directories here anyway."
    )
```

### E2. Atomic Operations

Skill installation follows a write-to-temp-then-rename pattern for the canonical store:

```python
import tempfile
import shutil

def _atomic_write_skill(target: Path, source_dir: Path) -> None:
    """Atomically write a skill folder to the canonical store."""
    tmp = Path(tempfile.mkdtemp(
        dir=target.parent,
        prefix=f'.{target.name}.',
    ))
    try:
        shutil.copytree(source_dir, tmp, dirs_exist_ok=True)
        # Atomic rename (same filesystem)
        if target.exists():
            backup = target.with_suffix('.bak')
            target.rename(backup)
            tmp.rename(target)
            shutil.rmtree(backup)
        else:
            tmp.rename(target)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
```

Symlink creation (`os.symlink`) is already atomic on POSIX systems. On Windows, `_winapi.CreateJunction()` is atomic as well.

### E3. Conflict Resolution

**Same name, different owners**: Fully qualified keys (`owner/name`) prevent collisions in the canonical store. At the agent level, symlinks use only the skill name (e.g., `.claude/skills/frontend-design/`). If two owners provide a skill with the same name, the second install raises `FileExistsError` with a message like: "Skill 'frontend-design' is already installed from 'anthropics'. Use --force to replace it, or --rename to install under a different name."

**Coexistence with Vercel CLI**: The Vercel CLI stores skills in `~/.agents/skills/` (or `.agents/skills/` per project) [6]. Our canonical store is separate (`DATA_DIR/skills/`). Both tools create symlinks into the same agent directories (`.claude/skills/`, etc.). The `skill list` command should detect the symlink target and report the source tool. If both tools try to install the same skill, the second one encounters the existing symlink and warns.

---

## F. Key Format Specification

### F1. Canonical Key Format

```
owner/skill-name
```

Rules:
- **owner**: Lowercase alphanumeric plus hyphens. Maps to GitHub username/org, or `_local` for user-created skills.
- **skill-name**: Lowercase alphanumeric plus hyphens. Matches the directory name on disk.
- **Normalization**: Input keys are lowercased, spaces converted to hyphens, consecutive hyphens collapsed.

Examples:
```
anthropics/frontend-design          # GitHub owner + skill name
vercel-labs/react-best-practices    # GitHub org + skill name
_local/my-custom-skill              # Locally created
```

### F2. Multi-Skill Repositories

Some repos contain multiple skills (e.g., `vercel-labs/agent-skills` has `frontend-design`, `skill-creator`, `web-design-guidelines`, etc.). The key still uses the skill name, not the repo name:

```
vercel-labs/frontend-design         # NOT vercel-labs/agent-skills/frontend-design
```

The lock file stores the full source URL (including repo and path within repo) for provenance, but the key is always `owner/skill-name`. This is consistent with the Vercel CLI, which installs skills by name, not by repo path.

### F3. Key Normalization Function

```python
import re

def normalize_key(raw: str) -> str:
    """Normalize a skill identifier to canonical 'owner/name' form.

    >>> normalize_key('Anthropics/Frontend Design')
    'anthropics/frontend-design'
    >>> normalize_key('my-skill')
    '_local/my-skill'
    >>> normalize_key('  vercel-labs / React--Best--Practices  ')
    'vercel-labs/react-best-practices'
    """
    raw = raw.strip().lower()
    raw = re.sub(r'\s+', '-', raw)     # spaces → hyphens
    raw = re.sub(r'-{2,}', '-', raw)   # collapse multiple hyphens
    raw = raw.strip('-/')              # strip leading/trailing

    parts = raw.split('/', 1)
    if len(parts) == 1:
        return f'_local/{parts[0]}'
    return f'{parts[0]}/{parts[1]}'
```

---

## G. Platform Gotchas and Mitigations

### G1. macOS: Config and Data Share a Directory

On macOS, `platformdirs` returns the same path (`~/Library/Application Support/skill/`) for both `user_data_dir` and `user_config_dir` [1]. This is correct per Apple's guidelines [10] — macOS doesn't separate config from data for non-plist apps. Our code must not assume they're different directories: we use distinct filenames (`config.json` at the root vs. the `skills/` subdirectory) so no collision occurs.

The `user_cache_dir` on macOS is `~/Library/Caches/skill/`, which *is* separate — the system may purge this automatically under disk pressure.

### G2. macOS: `user_config_dir` Points to `~/Library/Preferences`

**Caution**: `platformdirs` currently returns `~/Library/Preferences` for `user_config_dir` on macOS [11]. Apple's documentation explicitly states you should never create files in `~/Library/Preferences` directly — it's reserved for plist files managed by `NSUserDefaults` [10]. This is a known issue in `platformdirs` [11].

**Mitigation**: Use `user_data_dir` for config storage on macOS (which gives `~/Library/Application Support/skill/`), or use `user_config_dir` but override on macOS to `user_data_dir`. Practically, since both return `~/Library/Application Support/skill/` via `platformdirs` version 4.x behavior, this is moot for current versions, but we should pin to the expected behavior:

```python
from platformdirs import user_data_path, user_cache_path

def _config_path() -> Path:
    """Config path — uses data_dir on macOS to avoid ~/Library/Preferences."""
    return user_data_path("skill") / "config.json"
```

### G3. Windows: Symlink Permissions

Windows `os.symlink()` requires either Developer Mode or admin privileges [7]. Since Python 3.8, the `SYMBOLIC_LINK_FLAG_ALLOW_UNPRIVILEGED_CREATE` flag is automatically used if available [7]. Our fallback chain (symlink → junction → copy) handles all Windows configurations transparently.

`_winapi.CreateJunction()` does not require admin or Developer Mode, but only supports directories with absolute paths [8]. Since our canonical store uses absolute paths, this is fine.

### G4. Windows: Junction Limitations

Junctions require absolute paths and only support local paths (not UNC/network paths) [8]. The `pnpm` project documented this as a pain point for multi-device workflows [8]. Since our canonical store is always on the local filesystem, this limitation doesn't affect us. If a user's home directory is on a network drive (roaming profiles), junctions won't work and the copy fallback activates.

### G5. Git and Symlinks

By default, `git` stores symlinks as text files containing the target path. This means `.claude/skills/frontend-design` (a symlink) will be tracked as a text file containing the path to the canonical store. For project-scope installations, this is usually undesirable — `.claude/skills/` should typically be in `.gitignore`.

The `skill install --scope project` command should warn if the target directory isn't gitignored, and offer to add the appropriate entry.

### G6. Vercel CLI Canonical Store Coexistence

The Vercel CLI uses `~/.agents/skills/` as its canonical store for global installs and `.agents/skills/` for project installs [6]. Our package uses `DATA_DIR/skills/` (XDG-compliant, via `platformdirs`). This is deliberate:

- The Vercel CLI's `~/.agents/` convention is simple but non-standard (dotfile in home directory, not XDG-compliant).
- Our XDG-compliant path integrates better with system backup, cleanup, and packaging tools.
- Both tools create symlinks into the same agent directories, so skills from either source are visible to agents.

The `skill list` command should report the symlink target for each installed skill, distinguishing between skills managed by `skill` (Python) and skills managed by `npx skills`.

---

## H. `paths` Module: Single Source of Truth for All Paths

All directory resolution logic is centralized in a single module, ensuring consistency and testability:

```python
"""Path resolution for all skill package directories.

SSOT for canonical store, config, cache, and agent target paths.
"""
from pathlib import Path
from functools import cached_property
from platformdirs import PlatformDirs


class SkillPaths:
    """Resolve all paths used by the skill package.

    >>> p = SkillPaths()
    >>> p.skills_dir  # doctest: +SKIP
    PosixPath('/home/user/.local/share/skill/skills')
    """

    def __init__(self, *, app_name: str = 'skill'):
        self._dirs = PlatformDirs(app_name)

    @cached_property
    def data_dir(self) -> Path:
        """Root data directory."""
        return Path(self._dirs.user_data_dir)

    @cached_property
    def skills_dir(self) -> Path:
        """Canonical skill storage directory."""
        return self.data_dir / 'skills'

    @cached_property
    def config_path(self) -> Path:
        """Config file path (uses data_dir to avoid macOS Preferences issue)."""
        return self.data_dir / 'config.json'

    @cached_property
    def cache_dir(self) -> Path:
        """Cache directory (disposable)."""
        return Path(self._dirs.user_cache_dir)

    @cached_property
    def index_path(self) -> Path:
        """Metadata index cache."""
        return self.cache_dir / 'index.json'

    @cached_property
    def lock_path(self) -> Path:
        """Lock file tracking installations."""
        return self.data_dir / 'skill-lock.json'
```

---

## I. Agent Target Registry

Agent targets are defined declaratively, enabling easy addition of new agents:

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class AgentTarget:
    """Definition of an agent target's directory layout."""
    name: str
    global_skills_dir: Path        # e.g., Path.home() / '.claude' / 'skills'
    project_skills_dir: str        # Relative to project root, e.g., '.claude/skills'
    supports_skill_md: bool = True # Whether agent reads SKILL.md natively
    needs_translation: bool = False
    translation_format: str = ''   # e.g., 'mdc', 'copilot-md', 'windsurf-md'

AGENT_TARGETS = {
    'claude-code': AgentTarget(
        name='claude-code',
        global_skills_dir=Path.home() / '.claude' / 'skills',
        project_skills_dir='.claude/skills',
    ),
    'cursor': AgentTarget(
        name='cursor',
        global_skills_dir=Path.home() / '.cursor' / 'skills',
        project_skills_dir='.cursor/skills',
        needs_translation=True,
        translation_format='mdc',
    ),
    'copilot': AgentTarget(
        name='copilot',
        global_skills_dir=Path.home() / '.github',  # Not truly skill-based
        project_skills_dir='.github',
        needs_translation=True,
        translation_format='copilot-md',
    ),
    'windsurf': AgentTarget(
        name='windsurf',
        global_skills_dir=Path.home() / '.windsurf' / 'rules',
        project_skills_dir='.windsurf/rules',
        needs_translation=True,
        translation_format='windsurf-md',
    ),
    'amp': AgentTarget(
        name='amp',
        global_skills_dir=Path.home() / '.agents' / 'skills',
        project_skills_dir='.agents/skills',
    ),
}
```

---

## REFERENCES

[1] [platformdirs documentation](https://platformdirs.readthedocs.io/en/latest/api.html)  — API reference for `user_data_dir`, `user_config_dir`, `user_cache_dir`, cross-platform path resolution.

[2] [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/) — The standard for Unix user-specific directories.

[3] [haggle (Kaggle Mapping facade)](https://pypi.org/project/haggle/) — Two-tier sourced store pattern: local-first `Mapping` with remote fetch and automatic caching.

[4] [hfdol (HuggingFace Mapping facade)](https://pypi.org/project/hfdol/) — Same pattern as haggle applied to HuggingFace datasets.

[5] [dol (Data Object Layers)](https://pypi.org/project/dol/) — Foundation for `Mapping`-based storage abstractions.

[6] [Vercel skills CLI (vercel-labs/skills)](https://github.com/vercel-labs/skills) — Open source CLI for the agent skills ecosystem. Uses `~/.agents/skills/` as canonical store, symlinks to agent directories, maintains `.skill-lock.json`.

[7] [Python os.symlink documentation](https://docs.python.org/3/library/os.html#os.symlink) — On Windows: requires Developer Mode or admin privileges since Python 3.8; `target_is_directory=True` required for directory symlinks.

[8] [Windows symlinks and junctions](https://learn.microsoft.com/en-us/windows/win32/fileio/creating-symbolic-links) — NTFS junctions don't require admin; only support absolute local paths. Also: pnpm [issue #55](https://github.com/pnpm/symlink-dir/issues/55) documenting junction's absolute-path limitation.

[9] [CPython _winapi.CreateJunction](https://github.com/python/cpython/blob/main/Modules/_winapi.c) — Internal CPython API for creating directory junctions on Windows without admin privileges.

[10] [Apple: Where to Put Your App's Files](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPFileSystem/Articles/WhereToPutFiles.html) — `~/Library/Application Support/` is the correct location for app data and config; `~/Library/Preferences/` is reserved for plist files.

[11] [platformdirs macOS config_dir issue](https://github.com/platformdirs/platformdirs/issues/47) — Discussion about `user_config_dir` returning `~/Library/Preferences` (incorrect per Apple guidelines).

[12] [Python Discussions: Add os.junction](https://discuss.python.org/t/add-os-junction-pathlib-path-junction-to/50394) — Proposal to add junction support to the standard library; includes implementation examples.

[13] [Vercel: Agent Skills Guide](https://vercel.com/kb/guide/agent-skills-creating-installing-and-sharing-reusable-agent-context) — Comprehensive guide covering skill format, installation scopes (project/global), and symlink vs copy modes.
