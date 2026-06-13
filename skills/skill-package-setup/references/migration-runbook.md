# Migration & setup runbook

Concrete commands for the `skill-package-setup` skill. Run from the repo root.
Substitute `<pkg>` (importable package, e.g. `vd`) and `<owner>/<repo>`
(e.g. `thorwhalen/vd`). **Show the plan + a dry-run diff before mutating; never
break tests without asking.**

---

## 0. Inventory (always first)

```bash
# Real SKILL.md files anywhere (skills/, {pkg}/data/skills/, .claude/skills/)
find . -name SKILL.md -not -path './.git/*' -not -path './.venv/*' \
  -not -path './node_modules/*' | sort

# .claude/skills entries — real dirs vs symlinks (find won't descend symlinks)
ls -la .claude/skills 2>/dev/null

grep -nE 'data|include|package-data' pyproject.toml || true
```

From the `find` output, note per skill: where the real files are, and whether
`.claude/skills/<name>` is a real dir or a symlink. **Duplicate check:** the same
skill name under two real locations (e.g. both `skills/` and `{pkg}/data/skills/`)
must be consolidated to one.

## 1. Choose the ONE canonical location

| Repo kind | Location |
|---|---|
| Pip package whose skills should ship with `pip install` | `<pkg>/data/skills/` |
| Everything else / dev-only skills | `skills/` (repo root) |

`gh skill` discovers both; only `<pkg>/data/skills/` also ships in the wheel.

---

## Flow A — new package

```bash
DEST=skills                      # or: DEST=<pkg>/data/skills  (pip-shipped)
mkdir -p "$DEST/<pkg>-quickstart"
```

Author `"$DEST/<pkg>-quickstart/SKILL.md"` (folder name == `name`, lowercase
hyphenated; `description` with trigger keywords; `metadata.audience: users`).
Use **skill-build**/**skill-creator** for content. Then bridge + validate +
publish as in Flow B steps B2–B5.

---

## Flow B — migrate an existing repo

### B1. Relocate real skill dirs to the canonical location

```bash
DEST=skills                      # or <pkg>/data/skills (pip-shipped); pick per step 1
mkdir -p "$DEST"

# Move real (non-symlink) dirs out of .claude/skills/ (Claude-only, hidden)
for d in .claude/skills/*/; do
  n=$(basename "$d")
  [ -L "${d%/}" ] && continue                  # already a symlink — skip
  [ -f "$d/SKILL.md" ] || continue
  git mv ".claude/skills/$n" "$DEST/$n"
done

# If real dirs live in the *other* canonical spot, consolidate into DEST too
# (e.g. moving skills/* -> <pkg>/data/skills/* when switching to pip-shipped):
# for d in skills/*/; do n=$(basename "$d"); git mv "skills/$n" "$DEST/$n"; done
```

### B2. Bridge: relative per-skill symlinks in `.claude/skills/`

```bash
mkdir -p .claude/skills
# rel prefix: skills/ -> ../../ ; <pkg>/data/skills/ -> ../../<pkg>/data/skills (compute from DEST)
for d in "$DEST"/*/; do
  n=$(basename "$d")
  ln -snf "../../$DEST/$n" ".claude/skills/$n"   # $DEST is repo-root-relative
done
git add .claude/skills
ls -la .claude/skills                            # each entry: symlink -> ../../$DEST/<name>
# guard against absolute/broken links:
for L in .claude/skills/*; do [ -e "$L" ] || echo "BROKEN: $L"; \
  case "$(readlink "$L")" in /*) echo "ABSOLUTE (fix): $L";; esac; done
```

### B3. Fix spec conformance (per skill)

```bash
grep -rnE '^audience:'       "$DEST"/*/SKILL.md || true   # -> move under metadata.audience
grep -rnE '^name:.*_'        "$DEST"/*/SKILL.md || true   # -> hyphenate + rename folder
grep -rnE '^agent-version:'  "$DEST"/*/SKILL.md || true   # -> delete; use compatibility
grep -rnE '^allowed-tools:\s*(\[|$)' "$DEST"/*/SKILL.md || true  # -> space-separated string
```

Plus: folder name == `name`; lowercase `[a-z0-9-]`; no Claude-only keys
(`when_to_use`, `argument-hint`, `paths`, `hooks`); `description` ≤ 1024 chars;
body < 500 lines.

### B4. Pip-shipped only — wire package-data (delegate to skill-enable)

If `DEST=<pkg>/data/skills`, ensure the wheel includes it (hatchling):

```toml
[tool.hatch.build.targets.wheel]
include = ["<pkg>/data/*"]
```

Verify: `python -m build --wheel >/dev/null && unzip -l dist/*.whl | grep -i skills`.
(**skill-enable** owns the full package-data / installer / convenience-function setup.)

### B5. Validate, document, publish

```bash
gh skill --help >/dev/null 2>&1 || echo "gh too old — need >= 2.90.0 (gh --version)"
gh skill publish --dry-run          # or: skill validate ./<DEST>/*  | skills-ref validate ./<DEST>/<name>
# README "Skills" section: gh skill install <owner>/<repo> <name>  (skill-docs)
gh skill publish                    # hygiene checks + immutable releases
gh skill publish --tag v0.1.0       # so consumers can pin @v0.1.0
```

---

## README "Skills" snippet

```markdown
## Skills (AI agent integration)

Install with the GitHub CLI (`gh` ≥ 2.90.0), targeting any agent host:

\`\`\`bash
gh skill install <owner>/<repo> <pkg>-quickstart --agent claude-code
gh skill install <owner>/<repo> <pkg>-<feature>  --agent copilot
\`\`\`

Preview first: \`gh skill preview <owner>/<repo> <pkg>-quickstart\`.
```

Pip-shipped packages also document the offline path (skills bundled in
`<pkg>/data/skills/`; link with `skill link-skills $(python -c "import <pkg>,os;
print(os.path.join(<pkg>.__path__[0],'data','skills'))")`).

---

## Rollback (pre-publish, all local)

```bash
git restore --staged . && git checkout -- .
git clean -fd skills .claude/skills   # review before running
```
