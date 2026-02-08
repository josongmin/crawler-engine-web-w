# Wine Crawler Admin -- Web Tool 설계 문서

> **Status**: Draft v3.0 (PR-Ready)
> **Author**: wine-crawler team
> **Date**: 2026-02-08
> **Target**: MVP 2주 / Full 5주

---

## 1. Executive Summary

wine-crawler CLI는 강력하지만, 세션 상태 확인 / 크롤 실행 / 로그 추적 / 데이터 확인을
터미널에서 반복하는 건 비효율적이다. **Admin Web Tool**은 크롤러의 전체 생명주기를
브라우저 한 화면에서 제어하는 개발자 전용 대시보드다.

### 핵심 가치

| 원칙 | 설명 |
|---|---|
| **Single Pane of Glass** | 세션, 크롤, 로그, 데이터를 한 화면에서 |
| **Zero Config** | `winecrawl admin` 한 줄로 로컬 서버 기동 |
| **Real-time** | WebSocket으로 로그 스트리밍, 작업 진행률 라이브 |
| **DX First** | API-first 설계, 모든 UI 동작 = REST/WS endpoint |
| **Request Kit Export** | 인증 1회 → cURL/httpx 스니펫 복붙으로 오퍼레이터 즉시 작업 |
| **Rule as Code** | 크롤 규칙을 코드가 아닌 JSON/YAML 선언으로 관리, 버전 추적 |

### Architecture at a Glance

```
┌───────────────────────────────────────────────────────────────────┐
│                    Browser (localhost:8470)                        │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │            SPA (React + Tailwind + shadcn/ui)               │  │
│  │  Dashboard│Sessions│RequestKits│Rules│Jobs│Data│Logs│Settings│
│  └────────────────────────┬────────────────────────────────────┘  │
│                            │ REST + WebSocket                     │
│  ┌─────────────────────────┴───────────────────────────────────┐  │
│  │               FastAPI Backend (uvicorn)                      │  │
│  │  ┌────────┐┌────────┐┌──────────┐┌────────┐┌───────────────┐ │  │
│  │  │Session ││  Job   ││ Request  ││  Rule  ││  WebSocket    │ │  │
│  │  │Manager ││ Runner ││ Kit     ││ Engine ││  Hub          │ │  │
│  │  └───┬────┘└───┬────┘└───┬──────┘└───┬────┘└──────┬────────┘ │  │
│  │      │         │         │           │             │          │  │
│  │  ┌───┴─────────┴─────────┴───────────┴─────────────┴───────┐ │  │
│  │  │           wine_crawler core (기존 코드)                    │ │  │
│  │  │  SessionManager · BrowserManager · SiteCrawler            │ │  │
│  │  └──────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                            │                                      │
│  ┌─────────────────────────┴───────────────────────────────────┐  │
│  │                    SQLite (admin.db)                          │  │
│  │  jobs · job_logs · credentials · schedules                   │  │
│  │  request_kits · crawl_rules · rule_versions · projects      │  │
│  │  site_capabilities                                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Concepts & Terminology

### 2-1. 핵심 용어 정의

| 용어 | 정의 | 저장 위치 |
|---|---|---|
| **Session** | Playwright/브라우저 기반 로그인 상태. `storage_state.json`에 쿠키, localStorage, sessionStorage 포함 | `storage_state/{site}/state.json` |
| **Persona** | User-Agent + sec-ch-ua + viewport/timezone + 언어 등 **fingerprint 일관성**. 브라우저처럼 보이게 하는 헤더/속성 집합 | `storage_state/{site}/persona.json` |
| **Request Kit** | Session에서 추출한 재사용 가능한 요청 재료(cookies + headers + snippet). "토큰"이 아니라 **"요청 키트"** | `request_kits` 테이블 |
| **Site Capability** | 사이트별 특성(로그아웃 방식, 로그인 성공 판별, Request Kit 지원 여부 등) | `site_capabilities` 테이블 |

### 2-2. Session vs Persona vs Request Kit 관계

```
┌─────────────────────────────────────────────────────────────┐
│  Session (Playwright storage_state)                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Cookies: PHPSESSID, tn_user, remember_me             │  │
│  │  localStorage: {}                                      │  │
│  │  sessionStorage: {}                                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ├─────────────────┐                 │
│                          ▼                 ▼                 │
│  ┌─────────────────────────────┐  ┌──────────────────────┐  │
│  │  Persona                    │  │  Request Kit Export │  │
│  │  ┌───────────────────────┐  │  │  ┌────────────────┐ │  │
│  │  │ UA: Chrome/144        │  │  │  │ cookies        │ │  │
│  │  │ sec-ch-ua: ...        │  │  │  │ headers (min)  │ │  │
│  │  │ viewport: 1440×900    │  │  │  │ snippet (curl) │ │  │
│  │  │ locale: en-US         │  │  │  │ CSRF extractor │ │  │
│  │  │ timezone: America/... │  │  │  └────────────────┘ │  │
│  │  └───────────────────────┘  │  │                      │  │
│  └─────────────────────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**핵심**: Session은 브라우저 상태, Persona는 일관성 유지용, Request Kit은 **외부 도구(cURL/httpx)에서 바로 쓸 수 있는 재료**.

---

## 3. Tech Stack

### Backend

| Layer | Choice | Rationale |
|---|---|---|
| Framework | **FastAPI** | async 네이티브, 자동 OpenAPI docs, wine_crawler와 동일 Python 런타임 |
| Server | **Uvicorn** | ASGI, hot-reload, 가볍다 |
| DB | **SQLite + aiosqlite** | 설치 0, 파일 1개, 개발자 로컬 도구에 최적 |
| Migration | **Alembic** (또는 raw SQL init) | 스키마 버전 관리 |
| Task Queue | **In-process asyncio.Queue** | 외부 의존성 0, 크롤 작업은 한 번에 1개 |
| WebSocket | **FastAPI WebSocket** | 로그 스트리밍, 작업 진행 실시간 push |

### Frontend

| Layer | Choice | Rationale |
|---|---|
| Framework | **React 19** + **Vite** | 빠른 HMR, 생태계, 개발자 친숙도 |
| Styling | **Tailwind CSS 4** | utility-first, dark mode 내장 |
| Components | **shadcn/ui** | radix 기반, 복붙으로 커스터마이즈, 종속성 최소 |
| State | **TanStack Query v5** | 서버 상태 캐싱, 자동 refetch, optimistic update |
| Routing | **React Router v7** | 파일 기반 라우팅 |
| Charts | **Recharts** | 경량, React 네이티브 |
| Code Editor | **Monaco Editor** | JSON 규칙 편집, 로그 하이라이팅 |
| Real-time | **native WebSocket** + reconnect wrapper | 로그/작업 상태 스트리밍 |

---

## 4. Data Model

### 4-1. SQLite Schema

```sql
-- =============================================
-- Core Tables
-- =============================================

CREATE TABLE jobs (
    id          TEXT PRIMARY KEY,
    project_id  TEXT REFERENCES projects(id),
    site        TEXT NOT NULL,
    rule_id     TEXT REFERENCES crawl_rules(id),
    executor    TEXT DEFAULT 'local',              -- 'local' | 'remote_proxy'
    executor_meta TEXT,                            -- JSON: remote endpoint, auth 등
    status      TEXT NOT NULL DEFAULT 'pending',
    limit_n     INTEGER DEFAULT 10,
    headless    BOOLEAN DEFAULT TRUE,
    created_at  TEXT NOT NULL,
    started_at  TEXT,
    finished_at TEXT,
    duration_ms INTEGER,
    item_count  INTEGER DEFAULT 0,
    error       TEXT,
    output_path TEXT,
    meta        TEXT
);

CREATE TABLE job_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id     TEXT NOT NULL REFERENCES jobs(id),
    level      TEXT NOT NULL,
    message    TEXT NOT NULL,
    timestamp  TEXT NOT NULL,
    source     TEXT
);

CREATE TABLE credentials (
    site       TEXT PRIMARY KEY,
    email      TEXT NOT NULL,
    password_enc TEXT NOT NULL,                    -- AES-256-GCM 암호화
    notes      TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE schedules (
    id         TEXT PRIMARY KEY,
    site       TEXT NOT NULL,
    project_id TEXT REFERENCES projects(id),
    rule_id    TEXT REFERENCES crawl_rules(id),
    cron_expr  TEXT NOT NULL,
    limit_n    INTEGER DEFAULT 10,
    enabled    BOOLEAN DEFAULT TRUE,
    last_run   TEXT,
    next_run   TEXT,
    created_at TEXT NOT NULL
);

-- =============================================
-- Request Kit Export (NEW - renamed from token_exports)
-- =============================================

CREATE TABLE request_kits (
    id              TEXT PRIMARY KEY,
    site            TEXT NOT NULL,
    format          TEXT NOT NULL,                 -- "curl" | "httpx" | "cookies" | "storage_state"
    snippet_enc     TEXT NOT NULL,                 -- 암호화된 스니펫
    cookies_enc     TEXT NOT NULL,                 -- 암호화된 쿠키 JSON
    headers_enc     TEXT,                          -- 암호화된 헤더 JSON (선택)
    csrf_extractor  TEXT,                          -- JSON: {source: "cookie|meta|input", key: "..."}
    user_agent      TEXT,
    expires_at      TEXT,                          -- 쿠키 만료 기반 추정
    created_at      TEXT NOT NULL,
    used_count      INTEGER DEFAULT 0,
    last_used       TEXT,
    notes           TEXT
);

-- =============================================
-- Site Capabilities (NEW)
-- =============================================

CREATE TABLE site_capabilities (
    site                TEXT PRIMARY KEY,
    supports_request_kit BOOLEAN DEFAULT TRUE,     -- Request Kit export 가능 여부
    logout_strategy     TEXT NOT NULL,             -- JSON: {type: "url_get"|"url_post"|"ui_click", ...}
    login_validator      TEXT NOT NULL,             -- JSON: {type: "dom_text"|"redirect"|"status", ...}
    token_validator      TEXT NOT NULL,             -- JSON: {type: "dom_text"|"status", ...}
    csrf_required        BOOLEAN DEFAULT FALSE,
    csrf_source          TEXT,                     -- "cookie" | "meta" | "input"
    csrf_key             TEXT,                      -- 쿠키/메타/인풋 이름
    updated_at           TEXT NOT NULL
);

-- =============================================
-- Projects & Rules
-- =============================================

CREATE TABLE projects (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    site        TEXT NOT NULL,
    description TEXT,
    status      TEXT DEFAULT 'active',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE crawl_rules (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id),
    name        TEXT NOT NULL,
    page_type   TEXT NOT NULL,
    url_pattern TEXT,
    version     INTEGER DEFAULT 1,
    rule_body   TEXT NOT NULL,                    -- JSON/YAML
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    created_by  TEXT DEFAULT 'admin'
);

CREATE TABLE rule_versions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id     TEXT NOT NULL REFERENCES crawl_rules(id),
    version     INTEGER NOT NULL,
    rule_body   TEXT NOT NULL,
    change_note TEXT,
    created_at  TEXT NOT NULL,
    UNIQUE(rule_id, version)
);

CREATE TABLE rule_test_results (
    id          TEXT PRIMARY KEY,
    rule_id     TEXT NOT NULL REFERENCES crawl_rules(id),
    test_url    TEXT NOT NULL,
    status      TEXT NOT NULL,
    extracted   TEXT,
    errors      TEXT,
    screenshot  TEXT,
    duration_ms INTEGER,
    created_at  TEXT NOT NULL
);

-- =============================================
-- KV Store
-- =============================================

CREATE TABLE kv_store (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

### 4-2. Site Capability Schema (상세)

```jsonc
// site_capabilities.logout_strategy
{
  "type": "url_get",                    // "url_get" | "url_post" | "ui_click"
  "url": "/logout.php",                 // type이 url_*일 때
  "method": "GET",                      // type이 url_post일 때
  "csrf_field": "_token",               // CSRF 토큰 필드명 (필요 시)
  "selector": "button#logout",          // type이 ui_click일 때
  "pre_actions": [                      // 클릭 전 사전 동작 (예: 모달 닫기)
    { "type": "click", "selector": ".modal-close" }
  ]
}

// site_capabilities.login_validator
{
  "type": "dom_text",                   // "dom_text" | "redirect" | "status" | "cookie"
  "success_selector": ".user-menu",     // type이 dom_text일 때: 이 셀렉터에 텍스트 존재하면 성공
  "success_text": "Logout",             // 또는 특정 텍스트 포함 여부
  "failure_selector": ".error-message", // 실패 시 나타나는 셀렉터
  "redirect_success": "/dashboard",     // type이 redirect일 때: 이 URL로 가면 성공
  "cookie_name": "session_id"            // type이 cookie일 때: 이 쿠키 존재하면 성공
}

// site_capabilities.token_validator
{
  "type": "dom_text",                   // "dom_text" | "status"
  "test_url": "/account",               // 유효성 검증용 URL
  "success_selector": ".account-info",   // 이 셀렉터 존재하면 유효
  "failure_redirect": "/login"          // 실패 시 이 URL로 리다이렉트
}
```

### 4-3. Crawl Rule Schema (v3 - 개선)

```jsonc
{
  "name": "search-results",
  "page_type": "search",
  "url_pattern": "tnsearch/tasting_notes\\.php",

  "pre_actions": [
    { "type": "wait", "selector": "#results-table", "timeout_ms": 5000 },
    { "type": "dismiss", "selector": ".cookie-banner" }
  ],

  "extract": {
    "container": "table#results tbody tr",
    "fields": {
      "producer": {
        "selector": ["td:nth-child(1)", "td.producer"],  // ← 배열: fallback
        "type": "text",
        "transform": {                                    // ← 파라미터화
          "name": "trim"
        }
      },
      "wine": {
        "selector": "td:nth-child(2)",
        "type": "text",
        "transform": {
          "name": "regex",
          "pattern": "^(.+?)\\s+\\((\\d{4})\\)$",        // "Wine (2019)" → "Wine"
          "group": 1
        }
      },
      "vintage": {
        "selector": "td:nth-child(2)",
        "type": "text",
        "transform": {
          "name": "regex",
          "pattern": "\\((\\d{4})\\)",
          "group": 1
        },
        "post_process": "int"                            // 문자열 → 정수
      },
      "score": {
        "selector": "td:nth-child(4)",
        "type": "text",
        "transform": {
          "name": "regex",
          "pattern": "(\\d+)-(\\d+)",
          "group": "all"                                  // 전체 매칭
        }
      },
      "detail_url": {
        "selector": "td:nth-child(2) a",
        "type": "attr",
        "attr": "href",
        "transform": {
          "name": "absolute_url",                         // 상대 → 절대 URL
          "base": "https://www.burghound.com"
        }
      }
    }
  },

  "pagination": {
    "type": "click",                                     // "click" | "url_param"
    "next_selector": "a.next-page",
    "next_url_selector": "a.next-page",                  // ← NEW: href 직접 추출
    "has_next": "a.next-page:not(.disabled)",
    "max_pages": 100,
    "delay_between_ms": { "min": 1500, "max": 3000 }
  },

  "follow": {
    "field": "detail_url",
    "rule": "wine-detail",
    "merge_into_parent": true,
    "dedupe_by": "detail_url",                           // ← NEW: 중복 제거 기준
    "cache_ttl_hours": 24                                // ← NEW: 같은 job 내 캐시
  },

  "throttle": {
    "requests_per_minute": 20,
    "delay_ms": { "min": 800, "max": 2000 }
  }
}
```

**주요 개선점**:
- `selector`: `string | string[]` (fallback 지원)
- `transform`: 파라미터화 (`regex`, `trim`, `absolute_url` 등)
- `follow`: `dedupe_by`, `cache_ttl_hours` 추가
- `pagination`: `next_url_selector` 추가 (URL 직접 추출)

---

## 5. Feature Specification

### 5-1. Dashboard

(v2와 동일 -- 상세 생략)

### 5-2. Session Management

(v2와 동일 + Site Capability 기반 logout_strategy 적용)

### 5-3. Request Kit Export (v3 - 개선)

**목표**: Session에서 추출한 재사용 가능한 요청 재료를 cURL/httpx/storage_state로 내보내기

#### Export Options

```
┌──────────────────────────────────────────────────────────┐
│  Export Request Kit: burghound                           │
│                                                          │
│  Format:                                                 │
│  ◉ cURL (minimal headers)                                │
│  ○ httpx (Python)                                        │
│  ○ Raw Cookies (Netscape)                                │
│  ○ Storage State (Playwright JSON)                       │
│                                                          │
│  Options:                                                │
│  [✓] Include CSRF extractor                             │
│  [✓] Minimal headers only (recommended)                  │
│  [ ] Include all headers (advanced)                     │
│                                                          │
│  Base URL:                                               │
│  [ https://www.burghound.com/tnsearch/... ]             │
│                                                          │
│  ┌─ Generated Snippet ───────────────────────────────┐  │
│  │  curl 'https://www.burghound.com/tnsearch/...' \  │  │
│  │    -H 'User-Agent: Mozilla/5.0 ...' \             │  │
│  │    -H 'Accept: text/html,...' \                    │  │
│  │    -H 'Cookie: PHPSESSID=abc123; tn_user=xyz'      │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ CSRF Extractor (if needed) ──────────────────────┐  │
│  │  # Extract CSRF from meta tag:                     │  │
│  │  csrf=$(curl ... | grep -oP 'name="csrf" ...')     │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  [ Copy to Clipboard ]  [ Download as .sh ]            │
│                                                          │
│  ┌─ Kit Health ───────────────────────────────────────┐  │
│  │  Session valid:  ✓ (PHPSESSID expires in 23h)      │  │
│  │  Cookies:        3 (PHPSESSID, tn_user, remember) │  │
│  │  Headers:        4 minimal (UA, Accept, Lang, Cookie)││
│  │  CSRF support:   ✓ (from cookie: _token)           │  │
│  │  Last exported:  2 min ago                          │  │
│  │  Used:           5 times                             │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  [ Validate Kit ]  [ Re-login & Export Fresh ]           │
└──────────────────────────────────────────────────────────┘
```

**핵심 개선**:
- **Minimal headers 기본**: User-Agent, Accept, Accept-Language, Cookie만 (성공률 높음)
- **CSRF extractor**: 사이트별 설정 기반 자동 생성
- **Storage State export**: Playwright JSON 그대로 (다른 Playwright 스크립트에서 재사용)
- **Validate**: 사이트별 `token_validator`로 실제 HTTP 요청 → 유효성 검증

### 5-4. Project Management

(v2와 동일 -- 상세 생략)

### 5-5. Crawl Rule Editor (v3 - 개선)

**Live Preview 개선**:

```
┌──────────────────────────────────────────────────────────────┐
│  Rule Editor: search-results (v3)          Project: full-db  │
│                                                              │
│  ┌─ Left: Rule Definition ────┐┌─ Right: Live Preview ─────┐│
│  │                            ││                            ││
│  │  Container:                ││  URL: [burghound.com/...] ││
│  │  [ table#results tbody tr]││                            ││
│  │                            ││  [ Load & Test ]          ││
│  │  Fields:                   ││                            ││
│  │  ┌──────────────────────┐  ││  ┌─ Matched: 25 rows ────┐││
│  │  │ producer             │  ││  │ ┌──────┬─────────┐   │││
│  │  │ sel: [td:nth-child(1)│  ││  │ │prod │wine     │   │││
│  │  │      td.producer]    │  ││  │ ├──────┼─────────┤   │││
│  │  │ type: text           │  ││  │ │DRC   │La Tâche │   │││
│  │  │ transform: trim      │  ││  │ │DRC   │Romanée  │   │││
│  │  │ ✓ 25/25 matched      │  ││  │ └──────┴─────────┘   │││
│  │  │               [ Edit ]│  ││  └──────────────────────┘││
│  │  └──────────────────────┘  ││                            ││
│  │                            ││  ┌─ Selector Validation ─┐││
│  │  ┌──────────────────────┐  ││  │ td:nth-child(1): ✓ 25 │││
│  │  │ wine                 │  ││  │ td.producer:    ✓ 25 │││
│  │  │ sel: td:nth-child(2)│  ││  │ (fallback not used)   │││
│  │  │ transform: regex    │  ││  └──────────────────────┘││
│  │  │   pattern: ^(.+?)  │  ││                            ││
│  │  │   group: 1          │  ││  ┌─ Raw Extracted ───────┐││
│  │  │ ✓ 25/25 matched      │  ││  │ {                      │││
│  │  │               [ Edit ]│  ││  │   "producer":"DRC",   │││
│  │  └──────────────────────┘  ││  │   "wine":"La Tâche",   │││
│  │                            ││  │   "vintage": 2019,     │││
│  │  [ + Add Field ]          ││  │   "score":"96-98"       │││
│  │                            ││  │ }                      │││
│  │  ┌─ Follow (Chained) ───┐ ││  └──────────────────────┘││
│  │  │ Field: detail_url     │ ││                            ││
│  │  │ Rule: wine-detail     │ ││  ┌─ Follow Preview ──────┐││
│  │  │ Dedupe: detail_url    │ ││  │ Will crawl 25 detail  │││
│  │  │ Cache: 24h            │ ││  │ pages (deduplicated)  │││
│  │  └───────────────────────┘ ││  └──────────────────────┘││
│  └────────────────────────────┘└────────────────────────────┘│
│                                                              │
│  [ Test Rule (Dry Run) ]  [ Save as v4 ]  [ Export YAML ]   │
└──────────────────────────────────────────────────────────────┘
```

**개선점**:
- Selector fallback 표시 (`td:nth-child(1)` vs `td.producer`)
- Transform 파라미터 편집 UI
- Follow dedupe/cache 미리보기
- Dry-run 모드 (1페이지만, pagination 없이)

### 5-6. Job Runner

(v2와 동일 + `executor` 컬럼 기반 local/remote 분기)

---

## 6. API Design

### 6-1. REST Endpoints

```
# =============================================
# Sessions
# =============================================
GET    /api/sessions
GET    /api/sessions/{site}
POST   /api/sessions/{site}/login
POST   /api/sessions/{site}/logout          # site_capabilities.logout_strategy 사용
POST   /api/sessions/{site}/refresh
DELETE /api/sessions/{site}
GET    /api/sessions/{site}/cookies
GET    /api/sessions/{site}/persona
POST   /api/sessions/{site}/persona

# =============================================
# Request Kits (NEW - renamed from tokens)
# =============================================
POST   /api/request-kits/{site}/export      # format: curl|httpx|cookies|storage_state
GET    /api/request-kits/{site}/latest
GET    /api/request-kits/{site}/history
GET    /api/request-kits/{site}/{id}
POST   /api/request-kits/{site}/refresh-export
POST   /api/request-kits/{site}/{id}/validate  # site_capabilities.token_validator 사용
DELETE /api/request-kits/{site}/{id}

# =============================================
# Sites & Capabilities (NEW)
# =============================================
GET    /api/sites                           # 등록된 사이트 목록 + capabilities
GET    /api/sites/{site}/capabilities       # 사이트별 capability 상세
PUT    /api/sites/{site}/capabilities       # capability 수정

# =============================================
# Projects
# =============================================
GET    /api/projects
POST   /api/projects
GET    /api/projects/{id}
PUT    /api/projects/{id}
DELETE /api/projects/{id}
GET    /api/projects/{id}/stats

# =============================================
# Crawl Rules
# =============================================
GET    /api/rules
POST   /api/rules
GET    /api/rules/{id}
PUT    /api/rules/{id}
DELETE /api/rules/{id}
GET    /api/rules/{id}/versions
GET    /api/rules/{id}/versions/{ver}
POST   /api/rules/{id}/rollback/{ver}
POST   /api/rules/{id}/test              # Live Preview (1페이지)
POST   /api/rules/{id}/dry-run           # NEW: pagination 없이 N개만 추출
GET    /api/rules/{id}/test-results
POST   /api/rules/{id}/export
POST   /api/rules/import
POST   /api/rules/{id}/validate          # 셀렉터만 검증 (페이지 로드 없이)

# =============================================
# Jobs (기존 + 확장)
# =============================================
GET    /api/jobs
POST   /api/jobs                          # executor, executor_meta 추가
GET    /api/jobs/{id}
POST   /api/jobs/{id}/cancel
POST   /api/jobs/{id}/rerun               # NEW: 동일 설정 재실행
GET    /api/jobs/{id}/logs

# =============================================
# Data / Credentials / Schedules / Logs / System
# =============================================
# (v2와 동일)
```

### 6-2. Request Kit Export Request/Response

```jsonc
// POST /api/request-kits/burghound/export
// Request
{
  "format": "curl",
  "base_url": "https://www.burghound.com/tnsearch/tasting_notes.php",
  "options": {
    "minimal_headers": true,              // 기본값: true
    "include_csrf": true,                 // CSRF extractor 포함 여부
    "include_storage_state": false        // storage_state JSON 포함 여부
  }
}

// Response
{
  "id": "01JKXYZ...",
  "format": "curl",
  "snippet": "curl 'https://www.burghound.com/...' \\\n  -H 'User-Agent: ...' \\\n  -H 'Cookie: ...'",
  "csrf_extractor": {
    "source": "cookie",
    "key": "_token",
    "example": "# Extract: csrf=$(curl ... | grep -oP '_token=([^;]+)' | cut -d= -f2)"
  },
  "expires_at": "2026-02-09T10:00:00Z",
  "created_at": "2026-02-08T10:35:37Z"
}
```

### 6-3. WebSocket Endpoints

```
WS  /ws/logs
WS  /ws/jobs/{id}
WS  /ws/sessions/{site}
WS  /ws/rules/{id}/test
```

---

## 7. Backend Services

### 7-1. RequestKitService (NEW - renamed from TokenRelay)

```python
class RequestKitService:
    """Session에서 Request Kit 추출 + 스니펫 생성."""

    async def export(
        self, site: str, *, format: str = "curl", base_url: str = "",
        minimal_headers: bool = True, include_csrf: bool = True,
    ) -> RequestKit:
        """state.json + persona.json → 스니펫 조립."""
        # 1. 쿠키 로드 (state.json)
        # 2. 헤더 로드 (persona.json)
        # 3. 최소 헤더만 선택 (minimal_headers=True면)
        # 4. CSRF extractor 생성 (site_capabilities 기반)
        # 5. 스니펫 조립 (format별)
        # 6. 암호화 저장

    def _build_curl(
        self, cookies: dict, headers: dict, url: str, *, minimal: bool = True,
    ) -> str:
        """cURL 스니펫 생성."""
        # Minimal: User-Agent, Accept, Accept-Language, Cookie만
        # Full: persona.json의 모든 헤더

    def _build_httpx(self, cookies: dict, headers: dict, url: str) -> str: ...

    def _build_storage_state(self, site: str) -> dict:
        """Playwright storage_state.json 그대로 반환."""

    async def validate(self, kit_id: str) -> bool:
        """site_capabilities.token_validator로 유효성 검증."""
        # 1. kit 로드
        # 2. test_url로 HTTP GET
        # 3. validator 규칙 적용 (dom_text, redirect, status 등)
```

### 7-2. RuleEngine (v3 - 개선)

```python
class RuleEngine:
    """크롤 규칙 파싱, 검증, 실행."""

    async def test_rule(
        self, rule_id: str, test_url: str, *, session: BrowserSession,
    ) -> TestResult:
        """Live Preview: 1페이지만 추출."""

    async def dry_run(
        self, rule_id: str, test_url: str, *, limit: int = 10,
        session: BrowserSession,
    ) -> list[dict]:
        """Dry-run: pagination 없이 N개만."""

    async def execute_rule(
        self, rule: CrawlRule, *, session: BrowserSession, logger: Logger,
        limit: int,
    ) -> list[dict]:
        """규칙 기반 크롤 실행."""
        # 1. container 추출
        # 2. fields 추출 (selector fallback, transform 적용)
        # 3. pagination 처리
        # 4. follow 처리 (dedupe_by, cache_ttl_hours 적용)
        # 5. 결과 병합

    def _extract_fields(
        self, page: Page, rule: dict, *, container: Locator,
    ) -> list[dict]:
        """필드 추출 (selector 배열 fallback 지원)."""
        for field_name, field_def in rule["extract"]["fields"].items():
            selectors = field_def["selector"]
            if isinstance(selectors, str):
                selectors = [selectors]
            # 첫 번째 매칭되는 셀렉터 사용

    def _apply_transform(self, value: str, transform: dict) -> Any:
        """Transform 적용 (파라미터화)."""
        if transform["name"] == "regex":
            import re
            match = re.search(transform["pattern"], value)
            if transform.get("group") == "all":
                return match.groups() if match else None
            return match.group(transform["group"]) if match else None
        elif transform["name"] == "trim":
            return value.strip()
        elif transform["name"] == "absolute_url":
            from urllib.parse import urljoin
            return urljoin(transform["base"], value)
```

### 7-3. JobRunner (v3 - Worker Abstraction)

```python
class ExecutionTarget(Enum):
    LOCAL = "local"
    REMOTE_PROXY = "remote_proxy"  # 미래 확장용

class JobRunner:
    """작업 실행 엔진 (local/remote 분기)."""

    def __init__(self):
        self._local_runner = RunnerLocal()
        self._remote_runner = RunnerRemoteProxy()  # stub

    async def submit(self, job: Job) -> str:
        """작업 제출."""
        executor = ExecutionTarget(job.executor)
        if executor == ExecutionTarget.LOCAL:
            return await self._local_runner.execute(job)
        elif executor == ExecutionTarget.REMOTE_PROXY:
            return await self._remote_runner.execute(job)  # 미래 구현

class RunnerLocal:
    """로컬 실행 (기존 로직)."""
    async def execute(self, job: Job) -> str: ...

class RunnerRemoteProxy:
    """원격 프록시 실행 (미래)."""
    async def execute(self, job: Job) -> str:
        raise NotImplementedError("Remote proxy execution not yet implemented")
```

### 7-4. SiteCapabilityService (NEW)

```python
class SiteCapabilityService:
    """사이트별 capability 관리."""

    async def get_capability(self, site: str) -> SiteCapability:
        """capability 조회 (없으면 기본값)."""

    async def logout(
        self, site: str, *, session: BrowserSession,
    ) -> bool:
        """site_capabilities.logout_strategy 기반 로그아웃."""
        cap = await self.get_capability(site)
        strategy = cap.logout_strategy
        if strategy["type"] == "url_get":
            await session.page.goto(strategy["url"])
        elif strategy["type"] == "url_post":
            # CSRF 토큰 추출 (필요 시)
            # POST 요청
        elif strategy["type"] == "ui_click":
            # pre_actions 실행
            # selector 클릭

    async def validate_login(
        self, site: str, *, session: BrowserSession,
    ) -> bool:
        """site_capabilities.login_validator로 로그인 성공 여부 판별."""

    async def validate_token(
        self, site: str, *, kit: RequestKit,
    ) -> bool:
        """site_capabilities.token_validator로 토큰 유효성 검증."""
```

---

## 8. Security & DX

### 8-1. 암호화 현실적 접근

| 항목 | 구현 |
|---|---|
| **키 관리** | OS Keychain (macOS Keychain, Windows Credential Manager) 또는 `.env`의 `ADMIN_SECRET_KEY` |
| **암호화 대상** | `credentials.password_enc`, `request_kits.snippet_enc`, `request_kits.cookies_enc`, `request_kits.headers_enc` |
| **알고리즘** | AES-256-GCM (Python `cryptography` 라이브러리) |
| **UI 마스킹** | 민감 정보는 기본 마스킹, "Reveal" 버튼으로 일시 표시 |

```python
# admin/services/crypto.py
from cryptography.fernet import Fernet
import keyring  # pip install keyring

def get_secret_key() -> bytes:
    """키 가져오기 (Keychain → .env → 자동 생성)."""
    key = os.getenv("ADMIN_SECRET_KEY")
    if not key:
        key = keyring.get_password("wine_crawler", "admin_secret_key")
    if not key:
        key = Fernet.generate_key().decode()
        keyring.set_password("wine_crawler", "admin_secret_key", key)
    return key.encode() if isinstance(key, str) else key
```

### 8-2. Request Kit 스니펫 생성 규칙

**Minimal Headers (기본값)**:
```
User-Agent: <persona.user_agent>
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: <persona.locale>
Cookie: <cookies>
Referer: <base_url> (필요 시)
```

**Full Headers (고급 모드)**:
- persona.json의 모든 헤더 포함
- sec-ch-ua, sec-fetch-* 등 (단, cURL에서 재현 불가능한 건 제외)

### 8-3. Developer Experience

| 원칙 | 구현 |
|---|---|
| **Zero Config** | `winecrawl admin` 한 줄로 서버 시작 |
| **API-first** | 모든 동작 = REST endpoint, cURL로 가능 |
| **Copy-Paste DX** | Request Kit export → 클립보드 → 터미널 붙여넣기 |
| **Rule as Code** | 규칙 YAML 파일 → Git 추적 → 코드 리뷰 가능 |
| **Dry-run First** | Rule 테스트 → Dry-run → Job 실행 (실패 전에 검증) |
| **Rerun** | Job 실패 시 "Rerun" 한 번에 재시도 |

---

## 9. Implementation Roadmap (v3 - Impact-First)

### Phase 1: Core Value (Week 1 - Days 1-7)

**목표**: "로그인 → Request Kit 뽑힘 → 규칙 테스트가 맞음 → 바로 job 돌아감" 흐름 완성

| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | 프로젝트 셋업 | FastAPI app, SQLite 전체 스키마, Vite+React scaffold |
| 2 | Session API + Site Capabilities | `/api/sessions/*`, `/api/sites/*`, `site_capabilities` 테이블 + 기본값 |
| 3 | **Request Kit Export** | `/api/request-kits/*/export` (cURL minimal), 스니펫 생성 로직 |
| 4 | Request Kit UI | RequestKitExporter, SnippetViewer, Copy 버튼 |
| 5 | **Rule Test (Live Preview)** | `/api/rules/{id}/test`, 실제 페이지 로드 → 추출 결과 |
| 6 | Rule Editor UI | Split-pane, Live Preview 패널, 셀렉터 검증 표시 |
| 7 | **Job 실행 (Rule 기반)** | `/api/jobs` (rule_id), JobRunner, WebSocket 로그 |

### Phase 2: Polish & Projects (Week 2 - Days 8-14)

| Day | Task | Deliverable |
|-----|------|-------------|
| 8  | Rule Schema 개선 | selector[], transform params, follow dedupe/cache |
| 9  | Rule Dry-run | `/api/rules/{id}/dry-run`, pagination 없이 N개만 |
| 10 | Projects + Rules CRUD | `/api/projects/*`, `/api/rules/*`, 버전 관리 |
| 11 | Job Rerun | `/api/jobs/{id}/rerun`, 동일 설정 재실행 |
| 12 | Data Explorer | `/api/data/*`, 검색/필터/내보내기 |
| 13 | Log Viewer | `/api/logs`, WebSocket tail |
| 14 | Dashboard + QA | StatCards, SessionHealth, 통합 테스트 |

### Phase 3: Advanced (Week 3-5, Optional)

| Feature | Description |
|---------|-------------|
| Storage State Export | Playwright JSON 포맷 |
| CSRF Extractor 고급 | meta tag, input field 자동 감지 |
| Remote Proxy Runner | `executor=remote_proxy` 구현 |
| Scheduler | cron 스케줄러 + UI |
| Rule Import/Export | YAML ↔ DB 양방향 싱크 |
| Performance Dashboard | 크롤 속도, 성공률 차트 |

---

## 10. Dependencies & Configuration

### 추가 의존성

```toml
# pyproject.toml
[project.optional-dependencies]
admin = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "aiosqlite>=0.21",
    "cryptography>=44.0",
    "croniter>=6.0",
    "python-multipart>=0.0.20",
    "pyyaml>=6.0",
    "keyring>=25.0",              # OS Keychain 지원
]
```

### 환경 변수

```bash
# .env
ADMIN_PORT=8470
ADMIN_HOST=127.0.0.1
ADMIN_PASSWORD=                    # 빈 값이면 인증 비활성화
ADMIN_SECRET_KEY=                 # 암호화 키 (없으면 Keychain 또는 자동 생성)
```

---

## 11. Site Capability Implementation Guide

### 11-1. Burghound.com Capability 예시

```python
# sites/burghound/capability.py (또는 admin/db/seed_capabilities.sql)

{
    "site": "burghound",
    "supports_request_kit": True,
    "logout_strategy": {
        "type": "ui_click",
        "selector": "a[href*='logout']",
        "pre_actions": []
    },
    "login_validator": {
        "type": "dom_text",
        "success_selector": ".user-menu",
        "failure_selector": ".error-message"
    },
    "token_validator": {
        "type": "dom_text",
        "test_url": "/tnsearch/index.php",
        "success_selector": ".search-form",
        "failure_redirect": "/login.php"
    },
    "csrf_required": False
}
```

### 11-2. 새 사이트 추가 시 Capability 정의

1. `site_capabilities` 테이블에 INSERT
2. `logout_strategy`, `login_validator`, `token_validator` JSON 정의
3. 필요 시 CSRF 설정 (`csrf_source`, `csrf_key`)
4. Admin UI에서 "Supports Request Kit" 표시 자동 반영

---

## 12. Request Kit Snippet Generation Rules

### 12-1. Header Whitelist (Minimal)

```python
MINIMAL_HEADERS = [
    "User-Agent",
    "Accept",
    "Accept-Language",
    "Cookie",
    "Referer",  # 필요 시만
]
```

### 12-2. CSRF Extractor 생성 규칙

```python
def generate_csrf_extractor(capability: SiteCapability) -> dict:
    """CSRF extractor 스니펫 생성."""
    if not capability.csrf_required:
        return None
    
    source = capability.csrf_source
    key = capability.csrf_key
    
    if source == "cookie":
        return {
            "source": "cookie",
            "key": key,
            "example": f"# Extract: csrf=$(curl ... | grep -oP '{key}=([^;]+)' | cut -d= -f2)"
        }
    elif source == "meta":
        return {
            "source": "meta",
            "key": key,
            "example": f"# Extract: csrf=$(curl ... | grep -oP 'name=\"{key}\" content=\"([^\"]+)\"' | cut -d'\"' -f4)"
        }
```

---

## 13. Worker Abstraction: Local → Remote Proxy

### 13-1. Service Layer 구조

```python
# admin/services/execution/__init__.py

class ExecutionService(ABC):
    """실행 서비스 인터페이스."""
    
    @abstractmethod
    async def execute(self, job: Job) -> str:
        """작업 실행, job_id 반환."""
        pass

# admin/services/execution/local.py
class LocalExecutionService(ExecutionService):
    """로컬 실행 (현재 구현)."""
    async def execute(self, job: Job) -> str: ...

# admin/services/execution/remote_proxy.py
class RemoteProxyExecutionService(ExecutionService):
    """원격 프록시 실행 (미래)."""
    async def execute(self, job: Job) -> str:
        # HTTP API로 원격 에이전트에 작업 제출
        # 또는 WebSocket으로 실시간 제어
        pass
```

### 13-2. JobRunner 통합

```python
class JobRunner:
    def __init__(self):
        self._executors: dict[str, ExecutionService] = {
            "local": LocalExecutionService(),
            "remote_proxy": RemoteProxyExecutionService(),  # stub
        }
    
    async def submit(self, job: Job) -> str:
        executor = self._executors.get(job.executor)
        if not executor:
            raise ValueError(f"Unknown executor: {job.executor}")
        return await executor.execute(job)
```

**미래 확장**: `executor_meta`에 원격 엔드포인트, 인증 정보 등을 JSON으로 저장.

---

> **다음 단계**: Phase 1 Day 1 착수.
> FastAPI app factory + SQLite 전체 스키마 init + Vite+React scaffold.
> **핵심 가치**: "로그인 → Request Kit 뽑힘 → 규칙 테스트 → Job 실행" 플로우를 1주일 안에 완성.

---

## 14. UI Architecture — Site-Centric Redesign (v4)

### 14-1. 설계 철학

기존 UI는 **기능 중심**(Sessions, Request Kits, Rules, Jobs...)으로 설계되었으나,
실제 사용 패턴은 **"이 사이트에서 무엇을 할 것인가"**이다.

| 기존 (Feature-centric) | 개선 (Site-centric) |
|---|---|
| Sidebar: Sessions → 모든 사이트의 세션 | Sidebar: Burghound → 이 사이트의 모든 기능 |
| Request Kit 페이지에서 사이트 선택 | 사이트 허브에서 바로 Export |
| Job 페이지에서 사이트 필터 | 사이트 허브에서 바로 Run |
| N번 클릭 (페이지 이동 + 사이트 선택) | **1번 클릭 (딸깍)** |

### 14-2. Navigation Structure

```
Sidebar:
├─ Overview (cross-site dashboard)
├─ ──── Sites ──────────────────
│  ├─ ● Burghound     ← active
│  ├─ ○ Vivino         ← not connected
│  └─ ⚠ Wine-Searcher  ← expired
├─ ──── Tools ──────────────────
│  ├─ Jobs
│  ├─ Rules
│  ├─ Playground
│  └─ Logs
└─ API Connected
```

**Routes:**
```
/                      → OverviewPage (cross-site dashboard)
/sites/:site           → SitesPage (per-site command center)
/jobs                  → JobsPage (cross-site job history)
/rules                 → RulesPage (cross-site rule browser)
/rules/:id             → RuleEditorPage
/playground            → PlaygroundPage
/logs                  → LogsPage
```

### 14-3. Site Hub (SitesPage) — 핵심 화면

"사이트 하나에 대한 모든 것을 한 화면에서." 이 화면이 UX의 핵심이다.

```
┌──────────────────────────────────────────────────────────────────┐
│  [B] Burghound                                                    │
│  burghound.com ↗                                                  │
│                                                 2 operations ·    │
│                                                 Kit export ·      │
│                                                 Paste auth        │
│                                                                    │
│  SESSION                                                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ ● active    TTL 2d 14h                                      │  │
│  │ ██████████████████████░░░░░░░░░ 68%                        │  │
│  │ Uses: 23 · Last login: 2h ago · Clean close: yes · Kit ✓  │  │
│  │ Chrome/144.0 on macOS                                       │  │
│  │                        [Refresh] [Paste Auth] [🔴 Logout]  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  OPERATIONS (Login required to run)                               │
│  ┌──────────────────┐  ┌──────────────────┐                      │
│  │ 🔍 Search All     │  │ 📄 Wine Detail    │                      │
│  │ Search and extract│  │ Extract individual│                      │
│  │ wine tasting notes│  │ wine details      │                      │
│  │                   │  │                   │                      │
│  │ ✓ #47 142 · 3m   │  │ ✗ #45 failed · 2h │                      │
│  │ ┈┈ rule linked    │  │ ┈┈ rule linked    │                      │
│  │                   │  │                   │                      │
│  │ Limit [50] [▶Run] │  │ Limit [10] [▶Run] │                      │
│  └──────────────────┘  └──────────────────┘                      │
│                                                                    │
│  REQUEST KIT                      RECENT ACTIVITY                 │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐  │
│  │ [📋 cURL] [🐍 httpx]     │  │ #47 search-all  ✓ 142  3m   │  │
│  │ [📁 Storage State]       │  │ #46 search-all  ✓  89  1h   │  │
│  │                          │  │ #45 wine-detail ✗      2h   │  │
│  │ ● valid (23h left)       │  │                              │  │
│  │ [Validate]               │  │ View all jobs for Burghound →│  │
│  │                          │  │                              │  │
│  │ ┌── Copied snippet ───┐ │  └──────────────────────────────┘  │
│  │ │ curl '...' \         │ │                                    │
│  │ │   -H 'Cookie: ...'  │ │                                    │
│  │ └─────────────────────┘ │                                    │
│  └──────────────────────────┘                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 14-4. 주요 기능 상세

#### Authentication Actions (세션 관리)
| 액션 | 동작 | API |
|---|---|---|
| **Login** | Playwright 브라우저로 프로그래밍 로그인 | `POST /api/sessions/{site}/login` |
| **Logout** | `site_capabilities.logout_strategy` 기반 로그아웃 | `POST /api/sessions/{site}/logout` |
| **Paste Auth** | 쿠키/헤더/Storage State 복붙 → 세션 주입 | `POST /api/sessions/{site}/paste-auth` |
| **Refresh** | 세션 상태 재확인 + TTL 갱신 | `POST /api/sessions/{site}/refresh` |

**Paste Auth Dialog:**
```
┌─── Paste Authentication — Burghound ─────────────────┐
│                                                       │
│  [Cookie String] [Headers] [Storage State]            │
│                                                       │
│  Paste from DevTools → Network → Cookie header        │
│                                                       │
│  ┌───────────────────────────────────────────────┐   │
│  │ PHPSESSID=abc123; tn_user=xyz789;             │   │
│  │ remember_me=token_here                        │   │
│  │                                               │   │
│  └───────────────────────────────────────────────┘   │
│                                                       │
│  42 characters            [Cancel] [Apply & Login]   │
└───────────────────────────────────────────────────────┘
```

**지원 포맷:**
- **Cookie String**: `key=value; key2=value2` (가장 일반적)
- **Headers**: `key: value` 줄 단위 (Cookie + UA 등)
- **Storage State**: Playwright JSON 전체 (가장 완전)

#### Operation Cards (크롤 액션)
사이트별 가용한 크롤 작업을 카드 형태로 표시.
각 카드는 **1클릭으로 실행 가능**.

```ts
interface SiteOperation {
  id: string;           // "search-all"
  name: string;         // "Search All"
  type: OperationType;  // "search" | "detail" | "review" | "list"
  description: string;
  ruleId?: string;      // linked crawl rule
  defaultLimit: number;
}
```

| 타입 | 아이콘 | 색상 | 예시 |
|---|---|---|---|
| search | 🔍 | blue | Search All, Wine Search, Price Search |
| detail | 📄 | emerald | Wine Detail, Wine Page |
| review | 💬 | violet | User Reviews |
| list | 📋 | amber | Merchant Offers |

#### Request Kit Quick Export
1클릭으로 cURL/httpx/Storage State 스니펫 복사:
- 클릭 → 클립보드 복사 + 스니펫 미리보기 표시
- Kit 유효성 상태 (valid/expired) 실시간 표시
- Validate 버튼으로 실제 HTTP 요청 검증

### 14-5. Overview Page (Cross-site Dashboard)

모든 사이트의 상태를 한눈에 파악하는 랜딩 페이지.

```
┌──────────────────────────────────────────────────────────┐
│  Active Sessions: 1/3    Running Jobs: 0    Items: 2,847 │
│                                                          │
│  ┌── Burghound ──────┐ ┌── Vivino ──────────┐           │
│  │ ● Active           │ │ ○ Not Connected     │           │
│  │ TTL: 2d 14h       │ │                     │           │
│  │ #47 search-all ✓  │ │ No recent jobs      │           │
│  │        Open hub → │ │        Open hub →   │           │
│  └───────────────────┘ └─────────────────────┘           │
│                                                          │
│  ┌── Wine-Searcher ──┐                                   │
│  │ ⚠ Session Expired  │                                   │
│  │ #44 search ✓ 2d   │                                   │
│  │        Open hub → │                                   │
│  └───────────────────┘                                   │
│                                                          │
│  Recent Activity                                         │
│  #47 burghound search-all  ✓ 142 items  3m              │
│  #46 burghound search-all  ✓  89 items  1h              │
│  #45 burghound wine-detail ✗           2h               │
│  #44 wine-searcher search  ✓ 200 items 2d              │
└──────────────────────────────────────────────────────────┘
```

### 14-6. Site Definition Registry

사이트 추가 시 `shared/config/sites.ts`에 정의:

```ts
export const SITES: SiteDefinition[] = [
  {
    id: "burghound",
    name: "Burghound",
    domain: "burghound.com",
    url: "https://www.burghound.com",
    themeColor: "rose",           // Tailwind palette key
    operations: [
      { id: "search-all", name: "Search All", type: "search", ... },
      { id: "wine-detail", name: "Wine Detail", type: "detail", ... },
    ],
    supportsRequestKit: true,
    supportsPasteAuth: true,
  },
  {
    id: "vivino",
    name: "Vivino",
    domain: "vivino.com",
    url: "https://www.vivino.com",
    themeColor: "violet",
    operations: [
      { id: "search", name: "Wine Search", type: "search", ... },
      { id: "wine-detail", name: "Wine Page", type: "detail", ... },
      { id: "reviews", name: "User Reviews", type: "review", ... },
    ],
    ...
  },
  {
    id: "wine-searcher",
    name: "Wine-Searcher",
    domain: "wine-searcher.com",
    ...
    operations: [
      { id: "search", name: "Price Search", type: "search", ... },
      { id: "wine-detail", name: "Wine Detail", type: "detail", ... },
      { id: "merchant-list", name: "Merchant Offers", type: "list", ... },
    ],
  },
];
```

### 14-7. 파일 구조

```
admin-ui/src/
├─ shared/
│  ├─ config/
│  │  └─ sites.ts              ← Site definitions + operations
│  ├─ ui/
│  │  ├─ Dialog.tsx            ← Reusable modal dialog (NEW)
│  │  ├─ Button.tsx
│  │  ├─ Card.tsx
│  │  ├─ CodeBlock.tsx
│  │  ├─ StatusBadge.tsx
│  │  ├─ Input.tsx
│  │  └─ Select.tsx
│  └─ types/
│     └─ index.ts
├─ pages/
│  ├─ overview/
│  │  └─ OverviewPage.tsx      ← Cross-site dashboard (NEW)
│  ├─ sites/
│  │  ├─ SitesPage.tsx         ← Site hub - main command center (NEW)
│  │  └─ components/
│  │     ├─ SessionPanel.tsx   ← Auth status + actions (NEW)
│  │     ├─ OperationCard.tsx  ← One-click crawl action card (NEW)
│  │     └─ PasteAuthDialog.tsx ← Cookie paste dialog (NEW)
│  ├─ jobs/
│  │  └─ JobsPage.tsx          (기존 유지)
│  ├─ rules/
│  │  ├─ RulesPage.tsx         (기존 유지)
│  │  └─ RuleEditorPage.tsx    (기존 유지)
│  ├─ playground/
│  │  └─ PlaygroundPage.tsx    (기존 유지)
│  └─ logs/
│     └─ LogsPage.tsx          (기존 유지)
├─ widgets/
│  └─ layout/
│     ├─ Sidebar.tsx           ← Site-centric navigation (REDESIGNED)
│     ├─ Header.tsx            ← Site context awareness (UPDATED)
│     └─ Layout.tsx
└─ app/
   ├─ App.tsx
   ├─ router.tsx               ← New route structure (UPDATED)
   └─ styles/
      └─ index.css
```

### 14-8. 추가 API Endpoints (Paste Auth)

```
# 기존 Session API + 신규 paste-auth
POST   /api/sessions/{site}/paste-auth

# Request body
{
  "mode": "cookies" | "headers" | "storage-state",
  "content": "PHPSESSID=abc123; tn_user=xyz789"
}

# Response
{
  "status": "success",
  "session_status": "active",
  "cookies_count": 3,
  "expires_at": "2026-02-10T10:00:00Z"
}
```

---

## 15. Workflow Builder — Node & Pipeline Architecture (v5)

### 15-1. 설계 철학

개별 사이트 허브의 "딸깍" 버튼이 즉석 실행이라면,
**Workflow Builder**는 이 오퍼레이션들을 **노드 단위로 조합**하여
**재사용 가능한 파이프라인**으로 만드는 도구다.

| 개념 | 설명 |
|---|---|
| **Node** | 원자적 작업 단위 (Login, Search, Export cURL, Delay...) |
| **Edge** | 노드 간 연결 (데이터 + 제어 흐름) |
| **Workflow** | 노드 + 엣지로 구성된 DAG (Directed Acyclic Graph) |
| **Preset** | 자주 쓰는 파이프라인 템플릿 |
| **Run** | 워크플로우를 순서대로 실행 (노드별 상태 실시간 표시) |

### 15-2. Node Categories & Types

5개 카테고리, 16개 노드 타입:

| Category | Nodes | Color |
|---|---|---|
| **Auth** | Login, Logout, Paste Auth, Refresh Session, Check Session | emerald |
| **Crawl** | Search, Detail Extract, Review Extract, List Extract | blue |
| **Export** | Export cURL, Export httpx, Export Storage State | amber |
| **Control** | Delay, Condition (yes/no branch) | zinc |
| **Data** | Save to File, Notify | violet |

각 노드는 다음을 갖는다:
- **Input handle** (상단) — 이전 노드에서 데이터/트리거 수신
- **Output handle** (하단) — 다음 노드로 데이터/트리거 전달
- **Error handle** (오른쪽, 선택) — 실패 시 분기 경로
- **Config fields** — 노드별 설정 (limit, rule, headless, format 등)
- **Status** — idle / running / success / error / skipped

### 15-3. Visual Builder UI

3-column 레이아웃:

```
┌──────────────────────────────────────────────────────────────────────┐
│ [← Back] Full Crawl Pipeline    4 nodes · 3 edges    [Presets ▾]     │
│                                                    [▶ Run] [💾 Save] │
├───────────┬──────────────────────────────────────┬───────────────────┤
│ NODES     │                                      │ NODE CONFIG       │
│           │     ┌──────────┐                     │                   │
│ ── Auth   │     │🔑 Login  │                     │ 🔍 Search         │
│ [Login]   │     │headless ✓│                     │ ─────────────────  │
│ [Logout]  │     │● idle    │                     │ Limit: [50]       │
│ [Paste]   │     └────┬─────┘                     │ Rule: [v3 ▾]      │
│ [Refresh] │          │                           │ Headless: [●]     │
│ [Check]   │     ┌────▼─────┐                     │ Follow: [ ]       │
│           │     │🔍 Search │  ← selected         │                   │
│ ── Crawl  │     │limit: 50 │                     │ [Duplicate]       │
│ [Search]  │     │rule: v3  │                     │ [🔴 Delete]       │
│ [Detail]  │     │● idle    │                     │                   │
│ [Review]  │     └────┬─────┘                     │                   │
│ [List]    │          │                           │                   │
│           │     ┌────▼─────┐                     │                   │
│ ── Export │     │📄 Detail │                     │                   │
│ [cURL]    │     │rule: v2  │                     │                   │
│ [httpx]   │     │● idle    │                     │                   │
│ [Storage] │     └────┬─────┘                     │                   │
│           │          │                           │                   │
│ ── Ctrl   │     ┌────▼─────┐                     │                   │
│ [Delay]   │     │💾 Save   │                     │                   │
│ [If]      │     │json      │                     │                   │
│           │     │● idle    │                     │                   │
│ ── Data   │     └──────────┘                     │                   │
│ [Save]    │                                      │                   │
│ [Notify]  │        (drag & drop, zoom, pan)      │                   │
└───────────┴──────────────────────────────────────┴───────────────────┘
```

**주요 인터랙션:**
- **Left palette**: 노드를 캔버스로 드래그 & 드롭
- **Canvas**: ReactFlow 기반 — 노드 배치, 엣지 연결, 줌/팬, 선택
- **Right panel**: 선택된 노드의 설정 편집, 복제/삭제
- **Toolbar**: 이름 편집, 프리셋 로드, 실행, 저장

### 15-4. Preset Templates

| Preset | Nodes | 설명 |
|---|---|---|
| **Full Crawl** | Login → Search → Detail → Save | 전체 크롤링 파이프라인 |
| **Quick Export** | Login → Export cURL | 인증 후 즉시 Kit 추출 |
| **Review Pipeline** | Login → Search → Review → Save | 리뷰 수집 전용 |
| **Safe Session** | Check Session → (yes: Search) / (no: Login → Search) → Save → Notify | 조건 분기 포함 |

### 15-5. Workflow Execution

Run 클릭 시:
1. 노드를 위상 정렬 (topological sort)
2. 순서대로 실행 (node.status: idle → running → success/error)
3. 각 노드 실행 결과를 다음 노드의 input으로 전달
4. WebSocket으로 실시간 상태 업데이트
5. Error handle이 연결된 경우, 실패 시 해당 분기로 이동

```
Execution states per node:
  idle ──→ running ──→ success
                   └──→ error ──→ (error handle target)
```

### 15-6. Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Canvas | **@xyflow/react** (ReactFlow v12) | 업계 표준 노드 기반 UI, 드래그&드롭, 커스텀 노드 |
| Styling | Tailwind CSS + ReactFlow dark `colorMode` | 기존 디자인 시스템과 일관성 |
| State | `useNodesState` / `useEdgesState` (ReactFlow hooks) | 노드/엣지 로컬 상태 관리 |
| Persistence | SQLite `workflows` 테이블 (미래) | 저장/로드/실행 이력 |

### 15-7. API Endpoints (미래 구현)

```
# Workflow CRUD
GET    /api/workflows                    # 목록
POST   /api/workflows                    # 생성
GET    /api/workflows/{id}               # 조회
PUT    /api/workflows/{id}               # 수정
DELETE /api/workflows/{id}               # 삭제

# Workflow Execution
POST   /api/workflows/{id}/run           # 실행
GET    /api/workflows/{id}/runs          # 실행 이력
GET    /api/workflows/{id}/runs/{runId}  # 실행 상세

# WebSocket
WS     /ws/workflows/{id}/run            # 실행 중 실시간 상태
```

### 15-8. 파일 구조

```
pages/
  workflows/
    WorkflowsPage.tsx               ← 워크플로우 목록 + 프리셋 템플릿
    WorkflowBuilderPage.tsx         ← 비주얼 빌더 (3-column 레이아웃)
    components/
      WorkflowNode.tsx              ← 커스텀 ReactFlow 노드 컴포넌트
      NodePalette.tsx               ← 왼쪽 패널: 드래그 소스
      NodeConfigPanel.tsx           ← 오른쪽 패널: 노드 설정
shared/
  config/
    workflow-nodes.ts               ← 16개 노드 타입 레지스트리
```

### 15-9. Workflow Data Schema (SQLite)

```sql
CREATE TABLE workflows (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    site        TEXT NOT NULL,
    nodes_json  TEXT NOT NULL,     -- JSON: Node[]
    edges_json  TEXT NOT NULL,     -- JSON: Edge[]
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE workflow_runs (
    id            TEXT PRIMARY KEY,
    workflow_id   TEXT NOT NULL REFERENCES workflows(id),
    status        TEXT NOT NULL DEFAULT 'pending',  -- pending|running|success|error
    started_at    TEXT,
    finished_at   TEXT,
    node_results  TEXT,           -- JSON: Record<nodeId, { status, data, error }>
    created_at    TEXT NOT NULL
);
```

---

## 16. Design System — Theme Architecture (v6)

### 16-1. 설계 철학

모든 UI 색상을 **semantic design token**으로 공용화하여
Dark/Light 테마를 CSS custom property 교체만으로 전환.
하드코딩된 Tailwind 색상(zinc-*, emerald-*, etc.)을 완전히 제거하고
의미 기반 토큰으로 대체하여 유지보수성과 테마 확장성을 보장한다.

| 원칙 | 구현 |
|---|---|
| **Token-first** | 모든 색상은 CSS custom property (`--ds-*`) 기반 |
| **Semantic naming** | `fg-muted`, `surface-100`, `status-success` 등 용도 기반 이름 |
| **Zero zinc** | 컴포넌트에서 `text-zinc-*`, `bg-zinc-*` 직접 참조 0건 |
| **FOUC 방지** | `index.html`에 인라인 스크립트로 `.dark` 클래스 즉시 적용 |
| **Smooth transition** | 테마 전환 시 `theme-transition` 클래스로 0.2s 애니메이션 |

### 16-2. Token Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 1: @theme (Tailwind 4 Utility Registration)             │
│  --color-surface-0: var(--ds-surface-0);                      │
│  --color-fg: var(--ds-fg);                                    │
│  --color-status-success: var(--ds-status-success);            │
│  → Creates: bg-surface-0, text-fg, text-status-success, ...  │
├──────────────────────────────────────────────────────────────┤
│ Layer 2: :root (Light Theme Primitives)                       │
│  --ds-surface-0: oklch(1.00 0.00 0);     /* white */         │
│  --ds-fg: oklch(0.18 0.005 260);         /* zinc-900 */      │
│  --ds-status-success: oklch(0.45 0.16 155); /* emerald-700 */│
├──────────────────────────────────────────────────────────────┤
│ Layer 3: .dark (Dark Theme Overrides)                         │
│  --ds-surface-0: oklch(0.10 0.005 260);  /* zinc-950 */      │
│  --ds-fg: oklch(0.93 0.005 260);         /* zinc-100 */      │
│  --ds-status-success: oklch(0.75 0.18 155); /* emerald-400 */│
└──────────────────────────────────────────────────────────────┘
```

### 16-3. Token Categories

#### Surface (Background)
| Token | Dark | Light | Usage |
|-------|------|-------|-------|
| `surface-0` | zinc-950 | white | Page bg, deepest |
| `surface-50` | zinc-900 | zinc-50 | Cards, panels |
| `surface-100` | zinc-850 | zinc-100 | Hover, elevated |
| `surface-200` | zinc-800 | zinc-200 | Active, tags |
| `surface-300` | zinc-700 | zinc-300 | Scrollbar |
| `surface-400` | zinc-600 | zinc-400 | Strongest bg |

#### Foreground (Text)
| Token | Dark | Light | Usage |
|-------|------|-------|-------|
| `fg` | zinc-100 | zinc-900 | Headings, primary |
| `fg-secondary` | zinc-200 | zinc-700 | Body text |
| `fg-tertiary` | zinc-300 | zinc-600 | Secondary content |
| `fg-muted` | zinc-400 | zinc-500 | Nav, labels |
| `fg-subtle` | zinc-500 | zinc-400 | Meta, timestamps |
| `fg-faint` | zinc-600 | zinc-300 | Disabled, lightest |

#### Border
| Token | Dark | Light | Usage |
|-------|------|-------|-------|
| `border` | zinc-800 | zinc-200 | Default borders |
| `border-hover` | zinc-600 | zinc-300 | Hover borders |
| `border-strong` | zinc-700 | zinc-400 | Kbd, code borders |

#### Accent Interaction
| Token | Dark | Light | Usage |
|-------|------|-------|-------|
| `accent-fg` | accent-400 | accent-600 | Active nav, links |
| `accent-muted` | accent-500/10 | accent-50 | Active nav bg |

#### Semantic Status
| Token | Dark | Light | Usage |
|-------|------|-------|-------|
| `status-success` | emerald-400 | emerald-700 | Active, pass |
| `status-danger` | red-400 | red-600 | Failed, expired |
| `status-warning` | amber-400 | amber-600 | Partial, logged out |
| `status-info` | blue-400 | blue-600 | Running, info |
| `status-neutral` | zinc-400 | zinc-500 | Inactive, pending |

각 status에는 `-muted` (배경), `-subtle` (테두리) 파생 토큰 포함.

#### Overlay / Special
| Token | Dark | Light | Usage |
|-------|------|-------|-------|
| `overlay` | black/60 | black/30 | Dialog backdrop |
| `glass-bg` | surface-50/80 | white/80 | Glassmorphism |
| `selection-bg` | accent/30 | accent/20 | Text selection |
| `kbd-bg` | zinc-800 | zinc-100 | Keyboard shortcut bg |
| `kbd-border` | zinc-700 | zinc-300 | Keyboard shortcut border |

### 16-4. Theme Hook (`useTheme`)

```typescript
const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();

// theme         → "light" | "dark" | "system"
// resolvedTheme → "light" | "dark" (실제 적용값)
// setTheme      → 설정 + 트랜지션 + localStorage 저장
// toggleTheme   → 현재 ↔ 반대 전환
```

**Features:**
- `localStorage` 키: `wc-admin-theme`
- OS `prefers-color-scheme` 실시간 감지 (system 모드)
- `useSyncExternalStore` 기반 (React 18+, concurrent-safe)
- FOUC 방지: `index.html` 인라인 스크립트로 초기 `.dark` 클래스 설정

### 16-5. Theme Toggle UI

Sidebar 하단에 3-option segmented control:

```
┌──────────────────────────┐
│ [☀ Light] [🌙 Dark] [🖥 System] │
└──────────────────────────┘
```

### 16-6. Color Space

모든 색상값은 **OKLCH** 색공간 사용:
- 인지적 균일성 (perceptual uniformity)
- P3 gamut 지원
- Lightness 채널 직접 제어 → 테마 간 대칭 구조

### 16-7. 파일 구조 (Design System 관련)

```
admin-ui/
├─ index.html                         ← FOUC 방지 인라인 스크립트 + bg-surface-0
├─ src/
│  ├─ app/styles/
│  │  └─ index.css                    ← @theme 등록 + :root + .dark 토큰
│  └─ shared/
│     ├─ hooks/
│     │  └─ useTheme.ts              ← 테마 전환 훅 (NEW)
│     └─ ui/
│        ├─ Button.tsx               ← semantic token 기반 (UPDATED)
│        ├─ Card.tsx                  ← semantic token 기반
│        ├─ Dialog.tsx               ← semantic token 기반 (UPDATED)
│        ├─ Input.tsx                ← semantic token 기반 (UPDATED)
│        ├─ Select.tsx               ← semantic token 기반 (UPDATED)
│        ├─ CodeBlock.tsx            ← semantic token 기반 (UPDATED)
│        └─ StatusBadge.tsx          ← status category mapping (REDESIGNED)
```

### 16-8. Migration Rule

모든 컴포넌트에서 다음 매핑을 적용:

| Before (hardcoded) | After (semantic) |
|---|---|
| `text-zinc-100` | `text-fg` |
| `text-zinc-200` | `text-fg-secondary` |
| `text-zinc-300` | `text-fg-tertiary` |
| `text-zinc-400` | `text-fg-muted` |
| `text-zinc-500` | `text-fg-subtle` |
| `text-zinc-600` | `text-fg-faint` |
| `bg-zinc-800` | `bg-surface-100` |
| `border-zinc-700` | `border-border-strong` |
| `text-emerald-400` | `text-status-success` |
| `text-red-400` | `text-status-danger` |
| `text-amber-400` | `text-status-warning` |
| `text-blue-400` | `text-status-info` |
| `bg-emerald-500/15` | `bg-status-success-muted` |
| `bg-accent-500/10` | `bg-accent-muted` |
| `text-accent-400` | `text-accent-fg` |

**Site theme colors** (rose/violet/amber)는 장식적 용도이므로
`dark:text-rose-400 text-rose-500` 형태로 variant 사용.
