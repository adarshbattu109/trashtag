# CLAUDE.md — working agreement for TrashTag

Guidance for any AI agent (and humans) working in this repo. Read
[`docs/PROJECT-STATUS.md`](docs/PROJECT-STATUS.md) first — it's the resume anchor (branch map,
what's done, what's next, locked decisions). This file is *how we work*; that file is *where we are*.

## What this is

TrashTag turns citizen photos of potholes & garbage dumps into deduplicated, AI-detected civic
complaints for Indian municipalities — **a human always presses send**. One FastAPI service:
ops dashboard + REST API + MCP server, over a pluggable detection pipeline.

## Golden rules (don't break these)

- **All SQL lives in `src/trashtag/pipeline/db.py`.** No SQL anywhere else — call a `db.*` function.
- **Detection is a `Detector` protocol.** Providers (stub / VLM) swap via env, never by editing stages.
- **Package layout is the seam:** `constants/` · `helper/` (config + mock seed data) · `app/`
  (FastAPI service + worker lifespan + MCP mount) · `pipeline/` (models · geo · store · db ·
  interfaces, then the stages: ingest · detector · vlm · process · dedup · frames · worker).
- **Coordinates are stored as-is** (no geocoding yet — ward shows `—`).
- **Dedup radius is 10 m.** Worker runs **in-process** on the app lifespan (zero-infra).
- Design principles: human presses send · never guess an authority · "probable match, verify" ·
  **privacy is a hard gate** (face/plate blur before any public surface).

## How we build (the process)

Match the ceremony to the task; never skip the gates.

1. **Brainstorm → spec.** Non-trivial/architectural work gets a design doc in `docs/` (or
   `docs/superpowers/specs/`) and human sign-off before code. Bounded changes get a short design
   in chat first. (If the `superpowers` skills are installed, use `brainstorming`.)
2. **Plan.** Turn the spec into a task-by-task implementation plan in
   `docs/superpowers/plans/YYYY-MM-DD-<feature>.md` — each task independently testable, TDD steps
   spelled out. (Skill: `writing-plans`.)
3. **Execute task-by-task, TDD.** Write the failing test → minimal code → green → commit. One
   focused task per commit. After each task: a spec-compliance + quality review. After the whole
   feature: a broad whole-branch review. (Skill: `subagent-driven-development`.) Address
   load-bearing findings; park cosmetics with a written rationale (see PROJECT-STATUS).
4. **Verify what you claim.** For UI/endpoint changes, actually run it (`uv run trashtag`) and
   check the behavior — a passing string/HTML test is not proof the page renders. Report failures
   honestly with output.

## Quality gates (must be green before commit / PR)

```bash
uv run pytest -q                    # offline; no test hits the network
uv run ruff check .                 # lint (whole tree)
uv run ruff format --check .        # format (whole tree; docs/ is excluded — see pyproject)
```
CI (`.github/workflows/ci.yml`) runs the same via `uv tool run ruff` + `uv run pytest`, plus a
`pip-audit`. Keep local and CI green together.

## Commits, branches, PRs

- **Branches:** `main` is released; do feature work on a branch; PR into `main`. Don't commit or
  push unless asked; never force-push a shared branch.
- **Commit messages & PR titles are Conventional Commits** — CI (`pr-title.yml`) *rejects* a PR
  whose title doesn't match `type(scope): description` (`feat` → minor bump, `fix|perf|refactor`
  → patch, others → no bump). Example: `feat: add a ward heatmap toggle`.
- **Author:** Adarsh Battu <adarsh.battu109@gmail.com>. End AI-assisted commits with a
  `Co-Authored-By:` trailer for the model used.
- Never commit secrets or log files. `.env.local` (holds `GEMINI_API_KEY` etc.) is git-ignored.

## Running & detection

```bash
uv sync && uv run trashtag          # http://127.0.0.1:8000  (dashboard, /docs, /mcp)
```
Detector is `stub` by default (deterministic, offline). Opt into a VLM with `TRASHTAG_DETECTOR=vlm`
+ `TRASHTAG_VLM_*`. Local: Ollama `qwen3-vl:2b`. Cloud (free tier): Google AI Studio —
host `generativelanguage.googleapis.com`, path `/v1beta/openai`, model **`gemini-3.6-flash`**
(NOT `gemini-2.5-flash`, which is retired). Worker: `TRASHTAG_WORKER`, `TRASHTAG_WORKER_POLL_SECONDS`.

## Known constraints / gotchas

- **`mcp<2` is pinned on purpose** — `fastapi-mcp` 0.4.0 crashes on import against mcp 2.x. The
  fix-forward (migrate to `fastmcp`) is in [`docs/research/mcp-2x-upgrade-path.md`](docs/research/mcp-2x-upgrade-path.md).
  Let Dependabot ignore the mcp major bump until then.
- `except A, B, C:` without parentheses is valid Python 3.14 (PEP 758) — don't "fix" it.
- Read/grep can mis-render parens-less `except` tuples; trust `uv run` (py_compile/tests) over the display.
