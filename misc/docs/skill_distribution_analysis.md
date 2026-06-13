# Where to Put Consumer Skills in a Python Package

A focused analysis of the question: **for a Python package whose
maintainers want to ship AI agent skills to their users, where should
those skills live in the repository?**

This is the question your `skill-enable` skill currently answers with
"`{pkg}/data/skills/`". As of April 2026 — `gh skill install` shipped on
2026-04-16 — that answer is no longer obviously right. This doc lays out
the options, tradeoffs, and a recommendation.

---

## Two distinct things people mean by "where skills live"

Before the options: it helps to separate **publishing** from **installation**.

- **Publishing** — where skills sit in a repository so they can be shared.
  This is what `gh skill install`, `npx skills add`, and Claude Code's
  `/plugin install` look at when they fetch from a remote. The relevant
  question: "what layout does the repo need to have so these tools find
  the skills?"
- **Installation** — where skills end up on a user's machine, in the
  specific directory the agent reads. For Claude Code, that is hardcoded
  to `~/.claude/skills/` (global) or `.claude/skills/` (project). Other
  agents have their own hardcoded paths.

The two concerns are independent, and tools differ on both halves:

| Tool | Reads from (publishing) | Writes to (installation) |
|------|------------------------|--------------------------|
| `gh skill install` | `skills/<name>/SKILL.md` (and via `--allow-hidden-dirs`, `.claude/skills/...`) | `.agents/skills/` or agent-specific dir |
| `npx skills add` | ~30 paths incl. root, `skills/`, agent-specific dirs, plugin manifests, recursive fallback | Symlinks from `.agents/skills/` to each agent dir |
| Claude Code `/plugin install` | A marketplace manifest (`.claude-plugin/marketplace.json`) | `~/.claude/plugins/` (or project equivalent) |
| Your `skill link-skills` | `skills/`, `.claude/skills/`, `{pkg}/data/skills/` | Configurable via `--target` |

The Python-package question — "where do I put my skills?" — is really
a publishing question. The installation side is fixed by the agent.

## The two competing concerns

When a Python package wants to ship skills, two things are pulling in
different directions:

### Concern A — pip distribution
You want skill files to ride along with `pip install your-pkg`, so a user
who installs the package gets the skills automatically (no extra git
clone, works offline, version-locked to the package release). The
canonical Python way to do this is to put non-`.py` resources *inside the
package directory*: `{pkg}/data/skills/`. Anything outside the package
directory is by default not in the wheel.

### Concern B — the agent-skills ecosystem's discovery conventions
`gh skill install OWNER/REPO SKILL` and `npx skills add OWNER/REPO` look
in a specific set of paths inside a repo. Per the Vercel CLI source
(`src/skills.ts`), the priority order is:

1. Root `SKILL.md` (single-skill repo)
2. `skills/`
3. `skills/.curated/`, `skills/.experimental/`, `skills/.system/`
4. `.agents/skills/`, `.claude/skills/`, `.cursor/skills/`,
   `.windsurf/skills/`, `.cline/skills/`, `.codex/skills/`,
   `.continue/skills/`, `.github/skills/`, ~25 other agent-specific dirs
5. Plugin-manifest-declared paths (`.claude-plugin/marketplace.json`,
   `.claude-plugin/plugin.json`)
6. Recursive fallback (depth ≤ 5, skipping `node_modules`, `.git`,
   `dist`, `build`, `__pycache__`)

`{pkg}/data/skills/` is **only reached via step 6** (the recursive
fallback). For repos that have *anything* in steps 1–5, the `data/skills/`
directory is invisible to `gh skill install` and `npx skills add`.

The two concerns are independent — one is about wheels, the other is about
git repos — but they overlap because the *same files* need to satisfy
both.

---

## The five options

### Option 1 — Skills only at `{pkg}/data/skills/` (status quo)

```
your-package/
├── your_pkg/
│   └── data/
│       └── skills/
│           ├── skill-a/SKILL.md
│           └── skill-b/SKILL.md
└── pyproject.toml
```

- ✅ Pip ships skills automatically (assuming `package-data` is configured).
- ✅ Single source of truth.
- ❌ `gh skill list your-org/your-repo` shows nothing under standard paths.
  It works only because of the recursive fallback — which is fine for
  install but unhelpful for browsing.
- ❌ `gh skill install your-org/your-repo skill-a` works (via fallback
  too) but the experience is degraded — slower, no namespacing, harder
  to inspect from `gh skill preview`.
- ❌ Doesn't show up cleanly on skills.sh telemetry-driven leaderboards.
- ❌ Diverges from the convention the rest of the ecosystem uses.

### Option 2 — Skills only at `skills/` at the repo root

```
your-package/
├── skills/
│   ├── skill-a/SKILL.md
│   └── skill-b/SKILL.md
├── your_pkg/
│   └── ...
└── pyproject.toml
```

- ✅ `gh skill install` and `npx skills add` find skills via the
  canonical path.
- ✅ Discoverable by skills.sh telemetry.
- ✅ Convention-compliant — exactly what the rest of the ecosystem uses.
- ❌ **Pip won't ship the skills** — they're outside the package
  directory. A user who runs `pip install your-pkg` gets the code but
  not the skills.
- ❌ Forces users to install skills through a separate channel
  (`gh skill install`, `npx skills add`, `skill link-skills`, or git
  clone). That's an extra step that the current `data/skills/` layout
  avoids.

### Option 3 — Both, with `skills/` as source of truth

```
your-package/
├── skills/                      ← source of truth
│   ├── skill-a/SKILL.md
│   └── skill-b/SKILL.md
├── your_pkg/
│   └── data/
│       └── skills/              ← symlinks (in repo) or build-time copy (in wheel)
│           ├── skill-a -> ../../../../skills/skill-a
│           └── skill-b -> ../../../../skills/skill-b
└── pyproject.toml
```

- ✅ `gh skill install` works perfectly.
- ✅ Pip ships skills (the symlinks resolve at build time and the wheel
  contains real files).
- ✅ Convention-compliant.
- ⚠️ Symlinks in git work on Linux/macOS and Windows-with-git-LFS-or-junctions.
  Most build backends (hatchling, setuptools, flit) follow symlinks when
  building the sdist/wheel. Verify with your backend.
- ⚠️ Two paths to maintain mentally even if it's one set of files.

A variation: instead of in-repo symlinks, use a build hook to copy
`skills/` → `your_pkg/data/skills/` at build time. Cleaner from a git
perspective (no symlinks), but adds a build dependency.

### Option 4 — Both, with `{pkg}/data/skills/` as source of truth + plugin manifest

```
your-package/
├── .claude-plugin/
│   └── plugin.json              ← declares: skills are at your_pkg/data/skills
├── your_pkg/
│   └── data/
│       └── skills/              ← source of truth
│           ├── skill-a/SKILL.md
│           └── skill-b/SKILL.md
└── pyproject.toml
```

The `plugin.json` (or `marketplace.json`) tells `gh skill install` and
`npx skills add` where the skills live, sidestepping the convention.
This is what the Vercel CLI calls "plugin manifest discovery" and is
explicitly supported.

- ✅ Pip ships skills (they're inside the package).
- ✅ `gh skill install` works (via manifest).
- ✅ Single source of truth.
- ✅ Doesn't require symlinks or build hooks.
- ❌ Less standard than `skills/`. Browsers (skills.sh, GitHub UI) won't
  highlight the skills as obviously.
- ❌ The manifest format isn't yet officially standardized at
  agentskills.io — it's a Vercel-CLI convention. `gh skill install`'s
  support for it is implied by the announcement (it claims compatibility
  with the agentskills.io ecosystem) but not explicitly documented.
  *Verify before adopting as your default.*

### Option 5 — Ship as a Claude Code plugin marketplace

```
your-package/
├── .claude-plugin/
│   └── marketplace.json         ← declares plugins, skills, MCP servers
├── skills/
│   ├── skill-a/SKILL.md
│   └── skill-b/SKILL.md
├── your_pkg/
│   └── ...
└── pyproject.toml
```

Users install via Claude Code:

```
/plugin marketplace add your-org/your-repo
/plugin install your-package@your-org-your-repo
```

- ✅ Bundles skills with related artifacts (commands, agents, MCP servers)
  as a single installable unit. Makes sense if your package ships more
  than just skills.
- ✅ Native to Claude Code; no extra CLI required.
- ✅ Consistent with the growing third-party marketplace ecosystem
  (`claude-plugins-plus-skills`, `claude-skills-marketplace`, etc.).
- ❌ Claude Code-specific. Cursor / Copilot users get nothing.
- ❌ Manifest schema is still settling; less mature than `gh skill` and
  `npx skills`.
- ❌ Doesn't help with pip distribution either way.

This is **complementary**, not exclusive: a repo can simultaneously be a
Claude marketplace, an `gh skill` source, and a Python package. The
question is whether you ship the marketplace manifest *in addition to*
your other artifacts.

### Option 6 — Use `gh skill install` (or `skill install`) as the canonical install path; don't ship via pip at all

```
your-package/
├── skills/                      ← source of truth, only
│   ├── skill-a/SKILL.md
│   └── skill-b/SKILL.md
└── pyproject.toml
```

The package's README tells users:

```
pip install your-pkg                              # gets the code
gh skill install your-org/your-repo skill-a       # gets the skill
gh skill install your-org/your-repo skill-b
```

- ✅ Convention-compliant.
- ✅ Tracks the ecosystem direction. This is essentially how the
  Vercel/Anthropic camp expects packages to ship skills.
- ✅ Skills get version-pinned independently of the package
  (`gh skill install ... --pin v2.0.0`), which is arguably cleaner —
  skill versions and code versions can move at different rates.
- ❌ Two install steps. Some users won't bother.
- ❌ Offline / air-gapped use cases need an extra `git clone`.
- ❌ Loses the "automatic skills with pip install" user-delight angle.

---

## Recommendation

**Default: Option 3 (`skills/` source of truth + build-time copy or
symlink to `{pkg}/data/skills/`).**

Reasoning:

1. The cost of dual-location is low (one symlink each, or a 5-line build
   hook).
2. `skills/` as canonical aligns with `gh skill`, `npx skills`,
   skills.sh, and the agentskills.io spec's implicit examples. This is
   the path of least friction for the next 12+ months.
3. Keeping `{pkg}/data/skills/` populated preserves the pip-install
   delight and offline use case.
4. The current `link_skills()` machinery in `skill` already handles
   either source location (it has a fallback chain that includes
   `{pkg}/data/skills/`). Option 3 doesn't break it.
5. `skill-enable` skill becomes shorter and clearer: "put your skills in
   `skills/` and add a build hook (or symlink) to mirror them into
   `{pkg}/data/skills/`".

**Fallback if maintainers don't want symlinks/build hooks:** Option 4
(plugin manifest). This requires the spec/CLI to support manifests
reliably. Verify with a 5-minute test:

```bash
# In a scratch repo with skills only at your_pkg/data/skills/ and a
# .claude-plugin/plugin.json declaring that path:
gh skill list . --from-local
```

If it picks up the skills, Option 4 is viable.

**Worst case (fallback's fallback):** Option 1 (status quo). It works,
just less elegantly. Acceptable for packages where skills are an
afterthought.

**Don't do Option 6** unless you're a downstream package that already
trusts users to have `gh` and a network connection. The "two install
steps" tax is real.

**Consider Option 5 (Claude marketplace) as additive, not alternative.**
If your package targets Claude Code primarily, a `.claude-plugin/marketplace.json`
in addition to Option 3's `skills/` layout costs little and gives users
a `/plugin install` path. If your package is multi-agent, deprioritize
this — the marketplace is Claude-specific.

**Don't do Option 2 alone.** Losing pip distribution is a regression for
any meaningful Python user base.

---

## Implementation impact on `skill`

If you adopt Option 3 as the package's recommendation:

### `skill-enable` skill — rewrite

The skill currently directs users to `{pkg}/data/skills/`. Update it to:

1. Lead with: "Put skills at `skills/<name>/SKILL.md` at the repo root.
   This is the canonical layout that `gh skill install`, `npx skills add`,
   and `skill link-skills` all support."
2. Add: "If you want skills to ship via `pip install` too, mirror them
   into `your_pkg/data/skills/` using one of: (a) git-tracked symlinks,
   (b) a `hatch_build.py` build hook, (c) a `MANIFEST.in` rule that
   copies."
3. Update the audience-classification logic to still apply, but in step
   1 (which skills go into `skills/` vs. `.claude/skills/`-only).

### `_resolve_skills_source()` in `install.py` — extend

Add manifest-file detection (Option 4 fallback) to the resolution chain:

1. Direct skills under source ← already done
2. `source/.claude/skills/` ← already done
3. `source/skills/` ← **add this; it's the canonical path now**
4. `source/{pkg}/data/skills/` (Python convention) ← already done
5. `source/.claude-plugin/plugin.json` declared paths ← **add this**
6. `source/.claude-plugin/marketplace.json` declared paths ← **add this**

### `link_skills()` — verify priority

Currently `_resolve_skills_source` picks the first directory it finds. If
a repo has both `skills/` (canonical) and `your_pkg/data/skills/`
(mirror), make sure `skills/` wins. Otherwise users will hit confusing
"already exists" errors when both paths point to the same files.

### `skill install` provenance — align with `gh skill`

`gh skill install` writes provenance into installed `SKILL.md`
frontmatter (specifically `metadata.source`, `metadata.ref`,
`metadata.tree-sha` — verify against a real install). Adopt the same
keys when `skill install` writes via a remote backend, so that a skill
installed by `skill` can be updated by `gh skill update` and vice versa.

### Documentation — add a comparison table

```
                        gh skill         skill           npx skills
multi-agent             via --agent      yes (default)   yes
multi-backend search    no               yes             no
pip distribution        n/a              yes             n/a
provenance metadata     yes              add             no
version pinning         yes              add             no
publish workflow        yes              defer to gh     no
plugin-manifest disco.  ?                add             yes
```

This makes the differentiator obvious instead of leaving it implicit.

---

## This isn't really a Python-only question

Everything above frames the question as "where do Python packages put
their skills." But the same question applies to npm packages, Cargo
crates, Go modules, etc. Each ecosystem has its own native location
for shipping non-code resources:

| Ecosystem | Native package-data location |
|-----------|------------------------------|
| Python (wheel) | `{pkg}/data/skills/` |
| npm | `node_modules/<pkg>/skills/` (anything in the published `files` glob) |
| Cargo | `target/<crate>/skills/` (build artifact) or `<crate-src>/skills/` |
| Go | embedded via `//go:embed`, or repo-relative `skills/` |

For each, the same trade-off applies: there's a "ship via package
manager" location (inside the package directory) and a "ship via git
convention" location (`skills/` at repo root). Today, only the latter
is picked up by `gh skill install` and `npx skills add`.

**The polyglot fix in `skill`:** the current `_resolve_skills_source()`
function in `install.py:359` has a hardcoded Python branch (it looks at
`{pkg}/data/skills/` when it sees `pyproject.toml`). This should be
generalized to a registered convention so each language can add its own
fallback:

```python
package_data_conventions = Registry('package_data_conventions')
package_data_conventions.register('python', PythonPackageDataConvention())
package_data_conventions.register('npm', NpmPackageDataConvention())
# etc., via entry points
```

Each convention would: (a) detect whether a directory looks like a
package of its kind (e.g., `pyproject.toml` for Python,
`package.json` for npm), (b) yield candidate skill locations.

This keeps `skill`'s recommendation consistent across languages — the
canonical layout is `skills/<name>/SKILL.md`, with a language-specific
mirror inside the package directory if you want to ship via the
language's package manager. The same dual-location pattern (Option 3)
applies; only the second location's path differs.

**Implication for the `skill-enable` skill:** rename it to something
language-agnostic (e.g., `skill-distribute` or
`skill-package-shipping`) and split the Python-specific instructions
into a convention-specific reference file
(`references/python.md`), leaving the main body language-neutral. Add
sibling reference files for npm, etc., as the conventions get
implemented.

## A spec gotcha to avoid

Some external write-ups recommend a top-level `agent-version: ">=1.0.0"`
field in `SKILL.md` frontmatter to declare host-version constraints.
**This is not a valid spec field.** The agentskills.io spec defines
exactly six top-level fields: `name`, `description`, `license`,
`compatibility`, `metadata`, `allowed-tools`. Anything else will:

- fail `skills-ref validate`
- be stripped or rewritten by `gh skill publish --fix`
- be silently dropped by stricter agent hosts

The right pattern for version constraints is the free-text
`compatibility` field (e.g., `compatibility: Requires Claude Code
≥ 1.0.0`), or — if you need structured data — namespace it under
`metadata`, e.g.:

```yaml
metadata:
  host_version: ">=1.0.0"
```

This applies equally to your `audience` field — see below.

## A gotcha worth flagging

`gh skill install` writes provenance into the SKILL.md frontmatter as
`metadata.*` keys (per the agentskills.io spec, top-level fields beyond
the standard set are not allowed; arbitrary keys go under `metadata`).
**This is the same pattern you'd want for the `audience` field** —
namespacing it under `metadata.audience` until it's accepted as a
top-level field by the spec. Worth doing both at the same time so they
read as one consistent change.

---

## Sources

- [Agent Skills specification — agentskills.io](https://agentskills.io/specification)
- [`gh skill install` manual](https://cli.github.com/manual/gh_skill_install)
- [Vercel `skills` CLI source — `src/skills.ts`](https://raw.githubusercontent.com/vercel-labs/skills/main/src/skills.ts)
- [Big Hat Group write-up on `gh skill`](https://www.bighatgroup.com/blog/gh-skill-github-cli-agent-skills-management/)
- [Mintlify Vercel skills installation methods](https://www.mintlify.com/vercel-labs/skills/guides/installation-methods)
- [GitHub Changelog announcing `gh skill`](https://github.blog/changelog/2026-04-16-manage-agent-skills-with-github-cli/)
