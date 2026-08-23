# Contributing to TrashTag

Thanks for your interest. TrashTag aims to stay small and honest: the smallest thing that
works, no speculative abstraction.

## Getting set up

TrashTag uses [uv](https://docs.astral.sh/uv/) for dependency management and Python 3.14.

```bash
git clone https://github.com/adarshbattu109/trashtag.git
cd trashtag
uv sync
```

Run the server:

```bash
uv run trashtag                                # defaults to 127.0.0.1:8000
```

`main(host, port, reload)` in `src/trashtag/app/__init__.py` is the entry point. It binds
loopback and reloads on edit by default; see [SECURITY.md](SECURITY.md) before binding
`0.0.0.0`. Then open <http://localhost:8000> for the ops dashboard, or
<http://localhost:8000/docs> for the API.

Configuration is via environment variables — `TRASHTAG_HOST`, `TRASHTAG_PORT`, `TRASHTAG_ENV`
(`dev` enables auto-reload).

### Real detection (optional)

By default, TrashTag uses a deterministic stub detector (hash-based, no model required). To
enable real detection with a **local vision LLM**:

1. Install and run [Ollama](https://ollama.ai):
   ```bash
   ollama serve
   ollama pull llama3.2-vision
   ```

2. Set `TRASHTAG_DETECTOR=vlm` and restart:
   ```bash
   TRASHTAG_DETECTOR=vlm uv run trashtag
   ```

The VLM detector is opt-in, free (runs locally, no API key), and works with any OpenAI-compatible
endpoint (defaults to Ollama at `localhost:11434`). Configure via `TRASHTAG_VLM_HOST`,
`TRASHTAG_VLM_PORT`, `TRASHTAG_VLM_PATH`, `TRASHTAG_VLM_MODEL`.

## Project shape

- `src/trashtag/constants/` — names, classes, statuses, paths.
- `src/trashtag/helper/` — config + the canonical mock issue data.
- `src/trashtag/app/` — the service: `__init__.py` (uvicorn runner), `serve.py` (FastAPI app +
  MCP mount), and `static/dashboard.html`.

## Running the tests

```bash
uv run pytest
```

No test touches the network — the app serves hardcoded mock data. The suite finishes in well
under a second and should stay that way.

## Before you open a PR

```bash
uv tool run ruff check .
uv tool run ruff format --check .
uv run pytest
```

CI runs exactly these three, plus `pip-audit` against the locked dependency set.

### PR titles

Titles must follow [Conventional Commits](https://www.conventionalcommits.org/) — CI rejects
anything else, and the title decides the version bump:

| Type | Bump | Example |
|------|------|---------|
| `feat` | minor | `feat: add a ward heatmap toggle to the dashboard map` |
| `fix`, `perf`, `refactor` | patch | `fix(serve): return 404 for an unknown detection id` |
| `docs`, `style`, `test`, `build`, `ci`, `chore` | none | `docs: correct the /v1/issues response shape` |

A `!` after the type (`feat!:`) means a breaking change and bumps major. The version in
`pyproject.toml` is bumped automatically on your branch — don't edit it by hand.

## What gets merged

TrashTag deliberately does little for now. A change that adds a dependency, a build step, or a
layer of indirection needs to justify its keep. Some specifics:

- **The dashboard is one self-contained HTML file** with inline CSS and vanilla JS and no build
  step. Please don't introduce a framework or a bundler for it.
- **The mock issue data has one home:** `MOCK_ISSUES` in `src/trashtag/helper/helper.py` is the
  source of truth for the API and MCP; the dashboard carries an equivalent JS array only because
  it must be a self-contained single file. Keep the two in sync until the data stops being mock,
  then delete the JS array and point the dashboard at `/v1/issues`.
- **New behaviour needs a test.** One focused test that fails if the logic breaks is enough — no
  fixtures for the sake of fixtures.
- **Filing safeguards are non-negotiable.** If you touch anything that files a complaint, the
  human-always-presses-send rule and the privacy gates in [SECURITY.md](SECURITY.md) hold.

## Reporting things

- **Bugs and features** — use the issue templates.
- **Security vulnerabilities** — don't open a public issue; see [SECURITY.md](SECURITY.md).
- Log files (`logs/trashtag.log`) contain issue addresses — check before attaching to an issue.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
