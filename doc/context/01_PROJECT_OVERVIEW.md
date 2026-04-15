# 01. Project Overview — Cascading Opt Demo

> **목적**: AI 어시스턴트가 프로젝트 전체를 빠르게 파악하기 위한 컨텍스트 문서  
> **최종 갱신**: 2026-04-15

---

## 1. 프로젝트 개요

**Cascading Opt**는 해운 물류의 **선박 배치 최적화(Vessel Cascading Optimization)** 시뮬레이션 데모 시스템이다.  
시나리오 기반으로 입력 데이터를 관리하고, 최적화 엔진(현재는 Mock)을 통해 시뮬레이션을 실행·모니터링한다.

### 핵심 기능 요약
| 영역 | 설명 |
|------|------|
| **Input Data** | 시나리오 생성, Base→Scenario 데이터 복제, Proforma/Cascading/LRS 생성, Master CRUD, CSV/JSON Import/Export |
| **Simulation** | 시뮬레이션 생성·실행(Celery 비동기), 가짜 엔진(60초, 6초×10단계), 실시간 모니터링(Polling), 중단(Cancel) |
| **API** | DRF 기반 REST API (Distance, Proforma, Vessel, Week 조회), Swagger 문서 자동 생성 |

---

## 2. 기술 스택

| 구분 | 기술 | 버전 |
|------|------|------|
| Language | Python | 3.11 |
| Framework | Django | 5.2.10 |
| Database | PostgreSQL | 14 |
| Task Queue | Celery + Redis 7 | Celery 5.6.2 |
| API | Django REST Framework | 3.16.1 |
| API Docs | drf-spectacular | 0.29.0 |
| Frontend | Bootstrap 5.3, Vanilla JS | - |
| Audit | django-simple-history | 3.11.0 |
| Testing | pytest + pytest-django + pytest-xdist | - |
| Lint/Format | Black + Ruff + Pre-commit | - |
| Container | Docker / Podman (podman-compose) | - |
| Web Server | Gunicorn (prod), runserver (local) | - |
| Reverse Proxy | Nginx 1.25 (prod only) | - |

---

## 3. Django 앱 구조

```
cascadingDemo/                  ← 프로젝트 루트
├── config/                     ← Django 설정 (settings, urls, celery, wsgi)
├── common/                     ← 공통 모듈 (모델 base, 메뉴, 상수, 유틸, Export 매니저)
├── input_data/                 ← 입력 데이터 관리 앱 (시나리오, 스케줄, 선박, 비용 등)
├── simulation/                 ← 시뮬레이션 실행/모니터링 앱
├── api/                        ← DRF REST API 앱
├── tests/                      ← 테스트 루트 (conftest + 앱별 하위 디렉토리)
├── scripts/                    ← 엔트리포인트 스크립트 (entrypoint, worker, cleanup)
├── doc/                        ← 문서 (릴리즈 노트, 가이드, 테스트 시나리오)
├── static/ / staticfiles/      ← 정적 파일
├── media/                      ← 업로드/Export 파일
└── sql/                        ← SQL 스크립트
```

### INSTALLED_APPS
```python
["django.contrib.admin", "django.contrib.auth", "rest_framework", "drf_spectacular",
 "simple_history", "common", "input_data", "simulation", "api"]
# DEBUG=True 시 "debug_toolbar" 추가
```

---

## 4. URL 라우팅 요약

| Prefix | App | 설명 |
|--------|-----|------|
| `/admin/` | Django Admin | 관리자 |
| `/accounts/` | django.contrib.auth | 로그인/로그아웃 |
| `/input/` | input_data | 입력 데이터 관리 (루트 `/` → 여기로 리다이렉트) |
| `/simulation/` | simulation | 시뮬레이션 실행/모니터링 |
| `/api/` | api | REST API + Swagger |

---

## 5. 환경 설정

### 환경 분리
- `APP_ENV=local` → `.env.local` 로드, Celery EAGER 모드(동기), runserver
- `APP_ENV=docker` → `.env.docker` 로드, Celery 비동기, Gunicorn + Nginx

### Docker Compose 파일
| 파일 | 용도 | 서비스 |
|------|------|--------|
| `docker-compose.yml` | **운영 배포** | db, redis, web(Gunicorn), worker, nginx |
| `docker-compose.local.yml` | **로컬 개발** | db, redis, web(runserver --noreload), worker |

### 로컬 개발 컨테이너 실행
```bash
podman-compose -f docker-compose.local.yml up -d    # 백그라운드 실행 (빌드 없이)
podman-compose -f docker-compose.local.yml up -d --build  # 빌드 후 실행
podman-compose -f docker-compose.local.yml down      # 중지
```
- DB 포트: 호스트 `5433` → 컨테이너 `5432`
- Web 포트: 호스트 `8000` → 컨테이너 `8000`
- cleanup: `scripts/cleanup_local.ps1` (Podman 리소스 강제 정리)

---

## 6. 릴리즈 이력

| 버전 | 날짜 | 핵심 내용 |
|------|------|-----------|
| v0.1 | 2026-02 | Dual Table 아키텍처, Proforma/LRS 기본 모듈, pytest 기반 테스트 |
| v0.2 | 2026-03-26 | Master CRUD, CSV/JSON Import/Export, DataTables, Scenario Export ZIP, BaseDistance 리팩토링 |
| v0.3 (현재) | 2026-04 | Simulation 앱 (생성·실행·모니터링·취소), 가짜 엔진, Celery 비동기, 실시간 Polling |

---

## 7. 테스트 구조

```
tests/
├── conftest.py          ← 공통 Fixture (Master 데이터, 시나리오, Proforma 등)
├── api/                 ← API 뷰 테스트
├── input_data/          ← input_data 모델/뷰/서비스/관리 커맨드 테스트
└── simulation/          ← Simulation 모델/뷰/태스크 테스트
```

**설정**: `pyproject.toml` → `[tool.pytest.ini_options]`
- `addopts = "--reuse-db --nomigrations --ff -n 4 -v"` (병렬 4 프로세스)
- `DJANGO_SETTINGS_MODULE = "config.settings"`

