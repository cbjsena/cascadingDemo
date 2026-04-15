# 04. Key Patterns & Conventions — Cascading Opt Demo

> **목적**: 프로젝트에서 반복되는 코딩 패턴, 설정 규칙, 주요 의사결정을 빠르게 참조하기 위한 문서  
> **최종 갱신**: 2026-04-15

---

## 1. 아키텍처 패턴

### 1.1 Dual Table Strategy (Base ↔ Scenario)
- **원본 보존**: Base 테이블은 변경하지 않는다
- **시나리오 격리**: Scenario 테이블은 `scenario_id` FK로 분리
- **추상 모델**: `AbsXxx(models.Model)` 필드 정의 → `BaseXxx(AbsXxx)` + `Xxx(AbsXxx, ScenarioBaseModel)` 상속
- **복제**: `input_data/configs.py`의 `MODEL_MAPPING` 기반 bulk_create

### 1.2 뷰 팩토리 패턴
- `scenario_crud_view()`: 시나리오 기반 CRUD 자동 생성
- `master_crud_view()`: Master 데이터 CRUD 자동 생성
- 1개의 config 딕셔너리로 목록/추가/삭제/CSV/JSON 전체 흐름 자동화

### 1.3 서비스 레이어
- 뷰는 요청/응답만 처리, 비즈니스 로직은 `services/` 하위 클래스/함수에 위임
- 주요 서비스: `ProformaService`, `CascadingService`, `LongRangeService`, `ScenarioExportService`

### 1.4 비동기 처리 (Celery)
- **로컬**: `CELERY_TASK_ALWAYS_EAGER = True` (동기 실행, 브로커 불필요)
- **Docker**: Redis 기반 실제 비동기 실행
- Task 정의: `simulation/tasks.py`, `input_data/tasks.py`
- Celery 앱: `config/celery.py` (`app.autodiscover_tasks()`)

---

## 2. 데이터 Import/Export 패턴

### 2.1 CSV
- **매핑**: `common/csv_configs.py`의 3-tuple `(csv_header, orm_field, required)`
- **Export**: `export_csv(queryset, mapping, filename)` → HttpResponse
- **Import**: 파일 업로드 → row 파싱 → `Model.objects.create()` 또는 `bulk_create()`

### 2.2 JSON
- **매핑**: `common/json_configs.py`의 딕셔너리 (root_key, fields, children)
- **중첩 구조 지원**: Master-Detail 관계를 계층적으로 표현
- **Export**: `export_json(queryset, config, filename)` → HttpResponse
- **Import**: `parse_json_upload(file, config)` → rows 리스트

### 2.3 Excel
- **Proforma 전용**: `common/utils/excel_manager.py` + `common/excel_configs.py`
- **openpyxl 기반**: 템플릿 다운로드/업로드

### 2.4 Scenario Export (ZIP)
- **비동기**: Celery Task `export_scenario_task`
- **파일 경로**: `media/exports/scenarios/`
- **흐름**: JSON 생성 → ZIP 압축 → JSON 폴더 삭제 → ZIP URL 반환

---

## 3. 프론트엔드 패턴

### 3.1 템플릿 상속
```
base.html (사이드바 메뉴, Bootstrap 5)
  └── 각 앱 템플릿 ({% extends "base.html" %})
```

### 3.2 메뉴 시스템
- `common/context_processors.py`의 `global_menus()`가 모든 요청에 메뉴 구조 주입
- 뷰에서 `current_section`, `current_model` 전달 → 사이드바 active 표시
- `MenuSection`: CREATION, INPUT_MANAGEMENT, SIMULATION
- `MenuItem`: 각 메뉴 항목의 고유 키

### 3.3 DataTables (서버사이드)
- `_datatables_base.html`: 공통 DataTables 템플릿
- 페이징, 정렬, 검색 서버사이드 처리
- 20/50/100 ROW SELECT

### 3.4 실시간 모니터링 (Polling)
- `simulation_monitoring.html`에서 `setInterval`로 `/simulation/monitoring/data/` 주기적 호출
- JSON 응답으로 progress, status 갱신
- 취소 버튼: `POST /simulation/<pk>/cancel/` (AJAX)

---

## 4. 코딩 컨벤션

### 4.1 코드 포맷
- **Black**: line-length 88, Python 3.11 target
- **Ruff**: E, W, F, I, B, UP, C4 규칙 + isort 통합
- **Pre-commit**: Black + Ruff 자동 적용

### 4.2 Import 순서 (isort)
```
1. future
2. standard-library
3. django
4. third-party
5. first-party (config, common, input_data, api)
6. local-folder
```

### 4.3 네이밍 규칙
- **DB 테이블**: `base_*` (기준), `sce_*` (시나리오), `master_*` (마스터), `simulation_*`
- **코드 자동생성**: `SCYYYYMMDD_NNN` (시나리오), `SMYYYYMMDD_NNN` (시뮬레이션)
- **테스트 ID**: `{APP}_{MENU}_{TYPE}_{NNN}` (예: `IN_PRO_SVC_001`)
  - APP: IN(input_data), AP(api), CM(common), SM(simulation)
  - TYPE: DIS(화면), SVC(서비스), MDL(모델), CMD(커맨드), API, TSK(태스크)

### 4.4 인증
- 모든 뷰에 `@login_required` 적용
- `LOGIN_REDIRECT_URL = "/input/"`, `LOGOUT_REDIRECT_URL = "/accounts/login/"`

### 4.5 에러 처리
- FK 삭제 시 `ProtectedError` → 사용자 친화적 메시지
- 코드 자동생성 시 `IntegrityError` → 최대 10회 재시도
- Celery Task 실패 → `FAILED` 상태 + 에러 메시지 저장

---

## 5. Docker/Podman 운영 패턴

### 5.1 로컬 개발 (docker-compose.local.yml)
```yaml
services:
  db:      postgres:14 (port 5433:5432)
  redis:   redis:7-alpine
  web:     Dockerfile → local_entrypoint.sh → runserver --noreload (port 8000:8000)
  worker:  Dockerfile → worker_entrypoint.sh → celery worker
```
- `.env.local` 사용, `APP_ENV=local`
- 소스 코드 볼륨 마운트 (`.:/app`)
- `RUN_MIGRATIONS_ON_START=1`로 마이그레이션 자동 실행 가능

### 5.2 운영 배포 (docker-compose.yml)
```yaml
services:
  db:      postgres:14 (port 5433:5432)
  redis:   redis:7-alpine
  web:     Dockerfile → entrypoint.sh → gunicorn (expose 8000)
  worker:  celery worker (concurrency=2)
  nginx:   nginx:1.25-alpine (port 80, 443) + SSL certs
```
- `.env.docker` 사용, `APP_ENV=docker`
- Nginx 리버스 프록시 (static/media 직접 서빙)
- static_volume, media_volume 공유

### 5.3 Podman 주의사항
- `podman-compose -f docker-compose.local.yml up -d` (백그라운드 필수)
- `--noreload` 필수 (Podman에서 autoreload 부모 프로세스 종료 문제)
- `cleanup_local.ps1`로 강제 정리 가능 (컨테이너, Pod, 네트워크)
- `depends_on`은 시작 순서만 보장 → entrypoint에서 DB/Redis 준비 대기 로직 포함

---

## 6. 주요 설정값 참조

### settings.py 핵심 설정
| 설정 | 값 | 설명 |
|------|-----|------|
| `DATA_SOURCE_TYPE` | DB (기본) | 데이터 소스: DB 또는 API |
| `SIMULATION_ENGINE_API_URL` | (비어있으면 Mock) | 외부 엔진 URL |
| `CELERY_BROKER_URL` | redis://redis:6379/0 (Docker) / memory:// (Local) | Celery 브로커 |
| `LANGUAGE_CODE` | ko-kr | 한국어 |
| `TIME_ZONE` | UTC | 서버 시간대 |
| `PASSWORD_HASHERS` | MD5PasswordHasher | 테스트 속도 최적화용 (운영 시 변경 필요) |

### 환경변수 (주요)
| 변수 | 설명 |
|------|------|
| `APP_ENV` | local / docker |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | DB 연결 정보 |
| `REDIS_HOST` | Redis 호스트 |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Celery 연결 정보 |
| `SIMULATION_ENGINE_API_URL` | 외부 엔진 URL (비어있으면 Mock 사용) |
| `RUN_MIGRATIONS_ON_START` | 1이면 컨테이너 시작 시 migrate 실행 |

---

## 7. 현재 미구현/알려진 이슈

- Constraint 메뉴 (Fix Lane Vessel / Fix Vessel Schedule / Constraint Port) URL 연결 미완성
- JSON Import 중첩 구조(Master-Detail 동시 업로드)는 flat 레코드만 지원
- `ignore_conflicts=True` 사용 시 실제 insert 건수가 정확하지 않음
- 시뮬레이션 결과 분석/리포트 기능 미구현
- `PASSWORD_HASHERS`가 MD5로 설정됨 (운영 환경 배포 전 변경 필요)
- ETS & Fuel EU 관련 모델은 모두 주석 처리 상태 (향후 구현 예정)

