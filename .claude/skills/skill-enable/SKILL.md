---
name: skill-enable
description: >-
  Skill distribution tooling for the skill package. Guide users on shipping AI
  agent skills with pip-installable Python packages. Use this skill when the
  user asks how to include skills in their package distribution, make skills
  available after `pip install`, ship SKILL.md files with their package, set up
  `{pkg}/data/skills/`, configure package_data or data_files, or says things
  like "how do users get my skills after pip install", "ship skills with my
  package", "distribute skills", "package skills", or "enable skills in my
  library". Also trigger when working on pyproject.toml and the project has
  skills to distribute.
---

# Skill Enablement

How to ship AI agent skills with a pip-installable Python package, so users
get them automatically via `pip install your-package`.

## The problem

Skills live in `.claude/skills/` at the project root. That directory is
typically in `.gitignore` (or at least not included in the package distribution).
When someone `pip install`s your package, they get the Python code but not the
skills.

## The solution

Ship skills as **package data** inside your Python package, then let users
link them into their agent's skills directory using the `skill` package.

### Step 1: Decide which skills to ship

Not all skills in a project should be distributed with `pip install`. There are
two audiences:

- **Consumer skills** (`audience: users`) — Help people *use* the package. These
  should ship with pip install. Examples: "how to search for skills", "how to
  build storage interfaces with dol".
- **Contributor skills** (`audience: developers`) — Help people *develop* or
  *contribute to* the package. These belong in the repo (`.claude/skills/`) but
  should NOT ship in the distribution by default. Examples: "how to run the test
  suite", "how to set up the dev environment", "CI/CD workflow for this project".

Some skills serve both audiences — mark those `audience: both`.

#### How to classify

**If the skill has an `audience` field in its frontmatter, respect it.** But most
skills won't have one yet. In that case, read the skill's name, description, and
body to infer its audience. Here are the signals:

**Developer-only signals** — if *most* of these apply and *none* of the consumer
signals apply, classify as `developers`:

- **Name** contains: `dev`, `debug`, `ci`, `lint`, `contrib`, `internal`,
  `test`, `setup-dev`, `release`
- **Description** says things like: "contribute to", "develop the package",
  "maintain the codebase", "internal tooling", "run the test suite", "CI/CD
  pipeline for this project", "set up a development environment"
- **Body** primarily references: development setup (virtualenv, editable
  installs), running tests (pytest, tox, nox), linting/formatting (ruff, black,
  mypy), git workflows (branching, PR conventions), CI configuration
  (`.github/workflows/`), release processes, internal architecture that only
  matters for contributors
- **The skill only makes sense if you have the repo checked out** — not just the
  installed package

**Consumer signals** — if any of these apply, the skill is likely for users:

- **Description** focuses on what users of the package *do with it*: "use this
  skill when", "how to search", "how to build", "how to configure"
- **Body** references the package's public API — functions, classes, and CLI
  commands that are available after `pip install`
- **The skill works equally well for someone who only has the installed package**
  (no repo checkout needed)

**When in doubt, include it** — a slightly larger distribution is better than a
user missing a skill they need. Classify as `users` unless the skill is clearly
developer-only.

#### Applying the classification

When setting up `{pkg}/data/skills/`, only copy/symlink consumer skills
(`users` and `both`). For each excluded skill, tell the user:

> "Skipping `{name}` — classified as developer-only because {reason}.
> To include it anyway, add `audience: both` to its frontmatter."

This way the user sees what was excluded, understands why, and knows exactly how
to override the decision.

### Step 2: Create a data/skills directory (consumer skills only)

```
your-package/
├── your_pkg/
│   ├── __init__.py
│   ├── core.py
│   └── data/
│       └── skills/
│           ├── your-skill-1/
│           │   └── SKILL.md
│           └── your-skill-2/
│               ├── SKILL.md
│               └── references/
│                   └── api-guide.md
├── .claude/
│   └── skills/          ← dev-time symlinks (not shipped)
├── pyproject.toml
└── README.md
```

The key insight: `.claude/skills/` is for development (symlinks during dev),
while `{pkg}/data/skills/` is what gets distributed.

### Step 3: Include in pyproject.toml

Make sure the skill files are included in the distribution:

```toml
[tool.setuptools.package-data]
your_pkg = ["data/skills/**/*"]
```

Or if using `[tool.setuptools.packages.find]`, the `data/` directory should
already be discovered as long as it's inside the package directory.

For non-setuptools backends (flit, hatch, maturin), consult their docs on
including data files. The principle is the same: declare that `data/skills/`
and its contents should be part of the distribution.

### Step 4: Keep dev skills in sync

During development, you want `.claude/skills/` to point to the same content
as `{pkg}/data/skills/`. Symlinks make this easy:

```bash
# From the project root, during development:
cd .claude/skills
ln -s ../../your_pkg/data/skills/your-skill-1 your-skill-1
ln -s ../../your_pkg/data/skills/your-skill-2 your-skill-2
```

Or use the `skill` package itself:

```bash
skill link-skills your_pkg/data/skills --target .claude/skills --force
```

This way, `.claude/skills/` (used by Claude during development) always
reflects the latest skills from the source of truth in `{pkg}/data/skills/`.

### Step 5: Document the post-install step

After `pip install your-package`, users need to link the skills. Add this to
your README (the `skill-docs` skill can help with this):

```markdown
## Skills (AI Agent Integration)

After installing, link the bundled skills into your agent:

\```bash
# Into your current project
skill link-skills $(python -c "import your_pkg; print(your_pkg.__path__[0])")/data/skills

# Or globally (available in all projects)
skill link-skills $(python -c "import your_pkg; print(your_pkg.__path__[0])")/data/skills \
  --target ~/.claude/skills
\```
```

### Step 6 (optional): Add a convenience function

For a smoother user experience, add a helper to your package:

```python
# your_pkg/__init__.py or your_pkg/skills.py
from pathlib import Path

def skills_dir() -> Path:
    """Return the path to this package's bundled skills directory."""
    return Path(__file__).parent / "data" / "skills"
```

Then users (or your README) can do:

```bash
skill link-skills $(python -c "from your_pkg import skills_dir; print(skills_dir())")
```

Or even add a CLI command:

```python
# In your CLI module
def install_skills(target: str = ''):
    """Install this package's AI agent skills."""
    from skill import link_skills
    from your_pkg import skills_dir
    link_skills(str(skills_dir()), target=target)
```

### Step 7 (optional): Entry point registration

If you want your skills to be discoverable by the `skill` package's search
system, register them as entry points:

```toml
[project.entry-points."skill.skill_packs"]
your-pkg = "your_pkg:skills_dir"
```

This lets `skill search` find your package's skills even before they're
symlinked.

## The full picture

```
Development (all skills available):
  .claude/skills/your-skill → symlink → your_pkg/data/skills/your-skill
  .claude/skills/your-dev-skill → lives in .claude/skills/ only (not shipped)
  (Claude uses all of .claude/skills/ during dev)

Distribution (consumer skills only):
  pip install your-package
  → installs your_pkg/data/skills/your-skill/ as package data
  → developer-only skills stay in .claude/skills/, NOT in the distribution

Post-install:
  skill link-skills .../your_pkg/data/skills
  → symlinks into ~/.claude/skills/ or .claude/skills/
  (Users get consumer skills; dev skills remain in the repo for contributors)
```

## Common pitfalls

- **Forgetting `package-data`** — If you don't declare the skills as package
  data, they won't be included in the wheel/sdist. Test with
  `pip install -e .` and check if the data directory exists in the installed
  location.
- **Hardcoding paths** — Use `Path(__file__).parent` or `importlib.resources`
  to locate package data, not absolute paths.
- **Shipping `.claude/skills/` directly** — This directory is for project-local
  agent configuration. Ship via `{pkg}/data/skills/` instead, so skills are
  properly isolated and discoverable.
- **Shipping developer-only skills** — Skills that help contributors (run tests,
  set up dev environment, CI workflows) shouldn't be in the pip distribution.
  They clutter the user's skill list and may confuse the agent. Keep them in
  `.claude/skills/` in the repo, not in `{pkg}/data/skills/`. See Step 1.
- **Large reference files** — Skills with big reference docs will increase your
  package size. Consider whether the references are essential or if they could
  be downloaded on demand.
