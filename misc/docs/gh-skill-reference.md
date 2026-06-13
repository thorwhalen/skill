# `gh skill` — Complete Reference

> Research notes compiled 2026-06-12. `gh skill` shipped **2026-04-16** and is in
> **public preview** (subject to change). Requires **GitHub CLI ≥ v2.90.0**.
> Local machine is on `gh 2.72.0` — upgrade before using (`brew upgrade gh`).

Some low-level details below (the exact repo *scan* path patterns, some flag names)
are drawn from community deep-dives rather than first-party docs, because GitHub's
own docs are thin during preview. Each such item is flagged **[verify]** — confirm
with `gh skill <subcommand> --help` once the CLI is upgraded.

---

## 1. What it is

`gh skill` is a first-party GitHub CLI command group for **discovering, installing,
updating, and publishing Agent Skills** straight from GitHub repositories. It is the
package-manager-like front end for the **Agent Skills** open standard ([1]).

Key idea: a *skill* is just a folder containing a `SKILL.md` file (metadata +
instructions, plus optional `scripts/`, `references/`, `assets/`). The format was
created by Anthropic, released as an open standard, and is now supported by ~40+ agent
hosts — Claude Code, GitHub Copilot, Cursor, Codex, Gemini CLI, Goose, OpenCode,
Roo Code, and many more ([1], [2]). `gh skill` makes any GitHub repo a distribution
channel for these folders, **across all those hosts — not just Claude** ([3]).

This directly replaces a lot of bespoke "copy/symlink my skills into the right place"
tooling: instead of homegrown installers, you `gh skill install owner/repo skill`.

---

## 2. Requirements & status

| | |
|---|---|
| Minimum `gh` version | **v2.90.0** ([3], [4]) |
| Released | 2026-04-16 ([3]) |
| Maturity | Public preview — "subject to change without notice" ([3]) |
| Alias | `gh skills` works interchangeably with `gh skill` ([5]) |
| Standard | Agent Skills spec at **agentskills.io** ([1]) |
| Validator | `skills-ref validate ./my-skill` (reference lib `agentskills/agentskills`) ([1]) |

---

## 3. Command surface

```bash
gh skill search   KEYWORD                       # discover skills on GitHub
gh skill preview  OWNER/REPO SKILL              # inspect a skill's content before installing
gh skill install  OWNER/REPO SKILL[@VERSION]    # install into the right host dir
gh skill list                                   # list locally installed skills
gh skill update   [--all]                       # check/apply upstream changes
gh skill publish  [--dry-run] [--fix]           # validate & publish skills in a repo
```

### `search`
Find skills by keyword across GitHub. `gh skill search terraform` ([5]).

### `preview`
Print a skill's `SKILL.md` / contents **without installing**. The recommended
safety step before installing anything, since GitHub does **not** verify skills and
they can contain prompt injection or malicious scripts ([3], [6]).

```bash
gh skill preview github/awesome-copilot documentation-writer
```

### `install`
Installs a skill into the correct on-disk directory for the chosen agent host.

```bash
gh skill install github/awesome-copilot documentation-writer
gh skill install github/awesome-copilot documentation-writer --agent claude-code --scope user
gh skill install github/awesome-copilot documentation-writer@v1.2.0      # pin by tag
gh skill install github/awesome-copilot documentation-writer --pin v1.2.0
gh skill install github/awesome-copilot documentation-writer --pin abc123def   # pin by SHA
```

Flags:
- `--agent <host>` — target agent host. Values seen: `copilot` (default), `claude-code`,
  `cursor`, `codex`, `gemini`, `antigravity` ([2]). **[verify]** the full enum.
- `--allow-hidden-dirs` — also scan hidden agent dirs (e.g. `.claude/skills/`,
  `.github/skills/`) as **sources** inside the repo, not just the top-level `skills/`.
- `--scope <user|project>` — `user` = personal (home dir, shared across projects);
  `project` = inside the current repo, shareable with the team ([7]). Choose `project`
  when you want the skill committed and shared.
- `--pin <ref>` — lock to a tag or commit SHA so broad `update --all` runs skip it ([8], [5]).
- `SKILL@VERSION` — install a specific tag/SHA inline ([3], [8]).

One repo can host **multiple** skills; you install them by name individually
(e.g. `documentation-writer@v1.2.0`, `code-reviewer@v2.0.1` from the same repo) ([2]).

### `list`
Show all installed skills across known host directories ([5]).

### `update`
Scans all known agent-host directories, reads the provenance metadata baked into each
installed `SKILL.md`, and checks upstream for changes. Comparison is by **git tree SHA
of the source directory**, so you see *real content drift*, not cosmetic version
bumps ([3], [8]). Pinned skills are skipped. `--all` updates everything
non-interactively; bare `gh skill update` is interactive ([5], [8]).

### `publish`
Validates the skills in the current repo against the Agent Skills spec and helps you
ship them. It ([3], [6], [8]):
- validates `SKILL.md` frontmatter & naming against the **agentskills.io** spec
  (`--fix` auto-corrects metadata issues; `--dry-run` validates without publishing),
- surfaces **repo-hygiene recommendations** — checks tag protection, secret scanning,
  and code scanning settings,
- offers to enable **immutable releases**, so published release content cannot be
  altered later — *even by repo admins*. Combined with tag/SHA pinning, this makes
  `gh skill install owner/repo skill@v1.2.0` **byte-stable even if the repo is later
  compromised** ([8]).

---

## 4. Where skills install (destinations)

`gh skill install` writes to the conventional directory for the chosen host and scope.
The standardized, host-neutral locations are `*/skills/` directories ([7], [9]):

| Scope | Discovered/installed directories |
|---|---|
| **Project** (in-repo, committed) | `.github/skills/`, `.claude/skills/`, `.agents/skills/` |
| **User** (home, cross-project) | `~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/` |

Each skill lands as `<dir>/<skill-name>/SKILL.md` (+ its bundled files). Example: a
project-scope Claude install of `next-best-practices` →
`.claude/skills/next-best-practices/` ([7]).

> **Note the distinction** between *destination* dirs (above — where install writes
> locally) and *source/scan* dirs (§6 — where `gh skill` looks **inside a repo** to
> find publishable skills). They are **not** the same set. Your package's
> `<pkg>/data/skills/` **is** a valid source (it's a `skills/` dir at a non-hidden
> depth — see §6) but is **not** an install destination.

---

## 5. Provenance metadata (the killer feature)

When `gh skill install` runs, it writes tracking metadata **directly into the installed
`SKILL.md`'s YAML frontmatter**. Because provenance lives inside the file, it travels
with the skill wherever it's copied ([3]). The keys ([7]):

| Frontmatter key | Meaning |
|---|---|
| `github-repo` | URL of the source GitHub repository |
| `github-path` | Path to the skill directory **inside** that repository |
| `github-ref` | Tag or commit hash referenced at install time |
| `github-pinned` | The pinned revision set via `--pin` (if any) |
| `github-tree-sha` | Hash of the skill directory's contents — used to detect updates |

`gh skill update` reads these to find what changed; `github-tree-sha` lets it detect
content changes even when a version label didn't move ([7], [8]).

> Practical consequence: **don't hand-author these keys.** They are install artifacts.
> Your source `SKILL.md` (in your repo) should *not* contain them; `gh skill install`
> adds them on the consumer's machine.

---

## 6. How `gh skill` finds skills in a repo (source discovery)

Per the `gh skill install` manual ([5a]): skills are *"discovered automatically using
the `skills/*/SKILL.md` convention … **including when the `skills/` directory is nested
under a prefix** (e.g. `terraform/code-generation/skills/...`)."* In other words, the
scan is effectively:

```
**/skills/<name>/SKILL.md          # any non-hidden 'skills/' directory, at ANY depth
```

What this means concretely:
- **`skills/<name>/SKILL.md`** at the repo root — the canonical convention.
- **`<pkg>/data/skills/<name>/SKILL.md`** — **also discovered**, because
  `<pkg>/data/skills/` *is* a `skills/` directory under a non-hidden prefix. So a
  Python package's `data/skills/` is a first-class `gh skill` source **and** ships via
  pip. This corrects an earlier assumption that `data/skills/` was invisible — that was
  the *Vercel `npx skills`* behavior (anchored paths + depth-≤5 fallback), not `gh skill`.
- **Hidden dirs** (`.claude/skills/`, `.agents/skills/`) are **excluded by default** —
  pass `--allow-hidden-dirs` to scan them as sources.
- **Explicit path** (`gh skill install OWNER/REPO path/to/skill`) bypasses discovery and
  avoids a full tree traversal (faster).
- The skill's **folder name must equal its `name:` field**; a repo may publish many skills.

Packaging takeaway: **a skill is discoverable if its real directory sits in any
non-hidden `skills/` directory.** Pick ONE real location — `<pkg>/data/skills/` for
pip-shipped packages (serves pip *and* `gh skill`), else top-level `skills/` — and never
duplicate the same skill across both (it'd show up twice). Claude Code reads only
`.claude/skills/`, so add a relative symlink there per skill.

---

## 7. The Agent Skills spec (SKILL.md format)

`gh skill` is just tooling over the open format. The spec ([1]):

### Directory structure
```
skill-name/
├── SKILL.md          # Required: frontmatter + instructions
├── scripts/          # Optional: executable code (python/bash/js)
├── references/       # Optional: docs loaded on demand (REFERENCE.md, etc.)
├── assets/           # Optional: templates, images, data files
└── ...
```

### `SKILL.md` frontmatter schema

| Field | Required | Constraints |
|---|---|---|
| `name` | **Yes** | 1–64 chars; lowercase `a-z`, `0-9`, hyphens; no leading/trailing hyphen; no `--`; **must match folder name** |
| `description` | **Yes** | 1–1024 chars; what it does **and** when to use it; include trigger keywords |
| `license` | No | License name or reference to a bundled license file |
| `compatibility` | No | ≤500 chars; environment needs (intended product, system packages, network). Most skills omit it |
| `metadata` | No | Arbitrary string→string map; namespace your keys to avoid clashes |
| `allowed-tools` | No | Space-separated pre-approved tools, e.g. `Bash(git:*) Bash(jq:*) Read`. **Experimental**, host support varies |

Minimal:
```markdown
---
name: pdf-processing
description: Extract PDF text, fill forms, merge files. Use when handling PDFs.
---
```

With options:
```markdown
---
name: pdf-processing
description: Extract PDF text/tables, fill forms, merge PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or extraction.
license: Apache-2.0
compatibility: Requires Python 3.14+ and uv
metadata:
  author: thorwhalen
  version: "1.0"
---
```

### Progressive disclosure (how hosts load skills)
1. **Discovery** (~100 tokens): only `name` + `description` loaded at startup for every skill.
2. **Activation** (<5000 tokens recommended): full `SKILL.md` body loaded when a task matches.
3. **Execution**: `scripts/`, `references/`, `assets/` loaded only when needed.

Guidance: keep `SKILL.md` **< 500 lines**; push detail into `references/`; keep file
references one level deep; use relative paths from the skill root ([1]).

### Validation
```bash
skills-ref validate ./my-skill   # checks frontmatter + naming conventions
```

---

## 8. Cross-agent reach

The whole point: author once, run everywhere. Hosts that support the Agent Skills
format (non-exhaustive, from the agentskills.io client showcase) ([1]):

> Claude Code, Claude (claude.ai), GitHub Copilot, VS Code, Cursor, OpenAI Codex,
> Gemini CLI, Goose, OpenCode, OpenHands, Roo Code, Amp, Letta, Kiro, Factory,
> Junie, Tabnine, Qodo, Laravel Boost, Databricks Genie, Snowflake Cortex Code,
> Spring AI, fast-agent, Emdash, Mux, and ~20 more.

Each host has its own per-host docs for *where* it loads skills, but all agree on the
`SKILL.md` format and the `*/skills/` directory convention.

---

## 9. Security model

- Skills are **not verified by GitHub**; they can contain prompt injection, hidden
  instructions, or malicious scripts. **Always `gh skill preview` before installing
  third-party skills** ([3], [6]).
- Provenance frontmatter (§5) gives auditability: you can always see where an installed
  skill came from and at what SHA.
- `gh skill publish` + **immutable releases** + **tag/SHA pinning** give consumers
  supply-chain integrity: a pinned, immutable release is byte-stable even against a
  later repo compromise ([8]).

---

## 10. Open questions to confirm post-upgrade

Run these once `gh ≥ 2.90.0` is installed:
- `gh skill --help`, `gh skill install --help`, `gh skill publish --help` — confirm the
  exact `--agent` enum, `--scope` values, and whether there's an `uninstall`/`remove`.
- Confirm the precise **source scan paths** (§6) — whether `.claude/skills/` *in a repo*
  is also scanned as a source, or only `skills/` and root `<name>/`.
- Confirm whether `gh skill` follows **git symlinks** when reading a repo (it almost
  certainly does **not** resolve a symlinked `skills/<name>` → elsewhere over the API).
- Confirm behavior on **monorepos / subdirectories** (does `OWNER/REPO` accept a
  subpath, or only repo-root-anchored discovery?).

---

## References

[1] Agent Skills — Overview & Specification. agentskills.io. https://agentskills.io and https://agentskills.io/specification
[2] "Managing Agent Skills from the GitHub CLI with gh skill." AgentPatterns.ai. https://www.agentpatterns.ai/tools/copilot/gh-skill-cli-management/
[3] "Manage agent skills with GitHub CLI." GitHub Changelog, 2026-04-16. https://github.blog/changelog/2026-04-16-manage-agent-skills-with-github-cli/
[4] "Release GitHub CLI 2.90.0." cli/cli. https://github.com/cli/cli/releases/tag/v2.90.0
[5] "gh skill" manual. GitHub CLI. https://cli.github.com/manual/gh_skill
[5a] "gh skill install" manual (documents the nested-prefix `skills/*/SKILL.md` discovery glob and `--allow-hidden-dirs`). GitHub CLI. https://cli.github.com/manual/gh_skill_install
[6] "gh skill: GitHub CLI — What Shipped on April 16, 2026." open-techstack.com. https://open-techstack.com/blog/github-cli-gh-skill-agent-skills-2026/
[7] "You Can Now Distribute Agent Skills with the gh Command." azukiazusa.dev. https://azukiazusa.dev/en/blog/gh-agent-skill-management/
[8] "gh skill: install, pin, and publish agent skills from GitHub repos." Mervin Praison. https://mer.vin/2026/04/gh-skill-install-pin-and-publish-agent-skills-from-github-repos/
[9] "About agent skills." GitHub Docs. https://docs.github.com/en/copilot/concepts/agents/about-agent-skills
[10] "gh skill: GitHub's New CLI Command Turns Agent Skills Into Installable Packages." DEV Community. https://dev.to/om_shree_0709/gh-skill-githubs-new-cli-command-turns-agent-skills-into-installable-packages-2p82
