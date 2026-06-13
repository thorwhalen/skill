# Canonical layout, distribution channels, and the SKILL.md spec

Reference for the `skill-package-setup` skill. Read the section you need.

---

## 1. Discovery facts (the basis for the layout rule)

Three readers, three behaviours:

- **`gh skill`** (and `npx skills`) discover skills by scanning for a directory
  named `skills/` and matching `skills/*/SKILL.md` — **at any non-hidden depth**.
  The `gh skill` manual: *"discovered automatically using the `skills/*/SKILL.md`
  convention … including when the `skills/` directory is nested under a prefix
  (e.g. `terraform/code-generation/skills/...`)."* So **`{pkg}/data/skills/` is a
  first-class source** (it contains a `skills/` dir under the non-hidden prefix
  `{pkg}/data/`), and so is repo-root `skills/`. Hidden dirs (`.claude/skills/`,
  `.agents/skills/`) are skipped unless you pass `--allow-hidden-dirs`.
- **Claude Code** reads only `.claude/skills/` (repo) and `~/.claude/skills/`
  (user). It does **not** read repo-root `skills/` or `{pkg}/data/skills/`.
- **`.agents/skills/`** etc. are install *destinations* (`gh skill install`
  writes there per `--agent`), not source conventions.

Consequence: no single real location satisfies both `gh skill` and Claude Code.
The fix is one real location + a symlink bridge — see §2.

> Note: the *Vercel `npx skills`* CLI uses anchored paths plus a depth-≤5
> recursive fallback (per `src/skills.ts`); earlier analysis that called
> `{pkg}/data/skills/` "only a degraded fallback" was describing that tool. For
> **`gh skill`**, `{pkg}/data/skills/` is a clean, first-class source.

## 2. The layout rule

**Real skill files live in exactly ONE non-hidden location; `.claude/skills/`
holds one relative symlink per skill.**

| Repo kind | Canonical real-files location |
|---|---|
| Pip-installable package whose skills should ship with `pip install` | `{pkg}/data/skills/<name>/` — ships via pip AND `gh skill`-discoverable; one location, both channels |
| Everything else (apps, skill-only repos, dev/maintainer-only skills) | `skills/<name>/` at repo root — the ecosystem convention |

- **Never both** real locations — `gh skill` would surface duplicates.
- **`.claude/skills/<name>`** → relative symlink (`../../skills/<name>` or
  `../../<pkg>/data/skills/<name>`). Per-skill, never the whole dir.
- **Symlink portability:** relative only (absolute links — anything starting with
  `/` — break in other clones); on Windows, git symlinks need `core.symlinks=true` + dev mode —
  if the repo has Windows contributors, commit real copies + a sync script instead.

## 3. Consumer vs developer skills

| | Consumer skill | Developer / maintainer skill |
|---|---|---|
| Audience | Users of the package (esp. their agents) | People working *on* the package |
| Examples | `vd-ingest`, `pdfdol-read` | `vd-add-backend`, "release this pkg" |
| Real-files location | `{pkg}/data/skills/` if pip-shipping, else `skills/` | `skills/` (no reason to bundle in the wheel) |
| Naming | `<pkg>-<verb/domain>` | `<pkg>-dev-<verb>` + `metadata.audience: developers` |

Use **skill-enable**'s signal lists to classify ambiguous cases. A package can
pip-ship its consumer skills from `{pkg}/data/skills/` and keep dev skills in
top-level `skills/` — that's two *different* skills in two locations, which is
fine (it's not the same skill duplicated).

## 4. Distribution matrix

| Goal | Channel |
|---|---|
| Cross-agent install, versioned, updatable | `gh skill install <owner>/<repo> <name> --agent <host>` (primary; `@vX.Y.Z` / `--pin <sha>`; `gh skill update`) |
| Skills bundled with the code, offline/CI/embedded | Pip — keep real files in `{pkg}/data/skills/`; document the offline link step |
| Claude Code, in-repo, for maintainers/contributors | The committed `.claude/skills/` relative symlinks |
| Other installers (additive) | `npx skills add <owner>/<repo>`; Claude marketplace via `.claude-plugin/marketplace.json` |

Pip package-data wiring (hatchling — most thorwhalen repos):

```toml
[tool.hatch.build.targets.wheel]
include = ["<pkg>/data/*"]   # or rely on hatchling's implicit <pkg>/** inclusion
```

(`skill-enable` owns the full package-data / installer details.)

## 5. The Agent Skills spec (SKILL.md format)

A skill is a folder with `SKILL.md` (+ optional `scripts/`, `references/`,
`assets/`). The **only** allowed top-level frontmatter keys:

| Field | Required | Constraints |
|---|---|---|
| `name` | yes | 1–64 chars; lowercase `a-z`,`0-9`,`-`; no leading/trailing/double hyphen; **must equal the folder name** |
| `description` | yes | 1–1024 chars; what it does **and** when to use it; trigger keywords |
| `license` | no | license name or bundled-file reference |
| `compatibility` | no | ≤500 chars; env needs (product, packages, network). Usually omitted |
| `metadata` | no | arbitrary string→string map; namespace keys (put `author`, `version`, `audience` here) |
| `allowed-tools` | no | **space-separated string** (not a YAML list), e.g. `Bash(git:*) Read`. Experimental |

Keep OUT of portable skills: Claude-Code-only keys (`when_to_use`,
`argument-hint`, `disable-model-invocation`, `paths`, `hooks`, `context`).
Never `agent-version` (not a spec field — use `compatibility` free-text).

Common thorwhalen fixes: top-level `audience:` → `metadata.audience`; underscore
names → hyphenate (`contaix_docs_to_markdown` → `contaix-docs-to-markdown`,
rename the folder too).

Progressive disclosure: hosts load `name`+`description` (~100 tokens) at startup,
the full body (<5000 tokens) on activation, and `scripts/`/`references/`/`assets/`
on demand. Keep `SKILL.md` < 500 lines; reference files one level deep, relative paths.

Validate: `gh skill publish --dry-run` (authoritative), or `skill validate
./<dir>` (this package), or `skills-ref validate ./<dir>` (agentskills.io).

## 6. `gh skill` command surface (needs `gh` ≥ v2.90.0)

```bash
gh skill search   KEYWORD
gh skill preview  OWNER/REPO SKILL                 # inspect before installing 3rd-party skills
gh skill install  OWNER/REPO SKILL[@VERSION]       # --agent <host> --scope <user|project> --pin <ref> [--allow-hidden-dirs]
gh skill list
gh skill update   [--all]                          # detects content drift via github-tree-sha; skips pinned
gh skill publish  [--dry-run] [--fix]              # validates spec; hygiene checks; offers immutable releases
```

Install destinations: project → `.github/skills/`, `.claude/skills/`,
`.agents/skills/`; user → `~/.copilot/skills/`, `~/.claude/skills/`,
`~/.agents/skills/`. `--agent`: `copilot` (default), `claude-code`, `cursor`,
`codex`, `gemini`, `antigravity`. Provenance keys written into the installed
SKILL.md (never authored): `github-repo`, `github-path`, `github-ref`,
`github-pinned`, `github-tree-sha`.

## 7. Sources

GitHub Changelog (2026-04-16), GitHub CLI manual (`gh_skill`, `gh_skill_install`
— the nested-prefix glob is documented there), agentskills.io spec, GitHub Docs
"about agent skills". Fuller catalogue + the older distribution analysis:
this repo's `misc/docs/gh-skill-reference.md`, `misc/docs/skill_distribution_analysis.md`.
