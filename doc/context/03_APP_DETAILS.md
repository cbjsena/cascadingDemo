# 03. App Details — Input Data, Simulation, API, Common

> **목적**: 각 앱의 뷰, 서비스, 템플릿, URL 구조를 빠르게 이해하기 위한 컨텍스트 문서  
> **최종 갱신**: 2026-04-15

---

## 1. input_data 앱

### 1.1 역할
시나리오 기반 입력 데이터의 생성, 조회, 수정, 삭제 및 Import/Export를 담당한다.

### 1.2 뷰 구조 (`input_data/views/`)

| 파일 | 주요 뷰 함수 | 설명 |
|------|-------------|------|
| `dashboard.py` | `input_home` | 입력 데이터 대시보드 (홈) |
| `scenario.py` | `scenario_list`, `scenario_create`, `scenario_delete`, `scenario_dashboard`, `create_base_scenario_view`, `scenario_export_*` | 시나리오 CRUD + Export(ZIP) |
| `proforma.py` | `proforma_list`, `proforma_detail`, `proforma_create`, `proforma_upload`, `proforma_template_download` | Proforma 스케줄 생성/조회/업로드 |
| `cascading.py` | `cascading_create`, `cascading_vessel_create`, `cascading_schedule_list`, `cascading_vessel_info`, `cascading_vessel_detail` | Cascading 스케줄/선박 배치 |
| `lane_proforma.py` | `lane_proforma_mapping`, `lane_proforma_list` | Lane↔Proforma 매핑 |
| `long_range.py` | `long_range_list` | Long Range Schedule 조회 |
| `master.py` | `master_trade_list`, `master_port_list`, `master_lane_list`, `master_week_period_list` | Master 데이터 CRUD |
| `vessel.py` | `vessel_info_list`, `charter_cost_list`, `vessel_capacity_list` | 선박 데이터 CRUD |
| `cost.py` | `canal_fee_list`, `distance_list`, `ts_cost_list` | 비용 데이터 CRUD |
| `bunker.py` | `bunker_consumption_sea_list`, `bunker_consumption_port_list`, `bunker_price_list` | 벙커 데이터 CRUD |
| `common.py` | `input_list` | 동적 데이터 조회 (group/model 기반) |
| `_crud_base.py` | (팩토리 함수) | 공통 CRUD 뷰 생성 팩토리 |

### 1.3 서비스 레이어 (`input_data/services/`)

| 파일 | 설명 |
|------|------|
| `proforma_service.py` | Proforma 생성 비즈니스 로직 (ETB/ETD 계산, Virtual Port 등) |
| `cascading_service.py` | Cascading Schedule/Vessel Position 생성 로직 |
| `long_range_service.py` | LRS 생성 로직 (VVD 기반 기항지 스케줄) |
| `scenario_service.py` | 시나리오 생성 (Base→Sce 복제) |
| `scenario_export_service.py` | 시나리오 전체 JSON+ZIP Export |
| `common_service.py` | 공통 서비스 (거리 조회 등) |
| `export_configs.py` | Export 경로, 만료 시간 설정 |

### 1.4 설정 파일 (`input_data/configs.py`)

- `MODEL_MAPPING`: Base→Scenario 모델 15쌍 매핑
- `SCENARIO_CREATION_FILTERS`: 시나리오 생성 시 필터 조건

### 1.5 Celery Tasks (`input_data/tasks.py`)

| Task | 설명 |
|------|------|
| `export_scenario_task` | 시나리오 JSON+ZIP 비동기 Export (진행률 콜백) |
| `cleanup_expired_exports` | 만료된 Export 파일 정리 |

### 1.6 URL 패턴 (prefix: `/input/`)

```
/                                          → input_home (대시보드)
/scenario/list/                            → scenario_list
/scenarios/create/                         → scenario_create
/scenarios/delete/<id>/                    → scenario_delete
/scenarios/dashboard/<id>/                 → scenario_dashboard
/scenario/create-base/                     → create_base_scenario
/scenario/<id>/export/                     → scenario_export_request
/scenario/export/status/<task_id>/         → scenario_export_status
/scenario/<id>/export/download/            → scenario_export_download
/proforma/list/                            → proforma_list
/proforma/detail/                          → proforma_detail
/proforma/create/                          → proforma_create
/proforma/upload/                          → proforma_upload
/proforma/template/                        → proforma_template_download
/cascading/create/                         → cascading_vessel_create
/cascading/schedule/create/                → cascading_create
/cascading/schedule/                       → cascading_schedule_list
/cascading/vessel-info/                    → cascading_vessel_info
/cascading/detail/<scenario_id>/<proforma_id>/ → cascading_vessel_detail
/long_range/list/                          → long_range_list
/lane-proforma-mapping/                    → lane_proforma_mapping
/lane-proforma-list/                       → lane_proforma_list
/master/trade/                             → master_trade_list
/master/port/                              → master_port_list
/master/lane/                              → master_lane_list
/master/week-period/                       → master_week_period_list
/vessel/info/                              → vessel_info_list
/vessel/charter-cost/                      → charter_cost_list
/vessel/capacity/                          → vessel_capacity_list
/cost/canal-fee/                           → canal_fee_list
/cost/distance/                            → distance_list
/cost/ts-cost/                             → ts_cost_list
/bunker/consumption-sea/                   → bunker_consumption_sea_list
/bunker/consumption-port/                  → bunker_consumption_port_list
/bunker/price/                             → bunker_price_list
/<group_name>/<model_name>/                → input_list (동적)
```

### 1.7 템플릿 (29개)

`input_data/templates/input_data/` 하위:
- **대시보드/시나리오**: `input_home.html`, `scenario_list.html`, `scenario_dashboard.html`
- **스케줄**: `proforma_*.html`, `cascading_*.html`, `long_range_list.html`, `lane_proforma_mapping.html`
- **마스터**: `master_*_list.html`, `master_list_base.html` (공통 팩토리 템플릿)
- **데이터 테이블**: `_datatables_base.html`
- **기타**: `input_list.html`, `vessel_*_list.html`, `canal_fee_list.html`, `distance_list.html`, `ts_cost_list.html`, `bunker_*_list.html`

---

## 2. simulation 앱

### 2.1 역할
시뮬레이션 생성, 비동기 실행, 실시간 모니터링, 중단, 결과 조회를 담당한다.

### 2.2 뷰 (`simulation/views.py`)

| 뷰 함수 | HTTP | URL 이름 | 설명 |
|----------|------|----------|------|
| `simulation_list` | GET | `simulation_list` | 전체 시뮬레이션 목록 |
| `simulation_monitoring` | GET | `simulation_monitoring` | 진행 중 시뮬레이션 모니터링 화면 |
| `simulation_monitoring_data` | GET | `simulation_monitoring_data` | 진행 중 시뮬레이션 JSON (Polling용) |
| `simulation_create` | GET | `simulation_create` | 시뮬레이션 생성 폼 |
| `simulation_run` | POST | `simulation_run` | 시뮬레이션 실행 시작 |
| `simulation_cancel` | POST | `simulation_cancel` | 시뮬레이션 중단 (CANCELED 상태로 변경 + Celery revoke) |
| `simulation_detail` | GET | `simulation_detail` | 시뮬레이션 상세/결과 조회 |
| `simulation_delete` | POST | `simulation_delete` | 시뮬레이션 삭제 (can_modify 검증) |

### 2.3 모니터링 상태 필터
```python
MONITORING_STATUSES = [SNAPSHOTTING, SNAPSHOT_DONE, PENDING, RUNNING]
```
모니터링 화면과 Polling API에서 이 상태들만 조회한다.

### 2.4 Celery Task (`simulation/tasks.py`)

**`run_simulation_task(simulation_id)`**:
1. SimulationRun 조회 + CANCELED 사전 체크
2. 상태를 RUNNING으로 변경, progress=0
3. Mock 엔진 사용 여부 판단 (`_use_mock_engine()`)
   - `SIMULATION_ENGINE_API_URL` 미설정 → Mock 엔진
   - 설정됨 → 외부 API 호출
4. 성공 시 SUCCESS, 실패 시 FAILED, 취소 시 CANCELED
5. `MockEngineCanceledError` 예외 처리

### 2.5 가짜 엔진 (`simulation/engine.py`)

**`run_mock_engine(simulation)`**:
1. **데이터 수량 집계**: `_collect_scenario_data_counts()` → 16개 시나리오 데이터 모델의 레코드 수 집계
2. **진행률 갱신**: 6초 간격 × 10단계 = 60초에 100% 완료
3. **취소 감지**: 매 단계마다 `_ensure_not_canceled()` 호출 → DB에서 상태 확인
4. **결과 반환**: `objective_value=12345.67`, `execution_time`, `model_status`, `data_summary`

**상수**:
```python
STEP_INTERVAL_SEC = 6    # 각 단계 간격 (초)
STEP_INCREMENT = 10      # 단계당 진행률 증가분 (%)
TOTAL_STEPS = 10         # 총 단계 수
```

### 2.6 URL 패턴 (prefix: `/simulation/`)

```
/                          → simulation_list
/monitoring/               → simulation_monitoring
/monitoring/data/          → simulation_monitoring_data (JSON)
/create/                   → simulation_create
/run/                      → simulation_run (POST)
/<pk>/cancel/              → simulation_cancel (POST)
/<pk>/                     → simulation_detail
/<pk>/delete/              → simulation_delete (POST)
```

### 2.7 템플릿 (4개)

| 파일 | 설명 |
|------|------|
| `simulation_list.html` | 전체 시뮬레이션 목록 (테이블) |
| `simulation_monitoring.html` | 진행 중 시뮬레이션 실시간 모니터링 (Polling + 취소 버튼) |
| `simulation_create.html` | 시뮬레이션 생성 폼 (시나리오 선택, Solver, Algorithm) |
| `simulation_detail.html` | 시뮬레이션 상세 정보 + 결과 |

---

## 3. api 앱

### 3.1 역할
프론트엔드 Ajax 호출 및 외부 연동을 위한 REST API 제공.

### 3.2 URL 패턴 (prefix: `/api/`)

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/schema/` | OpenAPI 스키마 (drf-spectacular) |
| `GET /api/docs/` | Swagger UI |
| `GET /api/port/distance/` | 항구 간 거리/ECA거리 조회 |
| `GET /api/proforma/options/` | Cascade Select 옵션 (Scenario→Lane→Proforma) |
| `GET /api/proforma/info/` | Proforma 상세 정보 |
| `GET /api/vessel/list/` | 선박 목록 (Capacity 기반) |
| `GET /api/vessel/base/` | 기준 선박 목록 |
| `GET /api/vessel/options/` | 선박 옵션 목록 |
| `GET /api/vessel/lane/check/` | 선박-Lane 점유 확인 |
| `GET /api/week-info/` | 주차 정보 조회 |

---

## 4. common 앱

### 4.1 역할
프로젝트 전체에서 공유하는 모델 base, 메뉴, 상수, 유틸리티, Export/Import 모듈을 제공한다.

### 4.2 주요 파일

| 파일 | 설명 |
|------|------|
| `models.py` | `CommonModel` (추상 Audit 모델) |
| `menus.py` | `MenuSection`, `MenuGroup`, `MenuItem` 상수 + `MENU_STRUCTURE`, `CREATION_MENU_STRUCTURE`, `MASTER_MENU_STRUCTURE`, `SIMULATION_MENU_STRUCTURE` |
| `constants.py` | Proforma 기본값, Solver 선택지(`SIMULATION_SOLVER_CHOICES`), Excel/Bunker 상수, Continent/ServiceType 코드 |
| `messages.py` | 사용자 메시지 상수 |
| `context_processors.py` | `global_menus()` — 모든 템플릿에 메뉴 구조 자동 전달 |
| `csv_configs.py` | CSV Import/Export 매핑 (Proforma, Vessel, Cost, Bunker) |
| `json_configs.py` | JSON Import/Export 매핑 (중첩 구조 지원, Master-Detail) |
| `export_manager.py` | `export_csv()`, `export_json()`, `parse_json_upload()` — CSV/JSON 공통 직렬화 |
| `excel_configs.py` | Excel 파일 설정 |

### 4.3 유틸리티 (`common/utils/`)

| 파일 | 설명 |
|------|------|
| `csv_manager.py` | CSV 파일 읽기/쓰기 유틸리티 |
| `excel_manager.py` | Excel 파일(openpyxl) 읽기/쓰기 유틸리티 |
| `date_utils.py` | 날짜 관련 유틸리티 함수 |
| `number_utils.py` | 숫자 유틸리티 (안전 반올림 등) |
| `_check_ids.py` | ID 검증 유틸리티 |

### 4.4 템플릿 (`common/templates/`)

| 파일 | 설명 |
|------|------|
| `base.html` | 프로젝트 기본 레이아웃 (Bootstrap 5, 사이드바 메뉴) |
| `messages_display.html` | Django messages 출력 컴포넌트 |
| `components/` | 재사용 가능한 UI 컴포넌트 (CSV 버튼 등) |
| `registration/` | 로그인/로그아웃 페이지 |

### 4.5 메뉴 구조 (`common/menus.py`)

```
MENU_STRUCTURE (dict):
  Schedule: [Proforma, Lane Proforma Mapping, Cascading Schedule, Cascading Vessel Info, Long Range Schedule]
  Vessel: [Vessel Info, Charter Cost, Vessel Capacity]
  Cost: [Canal Fee, Distance, TS Cost]
  Bunker: [Bunker Consumption Sea, Bunker Consumption Port, Bunker Price]
  Constraint: [Fix Lane Vessel, Fix Vessel Schedule, Constraint Port]

CREATION_MENU_STRUCTURE (dict):
  Schedule: [Proforma Creation, Lane Proforma Mapping, Cascading Creation, Cascading Vessel Creation]

MASTER_MENU_STRUCTURE (list):
  [Trade Info, Port Info, Lane Info, Week Period]

SIMULATION_MENU_STRUCTURE (list):
  [Simulation List, Create Simulation]
```

### 4.6 Solver 선택지 (`SIMULATION_SOLVER_CHOICES`)

| Algorithm Type | Solver Options |
|---------------|----------------|
| EXACT (MIP) | cplex, gurobi, xpress, ortools |
| EFFICIENT (Metaheuristic) | meta_default, meta_fast |
| FAST (Greedy) | greedy_rules, greedy_fast |

---

## 5. 스크립트 (`scripts/`)

| 파일 | 설명 |
|------|------|
| `entrypoint.sh` | 운영 배포: migrate → collectstatic → gunicorn 실행 |
| `local_entrypoint.sh` | 로컬 개발: DB/Redis 대기 → (선택) migrate → runserver --noreload |
| `worker_entrypoint.sh` | Celery Worker: DB/Redis 대기 → celery worker 실행 |
| `cleanup_local.ps1` | Podman 로컬 리소스 강제 정리 (컨테이너, Pod, 네트워크) |

