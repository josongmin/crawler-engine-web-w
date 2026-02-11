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
just venv
source .venv/bin/activate
just install
just playwright
just precommit
```

### Run (example)

```bash
winecrawl sites list
winecrawl run example --limit 5
```

기본 결과는 `data/<site>/<timestamp>.json`에 저장되고, 세션은 `storage_state/<site>.json`에 저장됩니다.

### Admin Web Tool (backend)

Admin API 서버를 로컬에서 띄우려면:

```bash
pip install -e ".[admin,dev]"
winecrawl admin
```

또는:

```bash
just backend-dev
```

### Lint / typecheck / test

```bash
ruff format .
ruff check .
mypy .
pytest
```

또는:

```bash
just format
just check
```

### Add a new site crawler

- `src/wine_crawler/sites/<site_name>/crawler.py` 추가
- `src/wine_crawler/sites/registry.py`에 등록
- `winecrawl run <site_name>`로 실행

### AWS 배포 (Job 관리 & 외부 크롤 요청)

AWS에서 Job 관리와 외부 디바이스에서 크롤 요청을 받으려면:

**빠른 시작 (권장):**
- **App Runner** (FastAPI) + **SQS** (Job 큐) + **ECS Fargate** (Worker)
- 상세 가이드: [`docs/aws-deployment.md`](docs/aws-deployment.md)

**구현된 기능:**
- `executor="aws_sqs"` 지원 (Job을 SQS에 제출)
- Worker 스크립트 (`scripts/worker.py`) - SQS 폴링 및 실행
- Dockerfile 준비됨 (`Dockerfile.api`, `Dockerfile.worker`)

**사용 예:**
```bash
# Job 생성 시 AWS SQS executor 사용
POST /api/jobs
{
  "site": "burghound",
  "executor": "aws_sqs",
  "executor_meta": "https://sqs.us-east-1.amazonaws.com/.../crawler-jobs"
}
```
