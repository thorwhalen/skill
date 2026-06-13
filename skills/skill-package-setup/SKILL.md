---
name: skill-package-setup
description: >-
  Canonical, agent-agnostic policy for WHERE a package's AI agent skills live
  and HOW they are distributed so they're discoverable by `gh skill` (and any
  agent host — Copilot, Cursor, Codex, Gemini, Claude) AND, where wanted,
  shipped with `pip install`. Use this skill to set up skills for a new package,
  migrate an existing repo to the canonical layout, consolidate skills scattered
  across `.claude/skills/` / `skills/` / `{pkg}/data/skills/`, make every
  SKILL.md spec-clean, or answer "where should my package's skills live". Also
  the authority other skills defer to (e.g. wads-skillify). Triggers on "set up
  skills", "where should skills live", "make skills gh-skill installable",
  "migrate/restructure the skills layout", "skillify this repo". Maintainer skill.
metadata:
  audience: developers
---

# Skill package setup — canonical layout & distribution

The **source of truth** for where a package's skills live and how they ship.
Agent-agnostic; other tooling (e.g. `wads-skillify`) defers here for layout and
spec compliance. Two flows: **set up** a new package, or **migrate** an existing
one. Detail lives in the references — read on demand:

- `references/canonical-layout-and-distribution.md` — the discovery facts, the
  full distribution matrix, the SKILL.md spec, and the `gh skill` surface.
- `references/migration-runbook.md` — exact commands for both flows.

Golden rule: **observe, don't invent.** Every layout move is shown as a plan
before it's applied; never break tests without asking.

## Who discovers what (why layout matters)

| Location | `gh skill` discovers? | Claude Code reads? | Ships via `pip`? |
|---|---|---|---|
| `{pkg}/data/skills/<name>/` | **yes** — `gh skill` matches any non-hidden `**/skills/*/SKILL.md` (nested-prefix glob) | no | **yes** (inside the package) |
| `skills/<name>/` (repo root) | **yes** — same glob, the ecosystem-wide convention | no | no |
| `.claude/skills/<name>/` | no — hidden dirs skipped (unless `--allow-hidden-dirs`) | **yes** | no |
| `.agents/skills/<name>/` | install *destination* for Copilot/Cursor/Codex/Gemini | no | no |

Key fact (confirmed against the `gh skill` manual): **`gh skill` discovers a
`skills/` directory at ANY non-hidden depth**, so `{pkg}/data/skills/` is a
first-class `gh skill` source — not a fallback. No single location serves
everyone, though: Claude Code reads only `.claude/skills/`. Hence the rule.

## The rule (memorize this)

**Real skill files live in exactly ONE non-hidden location, with relative
per-skill symlinks in `.claude/skills/`.** Pick the location:

| Repo kind | Canonical real-files location |
|---|---|
| Pip-installable package whose skills should ship with `pip install` | **`{pkg}/data/skills/<name>/`** — ships via pip AND `gh skill`-discoverable. One location serves both channels. |
| Everything else (apps, skill-only repos, dev/maintainer-only skills) | **`skills/<name>/`** at the repo root — the ecosystem convention. |

- **Never both.** Real files in both `skills/` and `{pkg}/data/skills/` means
  `gh skill` reports duplicate skills. The Step-0 `find` in the runbook is your
  duplicate check.
- **`.claude/skills/<name>` is a relative symlink** into the chosen location
  (`../../skills/<name>` or `../../<pkg>/data/skills/<name>`) — Claude Code
  doesn't read the canonical dirs, so this bridge is required. Symlink per skill,
  never the whole `.claude/skills/` dir (Claude writes `.system/` files there).
- **Don't publish symlinks as the source.** Whether `gh skill` dereferences a
  committed symlink at the *source* path is undocumented — keep real files in the
  canonical path; use symlinks only as the `.claude/skills/` bridge.

## Decide: new vs migrate

1. Inventory: `find . -name SKILL.md -not -path './.git/*'` + `ls -la .claude/skills`.
2. No skills anywhere → **Flow A (new)**. Skills already exist → **Flow B (migrate)**.

## Flow A — new package

1. Pick the canonical location per the rule (pip-shipped → `{pkg}/data/skills/`,
   else `skills/`).
2. Scaffold `…/<pkg>-quickstart/SKILL.md` with spec-valid frontmatter
   (`name` == folder name, lowercase `[a-z0-9-]`; `description` ≤ 1024 chars,
   packed with trigger keywords). Use **skill-build**/**skill-creator** for content.
3. Add relative per-skill symlinks in `.claude/skills/` (or `skill link-skills .`).
4. Classify audience (consumer vs developer) — reuse **skill-enable**'s signal
   lists. Prefix maintainer skills `<pkg>-dev-…`; put `metadata.audience` in
   frontmatter.
5. If pip-shipping, wire package-data (**skill-enable** owns the mechanics).
6. README "Skills" section with `gh skill install <owner>/<repo> <name>` lines
   (**skill-docs** can generate it).
7. Validate (`gh skill publish --dry-run`, or `skill validate`/`skills-ref
   validate`), then `gh skill publish` and tag a release for `@vX.Y.Z` pinning.

## Flow B — migrate an existing repo

Full commands in `references/migration-runbook.md`. Shape:

1. **Inventory** real files vs symlinks; detect duplicates across locations.
2. **Choose** the one canonical location (rule above).
3. **Relocate** real dirs there with `git mv` (e.g. out of `.claude/skills/`),
   leaving relative symlinks behind.
4. **Consolidate** any duplicates so real files exist in exactly one place.
5. **Fix spec conformance** (checklist below).
6. **Validate**, update the README, **publish**.

## Spec-conformance checklist (either flow)

- [ ] Folder name **equals** `name:`; `name` lowercase `[a-z0-9-]`, ≤64 chars,
      no leading/trailing/double hyphens (rename `foo_bar` → `foo-bar` + the folder).
- [ ] Only spec top-level keys: `name`, `description`, `license`,
      `compatibility`, `metadata`, `allowed-tools`. Custom keys (notably
      `audience`) go under `metadata:`. No Claude-only keys (`when_to_use`,
      `argument-hint`, `paths`, `hooks`, …) in portable skills. Never `agent-version`.
- [ ] `allowed-tools`, if present, is a **space-separated string**, not a YAML list.
- [ ] `description` ≤ 1024 chars (what it does + when to use it); body < 500 lines
      (push detail to `references/`).
- [ ] Provenance keys (`github-repo`, `github-path`, `github-ref`,
      `github-pinned`, `github-tree-sha`) are **never** hand-authored — `gh skill
      install` writes them on the consumer's machine.

## Distribution

- **Primary:** `gh skill install <owner>/<repo> <name> --agent <host>` — works
  for every agent host; supports pinning (`@vX.Y.Z` / `--pin <sha>`) and
  `gh skill update`.
- **Pip-shipped packages additionally** deliver skills inside the wheel
  (`{pkg}/data/skills/`); document the offline link step too.
- Always `gh skill preview` third-party skills before installing (not verified by GitHub).

## Related skills

- **wads-skillify** — wads-fleet repo-improvement entry; **defers to this skill**
  for layout & compliance, adds the wads assessment baseline + dispatch.
- **skill-enable** — pip package-data wiring + audience classification.
- **skill-build** / **skill-creator** — author skill content.
- **skill-docs** — README "Skills" section.
- **skill-sync** — keep skill content in sync with the code it documents.

Full `gh skill` surface and Agent Skills spec:
`references/canonical-layout-and-distribution.md`.
