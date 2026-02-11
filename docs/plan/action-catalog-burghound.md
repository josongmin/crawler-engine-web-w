# Appendix A: Burghound Action Catalog 초안

> **Status**: Draft — RFC "Site Action Decomposition + Prereq-Aware Workflow DAG" 의 구체화
> **Site**: `burghound` (burghound.com)
> **Date**: 2026-02-09

---

## 0. 리소스(Resource) 정의 — Burghound 기준

DAG 컴파일러가 requires/provides를 해석하려면 "리소스"라는 추상 단위가 먼저 정의돼야 합니다.
아래는 Burghound에서 실제로 사용되는 리소스 목록입니다.

| Resource ID | 설명 | 생산자(provider) | 소비자(consumer) |
|---|---|---|---|
| `Credential(burghound)` | `.env`의 BURGHOUND_EMAIL/PASSWORD | 시스템(환경변수) | `auth.login` |
| `BrowserContext` | Playwright BrowserContext (persona 포함) | 시스템(BrowserManager) | `auth.login`, `auth.check-session`, `auth.logout` |
| `SessionActive(burghound)` | 유효한 로그인 세션 (storage_state + meta.status=active) | `auth.login`, `auth.paste-auth` | `crawl.*`, `export.*` |
| `RequestKit(burghound,*)` | 인증 정보 스니펫 (curl/httpx/storage_state) | `export.export-curl`, `export.export-httpx`, `export.export-storage` | 외부 소비(clipboard/파일) |
| `StorageState(burghound)` | Playwright storage_state.json | `auth.login` (부수효과) | `auth.paste-auth` (복원), `export.export-storage` |
| `CrawlRule(ruleId)` | JSON 기반 추출 규칙 | 시스템(DB/파일) | `crawl.search`, `crawl.detail`, `crawl.review`, `crawl.list` |
| `Dataset(items)` | 추출된 아이템 배열 | `crawl.*` | `data.save-file`, `crawl.detail` (follow) |
| `Persona(burghound)` | browserforge 핑거프린트 (UA, viewport 등) | 시스템(SessionManager) | `auth.login`, `crawl.*` |

### 리소스 상태 전이도

```
┌─────────────┐   login/paste-auth   ┌──────────────────┐
│  No Session │ ──────────────────→  │ SessionActive     │
│  (inactive) │                      │ (TTL: 72h)        │
└─────────────┘                      └────────┬─────────┘
       ↑                                      │
       │ clear / expire                        │ logout
       │                             ┌─────────▼─────────┐
       └──────────────────────────── │ Logged Out /       │
                                     │ Expired             │
                                     └─────────────────────┘
```

> **Burghound 특이점**: 로그아웃하지 않으면 1시간 계정 잠금(lockout).
> 따라서 모든 크롤 워크플로우는 반드시 `auth.logout`을 finally 노드로 포함해야 합니다.

---

## 1. Auth 카테고리

### 1.1 `auth.check-session`

세션이 유효한지 비파괴적으로 확인합니다 (branch 노드).

```jsonc
{
  "actionId": "auth.check-session",
  "site": "burghound",
  "category": "auth",
  "display": {
    "name": "Check Session",
    "description": "로그인 페이지 접속 후 login form 존재 여부로 세션 유효성 판정",
    "icon": "ShieldCheck"
  },
  "inputsSchema": {},
  "outputsSchema": {
    "type": "object",
    "properties": {
      "active": { "type": "boolean" },
      "meta": { "$ref": "#/resources/SessionMeta" }
    }
  },
  "requires": ["BrowserContext"],
  "provides": [],                            // 판정만, 리소스 생산 없음
  "branches": {
    "yes": "SessionActive(burghound) 확인됨 → 다음 노드",
    "no":  "세션 없음/만료 → error handle로 분기"
  },
  "idempotency": "safe",
  "sideEffects": ["session.meta.last_used_at 갱신 (touch)"],
  "failureModes": ["timeout", "network_error"],
  "implementation": {
    "backend": "BurghoundCrawler._is_logged_in()",
    "mechanism": "BASE_URL 접속 → input[type=password] 존재 여부 확인"
  }
}
```

### 1.2 `auth.login`

Playwright 기반 human-like 로그인.

```jsonc
{
  "actionId": "auth.login",
  "site": "burghound",
  "category": "auth",
  "display": {
    "name": "Login",
    "description": "이메일/비밀번호 입력 + human-like 딜레이로 Playwright 로그인",
    "icon": "LogIn"
  },
  "inputsSchema": {
    "type": "object",
    "properties": {
      "headless": { "type": "boolean", "default": true },
      "timeout": { "type": "integer", "default": 30, "description": "초 단위" },
      "force": { "type": "boolean", "default": false, "description": "기존 세션 무시하고 재로그인" }
    }
  },
  "outputsSchema": {
    "type": "object",
    "properties": {
      "success": { "type": "boolean" },
      "sessionMeta": { "$ref": "#/resources/SessionMeta" }
    }
  },
  "requires": ["Credential(burghound)", "BrowserContext"],
  "provides": ["SessionActive(burghound)", "StorageState(burghound)", "Persona(burghound)"],
  "idempotency": "safe",            // force=false면 이미 로그인 시 skip
  "sideEffects": [
    "storage_state/burghound/state.json 저장",
    "session.meta.json 갱신 (mark_login)",
    "screenshots/post_login.png 캡처 (디버그)"
  ],
  "failureModes": [
    "invalid_credentials",           // 이메일/비밀번호 틀림
    "account_locked",                // 이전 세션 미로그아웃 → 1시간 잠금
    "captcha",                       // (현재 미발견, 향후 대비)
    "timeout",                       // 네트워크/페이지 로딩 타임아웃
    "modal_block"                    // 쿠키배너/모달이 폼을 가림
  ],
  "implementation": {
    "backend": "BurghoundCrawler._login()",
    "steps": [
      "1. force=false이면 _is_logged_in() 선확인 → 이미 유효하면 touch() 후 return True",
      "2. BASE_URL 이동 → domcontentloaded 대기",
      "3. _dismiss_cookie_banner() → _dismiss_modals()",
      "4. email input 탐색 (4개 셀렉터 폴백) → human_type()",
      "5. password input 탐색 → human_type()",
      "6. Sign In 버튼 탐색 (3개 셀렉터 폴백) → human_click()",
      "7. networkidle 대기 (20s 타임아웃, 실패 시 3s sleep)",
      "8. _is_account_locked() 검사 → True면 mark_expired() + return False",
      "9. _has_login_error() 검사 → True면 return False",
      "10. password input 잔존 확인 → 여전히 로그인 페이지면 return False",
      "11. storage_state() 저장 → mark_login() → return True"
    ]
  }
}
```

### 1.3 `auth.logout`

명시적 로그아웃 (1시간 lockout 방지).

```jsonc
{
  "actionId": "auth.logout",
  "site": "burghound",
  "category": "auth",
  "display": {
    "name": "Logout",
    "description": "DATABASE LOGOUT 버튼 클릭으로 서버 세션 해제 (lockout 방지)",
    "icon": "LogOut"
  },
  "inputsSchema": {},
  "outputsSchema": {
    "type": "object",
    "properties": {
      "success": { "type": "boolean" }
    }
  },
  "requires": ["BrowserContext"],
  "provides": [],                            // 리소스 소멸 (SessionActive 해제)
  "consumes": ["SessionActive(burghound)"],  // 이 리소스를 "소비"(해제)함
  "idempotency": "safe",                     // 이미 로그아웃이면 True 반환
  "sideEffects": [
    "session.meta.json 갱신 (mark_logout)",
    "서버 세션 해제 → 계정 잠금 해소"
  ],
  "failureModes": ["logout_button_not_found", "timeout"],
  "constraints": {
    "CRITICAL": "Burghound는 로그아웃 없이 세션 종료 시 1시간 계정 잠금. 모든 워크플로우에 finally 노드로 포함 필수."
  },
  "implementation": {
    "backend": "BurghoundCrawler._logout()",
    "steps": [
      "1. BASE_URL 이동 → networkidle 대기",
      "2. 5개 logout 셀렉터 순차 탐색:",
      "   - a:has-text('DATABASE LOGOUT')",
      "   - a:has-text('LOGOUT')",
      "   - button:has-text('LOGOUT')",
      "   - a[href*='logout' i]",
      "   - :text('DATABASE LOGOUT')",
      "3. 찾으면 human_click() → networkidle 대기 → mark_logout()",
      "4. 못 찾으면 login form 존재 확인 → 있으면 '이미 로그아웃' 판정"
    ]
  }
}
```

### 1.4 `auth.paste-auth`

외부에서 복사한 쿠키/헤더/storage state를 주입.

```jsonc
{
  "actionId": "auth.paste-auth",
  "site": "burghound",
  "category": "auth",
  "display": {
    "name": "Paste Auth",
    "description": "쿠키/헤더/storage state를 주입하여 로그인 없이 세션 확보",
    "icon": "ClipboardPaste"
  },
  "inputsSchema": {
    "type": "object",
    "properties": {
      "mode": {
        "type": "string",
        "enum": ["cookies", "headers", "storage-state"],
        "default": "cookies"
      },
      "content": {
        "type": "string",
        "description": "주입할 쿠키 문자열 / 헤더 블록 / storage state JSON"
      }
    },
    "required": ["content"]
  },
  "outputsSchema": {
    "type": "object",
    "properties": {
      "success": { "type": "boolean" },
      "cookieCount": { "type": "integer" }
    }
  },
  "requires": ["BrowserContext"],
  "provides": ["SessionActive(burghound)"],
  "idempotency": "safe",
  "sideEffects": ["브라우저 쿠키 스토어 변경"],
  "failureModes": ["parse_error", "invalid_cookies", "session_expired"],
  "implementation": {
    "backend": "admin API → POST /api/request-kits/{site}/export (reverse)",
    "mechanism": "storage state JSON 파싱 → context.add_cookies() / storage_state 복원"
  }
}
```

### 1.5 `auth.refresh-session`

세션 TTL 갱신 + 유효성 확인.

```jsonc
{
  "actionId": "auth.refresh-session",
  "site": "burghound",
  "category": "auth",
  "display": {
    "name": "Refresh Session",
    "description": "세션 state 갱신 및 TTL 리셋",
    "icon": "RefreshCw"
  },
  "inputsSchema": {},
  "outputsSchema": {
    "type": "object",
    "properties": {
      "active": { "type": "boolean" },
      "ttlRemaining": { "type": "string" }
    }
  },
  "requires": ["SessionActive(burghound)", "BrowserContext"],
  "provides": ["SessionActive(burghound)"],  // TTL 갱신
  "idempotency": "safe",
  "sideEffects": [
    "session.meta.json 갱신 (touch)",
    "storage_state 재저장 가능"
  ],
  "failureModes": ["session_expired", "timeout"],
  "implementation": {
    "backend": "SessionManager.touch() + _is_logged_in() 검증",
    "mechanism": "BASE_URL 접속 → 로그인 상태 확인 → touch() → storage_state 재저장"
  }
}
```

---

## 2. Crawl 카테고리

### 2.1 `crawl.search`

검색/리스트 + 페이징.

```jsonc
{
  "actionId": "crawl.search",
  "site": "burghound",
  "category": "crawl",
  "display": {
    "name": "Search All",
    "description": "테이스팅 노트 검색 결과 추출 (페이징 포함)",
    "icon": "Search"
  },
  "inputsSchema": {
    "type": "object",
    "properties": {
      "limit": { "type": "integer", "default": 50, "minimum": 1, "maximum": 10000 },
      "ruleId": { "type": "string", "default": "r1", "description": "search-results 규칙 ID" },
      "headless": { "type": "boolean", "default": true },
      "followLinks": { "type": "boolean", "default": false, "description": "상세 페이지 자동 follow" },
      "query": { "type": "string", "description": "검색어 (비어있으면 전체)" }
    }
  },
  "outputsSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "producer": { "type": "string" },
            "wine": { "type": "string" },
            "vintage": { "type": "string" },
            "score": { "type": "string" },
            "detail_url": { "type": "string" }
          }
        }
      },
      "totalExtracted": { "type": "integer" },
      "pagesVisited": { "type": "integer" }
    }
  },
  "requires": ["SessionActive(burghound)", "CrawlRule(ruleId)"],
  "provides": ["Dataset(items)"],
  "idempotency": "read-only",
  "sideEffects": ["rate limit 소비"],
  "failureModes": ["session_expired", "rule_not_found", "selector_changed", "rate_limited", "timeout"],
  "constraints": {
    "rateLimit": "페이지 간 1.5~3s 딜레이 (throttle 설정에 따름)",
    "maxPages": "pagination.max_pages (default 100)"
  },
  "implementation": {
    "backend": "CrawlRule(r1) 기반 추출 (TODO: 구현 중)",
    "mechanism": "BASE_URL 이동 → 검색폼 입력 → results table 추출 → pagination click 반복",
    "ruleMapping": {
      "r1": "search-results v3 — table#results tbody tr 기반"
    }
  }
}
```

### 2.2 `crawl.detail`

개별 와인 상세 페이지 추출.

```jsonc
{
  "actionId": "crawl.detail",
  "site": "burghound",
  "category": "crawl",
  "display": {
    "name": "Wine Detail",
    "description": "개별 와인 테이스팅 노트 상세 페이지 추출",
    "icon": "FileText"
  },
  "inputsSchema": {
    "type": "object",
    "properties": {
      "ruleId": { "type": "string", "default": "r2", "description": "wine-detail 규칙 ID" },
      "headless": { "type": "boolean", "default": true },
      "concurrency": { "type": "integer", "default": 1, "minimum": 1, "maximum": 5 },
      "urls": {
        "type": "array",
        "items": { "type": "string" },
        "description": "upstream search에서 전달받은 detail_url 목록 (또는 수동 지정)"
      }
    }
  },
  "outputsSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "producer": { "type": "string" },
            "wine": { "type": "string" },
            "vintage": { "type": "string" },
            "score": { "type": "number" },
            "drinkWindow": { "type": "string" },
            "tastingNote": { "type": "string" },
            "reviewer": { "type": "string" },
            "reviewDate": { "type": "string" }
          }
        }
      },
      "totalExtracted": { "type": "integer" },
      "errors": { "type": "integer" }
    }
  },
  "requires": ["SessionActive(burghound)", "CrawlRule(ruleId)", "Dataset(items)?"],
  "provides": ["Dataset(items)"],
  "idempotency": "read-only",
  "sideEffects": ["rate limit 소비"],
  "failureModes": ["session_expired", "rule_not_found", "404_not_found", "selector_changed", "timeout"],
  "constraints": {
    "rateLimit": "요청 간 1.5~3s 딜레이",
    "concurrency": "동시 탭 수 제한 (default 1)"
  },
  "implementation": {
    "backend": "CrawlRule(r2) 기반 추출 (TODO: 구현 중)",
    "mechanism": "urls 목록 순회 → 각 URL 방문 → rule 기반 필드 추출 → merge into items",
    "ruleMapping": {
      "r2": "wine-detail v2"
    }
  }
}
```

### 2.3 `crawl.review`

리뷰/평점 추출 (Burghound에서는 tasting note가 곧 리뷰).

```jsonc
{
  "actionId": "crawl.review",
  "site": "burghound",
  "category": "crawl",
  "display": {
    "name": "Review Extract",
    "description": "테이스팅 노트 리뷰/평점 추출",
    "icon": "MessageSquare"
  },
  "inputsSchema": {
    "type": "object",
    "properties": {
      "limit": { "type": "integer", "default": 50 },
      "ruleId": { "type": "string", "description": "리뷰 추출 규칙 ID" }
    }
  },
  "outputsSchema": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "wine": { "type": "string" },
            "score": { "type": "number" },
            "tastingNote": { "type": "string" },
            "reviewer": { "type": "string" },
            "reviewDate": { "type": "string" }
          }
        }
      }
    }
  },
  "requires": ["SessionActive(burghound)", "CrawlRule(ruleId)"],
  "provides": ["Dataset(items)"],
  "idempotency": "read-only",
  "failureModes": ["session_expired", "rule_not_found", "timeout"],
  "implementation": {
    "backend": "CrawlRule 기반 추출 (TODO)",
    "note": "Burghound에서는 detail과 review가 같은 페이지. 별도 review 탭은 없으나, taxonomy 일관성을 위해 분리."
  }
}
```

### 2.4 `crawl.list`

테이블/리스트 페이지 추출.

```jsonc
{
  "actionId": "crawl.list",
  "site": "burghound",
  "category": "crawl",
  "display": {
    "name": "List Extract",
    "description": "리스트/테이블 페이지에서 아이템 추출",
    "icon": "List"
  },
  "inputsSchema": {
    "type": "object",
    "properties": {
      "limit": { "type": "integer", "default": 20 },
      "ruleId": { "type": "string" }
    }
  },
  "outputsSchema": {
    "type": "object",
    "properties": {
      "items": { "type": "array" },
      "totalExtracted": { "type": "integer" }
    }
  },
  "requires": ["SessionActive(burghound)", "CrawlRule(ruleId)"],
  "provides": ["Dataset(items)"],
  "idempotency": "read-only",
  "failureModes": ["session_expired", "rule_not_found", "timeout"],
  "implementation": {
    "backend": "CrawlRule 기반 추출 (TODO)",
    "note": "search와 유사하나 검색 폼 없이 특정 URL의 리스트 직접 추출"
  }
}
```

---

## 3. Export 카테고리

### 3.1 `export.export-curl`

```jsonc
{
  "actionId": "export.export-curl",
  "site": "burghound",
  "category": "export",
  "display": {
    "name": "Export cURL",
    "description": "인증된 cURL 스니펫 생성 (최소 헤더)",
    "icon": "Terminal"
  },
  "inputsSchema": {
    "type": "object",
    "properties": {
      "baseUrl": {
        "type": "string",
        "default": "https://www.burghound.com/tnsearch/tasting_notes.php"
      },
      "minimalHeaders": { "type": "boolean", "default": true }
    }
  },
  "outputsSchema": {
    "type": "object",
    "properties": {
      "snippet": { "type": "string", "description": "cURL 명령어" },
      "kitId": { "type": "string" },
      "expiresAt": { "type": "string" }
    }
  },
  "requires": ["SessionActive(burghound)"],
  "provides": ["RequestKit(burghound,curl)"],
  "idempotency": "safe",
  "sideEffects": ["DB에 request_kit 레코드 생성 (암호화 저장)"],
  "failureModes": ["session_expired", "no_cookies"],
  "implementation": {
    "backend": "POST /api/request-kits/burghound/export {format:'curl'}",
    "mechanism": "storage_state → 쿠키 추출 → 최소 헤더(UA, Accept, Cookie) 조합 → cURL 문자열 생성 → 암호화 저장"
  }
}
```

### 3.2 `export.export-httpx`

```jsonc
{
  "actionId": "export.export-httpx",
  "site": "burghound",
  "category": "export",
  "display": {
    "name": "Export httpx",
    "description": "인증된 Python httpx 스니펫 생성",
    "icon": "Send"
  },
  "inputsSchema": {
    "type": "object",
    "properties": {
      "baseUrl": {
        "type": "string",
        "default": "https://www.burghound.com/tnsearch/tasting_notes.php"
      }
    }
  },
  "outputsSchema": {
    "type": "object",
    "properties": {
      "snippet": { "type": "string" },
      "kitId": { "type": "string" }
    }
  },
  "requires": ["SessionActive(burghound)"],
  "provides": ["RequestKit(burghound,httpx)"],
  "idempotency": "safe",
  "sideEffects": ["DB에 request_kit 레코드 생성"],
  "failureModes": ["session_expired", "no_cookies"],
  "implementation": {
    "backend": "POST /api/request-kits/burghound/export {format:'httpx'}",
    "mechanism": "storage_state → cookies dict + headers dict → httpx.get() 코드 생성"
  }
}
```

### 3.3 `export.export-storage`

```jsonc
{
  "actionId": "export.export-storage",
  "site": "burghound",
  "category": "export",
  "display": {
    "name": "Export Storage State",
    "description": "Playwright storage state JSON 전체 내보내기",
    "icon": "FileJson"
  },
  "inputsSchema": {},
  "outputsSchema": {
    "type": "object",
    "properties": {
      "storageState": { "type": "object" },
      "kitId": { "type": "string" }
    }
  },
  "requires": ["SessionActive(burghound)", "StorageState(burghound)"],
  "provides": ["RequestKit(burghound,storage_state)"],
  "idempotency": "safe",
  "sideEffects": ["DB에 request_kit 레코드 생성"],
  "failureModes": ["state_file_missing", "session_expired"],
  "implementation": {
    "backend": "POST /api/request-kits/burghound/export {format:'storage_state'}",
    "mechanism": "storage_state/burghound/state.json 읽기 → 암호화 저장"
  }
}
```

---

## 4. Control 카테고리

### 4.1 `control.delay`

```jsonc
{
  "actionId": "control.delay",
  "site": "*",
  "category": "control",
  "display": { "name": "Delay", "description": "다음 노드 실행 전 대기", "icon": "Timer" },
  "inputsSchema": {
    "type": "object",
    "properties": {
      "seconds": { "type": "number", "default": 5 },
      "jitter": { "type": "number", "default": 2, "description": "±초 랜덤 편차" }
    }
  },
  "outputsSchema": {},
  "requires": [],
  "provides": [],
  "idempotency": "safe",
  "failureModes": []
}
```

### 4.2 `control.condition`

```jsonc
{
  "actionId": "control.condition",
  "site": "*",
  "category": "control",
  "display": { "name": "Condition", "description": "조건 분기 (yes→output, no→error)", "icon": "GitBranch" },
  "inputsSchema": {
    "type": "object",
    "properties": {
      "conditionType": {
        "type": "string",
        "enum": ["session-active", "items-gt", "status-ok"],
        "default": "session-active"
      },
      "value": { "type": "number", "default": 0 }
    }
  },
  "outputsSchema": {
    "type": "object",
    "properties": {
      "result": { "type": "boolean" }
    }
  },
  "requires": [],
  "provides": [],
  "branches": { "yes": "조건 참 → output", "no": "조건 거짓 → error handle" },
  "idempotency": "safe",
  "failureModes": []
}
```

---

## 5. Data 카테고리

### 5.1 `data.save-file`

```jsonc
{
  "actionId": "data.save-file",
  "site": "*",
  "category": "data",
  "display": { "name": "Save to File", "description": "추출 데이터를 JSON/CSV/JSONL로 저장", "icon": "Save" },
  "inputsSchema": {
    "type": "object",
    "properties": {
      "format": { "type": "string", "enum": ["json", "csv", "jsonl"], "default": "json" },
      "filename": { "type": "string", "default": "", "description": "비워두면 자동 생성" }
    }
  },
  "outputsSchema": {
    "type": "object",
    "properties": {
      "path": { "type": "string" },
      "itemCount": { "type": "integer" }
    }
  },
  "requires": ["Dataset(items)"],
  "provides": [],
  "idempotency": "safe",
  "sideEffects": ["파일 시스템 쓰기"],
  "failureModes": ["empty_dataset", "write_error"]
}
```

### 5.2 `data.notify`

```jsonc
{
  "actionId": "data.notify",
  "site": "*",
  "category": "data",
  "display": { "name": "Notify", "description": "알림 전송 (웹훅/로그)", "icon": "Bell" },
  "inputsSchema": {
    "type": "object",
    "properties": {
      "message": { "type": "string", "default": "Workflow completed" }
    }
  },
  "outputsSchema": {},
  "requires": [],
  "provides": [],
  "idempotency": "safe",
  "sideEffects": ["로그 기록 / 웹훅 호출"],
  "failureModes": ["webhook_error"]
}
```

---

## 6. 컴파일된 DAG 예시 — Burghound 골든패스

### 6.1 "Safe Session → Search → Detail → Save" (기본 크롤)

사용자 Intent: **"Burghound에서 와인 검색 후 상세까지 뽑아서 저장"**

컴파일러가 생성하는 DAG:

```
                    ┌─────────────────┐
                    │ check-session   │
                    │ (auth)          │
                    └──┬──────────┬───┘
                  yes  │          │  no (error)
                       │          │
                       │    ┌─────▼─────┐
                       │    │   login    │
                       │    │   (auth)   │
                       │    └─────┬──────┘
                       │          │
                       ▼          ▼
                    ┌─────────────────┐
                    │    search       │
                    │ ruleId=r1       │
                    │ limit=50        │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    detail       │
                    │ ruleId=r2       │
                    │ concurrency=1   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   save-file     │
                    │ format=json     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    logout       │  ← 컴파일러 자동 삽입 (Burghound 제약)
                    │   (finally)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    notify       │
                    │ "Crawl done"    │
                    └─────────────────┘
```

#### 컴파일러 자동 삽입 내역

| 삽입된 노드 | 이유 | 근거 |
|---|---|---|
| `check-session` | `search.requires: SessionActive(burghound)` → EnsureSessionActive 패턴 | RFC §6.2 |
| `login` (error branch) | `check-session.no` → 세션 없으면 로그인 필요 | `login.provides: SessionActive(burghound)` |
| `logout` (finally) | Burghound `constraints.CRITICAL` — 모든 워크플로우에 필수 | 사이트 제약 |

#### Workflow JSON (선언적, 저장/PR 가능)

```jsonc
{
  "workflowId": "burghound-search-detail-save",
  "site": "burghound",
  "version": 1,
  "intent": "search-detail-save",
  "nodes": [
    { "id": "n1", "action": "auth.check-session",   "config": {} },
    { "id": "n2", "action": "auth.login",            "config": { "headless": true, "timeout": 30 } },
    { "id": "n3", "action": "crawl.search",          "config": { "limit": 50, "ruleId": "r1", "followLinks": false } },
    { "id": "n4", "action": "crawl.detail",          "config": { "ruleId": "r2", "concurrency": 1 } },
    { "id": "n5", "action": "data.save-file",        "config": { "format": "json" } },
    { "id": "n6", "action": "auth.logout",           "config": {}, "finally": true },
    { "id": "n7", "action": "data.notify",           "config": { "message": "Burghound crawl completed" } }
  ],
  "edges": [
    { "from": "n1", "to": "n3", "handle": "output" },
    { "from": "n1", "to": "n2", "handle": "error" },
    { "from": "n2", "to": "n3", "handle": "output" },
    { "from": "n3", "to": "n4", "handle": "output" },
    { "from": "n4", "to": "n5", "handle": "output" },
    { "from": "n5", "to": "n6", "handle": "output" },
    { "from": "n6", "to": "n7", "handle": "output" }
  ],
  "finallyNodes": ["n6"],
  "compiledAt": "2026-02-09T00:00:00Z",
  "autoInserted": ["n1", "n2", "n6"]
}
```

### 6.2 "Quick Kit Export" (Request Kit 빠른 내보내기)

사용자 Intent: **"Burghound 인증 후 cURL 키트 생성"**

```
  check-session ─yes→ export-curl → logout → notify
       │ no
       ▼
     login ──────→ export-curl → logout → notify
```

### 6.3 "Review Pipeline"

```
  check-session ─yes→ search(limit=100) → review → save-file(jsonl) → logout
       │ no
       ▼
     login ──────→ search(limit=100) → review → save-file(jsonl) → logout
```

---

## 7. 사이트 확장 템플릿 — Vivino / Wine-Searcher 예시

Burghound 카탈로그와 동일한 구조로, 다른 사이트는 **requires/provides와 사이트 특화 제약만 변경**하면 됩니다.

### 7.1 Vivino 차이점

| 항목 | Burghound | Vivino |
|---|---|---|
| 로그인 방식 | Playwright form login | OAuth/소셜 로그인 가능 → `paste-auth` 주력 |
| 로그아웃 제약 | **필수** (1h lockout) | 불필요 (세션 timeout 방식) |
| 리뷰 | detail과 같은 페이지 | 별도 리뷰 탭 → `crawl.review` 실제 분리 |
| 추가 Action | — | `crawl.review` (ratingDistribution 포함) |
| CSRF | 없음 | 잠재적으로 존재 |

```jsonc
// Vivino 전용 리소스 (Burghound와 다른 부분만)
{
  "actionId": "auth.login",
  "site": "vivino",
  "requires": ["Credential(vivino)", "BrowserContext"],
  "provides": ["SessionActive(vivino)"],
  "constraints": {
    "note": "OAuth 리다이렉트 핸들링 필요. paste-auth가 더 안정적."
  }
}
```

### 7.2 Wine-Searcher 차이점

| 항목 | Burghound | Wine-Searcher |
|---|---|---|
| 로그인 | 필수 (유료 콘텐츠) | 일부 무료, Pro 회원 로그인 |
| 추가 Action | — | `crawl.list` (merchant-list) 활성 사용 |
| Rate Limit | 중간 | 엄격 (Cloudflare WAF) |
| CSRF | 없음 | Cloudflare 토큰 필요 가능 |

```jsonc
{
  "actionId": "crawl.list",
  "site": "wine-searcher",
  "display": { "name": "Merchant Offers", "description": "와인별 판매처/가격 목록 추출" },
  "requires": ["SessionActive(wine-searcher)", "CrawlRule(ruleId)"],
  "provides": ["Dataset(items)"],
  "constraints": {
    "rateLimit": "Cloudflare 감지 대비 3~5s 딜레이 권장",
    "note": "merchant-list는 Wine-Searcher 고유 Operation"
  }
}
```

---

## 8. NODE_DEFS 매핑 테이블

현재 UI의 `NODE_DEFS` (workflow-nodes.ts) → Action Catalog 매핑:

| UI Node Type | Action ID | requires (Burghound) | provides |
|---|---|---|---|
| `login` | `auth.login` | Credential, BrowserContext | SessionActive, StorageState, Persona |
| `logout` | `auth.logout` | BrowserContext | _(consumes SessionActive)_ |
| `paste-auth` | `auth.paste-auth` | BrowserContext | SessionActive |
| `refresh-session` | `auth.refresh-session` | SessionActive, BrowserContext | SessionActive (갱신) |
| `check-session` | `auth.check-session` | BrowserContext | _(branch만)_ |
| `search` | `crawl.search` | SessionActive, CrawlRule | Dataset |
| `detail` | `crawl.detail` | SessionActive, CrawlRule, Dataset? | Dataset |
| `review` | `crawl.review` | SessionActive, CrawlRule | Dataset |
| `list` | `crawl.list` | SessionActive, CrawlRule | Dataset |
| `export-curl` | `export.export-curl` | SessionActive | RequestKit(curl) |
| `export-httpx` | `export.export-httpx` | SessionActive | RequestKit(httpx) |
| `export-storage` | `export.export-storage` | SessionActive, StorageState | RequestKit(storage_state) |
| `delay` | `control.delay` | _(없음)_ | _(없음)_ |
| `condition` | `control.condition` | _(없음)_ | _(없음, branch)_ |
| `save-file` | `data.save-file` | Dataset | _(파일 출력)_ |
| `notify` | `data.notify` | _(없음)_ | _(없음)_ |

---

## 9. 다음 단계 (Phase B 진입 시)

1. **서버에 `/api/action-catalog` 구현**: 이 문서의 JSON 스키마를 그대로 반환
2. **UI에서 `NODE_DEFS`를 catalog에서 동적 로딩**: `configFields`를 `inputsSchema`에서 자동 생성
3. **`/api/workflows/compile` 구현**: intent + site → 이 문서의 §6 DAG를 생성
4. **`/api/workflows/validate` 구현**: requires/provides 그래프 검증
5. **Burghound `logout` 자동 삽입 규칙**: `constraints.CRITICAL` 조건 → finallyNodes에 자동 추가
