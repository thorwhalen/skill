---
name: skill-enable
description: >-
  Ship a Python package's AI agent skills with `pip install` — and decide WHICH
  skills to ship. Use when the user asks how to include skills in their package
  distribution, make skills available after `pip install`, ship SKILL.md files
  with their package, set up `{pkg}/data/skills/`, configure package-data, add a
  skills installer/convenience function, or says "how do users get my skills
  after pip install", "ship skills with my package", "distribute skills",
  "package skills", or "enable skills in my library". Also trigger when working
  on pyproject.toml and the project has skills to distribute. The overall layout
  decision (where real files live, the `.claude/skills/` symlink bridge, spec
  compliance) is owned by **skill-package-setup**; this skill covers the
  pip-distribution mechanics and audience classification.
metadata:
  audience: developers
---

# Skill enablement — shipping skills via pip

How to ship a package's **consumer** skills with `pip install your-package`, and
how to decide which skills qualify. Layout and spec compliance are owned by the
**skill-package-setup** skill — read it first if you haven't picked a layout.

## Where pip-shipped skills go (and why it just works)

To ride along with `pip install`, skill files must live **inside the importable
package**: `{pkg}/data/skills/<name>/`. That's the only place a wheel reliably
ships non-code data.

Bonus: `{pkg}/data/skills/` is **also a first-class `gh skill` source** —
`gh skill` discovers any non-hidden `**/skills/*/SKILL.md`, and `{pkg}/data/skills/`
contains a `skills/` dir under the non-hidden prefix `{pkg}/data/`. So one real
location serves **both** channels: `pip install <pkg>` (bundled, offline) **and**
`gh skill install <owner>/<repo> <name>` (cross-agent). Claude Code reads neither
directly, so commit a relative symlink per skill in `.claude/skills/` (the bridge
that skill-package-setup sets up).

> Use `{pkg}/data/skills/` only when you actually want skills in the wheel. Pure
> dev/maintainer skills belong in top-level `skills/` instead (skill-package-setup
> rule). Never put the *same* skill in both — `gh skill` would report duplicates.

## Step 1: decide which skills to ship (audience classification)

Not every skill should ship with `pip install`. Two audiences:

- **Consumer skills** (`metadata.audience: users`) — help people *use* the
  package. These ship (`{pkg}/data/skills/`). E.g. "how to search for skills",
  "how to build storage interfaces with dol".
- **Contributor skills** (`metadata.audience: developers`) — help people
  *develop/contribute*. These stay in top-level `skills/` and do NOT ship. E.g.
  "run the test suite", "set up the dev environment", "CI/CD workflow".

Some serve both — mark `metadata.audience: both`.

> Spec note: `audience` is **not** a top-level spec field — put it under
> `metadata:`. A bare top-level `audience:` fails `gh skill publish` validation.

### How to classify

**If the skill has `metadata.audience`, respect it.** Otherwise infer from name,
description, and body:

**Developer-only signals** — if *most* apply and *no* consumer signals do →
`developers`:

- **Name** contains: `dev`, `debug`, `ci`, `lint`, `contrib`, `internal`,
  `test`, `setup-dev`, `release`
- **Description**: "contribute to", "develop the package", "maintain the
  codebase", "internal tooling", "run the test suite", "CI/CD pipeline for this
  project", "set up a development environment"
- **Body** primarily references: dev setup (virtualenv, editable installs),
  running tests (pytest/tox/nox), linting/formatting (ruff/black/mypy), git/PR
  workflow, CI config (`.github/workflows/`), release processes, contributor-only
  internals
- **Only makes sense with the repo checked out** — not just the installed package

**Consumer signals** — if any apply, likely for users:

- **Description** focuses on what users *do with the package*: "use this skill
  when", "how to search/build/configure"
- **Body** references the public API available after `pip install`
- **Works for someone who only has the installed package** (no repo checkout)

**When in doubt, include it** — classify `users` unless clearly developer-only.

### Applying it

Ship only consumer skills (`users`/`both`) from `{pkg}/data/skills/`; keep
developer-only skills in top-level `skills/`. For each excluded skill, tell the user:

> "Keeping `{name}` in top-level `skills/` (not pip-shipped) — classified
> developer-only because {reason}. To ship it anyway, set
> `metadata.audience: both`."

## Step 2: layout (delegate to skill-package-setup)

```
your-package/
├── your_pkg/
│   └── data/skills/                 ← pip-shipped consumer skills (real files)
│       ├── your-pkg-feature-a/SKILL.md
│       └── your-pkg-feature-b/
│           ├── SKILL.md
│           └── references/api-guide.md
├── skills/                          ← dev/maintainer skills (real files, not shipped)
│   └── your-pkg-dev-task/SKILL.md
├── .claude/skills/                  ← relative symlinks into BOTH of the above
│   ├── your-pkg-feature-a -> ../../your_pkg/data/skills/your-pkg-feature-a
│   └── your-pkg-dev-task  -> ../../skills/your-pkg-dev-task
├── pyproject.toml
└── README.md
```

(skill-package-setup's runbook has the exact `git mv` + symlink commands.)

## Step 3: include the data in the distribution

**Hatchling** (most thorwhalen repos):

```toml
[tool.hatch.build.targets.wheel]
include = ["your_pkg/data/*"]      # or rely on hatchling's implicit your_pkg/** inclusion
```

**Setuptools:**

```toml
[tool.setuptools.package-data]
your_pkg = ["data/skills/**/*"]
```

Verify the wheel actually contains them:

```bash
python -m build --wheel >/dev/null && unzip -l dist/*.whl | grep -i skills
```

## Step 4: document install (README)

`gh skill` is the primary, cross-agent path; pip is the bundled/offline path:

```markdown
## Skills (AI agent integration)

# Cross-agent (any host), versioned:
gh skill install your-org/your-repo your-pkg-feature-a --agent claude-code

# Or use the skills bundled with the pip package (offline):
pip install your-package
skill link-skills "$(python -c 'import your_pkg, os; print(os.path.join(your_pkg.__path__[0], "data", "skills"))')"
```

## Step 5 (optional): convenience helpers

```python
# your_pkg/__init__.py or your_pkg/skills.py
from pathlib import Path

def skills_dir() -> Path:
    """Return the path to this package's bundled skills directory."""
    return Path(__file__).parent / "data" / "skills"
```

Then a CLI installer:

```python
def install_skills(target: str = ''):
    """Install this package's bundled AI agent skills."""
    from skill import link_skills
    from your_pkg import skills_dir
    link_skills(str(skills_dir()), target=target)
```

And/or entry-point registration so `skill search` finds them pre-link:

```toml
[project.entry-points."skill.skill_packs"]
your-pkg = "your_pkg:skills_dir"
```

## Common pitfalls

- **Forgetting package-data** — declare it (Step 3) or the wheel omits the skills;
  test with `pip install -e .` + the `unzip -l` check.
- **Hardcoding paths** — use `Path(__file__).parent` / `importlib.resources`.
- **Same skill in two real locations** — `gh skill` reports duplicates. One real
  location per skill (skill-package-setup rule).
- **Top-level `audience:`** — must be `metadata.audience` or `gh skill publish` rejects it.
- **Shipping dev-only skills** — they clutter users' skill lists; keep them in
  top-level `skills/`, not `{pkg}/data/skills/`.
- **Large reference files** bloat the wheel — keep references lean or fetch on demand.

## Related

- **skill-package-setup** — the canonical layout & spec authority (read first).
- **skill-docs** — generate the README "Skills" section.
- **skill-build** / **skill-creator** — author skill content.
- **skill-sync** — keep shipped skills in sync with the code they document.
