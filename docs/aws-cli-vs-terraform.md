# AWS CLI vs Terraform — 차이점과 선택 가이드

현재 프로젝트(wine-crawler) 배포 관점에서 두 방식의 차이를 설명합니다.

---

## 🎯 핵심 차이

| 항목 | AWS CLI | Terraform |
|------|---------|-----------|
| **방식** | 명령어 하나씩 실행 | 코드로 인프라 정의 |
| **상태 관리** | ❌ 없음 (수동 추적) | ✅ `.tfstate` 파일로 추적 |
| **재현성** | ❌ 매번 수동 실행 | ✅ `terraform apply` 한 번 |
| **버전 관리** | ❌ 히스토리 없음 | ✅ Git으로 관리 |
| **롤백** | ❌ 수동 삭제 | ✅ `terraform destroy` |
| **팀 협업** | ❌ 누가 뭘 만들었는지 모름 | ✅ 코드 리뷰 가능 |
| **학습 곡선** | ⭐ (쉬움) | ⭐⭐⭐ (보통) |

---

## 📝 실제 예시: SQS 큐 + ECS Task 생성

### AWS CLI 방식

```bash
# 1. SQS 큐 생성
aws sqs create-queue \
  --queue-name crawler-jobs \
  --attributes VisibilityTimeout=300,MessageRetentionPeriod=345600

# 큐 URL 저장 (수동으로 복사)
QUEUE_URL=$(aws sqs get-queue-url --queue-name crawler-jobs --query 'QueueUrl' --output text)
echo $QUEUE_URL  # 나중에 쓸 수 있게 저장해야 함

# 2. ECR 리포지토리 생성
aws ecr create-repository --repository-name wine-crawler-api
aws ecr create-repository --repository-name wine-crawler-worker

# 3. ECS 클러스터 생성
aws ecs create-cluster --cluster-name crawler-cluster

# 4. Task Definition 생성 (JSON 파일 필요)
aws ecs register-task-definition --cli-input-json file://task-definition.json

# 5. ECS Service 생성
aws ecs create-service \
  --cluster crawler-cluster \
  --service-name crawler-worker \
  --task-definition crawler-worker:1 \
  --desired-count 2

# 문제: 나중에 수정하려면?
# → 또 명령어 실행해야 함
# → 뭘 만들었는지 기억해야 함
# → 삭제할 때도 하나씩 찾아서 삭제
```

**문제점:**
- ❌ 큐 URL, 리소스 ID를 수동으로 저장해야 함
- ❌ 환경별(dev/staging/prod) 설정이 달라지면 명령어도 달라짐
- ❌ 삭제할 때도 하나씩 찾아서 삭제해야 함
- ❌ 팀원이 똑같은 환경 만들려면 명령어 목록 공유 필요

---

### Terraform 방식

```hcl
# infrastructure/main.tf
variable "environment" {
  default = "dev"
}

resource "aws_sqs_queue" "crawler_jobs" {
  name = "crawler-jobs-${var.environment}"
  
  visibility_timeout_seconds = 300
  message_retention_seconds  = 345600
  
  tags = {
    Environment = var.environment
    Project     = "wine-crawler"
  }
}

resource "aws_ecr_repository" "api" {
  name = "wine-crawler-api"
}

resource "aws_ecr_repository" "worker" {
  name = "wine-crawler-worker"
}

resource "aws_ecs_cluster" "main" {
  name = "crawler-cluster-${var.environment}"
}

resource "aws_ecs_task_definition" "worker" {
  family = "crawler-worker"
  
  container_definitions = jsonencode([{
    name  = "worker"
    image = "${aws_ecr_repository.worker.repository_url}:latest"
    environment = [
      { name = "SQS_QUEUE_URL", value = aws_sqs_queue.crawler_jobs.url }
    ]
  }])
  
  cpu    = "1024"
  memory = "2048"
  requires_compatibilities = ["FARGATE"]
  network_mode            = "awsvpc"
}

resource "aws_ecs_service" "worker" {
  name            = "crawler-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = 2
  launch_type     = "FARGATE"
}

# 출력값 (다른 모듈에서 참조 가능)
output "sqs_queue_url" {
  value = aws_sqs_queue.crawler_jobs.url
}
```

**사용:**
```bash
# 초기화
terraform init

# 계획 확인 (실제로 뭘 만들지 미리보기)
terraform plan

# 적용 (한 번에 모든 리소스 생성)
terraform apply

# 삭제 (한 번에 모든 리소스 삭제)
terraform destroy

# 환경별 배포
terraform apply -var="environment=prod"
```

**장점:**
- ✅ 상태 파일(`.tfstate`)에 모든 리소스 ID 저장
- ✅ 코드로 버전 관리 (Git)
- ✅ 환경별 변수로 재사용 가능
- ✅ `terraform destroy`로 깔끔하게 삭제
- ✅ 팀원이 `terraform apply` 한 번으로 동일 환경 생성

---

## 🔄 실제 워크플로우 비교

### 시나리오: "dev 환경 만들고, 나중에 worker 개수를 2→5로 늘리기"

#### AWS CLI 방식

```bash
# 1. 처음 만들 때 (위 명령어들 실행)
# ... 10개 명령어 실행 ...

# 2. 나중에 worker 개수 늘리기
# → 뭘 만들었는지 기억해야 함
# → Service 이름이 뭐였지? 클러스터 이름은?
aws ecs update-service \
  --cluster crawler-cluster \
  --service crawler-worker \
  --desired-count 5

# 문제: 다른 환경(staging)도 만들려면?
# → 또 10개 명령어 실행 (환경 이름만 바꿔서)
```

#### Terraform 방식

```hcl
# 1. 처음 만들 때
# main.tf 작성 후
terraform apply

# 2. 나중에 worker 개수 늘리기
# main.tf에서 desired_count = 5로 수정
terraform apply  # 변경사항만 자동 적용

# 3. 다른 환경 만들기
terraform workspace new staging
terraform apply -var="environment=staging"
# → 코드는 같고 변수만 다름
```

---

## 💰 비용 관리

### AWS CLI
- ❌ 리소스 추적 어려움 → **비용 폭탄 위험**
- ❌ "이거 내가 만든 거 맞나?" 확인 어려움
- ❌ 삭제할 때 하나씩 찾아야 함

### Terraform
- ✅ `terraform show`로 모든 리소스 확인
- ✅ `terraform destroy`로 한 번에 삭제
- ✅ 코드 리뷰로 불필요한 리소스 생성 방지

---

## 🎓 언제 뭘 쓸까?

### AWS CLI가 좋은 경우
- ✅ **일회성 작업**: 테스트용 리소스 하나만 만들 때
- ✅ **빠른 프로토타입**: "일단 돌려보고 싶다"
- ✅ **학습**: AWS 서비스 이해할 때
- ✅ **스크립트 자동화**: CI/CD에서 특정 작업만 할 때

**예시:**
```bash
# 개발 중에 임시 S3 버킷 하나만 만들기
aws s3 mb s3://my-test-bucket
# → 나중에 수동으로 삭제해도 됨
```

### Terraform이 좋은 경우
- ✅ **프로덕션 환경**: 안정적이고 재현 가능해야 할 때
- ✅ **여러 환경**: dev/staging/prod 각각 만들어야 할 때
- ✅ **팀 협업**: 여러 명이 같은 인프라 관리할 때
- ✅ **장기 운영**: 나중에 수정/삭제가 필요할 때

**예시:**
```hcl
# 프로덕션 환경 전체를 코드로 관리
# → Git으로 버전 관리
# → 코드 리뷰로 실수 방지
# → 언제든 재생성 가능
```

---

## 🚀 현재 프로젝트 추천

### 단계별 접근

**1단계: 빠른 시작 (AWS CLI)**
```bash
# 일단 돌려보고 싶을 때
aws sqs create-queue --queue-name crawler-jobs
aws ecr create-repository --repository-name wine-crawler-api
# ... 빠르게 테스트
```

**2단계: 프로덕션 준비 (Terraform)**
```hcl
# 안정적인 환경이 필요할 때
# infrastructure/ 폴더에 Terraform 코드 작성
# → Git으로 관리
# → 환경별 배포 자동화
```

---

## 📚 하이브리드 접근 (실용적)

**Terraform으로 인프라 생성 + AWS CLI로 운영**

```bash
# Terraform으로 인프라 생성
terraform apply

# 운영 중에는 AWS CLI로 빠르게 조작
aws ecs update-service --desired-count 10  # 급하게 스케일 업
aws sqs purge-queue --queue-url ...        # 큐 비우기

# 변경사항은 나중에 Terraform 코드에도 반영
```

---

## 🎯 결론

| 상황 | 추천 |
|------|------|
| **지금 당장 테스트** | AWS CLI |
| **프로덕션 배포** | Terraform |
| **팀 프로젝트** | Terraform |
| **일회성 작업** | AWS CLI |
| **장기 운영** | Terraform |

**현재 프로젝트 권장:**
1. **지금은 AWS CLI로 빠르게 테스트** (Option 1 구현)
2. **나중에 Terraform으로 전환** (프로덕션 준비 시)

원하시면 **Terraform 코드도 작성**해드릴 수 있습니다! 🚀
