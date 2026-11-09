# Wine Crawler Workspace

An extensible Playwright collection workspace with site-specific crawlers, shared browser/session/retry infrastructure, a FastAPI administration API, and a React administration UI.

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
