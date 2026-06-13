# Deep Research Prompt: Does the `skill` Package Fill a Gap?

This is the **strategic / existential** prompt — questions about
positioning, audience, gaps, and whether the `skill` package should
exist at all in its current form. Run this **before** the
implementation/tactics prompt in
`skill_implementation_research_prompt.md`. If the answer to this one
is "no, the gap has closed," the implementation questions are moot.

Run as a deep-research task; expect 2,500–6,000 words with concrete
citations.

---

## Background (paste this into the deep-research tool)

I'm the maintainer of a Python package called `skill`
(github.com/thorwhalen/skill, PyPI: `pip install skill`). It does AI
agent skill management — search, install, validate, link skills across
multiple AI coding agents (Claude Code, Cursor, Copilot, Windsurf,
etc.), with a multi-backend search facade (GitHub, Smithery, Composio,
awesome-list, SkillsDirectory).

The package was conceived in early 2025, when the agent skills
ecosystem was nascent and tools were fragmented. Since then:

- Anthropic published the Agent Skills specification at agentskills.io
  (December 2025).
- Vercel's `npx skills add` (~7.5K stars) became the de facto
  installer (~late 2025).
- GitHub launched `gh skill install` in `gh` v2.90.0 on **2026-04-16**,
  with provenance tracking, version pinning (`--pin`), update
  detection (`gh skill update`), and immutable releases via
  `gh skill publish`.
- Claude Code's `/plugin install` and marketplace ecosystem has
  matured: `claude-plugins-official` is default-installed, and
  third-party catalogs (e.g., `claude-plugins-plus-skills` with 423
  plugins / 2,849 skills) are active.
- Multiple competing tools (rule-porter, cursor-doctor, PRPM,
  promptfoo, Smithery.ai, Composio) each cover slices of the
  lifecycle.

Existing internal research (in `misc/docs/` of the repo) includes:

- `The AI agent skills ecosystem - a complete landscape survey.md`
  (pre-`gh skill`)
- `Cross-agent skill format compatibility and translation.md`
- `Remote skill backends for building a Python skill package.md`
- `Skill - Storage Architecture & Installation Patterns.md`
- `Skill - AI API Facade & Configuration Management.md`

The 2025 landscape survey concluded that the gap was the
**programmatic Python layer** — Pydantic-modeled skill objects,
deterministic version resolution, lock files, private-registry
protocols, evaluation hooks. With `gh skill` and the Claude
marketplace having shipped since, this thesis needs re-evaluation.

I'm at a fork: keep building `skill` as conceived, pivot to a narrower
gap-filling role, or sunset it and contribute to the existing tools.
This research should produce evidence to choose.

---

## Research questions

### Q1 — What's the actual state of the "feature gap" landscape today?

The 2025 landscape survey identified five gaps:

1. Versioning / pinning
2. Security / supply-chain trust
3. Dependency management between skills
4. Testing / evaluation framework
5. Private registries

For each, report the state as of April 2026:

- Is the gap fully closed, partially closed, or still open?
- Which tools have addressed it (if any), and how completely?
- For partial closures: what's left? (E.g., `gh skill install --pin`
  exists but lock files don't.)
- For still-open gaps: is anyone working on them publicly?

Be specific. Cite actual GitHub issues, blog posts, release notes,
spec changes. Don't generalize from the survey — verify.

### Q2 — Who is the audience for a "Python multi-agent skill manager"?

The implicit user persona for `skill` has been "a Python developer
managing skills across Claude Code, Cursor, and Copilot in their
project." Validate or invalidate this:

- Search Reddit, Hacker News, Twitter/X, Discord (Anthropic dev
  community, Vercel community), and GitHub issues for evidence of
  developers who:
  - Use multiple AI agents in the same project (the whole premise).
  - Have asked for cross-agent skill management.
  - Have specifically asked for a Python tool to do this.
- How big is this audience? (Ballpark: dozens? hundreds? tens of
  thousands?)
- Is the audience growing or shrinking? (Are devs converging on one
  agent or staying multi?)
- What's the median Python sophistication of this audience? (Are they
  Python developers using AI agents, or ML engineers with Python
  in their toolkit, or general developers who happen to have
  Python installed?)

If the audience is "Python developers who use Claude Code only,"
the multi-agent story is mostly aspirational, and `skill` might be
better repositioned around shipping skills *with* Python packages.

### Q3 — Does `skill` overlap with `gh skill` enough that one will dominate?

Compare feature-by-feature:

| Capability | `gh skill` | `skill` (current) | `skill` (planned) |
|------------|-----------|-------------------|-------------------|
| Install from GitHub | ✓ | ✓ | ✓ |
| Multi-backend search | ✗ | ✓ | ✓ |
| Pin to tag/SHA | ✓ | ✗ | (planned) |
| Provenance metadata | ✓ | sidecar JSON | (align) |
| Multi-agent translate (mdc, copilot) | ✗ | ✓ | ✓ |
| Lock files | ✗ | ✗ | (planned) |
| Private registry server | ✗ | ✗ | (planned) |
| Programmatic API | ✗ | ✓ | ✓ |
| Testing/eval hooks | ✗ | ✗ | (planned) |

Questions:

- Is GitHub likely to add the missing capabilities (multi-agent
  translation, multi-backend search) to `gh skill` in the next 6-12
  months? Look for roadmap signals, GitHub issues, RFCs.
- Is the differentiation surface (multi-agent translate, private
  registry, lock files, testing) durable, or will `gh skill` extend
  into it within a year?
- For each "differentiator" `skill` has, is it actually *valuable to
  users* or just *technically distinct*?

### Q4 — What does success look like for `skill`, and what does failure look like?

Sketch concrete success and failure scenarios:

- **Success scenarios** (what would have to be true for `skill` to be
  considered "won"?). E.g., "X downloads/month on PyPI, Y stars,
  adopted by Z named projects, used as the publisher for ≥N skill
  packages, mentioned in agentskills.io docs."
- **Failure scenarios**. E.g., "PyPI installs flat, project repos
  abandoned, `gh skill` covers all use cases, contributors leave."
- **Median scenarios**. The realistic middle: niche tool used by a
  hundred Python devs, not zero, not thousands.

For each, what are the leading indicators (visible 6 months ahead)?

### Q5 — What's the right scope, given the 2026-04 ecosystem state?

Given the answers to Q1–Q4, propose 3 alternative scopings for a
re-imagined `skill`, ranked by ROI:

1. **Maximalist** — keep current scope, extend across all five gap
   areas. Maximum opportunity, maximum risk of overreach.
2. **Programmatic-only** — drop the CLI installer (defer to
   `gh skill` / `npx skills`), keep only the Python API for
   programmatic skill manipulation, validation, translation, and
   testing. Sharper positioning, smaller surface.
3. **Specialist** — pick exactly one of the open gaps (lock files /
   private registry / testing harness / multi-agent translation) and
   own it completely. Becomes "the X for skills" instead of "another
   skill manager."
4. **Sunset** — deprecate `skill`, contribute the multi-agent
   translation logic upstream to `gh skill` or `npx skills` as a
   plugin, redirect users.

For each, give a realistic best-case adoption ceiling and the cost
to get there.

### Q6 — Is there demand for skill management *from Python build/CI workflows*?

This is the angle the existing landscape survey emphasized: that the
ecosystem's tools are CLI-first / Node-first, and a Python library
that integrates with build scripts and CI is missing.

- Find real CI workflows (GitHub Actions, GitLab CI) that run
  `npx skills add` or `gh skill install`. How clunky is this in a
  Python-flavored CI?
- Is there a use case for "validate all skills in this repo on every
  PR" that doesn't have a clean Python tool?
- Are there packages whose CI publishes / validates skills as part of
  the release pipeline? What do they use?
- Could `skill` become "the skills equivalent of `pre-commit`"?

This Q is specifically about whether *Python build/CI users* exist as
a real audience, distinct from end-users running ad-hoc CLI commands.

### Q7 — Is there demand for *self-hosted* / *private* skill registries?

The landscape survey flagged this as a clear gap. Re-validate:

- Are enterprise teams actually asking for private skill registries,
  or is this a theoretical need?
- localskills.sh exists (SaaS); is it gaining traction?
- Are there GitHub issues on `gh skill` or `npx skills` requesting
  private/internal mode?
- What does "private registry" minimally look like: a directory + a
  HTTP shim that pretends to be skills.sh? Something more?

If demand exists, this is one of the cleanest gaps for `skill` to
own — and one that `gh skill` is structurally unlikely to fill
(GitHub-native means GitHub-hosted).

### Q8 — What does the path-of-least-regret look like?

Synthesizing everything: if I had to pick one direction with the
following constraints, what would you recommend?

- Minimum 6 months of visible pulse before adoption is judged.
- Solo maintainer (me), with limited time.
- Strong preference for *integrating* with `gh skill` and `npx skills`
  rather than competing with them.
- Strong preference for Python-native interfaces (programmatic API,
  CI integration, build hooks).
- Open to reframing the package's identity completely.

Don't hedge. Recommend a single direction (one of Q5's options, or a
combination, or something else entirely), and explain why it's the
least-regret bet for the next 6 months.

---

## Output format

A single markdown document with:

- One section per question, leading with a 1–2 sentence answer
  followed by evidence and citations.
- A final "Synthesis & Recommendation" section that maps to a
  concrete next-step decision: keep, pivot, or sunset.
- Vancouver-style references (`[1]`, `[2]`, ...) with a REFERENCES
  section. Hyperlink with `[name](url)` where possible.

If a question can't be answered conclusively from public sources,
report what *is* knowable and explicitly flag the gap rather than
speculating.

---

## Why this matters

The previous landscape survey concluded "the gap is wide open" — but
it was written before `gh skill` and the Claude marketplace ecosystem
shipped. Six months in software ecosystem time is a long time. The
honest answer to "should `skill` continue to exist" might be yes, no,
or "yes but as something different." A decision made now without
re-checking is a decision made in 2025 conditions, not 2026.

The output of this research feeds directly into a redesign plan for
the package. If the answer is "yes, here's the durable gap" — the
redesign focuses there. If the answer is "no, hand off and sunset" —
that's also valuable to know now rather than after another year of
maintenance.
