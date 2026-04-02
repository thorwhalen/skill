---
name: skill-build
description: >-
  Skill-building tooling for the skill package. Build AI agent skills for any
  Python package by analyzing its code, tests, and docs. Use this skill when
  the user wants to create skills for a package, analyze a codebase to suggest
  what skills would be useful, generate SKILL.md files from existing
  code/tests/docs, or when someone says things like "make skills for this
  package", "what skills should this project have", "create a skill from this
  module", or "generate skills". Also trigger when the user points at a package
  and asks for AI-powered interfaces to it.
---

# Skill Builder

Build AI agent skills for any Python package by analyzing its code, tests, and
documentation.

## What this skill does

You are helping someone create skills — structured instruction sets (SKILL.md
files) that teach AI agents how to use a package effectively. Think of a skill
as a cheat sheet that makes an AI *actually good* at using a tool, rather than
just guessing from docstrings.

There are two kinds of skills a package can offer:

1. **Consumer skills** — Help users *use* the package (e.g., "use this skill
   when you need to search for skills" or "use this skill when building storage
   interfaces"). These trigger automatically when a user's request matches the
   skill's domain.
2. **Producer skills** — Help developers *build on* or *contribute to* the
   package (e.g., "use this skill when adding a new backend" or "use this skill
   when writing validators").

Most packages benefit more from consumer skills. Prioritize those unless the
user specifically asks for producer/contributor skills.

## Process

### 1. Analyze the package

Read the package to understand what it does and how people use it:

- **README** — What does the package promise? What are the quick-start examples?
- **`__init__.py`** — What's the public API? What gets exported?
- **Core modules** — What are the main functions/classes? How do they compose?
- **Tests** — What usage patterns do tests demonstrate? Tests often reveal the
  *real* API surface better than docs.
- **`pyproject.toml`** — Entry points, dependencies, CLI commands?
- **Existing skills** — Check `.claude/skills/`, `{pkg}/data/skills/`, and
  `~/.claude/skills/` for skills that already exist for this package.

### 2. Suggest skills

Based on your analysis, propose a list of skills. For each, provide:

- **Name** — Follow the `{pkg}-{verb-or-domain}` convention (see naming below)
- **Kind** — Consumer or Producer
- **One-liner** — What it does
- **Trigger scenarios** — When should this skill activate?
- **Key content** — What knowledge/instructions would it contain?

Present this as a table and ask the user to confirm, modify, or prioritize.

**Naming convention:**

Use `{pkg}-{thing}` where `{pkg}` is the package name (shortened if long) and
`{thing}` is a verb or domain. This prefix builds a consistent mental model for
users: "skills from package X always start with `x-`."

- Keep the package prefix short. If the package is `my-long-package`, consider
  `mlp-` or just pick the most recognizable abbreviation.
- Use the prefix consistently across all skills for that package.
- In the description, still mention the package name explicitly so semantic
  routing doesn't depend only on the name prefix.
- For packages with many skills, the second segment becomes the verb or domain:
  `reci-ci-migration`, `reci-recipe-validate`, `reci-config-lint`.

Examples: `skill-build`, `skill-sync`, `skill-manage`, `dol-store-setup`,
`reci-ci-migration`.

**Guidelines for good skill boundaries:**

- One skill per *workflow*, not per *function*. A skill for "searching and
  installing skills" is better than separate skills for `search()` and
  `install()`.
- If two features are almost always used together, they belong in one skill.
- If a feature has complex options/patterns that would bloat another skill,
  give it its own.
- Aim for 2-5 consumer skills for a typical package. More than 7 total is
  usually a sign you're slicing too thin.

### 3. Build skills

For each approved skill, create a `SKILL.md` in `.claude/skills/{name}/`:

**Frontmatter:**
```yaml
---
name: {pkg}-{thing}
description: >-
  {Domain} tooling for the {package} package. {One-liner about what it does}.
  Use this skill when {trigger scenarios}.
  {Be slightly "pushy" — describe adjacent triggers that should also match.}
---
```

Note the description pattern: lead with `"{Domain} tooling for the {package}
package."` so the package name appears early in the description for semantic
matching.

**Body structure:**
- Lead with *what* and *why* — a 2-3 sentence summary.
- Core instructions in imperative form ("Read the config file", not "You should
  read the config file").
- Include concrete examples — real function calls with realistic arguments.
- Reference specific files/modules from the package by path.
- Include common gotchas or non-obvious behavior.
- If the skill references large reference material, put it in a `references/`
  subdirectory and point to it from the SKILL.md.

**Quality checklist:**
- [ ] Description is specific enough to trigger correctly (not just "helps with X")
- [ ] Instructions tell the agent *what to do*, not just *what exists*
- [ ] Examples use real API calls, not pseudo-code
- [ ] Gotchas and edge cases are called out
- [ ] Under 500 lines (use references/ for overflow)

### 4. Validate

After writing each skill, validate it:

```python
from skill import validate
issues = validate('.claude/skills/{name}')
```

Or via CLI:
```bash
skill validate .claude/skills/{name}
```

Fix any issues before moving on.

### 5. Verify the skills are usable

After creating skills, verify they can be discovered:

```bash
# From the project root
skill link-skills . --target ~/.claude/skills --force
skill list-skills
```

## Tips for writing effective skills

**Be concrete, not abstract.** Instead of "use the search function to find
skills", write:

```python
from skill import search
results = search('react best practices', max_results=5)
for r in results:
    print(f"{r.canonical_key}: {r.description}")
```

**Explain the why.** Don't just say "always use `scope='project'`" — say "use
`scope='project'` so the skill is available only in this project and doesn't
pollute the global namespace."

**Include the failure modes.** If `install()` raises `KeyError` when a skill
isn't in the local store, say so. The agent can then give the user a helpful
error message instead of a traceback.

**Write for the workflow, not the API.** A user doesn't think "I need to call
`search()` then `install()`". They think "I want to find a skill for React and
start using it." Write the skill around that workflow.
