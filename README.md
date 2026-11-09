<p align="center"><img src="readme-banner.svg" alt="Wine Crawler Workspace — Site-specific browser adapters with a shared core and admin surface." width="100%"></p>

# Wine Crawler Workspace

An extensible Playwright collection workspace with site-specific crawlers, shared browser/session/retry infrastructure, a FastAPI administration API, and a React administration UI.


## Engineering highlights

| Mechanism | Engineering purpose |
| :--- | :--- |
| **Explicit site registry** | Crawler factories are registered centrally. The current registry includes `example` and `burghound`; unknown names reject. |
| **Layered Python package** | Configuration/logging, core primitives, sites, and admin layers have import-linter boundaries. |
| **Shared browser/session handling** | The core owns reusable browser and session behavior rather than duplicating it in each site adapter. |
| **Separate administration surface** | The admin API and React UI have their own dependency and execution requirements. |
| **Typed frontend data flow** | The admin interface uses React Query, route-level pages, shared API wrappers, and widget composition. |


## Architecture at a glance

```mermaid
flowchart LR
    C["winecrawl CLI"] --> R["Site registry"]
    R --> S["Site crawler adapter"]
    S --> B["Browser, session, retry core"]
    B --> O["Data output and session state"]
    U["React admin UI"] --> A["FastAPI admin services"]
    A --> R
```

## Architecture

| Path | Responsibility |
| --- | --- |
| [src/wine_crawler/core](src/wine_crawler/core) | Browser, session, and retry primitives |
| [src/wine_crawler/sites](src/wine_crawler/sites) | Site implementations and registration |
| [src/wine_crawler/admin](src/wine_crawler/admin) | Job management, database, and API |
| [admin-ui](admin-ui) | Vite/React administration interface |
| [scripts](scripts) | Worker and operational helpers |
| [tests](tests) | Collection and administration tests |

The core must not import site, administration, or CLI layers. Python dependency boundaries are enforced through the import-linter contract in `pyproject.toml`.

## Install and run

Use Python 3.10+ and Node.js.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[admin,dev]"
python -m playwright install

winecrawl sites list
winecrawl run example --limit 5
```

Run the administration backend and UI in separate terminals:

```sh
just admin-install
just backend-dev
just admin-dev
```

Default collection output is written to `data/<site>/<timestamp>.json`; browser sessions use `storage_state/<site>.json`. Keep sessions, cookies, and login material outside version control.

## Add a site and verify

1. Implement `src/wine_crawler/sites/<site>/crawler.py`.
2. Register it in `src/wine_crawler/sites/registry.py`.
3. Verify site-specific inputs, output, and failure behavior.

```sh
just check
just format
```

AWS execution uses the API/SQS/ECS-worker path and requires an actual account, queue, and permissions.

## Documentation

- [AWS deployment](docs/aws-deployment.md)
- [Contributor guide](AGENTS.md)
- [Command recipes](justfile)
- [Package and layer configuration](pyproject.toml)
