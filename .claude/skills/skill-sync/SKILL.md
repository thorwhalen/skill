---
name: skill-sync
description: >-
  Skill maintenance tooling for the skill package. Keep AI agent skills in sync
  with their source package code. Use this skill when a package's code, API, or
  behavior has changed and its skills may be outdated, when the user says
  "update the skills", "skills are stale", "sync skills with code", "refresh
  skills", or when you notice that skill instructions reference
  functions/classes/patterns that no longer exist in the codebase. Also use
  after major refactors, API changes, or version bumps.
---

# Skill Sync

Detect and fix drift between a package's code and the skills that describe it.

## Why this matters

Skills are documentation for AI agents. Like any documentation, they rot when
the code they describe changes. A stale skill is worse than no skill — it
confidently tells the agent to do things that no longer work.

## When to sync

- After significant code changes (new features, renamed functions, changed
  signatures, removed modules)
- Before a release (skills should match the version being shipped)
- When a user reports that a skill's instructions don't match reality
- Periodically as maintenance (e.g., monthly, or when touching the package)

## Process

### 1. Inventory current skills

Find all skills associated with this package:

```bash
# Check project-local skills
ls -la .claude/skills/

# Check if the package ships skills in data/
ls -la {pkg_name}/data/skills/ 2>/dev/null

# Check for symlinks from the global store
skill list-skills
```

### 2. Diff skills against code

For each skill, read its SKILL.md and check every claim against the current
codebase:

**API references:**
- Do the functions/classes mentioned still exist? (grep for them)
- Have their signatures changed? (read the source)
- Have default values or behaviors changed?
- Are there new parameters the skill should mention?

**Code examples:**
- Do the code examples still run correctly?
- Do imports still resolve?
- Are there deprecated patterns the skill still recommends?

**File paths:**
- Do referenced file paths still exist?
- Have modules been moved or renamed?

**Behavioral claims:**
- Does the skill describe behavior that has changed?
- Are there new edge cases or gotchas?

### 3. Categorize findings

Group issues by severity:

- **Breaking** — Skill references something that no longer exists or has changed
  in a way that would cause errors (wrong function name, removed parameter,
  changed return type). Fix these immediately.
- **Stale** — Skill is technically correct but incomplete (new features not
  mentioned, new options not documented). Update when convenient.
- **Cosmetic** — Minor wording issues, formatting. Low priority.

### 4. Apply updates

Edit each skill's SKILL.md to fix the issues found. When updating:

- Keep the existing structure and style — don't rewrite the whole skill.
- Update specific claims, examples, and references.
- Add notes about new features or changed behavior.
- Remove references to things that no longer exist.
- Update the description in frontmatter if the skill's scope has changed.

After editing, validate:
```bash
skill validate .claude/skills/{name}
```

### 5. Report

Summarize what changed:

```
## Skill Sync Report

### my-skill
- FIXED: `search()` now takes `backends` parameter (was `sources`)
- ADDED: New `link_skills()` function documentation  
- REMOVED: Reference to deprecated `AGENT_TARGETS` dict (now a Registry)

### other-skill  
- No changes needed ✓
```

## Automation tip

For packages with CI, consider adding a step that checks skill freshness:

```python
from skill import validate
import subprocess

# Validate all skills
for skill_dir in Path('.claude/skills').iterdir():
    if skill_dir.is_dir():
        issues = validate(str(skill_dir))
        if issues:
            print(f"⚠ {skill_dir.name}: {issues}")
```

This won't catch semantic drift (the skill says "returns a list" but now it
returns a generator), but it catches structural issues like missing fields.
