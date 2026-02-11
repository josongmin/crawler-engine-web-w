# Agent Guide (wine-crawler)

This repo contains a Python crawler (`src/wine_crawler`) and a Vite/React admin UI (`admin-ui`).

## Quick commands

- Backend install: `just backend-install` (or `just install` for all)
- Frontend install: `just admin-install`
- Run backend (FastAPI): `just backend-dev` (or `winecrawl admin`)
- Run frontend: `just admin-dev`
- Run all checks: `just check`
- Format all: `just format`

## Architecture rules (Python)

The Python package is layered and enforced by `import-linter` (see `pyproject.toml`):

- `wine_crawler.config` / `wine_crawler.logging`: foundation modules, **must not** import from higher layers.
- `wine_crawler.core`: primitives (browser/session/retry), **must not** import `sites`/`admin`/`cli`.
- `wine_crawler.sites`: per-site implementations, **must not** import `admin`/`cli`.
- `wine_crawler.admin`: admin DB + API (may integrate other layers as needed), **must not** import `cli`.

If you need cross-layer communication, prefer:
- moving shared types/utilities into `core` (if truly generic), or
- injecting dependencies (functions/classes) instead of importing upward.

## Frontend conventions (admin-ui)

- `src/shared/**`: reusable API wrappers, UI primitives, hooks, types.
- `src/pages/**`: route-level screens.
- `src/widgets/**`: layout and page composition.

Formatting is via Prettier; linting is via ESLint (type-aware).

## Adding a new site crawler

- Add `src/wine_crawler/sites/<site>/crawler.py`
- Register it in `src/wine_crawler/sites/registry.py`
- Run: `winecrawl sites list` and `winecrawl run <site>`

