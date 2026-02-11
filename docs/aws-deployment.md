# AWS 배포 가이드 — Job 관리 & 외부 크롤 요청

현재 프로젝트 구조(`executor: "local" | "remote_proxy"`)에 맞춘 AWS 서비스 추천 및 구현 가이드.

---

## 🎯 요구사항

- ✅ **Job 관리**: 큐잉, 스케일링, 재시도, 모니터링
- ✅ **외부 디바이스에서 크롤 요청**: API Gateway / ALB로 접근
- ✅ **Playwright 실행**: 브라우저 필요 (Lambda 제외)
- ✅ **비용 효율**: 사용한 만큼만 과금

---

## 🚀 추천 아키텍처 (3가지 옵션)

### Option 1: **빠른 시작** — App Runner + SQS + ECS Fargate

**적합한 경우:**
- 빠르게 프로토타입
- 트래픽 예측 불가
- 최소 인프라 관리

**구조:**
```
외부 요청 → API Gateway → App Runner (FastAPI) → SQS Queue
                                              ↓
                                    ECS Fargate (Worker)
                                    (Playwright 크롤러)
```

**장점:**
- App Runner: 코드 푸시만으로 배포 (Dockerfile 자동 빌드)
- SQS: 내장 재시도, DLQ, 메시지 순서 보장
- Fargate: 서버리스 컨테이너 (EC2 관리 불필요)

**비용 (월 예상):**
- App Runner: $0.007/vCPU-hour + $0.0008/GB-hour (약 $20-50)
- SQS: 첫 1M 요청 무료, 이후 $0.40/1M
- Fargate: $0.04/vCPU-hour + $0.004/GB-hour (작업 시간만 과금)

**구현 난이도:** ⭐⭐ (중)

---

### Option 2: **프로덕션 권장** — ALB + ECS (API + Worker) + RDS + EventBridge

**적합한 경우:**
- 안정적인 프로덕션 환경
- 높은 가용성 필요
- 스케줄링 (cron) 필요

**구조:**
```
외부 요청 → ALB → ECS Service (API) → RDS (PostgreSQL)
                              ↓
                    SQS Queue → ECS Task (Worker)
                              ↓
                    S3 (결과 저장)

EventBridge (Cron) → Lambda → API (Job 생성)
```

**장점:**
- ALB: SSL 종료, 헬스체크, 다중 AZ
- ECS: 오토스케일링, 롤링 업데이트
- RDS: SQLite → PostgreSQL 마이그레이션 쉬움
- EventBridge: 스케줄링 내장

**비용 (월 예상):**
- ALB: $0.0225/hour (약 $16)
- ECS: EC2/Fargate 비용 (약 $50-200)
- RDS: db.t3.micro (약 $15)
- SQS: $0.40/1M 요청

**구현 난이도:** ⭐⭐⭐ (중상)

---

### Option 3: **최대 확장성** — AWS Batch + Step Functions

**적합한 경우:**
- 대량 작업 처리
- 작업 우선순위/큐 관리
- Spot 인스턴스로 비용 절감

**구조:**
```
외부 요청 → API Gateway → Lambda → Batch Job Queue
                                    ↓
                            EC2 Spot Instances
                            (Playwright 크롤러)
                                    ↓
                            S3 (결과) + CloudWatch Logs
```

**장점:**
- Batch: 작업 큐, 우선순위, Spot 인스턴스 자동 관리
- Step Functions: 복잡한 워크플로우 오케스트레이션
- Spot: 최대 90% 비용 절감

**비용 (월 예상):**
- Batch: Spot 인스턴스 비용만 (약 $10-50)
- Step Functions: $0.025/1K 상태 전환
- Lambda: $0.20/1M 요청

**구현 난이도:** ⭐⭐⭐⭐ (상)

---

## 📋 Option 1 구현 가이드 (빠른 시작)

### 1. Dockerfile 준비

```dockerfile
# Dockerfile.api (FastAPI)
FROM python:3.10-slim

WORKDIR /app

# Playwright 의존성
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[admin]"

# 앱 코드
COPY src/ ./src/
COPY admin-ui/dist ./admin-ui/dist

EXPOSE 8000

CMD ["uvicorn", "wine_crawler.admin.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
```

```dockerfile
# Dockerfile.worker (크롤러 Worker)
FROM python:3.10-slim

WORKDIR /app

# Playwright 브라우저 설치
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir playwright && \
    playwright install chromium && \
    playwright install-deps chromium

# Python 의존성
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[admin]" boto3

# Worker 스크립트
COPY src/ ./src/
COPY scripts/worker.py ./scripts/

CMD ["python", "scripts/worker.py"]
```

### 2. SQS Worker 스크립트

```python
# scripts/worker.py
import asyncio
import json
import os
from wine_crawler.admin.db.connection import Database
from wine_crawler.admin.db.models import Job
from wine_crawler.admin.db.repositories.jobs import JobsRepository
import boto3

sqs = boto3.client("sqs")
queue_url = os.environ["SQS_QUEUE_URL"]
db_path = os.environ.get("DB_PATH", "/tmp/admin.db")

async def process_job(job: Job):
    """Job 실행 로직 (기존 크롤러 코드 재사용)"""
    # TODO: 실제 크롤러 실행
    pass

async def worker_loop():
    db = Database(db_path)
    await db.connect()

    while True:
        # SQS에서 메시지 수신
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
        )

        if "Messages" not in response:
            continue

        for msg in response["Messages"]:
            job_id = json.loads(msg["Body"])["job_id"]

            # DB에서 Job 로드
            job = await db.repos.jobs.get(job_id)
            if not job:
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])
                continue

            # 실행
            await process_job(job)

            # 메시지 삭제
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])

if __name__ == "__main__":
    asyncio.run(worker_loop())
```

### 3. FastAPI → SQS 연동

```python
# src/wine_crawler/admin/services/execution/aws_sqs.py
import json
import boto3
from wine_crawler.admin.db.models import Job

class AWSSQSExecutor:
    def __init__(self, queue_url: str):
        self.sqs = boto3.client("sqs")
        self.queue_url = queue_url

    async def submit(self, job: Job) -> str:
        """Job을 SQS에 제출"""
        self.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps({"job_id": job.id}),
        )
        return job.id
```

### 4. App Runner 설정

```yaml
# apprunner.yaml
version: 1.0
runtime: python3
build:
  commands:
    build:
      - pip install -r requirements.txt
run:
  runtime-version: 3.10
  command: uvicorn wine_crawler.admin.app:create_app --host 0.0.0.0 --port 8000 --factory
  network:
    port: 8000
  env:
    - name: ADMIN_DB_PATH
      value: /tmp/admin.db
    - name: SQS_QUEUE_URL
      value: https://sqs.us-east-1.amazonaws.com/.../crawler-jobs
```

### 5. ECS Fargate Task 정의

```json
{
  "family": "crawler-worker",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [{
    "name": "worker",
    "image": "your-ecr-repo/crawler-worker:latest",
    "environment": [
      {"name": "SQS_QUEUE_URL", "value": "..."},
      {"name": "DB_PATH", "value": "/tmp/admin.db"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/crawler-worker",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    }
  }]
}
```

---

## 🔧 Option 2 구현 가이드 (프로덕션)

### SQLite → RDS PostgreSQL 마이그레이션

```python
# src/wine_crawler/admin/db/connection.py 수정
import asyncpg  # PostgreSQL용

class Database:
    def __init__(self, connection_string: str):
        self._conn_string = connection_string
        # ... asyncpg 사용
```

### ECS Service 오토스케일링

```json
{
  "serviceName": "crawler-api",
  "desiredCount": 2,
  "autoScaling": {
    "minCapacity": 2,
    "maxCapacity": 10,
    "targetTrackingScalingPolicies": [{
      "targetValue": 70.0,
      "predefinedMetricSpecification": {
        "predefinedMetricType": "ECSServiceAverageCPUUtilization"
      }
    }]
  }
}
```

---

## 💡 즉시 사용 가능한 AWS 서비스 비교

| 서비스 | Job 관리 | 외부 요청 | Playwright | 비용 | 난이도 |
|--------|---------|----------|------------|------|--------|
| **App Runner** | ❌ (별도 필요) | ✅ | ✅ | 중 | ⭐⭐ |
| **ECS Fargate** | ✅ (SQS 연동) | ✅ (ALB) | ✅ | 중 | ⭐⭐⭐ |
| **AWS Batch** | ✅✅ | ❌ (별도 필요) | ✅ | 저 | ⭐⭐⭐⭐ |
| **Lambda** | ❌ | ✅ | ❌ (15분 제한) | 저 | ⭐ |
| **Step Functions** | ✅✅ | ✅ (API Gateway) | ❌ (별도 필요) | 저 | ⭐⭐⭐ |

---

## 🎯 최종 추천

### 지금 바로 시작: **Option 1 (App Runner + SQS + ECS Fargate)**

**이유:**
1. ✅ **빠른 배포**: App Runner가 Dockerfile만으로 자동 배포
2. ✅ **비용 효율**: 작업 실행 시간만 과금 (Fargate)
3. ✅ **확장성**: SQS 큐로 자동 스케일링
4. ✅ **현재 코드 재사용**: `executor_meta`에 SQS URL만 추가하면 됨

**구현 순서:**
1. Dockerfile 작성 (위 참고)
2. ECR에 이미지 푸시
3. App Runner 서비스 생성 (API)
4. SQS 큐 생성
5. ECS Fargate Task 정의 (Worker)
6. FastAPI에 `executor="aws_sqs"` 추가

**예상 시간:** 2-3시간

---

## 📚 참고 자료

- [App Runner 문서](https://docs.aws.amazon.com/apprunner/)
- [ECS Fargate 가이드](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [SQS Python SDK](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html)
- [Playwright Docker 이미지](https://hub.docker.com/r/mcr.microsoft.com/playwright)

---

## 🚦 다음 단계

1. **Option 1 구현 코드 작성** (Dockerfile, Worker 스크립트, SQS Executor)
2. **Terraform/CDK 인프라 코드** (IaC로 자동 배포)
3. **모니터링 설정** (CloudWatch, 알람)

원하시면 Option 1 구현 코드부터 작성해드릴게요! 🚀
