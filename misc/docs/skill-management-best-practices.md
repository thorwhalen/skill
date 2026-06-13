# Skills Management — Decision Record (2026-06)

How AI agent skills are organized and distributed across the package ecosystem,
now that `gh skill` (GitHub CLI ≥ v2.90.0, shipped 2026-04-16) is the cross-agent
standard. This is the capstone decision; the option analysis is in
`skill_distribution_analysis.md`, the `gh skill` reference in
`gh-skill-reference.md`, and the package review in `skill_project_review.md`.

---

## The decision

**Real skill files live in exactly ONE non-hidden location per repo:**

| Repo kind | Canonical location |
|---|---|
| Pip-installable package whose skills should ship with `pip install` | `{pkg}/data/skills/<name>/` |
| Everything else (apps, skill-only repos, dev/maintainer-only skills) | `skills/<name>/` at repo root |

- **Never both** real locations for the same skill (`gh skill` would report duplicates).
- **`.claude/skills/<name>` = relative per-skill symlink** into the canonical
  location (Claude Code reads only `.claude/skills/`).
- **Frontmatter is Agent-Skills-spec-clean**: folder name == `name`; only the six
  spec top-level keys; custom keys (e.g. `audience`) under `metadata`; no
  Claude-only keys; `name` lowercase-hyphenated.
- **Distribution:** `gh skill install <owner>/<repo> <name>` is the primary,
  cross-agent channel; pip-shipped packages additionally bundle skills in the wheel.

## Why (the load-bearing fact)

`gh skill` discovers skills by scanning for a `skills/` directory and matching
`skills/*/SKILL.md` **at any non-hidden depth** (per the `gh skill install`
manual: *"including when the `skills/` directory is nested under a prefix"*).

Therefore **`{pkg}/data/skills/` is a first-class `gh skill` source** — it's a
`skills/` directory under the non-hidden prefix `{pkg}/data/`. It serves *both*
channels at once: pip (it's inside the package) and `gh skill` (the nested glob).
So for pip packages, `{pkg}/data/skills/` is the single best location; top-level
`skills/` is for repos that don't pip-ship their skills.

> **Supersedes** the earlier "top-level `skills/` is the only SSOT; `{pkg}/data/skills/`
> is invisible/degraded" framing. That described the *Vercel `npx skills`* CLI
> (anchored paths + depth-≤5 fallback), not `gh skill`. The original
> `{pkg}/data/skills/` convention was right for pip packages all along — it only
> needed the `.claude/skills/` symlink bridge and spec-clean frontmatter.

## How it's operationalized

- **`skill-package-setup`** (in the `skill` package, top-level `skills/`) is the
  **canonical, agent-agnostic authority** for layout + distribution + spec
  compliance, with `references/` (runbook + gh-skill surface) and both flows
  (new + migrate).
- **`wads-skillify`** (in the `wads` package, part of `wads-repo-doctor`) is the
  **fleet entry point** for the big review/refactor — it **defers to
  `skill-package-setup`** for layout/compliance and adds the wads assessment
  baseline + dispatch. `skill` is an **optional dependency of `wads`**
  (`pip install 'wads[skills]'`).
- **`priv-rollout`** orchestrates the per-repo work across the ~190 packages.
- **`skill-enable`** owns the pip package-data mechanics + audience classification
  (which skills ship). **`skill-build`/`skill-creator`** author content;
  **`skill-docs`** writes the README section; **`skill-sync`** keeps content current.

## Migration

**On-touch**: each repo migrates when next worked on (the fleet review runs
`wads-repo-doctor` → `wads-skillify` → `skill-package-setup`'s runbook). Per repo:
relocate real dirs to the one canonical location, add `.claude/skills/` symlinks,
fix frontmatter, validate (`gh skill publish --dry-run`), document in the README,
publish + tag.

## Where to point the fleet-review agent

`wads-repo-doctor` (it dispatches the skills step to `wads-skillify`, which defers
to `skill-package-setup`), and `priv-rollout` for ordering. These already encode
this decision — no extra wiring.

## References

`gh-skill-reference.md` (full `gh skill` + spec reference),
`skill_distribution_analysis.md` (option analysis), `skill_project_review.md`
(`skill` package gaps + roadmap). Internal: exploration of `t/skill/` and ~45
package repos under `t/`, `i/`, `tt/`.
