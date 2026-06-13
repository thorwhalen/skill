# `skill` Package Review (2026-04-28)

A review of the `skill` package (this repo), in
the context of the agent-skills ecosystem as it stands in April 2026 — most
notably with `gh skill` shipping in GitHub CLI v2.90.0+ on 2026-04-16.

---

## A prior question: does this package fill a gap?

Before reading the rest of this review, hold this question open:

> Now that `gh skill install`, `npx skills add`, and Claude Code's
> `/plugin install` cover the install path with provenance, pinning,
> and 40+ agent targets, does `skill` still fill a gap that justifies
> its existence?

The package was conceived in early 2025, before `gh skill` shipped
(2026-04-16) and before the Claude marketplace ecosystem coalesced. The
existing `misc/docs/The AI agent skills ecosystem — a complete landscape
survey.md` argued that the gap was **the programmatic Python layer**:
Pydantic-modeled skill objects, deterministic version resolution, a
private-registry protocol, evaluation hooks. That thesis is largely
still defensible, but partially obsolete:

- **"No versioning"** is half-resolved. `gh skill install --pin <tag|sha>`
  exists. `gh skill update` exists. Lock files still don't.
- **"No security/sandboxing"** is still wide open. Nothing in the
  ecosystem signs, sandboxes, or scans skills with `scripts/`.
- **"No private registries"** is still wide open. localskills.sh is
  SaaS; no self-hosted server exists.
- **"No testing framework"** is still wide open. Anthropic's
  skill-creator has one but it's embedded.
- **"Multi-agent translation"** is partially resolved by symlinks-as-default
  in Vercel CLI, but lossy translation to `.mdc`, `applyTo`, `trigger`
  remains real and unhandled by `gh skill`.

So the real gaps that `skill` could *uniquely* fill, today, are:

1. Lock files / deterministic resolution across multiple sources.
2. Self-hosted private registry server.
3. Testing-framework integration (promptfoo, eval harness).
4. Lossy multi-agent format translation with explicit semantic
   annotations.
5. **Programmatic Python API for any of the above**, callable from
   build scripts and CI.

These are five legitimate gaps. None of them are "another installer."
**The strategic move is to stop being an installer and become a
programmatic operations layer that integrates with `gh skill`,
`npx skills`, and the Claude marketplace as backends or peers.**

A focused gap-analysis deep-research prompt is in
`skill_strategic_research_prompt.md`.

## TL;DR

Your package is well-architected and addresses real problems. But the
ecosystem has crystallized in the last ~6 months around two specific tools
and one canonical layout:

- **`gh skill install OWNER/REPO SKILL`** (GitHub CLI, public preview)
- **`npx skills add OWNER/REPO`** (Vercel, de facto since late 2025)
- **Canonical layout: `skills/<name>/SKILL.md` at repo root**

`skill`'s value proposition is *not* "yet another installer for skills from
GitHub" — `gh skill`, `npx skills`, **and Claude Code's `/plugin install`
marketplace system** already do that, with provenance tracking, git-tag
pinning, and immutable releases. Your package's value is **multi-agent
management, multi-backend search, package-data shipping, and local-first
workflows** — and the README/docs should re-frame around that.

Useful framing: distinguish **publishing** (where skills live in a repo
to be shareable) from **installation** (where an agent reads them on a
user's machine). Today's tools all collapse the gap between the two, but
they differ on conventions for both halves. Your `skill` package
straddles both, which is part of the reason it's hard to position.

The biggest concrete change to consider is around **shipping skills with
Python packages**: the current `{pkg}/data/skills/` recommendation is
defensible (offline, version-locked, no extra install step) but no longer
the obvious choice now that `gh skill install` is one command. See
`skill_distribution_analysis.md` for the focused analysis.

---

## What's strong

### 1. Architecture
- Clean Mapping-based core (`LocalSkillStore`, `LocalDirSource`,
  `GitHubSkillSource` all share the same `__getitem__` / `__contains__` /
  `search` surface). This is exactly the right abstraction.
- `Registry[T]` with entry-point discovery is the right plugin mechanism.
  Four registries (agent_targets, translators, backends, validators) cover
  every realistic extension point.
- `dol`-flavored design holds up: stores compose, sources stack, and the
  facade in `__init__.py` is small.
- `platformdirs` for paths, `argh` for CLI dispatch — both correct choices,
  consistent with your other projects.

### 2. Multi-agent translation
- The translator pipeline (SKILL.md → `.mdc` for Cursor, → appended block in
  `copilot-instructions.md`, native for Claude Code) is something neither
  `gh skill` nor `npx skills` does as systematically. **This is a real
  differentiator.** Lean into it.
- The `AgentTarget` dataclass with `{home}/{project}/{name}` templates is
  the right interface for plugin authors.

### 3. Backend coverage
The backends in `skill/backends/` already cover what's actually viable:
GitHub (canonical), Smithery, Composio, the awesome-list, SkillsDirectory.
Per the `Remote skill backends...md` doc you've already done the
reconnaissance — that doc is excellent and should probably be the basis of
a public design page on the package's docs site.

### 4. The `skill-*` skill set
Five well-scoped skills in `.claude/skills/` — `skill-build`, `skill-docs`,
`skill-enable`, `skill-manage`, `skill-sync` — eat your own cooking
correctly. The audience-field convention (`users` / `developers` / `both`)
in `skill-enable` and `skill-build` is a thoughtful invention; it's also
*not yet ecosystem-wide*, which is both an opportunity (lead) and a risk
(may need adjustment if the spec adopts a different field).

### 5. The docs in `misc/docs/`
The cross-agent compatibility doc, storage-architecture doc, and the
remote-backends doc are unusually substantive. They read like ~80% of a
small book on the agent-skills ecosystem. This is buried — at least one of
them (the backends survey) belongs on the docs site.

---

## What's gap-shaped

### 0. The Claude Code plugin marketplace ecosystem isn't on the radar at all

A separate distribution channel exists alongside `gh skill` and
`npx skills`: **Claude Code's plugin marketplace system**. Users can run
`/plugin install commit-commands@anthropics-claude-code` (or
`/plugin marketplace add owner/repo` to register a custom marketplace),
and the marketplace mechanism handles install + update for skills,
agents, and MCP servers as a unit.

- Anthropic ships `claude-plugins-official` as a default-enabled
  marketplace.
- Third-party marketplaces are discoverable via `/plugin marketplace add`.
- Several large community catalogs already exist:
  `mhattingpete/claude-skills-marketplace`,
  `jeremylongshore/claude-code-plugins-plus-skills` (423 plugins / 2,849
  skills), `dashed/claude-marketplace` (local-first), and others.

The `skill` package doesn't currently:

- Read a `.claude-plugin/marketplace.json` to advertise itself as a
  marketplace source.
- Provide a backend that searches Claude Code's marketplace ecosystem.
- Translate a directory of skills into a marketplace manifest.

This is a meaningful blind spot. Even a minimal "your `skill`-managed
skills directory is also a valid local marketplace" feature would
unlock `/plugin install` workflows for users who prefer them.

**Recommended action:** add `marketplace.json` generation to
`link_skills` (or a new `skill marketplace` command), and add a
`claude-marketplace` backend that reads marketplace manifests as a
search source.

### 1. No first-class `gh skill` integration

`gh skill install` shipped 2026-04-16. The `skill` README, the `skill-manage`
skill, and the search backends do not mention it. Specifically:

- `GitHubSkillSource` searches code via the legacy Code Search API. That's
  fine for discovery, but for *installation* the new community standard is
  `gh skill install owner/repo skill-name`. `skill install` should know
  about this.
- The `gh skill install` command writes provenance metadata into installed
  `SKILL.md` frontmatter (`source`, `ref`, `tree-sha`) so updates can be
  detected. Your installer doesn't write this metadata, which means skills
  installed by `skill` and skills installed by `gh skill` are not
  interoperable on the update side.
- Missing: a `gh-skill` backend that wraps `gh skill list`/`gh skill search`
  for discovery, and an installer mode that emits the same provenance
  frontmatter so `gh skill update` can manage skills installed by `skill`.

**Recommended action:** add `skill.backends.gh_skill` and have `install()`
optionally write the same `metadata.source / metadata.ref / metadata.tree-sha`
keys that `gh skill install` writes. The exact key names should be confirmed
against a real `gh skill install` output (sample one and inspect).

### 2. The `skill-enable` skill recommends a path the ecosystem doesn't search

`skill-enable` tells consumers to put shipped skills at `{pkg}/data/skills/`.
This is correct *for pip distribution*, but `gh skill install` and
`npx skills add` look at:

- root `SKILL.md`
- `skills/<name>/`
- `skills/.curated/`, `skills/.experimental/`, `skills/.system/`
- agent-specific dirs: `.agents/skills/`, `.claude/skills/`,
  `.cursor/skills/`, `.windsurf/skills/`, `.cline/skills/`,
  `.codex/skills/`, `.continue/skills/`, `.github/skills/`, `.goose/skills/`,
  `.opencode/skills/`, ~25 others
- plugin manifest declarations
- recursive fallback (depth ≤ 5, skipping `node_modules`, `.git`, `dist`,
  `build`, `__pycache__`)

`{pkg}/data/skills/` is reachable only via the recursive fallback. That
means: a Python repo with skills in `{pkg}/data/skills/` and *nothing* at
`skills/*/SKILL.md` will still be discoverable (because of the fallback),
but it won't show up cleanly in `gh skill list <repo>` because that command
expects the canonical layout.

**Recommended action:** see `skill_distribution_analysis.md` for options.
Short version: dual-location with `skills/*/SKILL.md` as source-of-truth
and `{pkg}/data/skills/` as a build-time materialization is probably the
right move.

### 3. No "publish" / "skill-publish" skill

`gh skill publish` is now part of the ecosystem. It validates against the
agentskills.io spec, ties releases to git tags, and offers immutable
releases. There's nothing in `skill` for the publishing workflow:

- No `skill publish` CLI command.
- No skill-publish guidance for consumers (e.g., "add a release workflow
  that runs `skills-ref validate` on every tag").
- No reference to the `skills-ref` validator from agentskills.io —
  `skill validate` re-implements the same checks but isn't tied to the
  upstream tool.

**Recommended action:** either (a) add a `skill publish` command that
delegates to `gh skill publish` with sensible defaults, or (b) add a
`skill-publish` skill in `.claude/skills/` that walks a maintainer through
the `gh skill publish` workflow and the surrounding hygiene (tag
protection, secret scanning, immutable releases).

### 4. Provenance and update tracking is half-built

`LocalSkillStore.set_source_meta` stores `_source.json` next to the skill,
with `url` and `source` keys. That's a decent local cache concept, but:

- `gh skill` writes its provenance *into the SKILL.md frontmatter*, not a
  sidecar file. That's the emerging convention.
- There's no `skill update <key>` command that would re-fetch from source
  and detect drift.
- `skill-sync` (the skill, not the function) is about *code drift* —
  updating skills when *the package they document* changes. There's no
  equivalent for *upstream drift* — updating skills when their *upstream
  repo* changes.

**Recommended action:** introduce `skill update` (re-fetch and diff) and
align provenance metadata with `gh skill`'s frontmatter convention so
either tool can own the update path.

### 5. Versioning / pinning

`gh skill install --pin v2.0.0` is now standard. `skill install` has no
pinning — when you install from a backend, you get HEAD. For Python users
who already think in pinned dependencies, this is conspicuous.

**Recommended action:** add `--pin` to install, and propagate the ref into
the source metadata.

### 6. Discovery: search results don't reflect popularity or trust

`SkillInfo` doesn't carry stars / install counts / trust signals.
`gh skill` and `skills.sh` both surface popularity. With no signal, your
search results are essentially "first 10 things matching keyword".

**Recommended action:** add an optional `popularity: int | None` and
`trust: dict | None` (or just `metadata: dict`) field on `SkillInfo`, and
populate from backends that have it (smithery has `qualityScore`, github
has stars via the repo metadata).

### 7. The CLI is good but doesn't speak `gh skill`'s vocabulary

`gh skill` uses `install`, `uninstall`, `update`, `list`, `search`,
`preview`, `publish`. You have most of those. Missing: `update`, `preview`
(show what would happen without writing), `publish`. Adding these would
make `skill` feel like a superset of `gh skill` for users who land here
already familiar with the GitHub workflow.

### 8. `audience` field is yours-only

The `audience: users | developers | both` invention is good and is
documented in `skill-enable` and `skill-build`. But it's not in the
agentskills.io spec frontmatter table. Two paths:

- **Push it upstream.** Open an issue or PR on agentskills.io proposing
  `audience` as an optional field. It's a small enough addition that it
  could land.
- **Namespace it under `metadata`.** `metadata.audience: users` is
  spec-compliant today and would survive `skills-ref validate`. The
  current top-level `audience` field will fail strict validation.

**Recommended action:** either move `audience` under `metadata` for
spec-compliance until accepted upstream, or push it upstream. Don't leave
it sitting as a non-standard top-level field — it's the kind of thing that
will silently break `gh skill publish --fix`.

### 8.5 The package is presented as Python-only, but it isn't

Reading the code: `skill` is ~95% language-agnostic. The only
Python-specific branch is `_resolve_skills_source()` in `install.py:381`,
which detects `pyproject.toml` and looks at `{pkg}/data/skills/`.
Everything else — `LocalSkillStore`, the agent-target registry, the
translators, all five backends, the CLI — is pure filesystem + HTTP. A
JS, Go, or Rust project can run `skill install owner/skill` today and
get exactly what a Python project gets.

But **perception is the problem**: a frontend dev sees `pip install
skill` and bounces, regardless of what the tool can do. That perception
is currently baked into:

- The README's first example (`from skill import search, install, ...`)
- The `skill-enable` skill, which is explicitly Python-only
- The `_resolve_skills_source` Python-aware branch, which is the only
  language-aware code in the core
- The (excellent) docs in `misc/docs/`, which assume a Python audience

Three resolution paths, in increasing order of cost:

1. **Reframe only.** Update README and `skill-enable` to position
   `skill` as "a CLI for managing AI skills across agents — works with
   any project, Python-installed for now." Move the
   `{pkg}/data/skills/` Python branch behind a registered convention so
   it sits as a peer to `node_modules/<pkg>/skills/`,
   `target/<crate>/skills/`, etc. Cost: a half-day. Wins ~all the
   reach you can plausibly get without npm publishing.
2. **Add npm consumption.** Make `skill` *consume* npm packages —
   detect `node_modules/<pkg>/skills/` and `package.json` "skills" key
   the way it currently detects `pyproject.toml`. This lets a Python
   user install skills shipped by JS packages. Cost: ~1-2 days. Win:
   genuine cross-language utility, no new distribution channel.
3. **Publish to npm too.** Either as a thin wrapper that requires
   Python ≥3.10 and shells out, or as a separately maintained
   reimplementation. Wrapper: cheap to build, awkward error message
   when Python isn't installed, ongoing release coordination.
   Reimplementation: huge ongoing cost, splits the codebase. Cost:
   high either way.

**My take:** path 1 is essentially free and should happen regardless.
Path 2 is the cheap-but-meaningful pivot — `skill` becomes the
polyglot package-data tool, and the Python-coupling moves from "you
must be a Python project" to "you must `pip install` to get the CLI".
Path 3 is probably not worth it: JS devs already have `gh skill` and
`npx skills`, and a wrapper-on-Python is an awkward sell.

**Don't conflate "implementation language" with "audience."** `skill`
is implemented in Python. Its audience can be polyglot.

### 9. README orientation

The README leads with the Python API. That's correct for Python developers
but misleading about the package's core value. The first thing a new user
should see is:

> "I have skills scattered across Claude Code, Cursor, and Copilot. How do
> I manage them all?" → **Answer: this package.**

The current README is effectively docs for the `LocalSkillStore` /
`install()` / `link_skills()` API, with the multi-agent narrative implied
but not foregrounded. The `skill-docs` skill itself has better instincts
than the actual README.

**Recommended action:** rewrite the top of the README around three user
journeys: (a) "I want to find a skill"; (b) "I want to use the same skill
across Claude Code, Cursor, Copilot"; (c) "I'm shipping a Python package
and want users to get its skills". Each becomes 5-10 lines.

### 10. No `.claude-plugin/marketplace.json` / `plugin.json` support

The Vercel CLI explicitly supports plugin-manifest skill discovery. This
matters because it's the most flexible way to declare *where in your repo
skills live* without adopting a particular convention. If `skill` shipped
plugin-manifest reading, it would inherit a lot of repos that don't use the
canonical layout — including, for example, repos that ship skills in
`{pkg}/data/skills/`.

**Recommended action:** add manifest-file discovery to `_resolve_skills_source()`
in `install.py`. This is the single highest-leverage change for repo
discovery breadth.

---

## Smaller observations

- `pyproject.toml` declares `requires-python = ">=3.10"` but the
  description type hints (`str | None`) work fine on 3.10. ✓
- The `_resolve_skills_source()` function in `install.py:359-388` already
  has a Python-aware branch (`{pkg}/data/skills/`). It's the only tool in
  the ecosystem that does. Worth highlighting in docs as a Python-specific
  feature.
- `validate()` re-implements much of what `skills-ref validate` does. If
  you're going to keep your own validator, consider also exposing
  "validate using the upstream `skills-ref` if available, fall back to
  built-in checks". This gives users one less spec to track.
- The `format_skill_info_table` table in `cli_format.py` would benefit from
  a `--json` output mode (essentially every CLI in this space has one
  now).
- The composability story is strong but invisible: a user who reads the
  README doesn't learn that `LocalSkillStore` is a `MutableMapping`. One
  line near the top of the README would do it.
- `_check_existing` in `install.py:90` is named slightly misleadingly —
  it's classifying the *kind* of thing at a path. Consider
  `_classify_target` or `_target_state`.
- `skill list-skills` is a bit redundant. Consider `skill list` (with
  `list-skills` as a backwards-compatible alias).
- Tests under `tests/` weren't reviewed in this pass — worth a separate
  audit for whether they exercise the multi-agent paths or only Claude
  Code.

---

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `gh skill` becomes the default and `skill` looks redundant | High | High | Re-frame `skill` as "multi-agent + multi-backend + Python-native"; integrate `gh skill` rather than compete with it |
| `audience` field gets squashed by upstream `gh skill publish --fix` | Medium | Medium | Move under `metadata.audience` until accepted into spec |
| Skills shipped via `{pkg}/data/skills/` aren't discoverable by `gh skill list` | Medium | Medium | Document the trade-off; consider dual-location for new packages |
| Provenance metadata divergence from `gh skill` breaks update interop | High | Medium | Adopt `gh skill`'s frontmatter convention for source/ref/sha |
| `skills-ref validate` rejects skills `skill validate` accepted | Low-Medium | Low | Run `skills-ref` in CI as a sanity check |

---

## Recommended priority order

1. **`audience` field placement** (cheap, prevents a future-painful break).
2. **Provenance frontmatter alignment with `gh skill`** (cheap, unlocks
   interop).
3. **Plugin manifest discovery** (medium, highest leverage for repo
   coverage).
4. **README re-orientation around user journeys** (cheap, large UX win).
5. **`gh-skill` backend + `skill update`** (medium).
6. **`--pin` and `--preview` flags on `install`** (small).
7. **`skill publish` (or skill-publish guidance skill)** (medium).
8. **Decide and document the package-data story** (see
   `skill_distribution_analysis.md`).

---

## Sources

- [Manage agent skills with GitHub CLI — GitHub Changelog](https://github.blog/changelog/2026-04-16-manage-agent-skills-with-github-cli/)
- [`gh skill install` manual](https://cli.github.com/manual/gh_skill_install)
- [`gh skill` manual](https://cli.github.com/manual/gh_skill)
- [Agent Skills specification — agentskills.io](https://agentskills.io/specification)
- [Vercel `skills` CLI — vercel-labs/skills](https://github.com/vercel-labs/skills)
- [Vercel skills CLI source — `src/skills.ts`](https://raw.githubusercontent.com/vercel-labs/skills/main/src/skills.ts)
- [Big Hat Group write-up on `gh skill`](https://www.bighatgroup.com/blog/gh-skill-github-cli-agent-skills-management/)
- [Mintlify guide: Skills installation methods](https://www.mintlify.com/vercel-labs/skills/guides/installation-methods)
