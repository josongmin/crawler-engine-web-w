## wine-crawler workspace

Playwright + Python 기반으로, **사이트별 크롤러는 분리**하고 **공통 코어는 공유**하도록 만든 확장 가능한 워크스페이스입니다.

### Requirements

- Python 3.10+

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
python -m playwright install
pre-commit install
```

또는:

```bash
make venv
source .venv/bin/activate
make install
make playwright
make precommit
```

### Run (example)

```bash
winecrawl sites list
winecrawl run example --limit 5
```

기본 결과는 `data/<site>/<timestamp>.json`에 저장되고, 세션은 `storage_state/<site>.json`에 저장됩니다.

### Lint / typecheck / test

```bash
ruff format .
ruff check .
mypy .
pytest
```

또는:

```bash
make fmt
make check
```

### Add a new site crawler

- `src/wine_crawler/sites/<site_name>/crawler.py` 추가
- `src/wine_crawler/sites/registry.py`에 등록
- `winecrawl run <site_name>`로 실행
