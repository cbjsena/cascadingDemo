# Release Notes — v0.2

**Release Date:** 2026-03-26  
**Tag:** `v0.2`  
**Previous Release:** `v0.1`  
**Commits since v0.1:** 58

---

## Summary

v0.2는 **Master 데이터 관리 CRUD 완성**, **CSV/JSON Import/Export 통합**, **DataTables 서버사이드 페이징 구현**, **Scenario Export (ZIP) 기능**, 그리고 **BaseDistance 모델 리팩토링**을 포함한 데이터 관리 기능 중심의 릴리즈입니다.

---

## 🆕 New Features

### 1. Master 데이터 관리 (공통 팩토리 패턴)
- **Trade / Port / Lane / Week Period** — `master_crud_view()` 팩토리 기반 CRUD 자동 생성
- **DataTables 서버사이드 통합** — 페이징, 정렬, 검색 기능 (20/50/100 ROW SELECT)
- **삭제 보호** — FK 참조 중인 Master 데이터 삭제 시 ProtectedError 처리 → 사용자 에러 메시지
- **Trade 모달** — From/To Continent `<select>` 드롭다운 (`CONTINENT_CODES` 상수 기반)
- **Port 모달** — Country Code 자동 생성 (Port Code 앞 2글자, readonly)
- **Week Period** — BaseWeekPeriod CRUD (year/week/month CharField 기반)

### 2. CSV Import/Export
- **Master CRUD 화면 CSV 지원** — Trade, Port, Lane, Week Period 데이터 다운로드/업로드
- **Cost 화면 CSV** — Canal Fee, Distance, TS Cost 데이터 Import/Export
- **Bunker 화면 CSV** — Bunker Consumption Sea/Port, Bunker Price 데이터 지원
- **Vessel 화면 CSV** — Vessel Info, Charter Cost 데이터 지원
- **UI 통합** — Export/Import 버튼 그룹 분리, 파일 선택 다이얼로그

### 3. JSON Import/Export
- **JSON 매핑 설정** — `common/json_configs.py` 중첩 구조(Master-Detail) 지원
- **Export/Import 모듈** — `common/export_manager.py` CSV/JSON 공통 직렬화
- **3-tuple 검증** — `(json_key, model_field, required)` 기반 필드 매핑
- **지원 화면** — Master (4) + Vessel (3) + Cost (3) + Bunker (3) = 총 13개 화면
- **UI 통합** — 버튼 클릭 시 파일 다운로드/업로드

### 4. Scenario Export (ZIP 기능)
- **Scenario 전체 내보내기** — Cascading Schedule 기반 모든 관련 데이터 ZIP 생성
- **Celery 비동기 처리** — 대용량 데이터 내보내기 백그라운드 실행
- **JSON/ZIP 엔드포인트** — API 기반 ZIP 파일 다운로드
- **테스트 시나리오** — Celery Task 통합 테스트

### 5. BaseDistance 모델 리팩토링
- **Scenario 의존성 제거** — ScenarioDistance → BaseDistance로 단순화
- **뷰 및 템플릿 업데이트** — Distance 관리 화면 리팩토링
- **테스트 업데이트** — Distance 테스트 시나리오 전면 개선

### 6. 데이터 로더 개선
- **tqdm 진행률 표시** — CSV 대량 로드 시 진행 상황 시각화
- **Batch 최적화** — bulk_create batch_size 튜닝 (FK 참조 최적화)
- **init_master_data 커맨드** — Master 데이터 전용 로더 추가

### 7. API 기능 확장
- **Distance API** — Port 간 거리/ECA 거리 조회
- **Proforma API** — Lane 필터 기반 Proforma 목록, 상세 조회
- **Vessel API** — 선박 목록(Capacity), 점유 확인, Lane 필터

### 8. UI/UX 개선
- **DataTables 기반 리스트** — 서버사이드 필터링/정렬/페이징
- **다이나믹 필터** — Vessel/Port Code, Trade/Lane 동적 검색
- **메뉴 구조 개선** — Creation 메뉴와 Input Management 메뉴 분리
- **컨텍스트 프로세서** — 메뉴 및 시나리오 정보 중앙 관리

---

## 🔧 Refactoring

### 뷰 팩토리 패턴 도입
- **scenario_crud_view()** — Scenario 기반 CRUD 자동 생성 (기존)
- **master_crud_view()** — Master 데이터 CRUD 자동 생성 (신규)
  - 1개 config 딕셔너리로 목록/추가/삭제/CSV/JSON 전체 흐름 자동화
  - Trade, Port, Lane, Week Period 적용
- **공통 템플릿** — `master_list_base.html` (DataTables 기반)

### 모델 변경
- **ProformaSchedule → Master + Detail 분리** — Detail에서 scenario FK 제거
- **BaseWeekPeriod** — year/week/month IntegerField → CharField 변경
- **BunkerConsumptionPort/Sea** — `base_year_month` 필드 제거
- **BaseDistance** — Scenario 의존성 제거 (Distance 단순화)
- **lane_code** — CharField → ForeignKey(MasterLane) 전환
- **effective_from_date / effective_to_date** — 필드명 통일
- **인덱스 추가** — BunkerConsumptionPort/Sea 모델에 성능 최적화

### 데이터 처리 최적화
- **FK 참조 최적화** — `select_related()` 일괄 적용, bulk_create `batch_size` 튜닝
- **tqdm 진행률 표시** — CSV 데이터 로드 시각화
- **FK 캐싱 메커니즘** — 데이터 로더에서 반복 조회 최소화

### 코드 품질 개선
- **메시지 상수화** — 하드코딩 문자열 → `common/messages.py` 중앙 집중
- **에러 처리 개선** — ProtectedError, ValidationError 사용자 친화적 메시지
- **메뉴 구조 개선** — Creation 메뉴와 Input Management 메뉴 분리
- **상수 관리** — `CONTINENT_CODES`, `SEA_SPEED_*` 추가
- **미사용 코드 제거** — 불필요한 변수/import 정리

---

## 🧪 Testing

### 테스트 현황
- **테스트 파일:** 23개
- **테스트 시나리오 (input_data):** 186개
- **테스트 시나리오 (api):** 13개
- **총 시나리오:** 199개

### 테스트 시나리오 ID 체계
- **4단계 표준 형식** 확립: `{APP}_{MENU}_{TYPE}_{NNN}`
- TYPE: `DIS`(화면), `SVC`(서비스), `MDL`(모델), `CMD`(커맨드), `API`
- APP 코드: `IN`(input_data), `AP`(api), `CM`(common)
- 명명 규칙 문서: `doc/test_scenarios/test_scenario_id_naming.md`

### 주요 테스트 범위
- Master CRUD (Trade/Port/Lane/Week Period) — 메뉴, 검색, 추가, 삭제, CSV/JSON
- Cost CRUD (Canal Fee/Distance/TS Cost) — 필터, 검색, 모달 저장, CSV/JSON
- Bunker CRUD (Sea/Port/Price) — DataTables, 필터, 저장
- Schedule (Proforma/Cascading/LPM/LRS) — 생성, 서비스 로직, 모델 무결성
- Vessel (Info/Charter/Capacity) — 추가, 삭제, 중복 체크
- API (Distance/Proforma/Vessel) — 정상/실패/비로그인 차단
- CSV/JSON Import/Export — 다운로드 구조, 업로드 저장, 에러 처리

---

## 📁 File Structure Changes

### 신규 파일 추가
| 파일 | 설명 |
|------|------|
| `common/export_manager.py` | CSV/JSON 공통 Export/Import 모듈 |
| `common/json_configs.py` | JSON 매핑 설정 (중첩 구조 지원) |
| `common/utils/date_utils.py` | 날짜 유틸리티 함수 |
| `common/utils/number_utils.py` | 숫자 유틸리티 함수 (안전 반올림) |
| `common/utils/_check_ids.py` | ID 검증 유틸리티 |
| `common/context_processors.py` | 컨텍스트 프로세서 (메뉴 및 시나리오) |
| `common/templates/components/csv_buttons.html` | CSV Export/Import 버튼 공통 컴포넌트 |
| `doc/test_scenarios/test_scenario_id_naming.md` | 테스트 시나리오 ID 명명 규칙 |
| `input_data/management/commands/_base_loader.py` | 기본 데이터 로더 공통 모듈 |
| `input_data/management/commands/init_master_data.py` | Master 데이터 초기화 커맨드 |
| `input_data/services/cascading_service.py` | Cascading Schedule 서비스 |
| `input_data/services/scenario_export_service.py` | Scenario Export (ZIP) 서비스 |
| `input_data/services/export_configs.py` | Export 설정 모듈 |
| `input_data/templates/input_data/_datatables_base.html` | DataTables 공통 템플릿 |
| `input_data/templates/input_data/master_list_base.html` | Master CRUD 공통 템플릿 |
| `config/celery.py` | Celery 비동기 작업 설정 |
| `input_data/tasks.py` | Scenario Export Celery Tasks |

### 주요 변경/삭제 파일
| 파일 | 변경 사항 |
|------|---------|
| `input_data/views.py` | → `input_data/views/master.py` (분리) |
| | → `input_data/views/cost.py` (분리) |
| | → `input_data/views/bunker.py` (분리) |
| | → `input_data/views/vessel.py` (분리) |
| | → `input_data/views/lane_proforma_mapping.py` (분리) |
| `common/csv_configs.py` | Master CSV 매핑 추가 |
| `common/json_configs.py` | 신규 JSON 매핑 설정 |
| `common/constants.py` | `CONTINENT_CODES`, `SEA_SPEED_*` 상수 추가 |
| `common/messages.py` | JSON/DELETE_PROTECTED 메시지 상수 추가 |
| `input_data/models.py` | 모델 리팩토링 (FK 전환, 필드 변경, 인덱스 추가) |
| `input_data/migrations/0001_initial.py` | 대규모 마이그레이션 (모델 변경 반영) |
| `doc/release_notes_v0.1.md` | v0.1 릴리즈 노트 추가 |
| `doc/release_notes_v0.3*.md` | v0.3 사전 작성 파일 (향후 참고용) |

---

## ⚠️ Breaking Changes

- `ProformaSchedule` 테이블이 Master/Detail로 분리됨 → 기존 데이터 마이그레이션 필요
- `BunkerConsumptionPort/Sea`에서 `base_year_month` 필드 제거
- `BaseWeekPeriod.year/week/month` IntegerField → CharField 변경
- `lane_code` CharField → ForeignKey(MasterLane) 전환 (기존 데이터 마이그레이션 필요)
- `effective_from_date / effective_to_date` 필드명 변경
- 테스트 시나리오 ID 전면 변경 (4단계 표준 형식)

---

## 📋 Known Issues

- Vessel Info는 커스텀 뷰 유지 (선택적 필드가 많아 공통 팩토리 부적합)
- JSON Import의 중첩 구조(children) 업로드는 flat 레코드만 지원 (향후 확장 예정)
- `ignore_conflicts=True` 사용 시 실제 insert 건수가 정확하지 않음

---

## 🔮 Next Steps (v0.3 예정)

- Constraint 메뉴 (Fix Lane Vessel / Fix Vessel Schedule / Constraint Port) 기능 구현
- 시뮬레이션 실행 앱 (`SIM`) 기반 설계
- JSON Import 중첩 구조(Master-Detail 동시 업로드) 지원
- 결과 분석/리포트 앱 (`RPT`) 기반 설계

