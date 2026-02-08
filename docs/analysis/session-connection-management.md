# 크롤러 세션 및 접속 관리 프로세스 분석

## 개요

이 문서는 wine-crawler의 세션 관리, 브라우저 연결, 재시도 메커니즘에 대한 전체적인 프로세스를 정리한 것입니다.

## 아키텍처 개요

크롤러는 다음과 같은 계층 구조로 세션과 연결을 관리합니다:

```
┌─────────────────────────────────────────┐
│         CLI / Crawler Entry Point       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      SessionManager (세션 영속성)        │
│  - 세션 메타데이터 관리                  │
│  - TTL 검증                              │
│  - Persona 캐싱                          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   with_session_browser (Context Manager) │
│  - SessionManager와 통합                │
│  - 자동 세션 로드/저장                   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      BrowserManager (브라우저 생명주기) │
│  - Playwright 브라우저 초기화           │
│  - Stealth 패치 적용                     │
│  - Persona 주입                         │
│  - Proxy 설정                            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         BrowserSession (실제 세션)       │
│  - Playwright, Browser, Context         │
└─────────────────────────────────────────┘
```

## 주요 컴포넌트

### 1. SessionManager (`core/session.py`)

**역할**: 사이트별 세션의 영속성과 생명주기 관리

**주요 기능**:

#### 세션 디렉터리 구조
```
storage_state/
└── <site_name>/
    ├── state.json          # Playwright storage state (cookies, localStorage 등)
    ├── persona.json         # browserforge fingerprint 캐시
    └── session.meta.json    # 세션 메타데이터 (생성일, 사용 횟수, TTL 등)
```

#### SessionMeta 데이터 구조
```python
@dataclass
class SessionMeta:
    site: str                    # 사이트 이름
    created_at: str              # 생성 시간 (ISO format)
    last_used_at: str            # 마지막 사용 시간
    last_login_at: str           # 마지막 로그인 시간
    use_count: int               # 사용 횟수
    ttl_hours: int = 72          # 기본 TTL: 3일
    user_agent: str              # 사용된 User-Agent
    status: str                  # "inactive" | "active" | "expired"
```

#### 주요 메서드

- `has_session`: 세션 파일 존재 여부 확인 (`state.json`과 `session.meta.json` 존재 여부)
- `is_expired`: TTL 기반 만료 여부 확인
- `is_usable`: 세션 존재 + 미만료 여부
- `touch()`: 세션 사용 시 호출 (last_used_at 업데이트, use_count 증가)
- `mark_login()`: 로그인 성공 시 호출 (last_login_at 업데이트, status="active")
- `mark_expired()`: 세션 만료 표시
- `get_or_create_persona()`: Persona 캐시에서 로드하거나 새로 생성
- `clear()`: 모든 세션 아티팩트 삭제
- `migrate_legacy()`: 레거시 파일 구조에서 새 구조로 마이그레이션

#### TTL (Time To Live) 관리

- 기본값: 72시간 (3일)
- 만료 기준: `last_login_at` 또는 `created_at` + `ttl_hours`
- 만료된 세션은 자동으로 `status="expired"`로 표시

### 2. BrowserManager (`core/browser.py`)

**역할**: Playwright 브라우저 인스턴스의 생성 및 관리

**보안 계층 (Layers)**:

1. **L1 - playwright-stealth**: 
   - `navigator.webdriver` 제거
   - `chrome.runtime` 패치
   - 기타 봇 탐지 우회

2. **L2 - browserforge persona**:
   - 일관된 User-Agent, Viewport, Screen 크기
   - HTTP 헤더 일관성 유지
   - 플랫폼 정보 일관성

3. **L5 - Proxy (선택적)**:
   - 프록시 서버 설정
   - 인증 정보 지원

**초기화 프로세스**:

```python
async def __aenter__(self) -> BrowserSession:
    # 1. Stealth 패치 적용
    self._stealth_cm = Stealth().use_async(async_playwright())
    self._pw = await self._stealth_cm.__aenter__()
    
    # 2. 브라우저 런치 (프록시 설정 포함)
    self._browser = await self._pw.chromium.launch(**launch_kwargs)
    
    # 3. Context 생성 (Persona 주입, Storage State 로드)
    self._context = await self._browser.new_context(**context_kwargs)
    
    # 4. 타임아웃 설정
    self._context.set_default_navigation_timeout(...)
    self._context.set_default_timeout(...)
    
    return BrowserSession(self._pw, self._browser, self._context)
```

**정리 프로세스** (`__aexit__`):
- Context 닫기
- Browser 닫기
- Stealth context manager 종료

### 3. Persona/Fingerprint 관리 (`core/fingerprint.py`)

**역할**: 일관된 브라우저 지문 생성 및 캐싱

**Persona 데이터 구조**:
```python
@dataclass(frozen=True)
class Persona:
    user_agent: str
    viewport_width: int
    viewport_height: int
    screen_width: int
    screen_height: int
    locale: str
    timezone_id: str
    platform: str
    http_headers: dict[str, str]
    raw_fingerprint: dict[str, Any]
```

**생성 프로세스**:
1. `browserforge`의 `FingerprintGenerator`로 일관된 지문 생성
2. `HeaderGenerator`로 HTTP 헤더 생성
3. 모든 속성이 내부적으로 일관성 유지 (예: macOS UA → macOS 플랫폼, macOS 화면 크기)
4. JSON 파일로 캐싱하여 재사용

**캐싱 전략**:
- `get_or_create_persona()`: 캐시 파일이 있으면 로드, 없으면 생성 후 저장
- `force_new=True`: 캐시 무시하고 새로 생성

### 4. 재시도 메커니즘 (`core/retry.py`)

**구현**: `tenacity` 라이브러리 사용

**설정**:
```python
@default_retry(max_attempts=settings.max_retries)
async def do_crawl() -> CrawlResult:
    ...
```

**재시도 전략**:
- **조건**: 모든 `Exception`에 대해 재시도
- **최대 시도 횟수**: `settings.max_retries` (기본값: 3)
- **대기 전략**: Exponential backoff with jitter
  - 초기 대기: 0.5초
  - 최대 대기: 10초
  - 지수적 증가 + 랜덤 지터

**사용 예시**:
```python
async def _run() -> None:
    async with with_session_browser(settings, site_name=site) as session:
        @default_retry(max_attempts=settings.max_retries)
        async def do_crawl() -> CrawlResult:
            return await crawler.crawl(...)
        
        result = await do_crawl()
```

## 전체 프로세스 플로우

### 1. 크롤러 실행 (`cli.py` - `run` 명령)

```
1. Settings 로드
   └─> 환경변수에서 설정 읽기 (.env 파일)

2. SessionManager 초기화
   └─> sm = SessionManager(settings, site)
   └─> sm.migrate_legacy()  # 레거시 파일 마이그레이션

3. with_session_browser 컨텍스트 진입
   ├─> SessionManager에서 Persona 로드/생성
   ├─> Storage State 파일 경로 확인
   └─> BrowserManager 초기화
       ├─> Stealth 패치 적용
       ├─> 브라우저 런치 (프록시 설정 포함)
       ├─> Context 생성 (Persona 주입, Storage State 로드)
       └─> BrowserSession 반환

4. 세션 사용 (touch)
   └─> sm.touch()  # last_used_at 업데이트, use_count 증가

5. 크롤링 실행 (재시도 포함)
   └─> @default_retry 데코레이터로 감싼 크롤링 함수 실행
       └─> 실패 시 지수 백오프로 재시도

6. Storage State 저장 (컨텍스트 내에서)
   └─> await session.context.storage_state(path=str(sm.state_path))

7. 컨텍스트 종료
   └─> BrowserManager.__aexit__
       ├─> Context 닫기
       ├─> Browser 닫기
       └─> Stealth context manager 종료
```

### 2. 로그인 프로세스 (`cli.py` - `login` 명령)

```
1. SessionManager 초기화 및 검증
   └─> sm.is_usable 확인
       ├─> 사용 가능하고 force=False → 종료
       └─> 만료되었거나 force=True → 로그인 진행

2. Persona 준비
   └─> sm.get_or_create_persona(force_new=force)

3. Storage State 준비
   └─> force=True면 None (새 세션)
   └─> force=False면 기존 파일 경로

4. BrowserManager로 브라우저 세션 생성
   └─> with_browser(...) 컨텍스트

5. 로그인 수행
   └─> crawler._login(...)
       ├─> 이미 로그인되어 있으면 → touch() 후 종료
       ├─> 로그인 폼 찾기
       ├─> 이메일/비밀번호 입력 (human_type)
       ├─> 로그인 버튼 클릭 (human_click)
       └─> 성공 여부 확인

6. 로그인 성공 시
   ├─> Storage State 저장
   ├─> sm.mark_login(user_agent=...) 호출
   │   └─> created_at, last_login_at, status="active" 설정
   └─> TTL 리셋

7. 로그인 실패 시
   └─> sm.mark_expired() 호출
```

### 3. 세션 검증 및 갱신

**자동 검증**:
- `with_session_browser` 진입 시 `sm.touch()` 호출
- 크롤링 전 `sm.is_usable` 확인 (간접적으로)

**수동 검증**:
```bash
winecrawl session status [site]
```

**세션 갱신**:
```bash
winecrawl login <site> --force
# 또는
winecrawl session refresh <site>
```

## 세션 생명주기

### 상태 전이

```
[없음]
  │
  ├─> login 성공
  │   └─> [active] (created_at, last_login_at 설정)
  │       │
  │       ├─> 사용 (touch)
  │       │   └─> last_used_at 업데이트, use_count++
  │       │
  │       └─> TTL 만료
  │           └─> [expired] (자동 또는 mark_expired())
  │
  └─> clear()
      └─> [없음]
```

### TTL 계산

```python
expires_at = (last_login_at or created_at) + timedelta(hours=ttl_hours)
is_expired = now() > expires_at
```

- 기본 TTL: 72시간 (3일)
- 만료 기준: 마지막 로그인 시간 또는 생성 시간
- 만료된 세션은 `is_usable=False` 반환

## 에러 처리 및 재시도

### 재시도 전략

**적용 범위**: 크롤링 함수 (`crawler.crawl()`)

**전략**:
- **모든 Exception**에 대해 재시도
- **Exponential Backoff with Jitter**:
  - 초기 대기: 0.5초
  - 최대 대기: 10초
  - 지터: 랜덤 변동 추가
- **최대 시도 횟수**: `settings.max_retries` (기본값: 3)

**예외**:
- 브라우저 연결 실패
- 네트워크 타임아웃
- 페이지 로드 실패
- 기타 예상치 못한 예외

### 세션 만료 처리

**로그인 실패 시**:
```python
if login_failed:
    session_mgr.mark_expired()
```

**자동 만료 감지**:
- `SessionMeta.is_expired` 속성으로 확인
- `SessionManager.is_usable`에서 자동 검증

## 설정 (Settings)

### 주요 설정 항목

```python
class Settings:
    # 디렉터리
    storage_state_dir: Path = "storage_state"
    logs_dir: Path = "logs"
    
    # Playwright
    headless: bool = True
    navigation_timeout_ms: int = 30_000
    action_timeout_ms: int = 15_000
    slow_mo_ms: int = 0
    
    # 재시도
    max_retries: int = 3
    
    # 프록시 (선택적)
    proxy_server: str = ""
    proxy_username: str = ""
    proxy_password: str = ""
    
    # 사이트별 인증 정보
    burghound_email: str = ""
    burghound_password: str = ""
```

### 환경변수 로드

- `.env` 파일에서 자동 로드
- `pydantic-settings` 사용
- 대소문자 구분 없음 (예: `BURGHOUND_EMAIL`)

## 보안 및 봇 탐지 우회

### 1. Stealth 패치 (playwright-stealth)

- `navigator.webdriver` 제거
- `chrome.runtime` 패치
- 기타 자동화 탐지 속성 제거

### 2. 일관된 Fingerprint (browserforge)

- User-Agent, Viewport, Screen 크기 일관성
- HTTP 헤더 일관성
- 플랫폼 정보 일관성
- 동일 Persona 재사용으로 "새로운 사용자" 신호 방지

### 3. 인간적인 상호작용 (`core/human.py`)

- **타이핑**: WPM 기반 가변 속도, 가우시안 지터
- **클릭**: 베지어 곡선 마우스 이동, 랜덤 위치
- **대기**: 정규 분포 기반 지연, 가변 길이 일시정지

### 4. Proxy 지원

- HTTP/HTTPS 프록시
- 인증 정보 지원
- IP 로테이션 가능

## CLI 명령어

### 세션 관리

```bash
# 세션 상태 확인
winecrawl session status [site]

# 세션 삭제
winecrawl session clear <site> [--yes]

# 세션 갱신 (강제 재로그인)
winecrawl session refresh <site>
```

### 로그인

```bash
# 로그인 (세션이 있으면 스킵)
winecrawl login <site>

# 강제 재로그인
winecrawl login <site> --force

# 헤드리스 모드
winecrawl login <site> --headless
```

### 크롤링

```bash
# 크롤링 실행
winecrawl run <site> [--limit N] [--headful] [--slowmo MS]

# 출력 파일 지정
winecrawl run <site> --out path/to/output.json
```

## 파일 구조 요약

```
storage_state/
└── <site_name>/
    ├── state.json          # Playwright storage state
    │   └─> cookies, localStorage, sessionStorage 등
    │
    ├── persona.json         # Browser fingerprint
    │   └─> user_agent, viewport, headers 등
    │
    └── session.meta.json    # 세션 메타데이터
        └─> created_at, last_used_at, ttl_hours, use_count 등
```

## 주요 코드 경로

- **세션 관리**: `src/wine_crawler/core/session.py`
- **브라우저 관리**: `src/wine_crawler/core/browser.py`
- **Fingerprint**: `src/wine_crawler/core/fingerprint.py`
- **재시도**: `src/wine_crawler/core/retry.py`
- **인간적 상호작용**: `src/wine_crawler/core/human.py`
- **설정**: `src/wine_crawler/config.py`
- **CLI**: `src/wine_crawler/cli.py`

## 결론

wine-crawler의 세션 및 접속 관리 시스템은 다음과 같은 특징을 가집니다:

1. **영속성**: 세션을 디스크에 저장하여 재사용
2. **자동화**: 세션 검증, 갱신, 만료 처리가 자동화됨
3. **보안**: Stealth 패치와 일관된 Fingerprint로 봇 탐지 우회
4. **안정성**: 재시도 메커니즘과 에러 처리
5. **유연성**: Proxy 지원, 설정 가능한 TTL, 다양한 CLI 옵션

이러한 구조를 통해 크롤러는 안정적이고 효율적으로 웹사이트와 상호작용할 수 있습니다.
