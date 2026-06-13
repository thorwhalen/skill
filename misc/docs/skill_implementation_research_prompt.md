# Deep Research Prompt: Skill Distribution & Installation Conventions

This is the **implementation/tactics** prompt — questions about
conventions, layouts, manifests, and ecosystem mechanics. It assumes
the prior question — "should the `skill` package exist at all?" — has
been answered yes. If you haven't run that one yet, see
`skill_strategic_research_prompt.md`.

This is a deep-research prompt to be run before settling on the
package-data + canonical-layout design described in
`skill_distribution_analysis.md`. Several open questions there are based
on partial info or recent (April 2026) ecosystem moves that need
ground-truthing before we commit.

Run as a deep-research task; expect the answer to be 2,000–5,000 words
with concrete citations and code samples where applicable.

---

## Background (paste this into the deep-research tool)

The Agent Skills ecosystem (skills as `SKILL.md` directories, per
agentskills.io) crystallized in late 2025 / early 2026 around two
installer tools:

- **Vercel's `npx skills add`** (vercel-labs/skills, ~7.5K stars), which
  has been the de facto installer since Q4 2025.
- **GitHub's `gh skill install`** (announced 2026-04-16, requires
  `gh` v2.90.0+), which adds provenance tracking, version pinning,
  immutable releases, and integration with GitHub Releases.

I maintain a Python package called `skill` (PyPI:
`pip install skill`) that does AI-agent-skill management with a
multi-agent / multi-backend focus. Source:
https://github.com/thorwhalen/skill

I'm at a decision point: **what is the right canonical layout for a
Python package that wants to ship installable agent skills, given both
the pip-distribution requirements (skills should live inside the
package directory to ship via wheels) and the gh-skill / npx-skills
discovery conventions (skills should live at `skills/<name>/SKILL.md`
at the repo root)?**

I have written a preliminary analysis (in
`skill_distribution_analysis.md`) recommending dual-location with
`skills/` at the repo root as source-of-truth and a build-hook /
symlink mirror to `{pkg}/data/skills/`. But several open questions need
to be resolved before I lock in the design.

---

## Research questions

Please investigate and report on each of the following with concrete
evidence (links, code samples, output of real commands where possible).

### Q1 — How does `gh skill install` actually discover skills inside a repo?

I have *some* info from blog posts and the public manual page, but I want
to confirm by reading the actual implementation. Specifically:

- What is the exact priority order of search paths inside a repo cloned
  by `gh skill install`?
- Does it support plugin-manifest discovery (`.claude-plugin/plugin.json`
  or `.claude-plugin/marketplace.json`), the way `npx skills add` does?
  Or only file-system convention?
- Does it have a recursive-fallback search if no skills are found in
  standard paths?
- What happens if a repo has skills *only* in
  `your_pkg/data/skills/`? Does `gh skill install OWNER/REPO some-skill`
  still find them, or does it give up?
- Is the `gh-skill` binary open-source? If so, link to the relevant
  source files (skill discovery and walking logic).

Cite the actual repo / source if findable, not just blog posts.

### Q2 — What provenance metadata does `gh skill install` actually write to installed `SKILL.md` files?

The blog announcements say "source tracking metadata" is "injected into
their frontmatter." I want the exact YAML keys, format, and any examples
from a real install.

- Run `gh skill install github/awesome-copilot documentation-writer
  --agent claude-code --scope user` (or pick any installable skill) on
  a sandbox machine, and report the resulting `SKILL.md` frontmatter
  diff vs. the upstream.
- Is the metadata under `metadata.*` (spec-compliant) or as
  top-level fields (which would *violate* the agentskills.io spec)?
- Does `gh skill update` use this metadata to detect drift, and if so,
  how (tree SHA comparison, semver, content hash)?

If a sandbox install isn't possible, find a repo where someone has
committed a skill that was installed by `gh skill install` and inspect
its frontmatter — search GitHub for "tree-sha" in YAML frontmatter, or
similar.

### Q3 — Does the agentskills.io spec allow custom top-level frontmatter fields?

The spec (https://agentskills.io/specification) defines these top-level
fields: `name`, `description`, `license`, `compatibility`, `metadata`,
`allowed-tools`. My `skill` package introduces a top-level `audience:
users | developers | both` field for distinguishing consumer skills from
developer skills.

- Is there an open issue, PR, or discussion at
  github.com/agentskills/agentskills proposing this or a similar field?
- Does the `skills-ref` validator (the upstream linter) accept extra
  top-level fields, warn on them, or reject them?
- Does `gh skill publish --fix` strip extra top-level fields, or
  preserve them?
- What's the right path: namespace under `metadata.audience` (safe but
  hidden), push upstream (high effort, uncertain), or fork the spec
  (high cost, fragmenting)?

### Q4 — How do popular packages (any language) currently ship agent skills?

Identify 10–15 packages across ecosystems (Python, npm, Cargo, Go) that
ship agent skills in some form. For each:

- Where do they put the skills (root `skills/`, package-data location,
  `.claude/skills/` shipped, plugin manifest, none of the above)?
- How do they document the install path (package-manager-only, gh-skill
  recommended, both, separate `skill link-skills` invocation, some
  other tool)?
- Do they use symlinks, build hooks, or commit the same content twice?
- Is there an emerging convention specific to npm packages (e.g., a
  `"skills"` key in `package.json`, or a `node_modules/<pkg>/skills/`
  search path used by `npx skills add`)?

Look in particular for:
- Python: `aisuite`, Anthropic-owned PyPI packages, LangChain libs
- npm: vercel-labs's own packages, Anthropic's `@anthropic-ai/*`
  packages, any framework that embeds skills
- Cargo / Go: anything you can find — likely sparse but informative
- Packages that have published to skills.sh

This grounds the recommendation in what real maintainers actually do
and surfaces whether the cross-language conventions are already
diverging.

### Q5 — Does the Vercel CLI's `npx skills add` find skills in `{pkg}/data/skills/`?

The Vercel CLI source (`src/skills.ts`) lists ~30 priority search paths,
none of which include `{pkg}/data/skills/` or any Python convention. But
it does have a recursive fallback (depth ≤ 5, skipping `node_modules`,
`.git`, `dist`, `build`, `__pycache__`).

- Test: clone a Python package whose only skills are in
  `{pkg}/data/skills/`, run `npx skills add . --list`, and report
  whether the skills appear.
- If yes: at what depth? Does the fallback work for `your_pkg/data/skills/`
  (4 levels deep)?
- If no: what's the failure mode? Silent? Error?

### Q6 — What's the build-hook story for hatch / setuptools / flit?

I want maintainers to have a one-line option for "mirror `skills/` into
`{pkg}/data/skills/` at build time." Investigate:

- Hatch (hatchling) build hooks: simplest config that copies `skills/`
  to `{pkg}/data/skills/` during sdist + wheel build.
- setuptools: simplest config that does the same, ideally without a
  custom `setup.py`.
- flit: whether this is even possible.
- A pure-symlink option: do hatchling/setuptools/flit follow symlinks
  inside the source tree when building? (Test by creating a repo with a
  symlink in `your_pkg/data/skills/` pointing to `../../../../skills/`,
  building a wheel, and inspecting the wheel's contents.)

### Q7 — Plugin manifest schema: is it standardized?

Vercel's CLI explicitly supports `.claude-plugin/plugin.json` and
`.claude-plugin/marketplace.json` for skill discovery. But I've seen no
spec for the schema. Investigate:

- What's the schema of these files? (Find examples in the wild and read
  Vercel's source if needed.)
- Is the `.claude-plugin/` directory name itself standardized, or is
  it a Vercel/Anthropic-specific convention?
- Does `gh skill install` read these manifests, or only Vercel's CLI?
- If `gh skill install` doesn't currently read them: is there an issue
  filed asking for that support?

### Q8 — User experience: do people actually run `gh skill install` after `pip install pkg`?

This is the real question underlying the whole design. Survey:

- GitHub issues, blog posts, or tweets about people's workflow for
  using skills shipped by Python packages.
- Does the friction of "two installs" (pip + gh skill install) matter
  in practice, or is it negligible?
- Is there evidence of users falling off when packages ship skills
  separately vs. shipping them with pip?

Even thin evidence (one or two real cases) is useful here. The default
should track what users *actually do*, not what we hope they do.

### Q9 — Forward-looking: where is the spec going?

agentskills.io is described as a spec maintained by Anthropic, but the
ecosystem (Vercel, GitHub, Cursor, etc.) is multilateral. Predict the
next 6 months:

- Is there a roadmap for `agentskills.io` v2?
- Are there open issues that suggest changes to frontmatter fields,
  directory layout, or installation conventions?
- Is there any consolidation expected (e.g., a single canonical
  registry analogous to npm)?

### Q10 — Claude Code's `/plugin install` and marketplace ecosystem: how does it relate to `gh skill` and `npx skills`?

There's a third installation channel I underweighted in the initial
analysis: Claude Code's own `/plugin install` and `/plugin marketplace add`
system. Anthropic ships `claude-plugins-official` as a default
marketplace, and third-party catalogs (e.g.,
`claude-plugins-plus-skills`, `claude-skills-marketplace`) host hundreds
of skills.

Investigate:

- What is the schema of `.claude-plugin/marketplace.json` and
  `.claude-plugin/plugin.json`? Find an authoritative source (Anthropic
  docs or canonical example repos).
- Can a single repo be simultaneously: a `gh skill install` source
  (canonical `skills/` layout), an `npx skills add` source (also
  works), and a Claude Code marketplace (manifest declares it)?
  Or do these conventions conflict?
- Does `/plugin install` write provenance metadata into the installed
  skills the way `gh skill install` does? If so, what keys?
- Is there overlap or substitutability between
  `/plugin marketplace add owner/repo` and `gh skill install owner/repo`,
  or are they different mental models (plugins-bundle-skills vs
  skill-as-unit-of-install)?
- Practical question: should the `skill` package generate a
  `marketplace.json` from a directory of skills, so that any repo
  managed by `skill` is automatically `/plugin install`-able?

This shapes whether Option 5 in `skill_distribution_analysis.md`
(Claude marketplace) deserves promotion to a default-on capability.

### Q11 — Polyglot publishing: should `skill` itself be installable from npm?

`skill` is implemented in Python and distributed via PyPI. It has a CLI
that is largely language-agnostic. A frontend dev's reaction to
`pip install skill` is plausibly "not for me" — even though the tool
would work fine on their JS project.

Investigate:

- Are there real cases of CLI tools published to *both* PyPI and npm?
  (e.g., `aws-cdk` for Python actually requires Node.) What's the
  pattern, and how painful is it operationally?
- What are the failure modes of a thin npm wrapper that requires
  Python ≥3.10 and shells out to `python -m skill`? (Specifically:
  the error message a Mac/Win user sees when they `npm install -g`
  and Python isn't installed.)
- Alternative: ship as a standalone binary via PyInstaller / shiv /
  Nuitka, distributed via Homebrew + a curl installer + npm wrapper.
  How does this affect cold-start time, install size, plugin/entry-point
  support?
- Is there evidence of demand for a polyglot `skill`-style tool?
  (GitHub issues asking for npm install on similar Python tools, or
  feature requests for cross-language support on `gh skill` /
  `npx skills`.)
- Counter-strategy: instead of going *to* npm, make `skill` *consume*
  npm — detect `node_modules/<pkg>/skills/` and a `"skills"` key in
  `package.json` the way it currently detects `pyproject.toml`. Is
  this convention already in use anywhere?

The implicit question is which audience is realistic. If JS devs use
`gh skill` and `npx skills` happily, then `skill`'s natural audience
stays Python-shaped. If JS devs would *prefer* `skill`'s feature set
(multi-backend search, lock files, etc.) but bounce on the Python
install, the npm-wrapper investment is justified.

### Q12 — Risk: what would break my package's design assumptions?

What ecosystem moves over the next 6 months would force a rewrite of
the `skill-enable` skill or the `skill` package's installer?

- Spec changes that deprecate top-level custom fields.
- A canonical registry that replaces GitHub-as-backend.
- A new convention for Python packages specifically.
- `gh skill` becoming required (e.g., GitHub auth becoming non-optional).

Identify the top 3 risks, ranked by likelihood × impact.

---

## Output format

A single markdown document with:

- One section per question, each leading with a 1–2 sentence answer
  followed by evidence and citations.
- A final "Synthesis" section with concrete recommendations for the
  `skill` package design, calibrated against the evidence found.
- Use Vancouver-style references (`[1]`, `[2]`, ...) with a
  REFERENCES section. Hyperlink with `[name](url)` where possible.

If a question can't be answered conclusively from public sources,
report what *is* knowable and explicitly flag the gap rather than
speculating.

---

## Why this matters

The default we set in `skill-enable` will propagate to every Python
package that uses the `skill` package to ship its consumer skills. Bad
defaults compound. Right now we're recommending `{pkg}/data/skills/`
based on Python conventions, but the ecosystem has moved to
`skills/<name>/` at the repo root as the convention that installers look
for. The decision to go single-location, dual-location, or
manifest-driven affects:

- How discoverable shipped skills are via `gh skill list <repo>`.
- Whether they show up on skills.sh leaderboards.
- Whether `gh skill update` can manage them.
- The friction users experience to start using the package's skills.
- Whether other tools in the ecosystem treat the package as a
  first-class skill source.

Get this right once, and we can stop thinking about it.
