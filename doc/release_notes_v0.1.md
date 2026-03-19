# 🚀 Release v0.1: Cascading Opt - Initial Base & LRS Module

**Cascading Opt** 시스템의 첫 번째 릴리즈입니다. 본 버전은 해운 물류 시나리오 시뮬레이션을 위한 데이터 아키텍처의 뼈대를 완성하고, 핵심 입력 모듈의 기반 및 UI 연동을 구축하는 데 집중했습니다.

## ✨ 주요 기능 (Key Features)

### 1. 시나리오 기반 데이터 아키텍처 (Dual Table Strategy)
* **Master & Scenario 분리:** Django `Abstract Base Class`를 활용하여 기준 데이터(`Base_`)와 시뮬레이션용 파생 데이터(`Sce_`)를 완벽히 분리했습니다.
* **Auto Initialization:** `post_migrate` 시그널을 통한 `init_base_data` 자동 적재 파이프라인을 구축하여 로컬/운영 환경의 초기 세팅을 자동화했습니다.

### 2. 반응형 UI/UX 및 비동기 프론트엔드 제어
* **Dynamic Grid UI:** Bootstrap 5 기반으로 엑셀 형태의 입력/수정 폼을 제공합니다.
* **Common API 모듈화 (`common_api.js`):** * 시나리오-노선-선박으로 이어지는 다단계 Select Box(Cascade) 비동기 제어.
  * UI 조작 중 백엔드 에러 발생 시 입력 데이터를 보존하고 화면을 복구하는 방어 로직(`restored_rows`) 탑재.
  * 실시간 선박 기간 점유 확인(Lane Check) API 연동.

### 3. 품질 관리 및 테스트 검증 (QA)
* **Pre-commit Hooks:** Black(포맷팅) 및 Ruff(린팅)를 적용하여 코드 컨벤션을 강제합니다.
* **Test Automation (`pytest`):** * LRS 도메인의 복잡한 비즈니스 로직(Service Layer)에 대한 유닛 테스트 완비.

### 4. Proforma 및 Long Range Schedule 데이터 관리
* 복잡한 해운 비즈니스 규칙(Virtual Port, 날짜 연속성 등)에 맞추어 **Proforma Schedule**과 **Long Range Schedule (LRS)** 데이터를 올바르게 생성하고, 이를 화면에서 효과적으로 검색 및 조회할 수 있는 핵심 기능을 개발 완료했습니다.

## 🛠 기술 스택 (Tech Stack)
* **Backend:** Python 3.11, Django 5.2
* **Database:** PostgreSQL 14
* **Frontend:** Bootstrap 5.3, Vanilla JavaScript (Fetch API)

## 🔜 다음 단계 (Next Steps)
**[v0.2] 확장 모델 UI 개발:** Cost & Distance, Bunker, Constraints 등 최적화에 필요한 나머지 기준 모델들에 대한 데이터 조회 및 관리 화면 개발.
* **[v0.3] 비동기 엔진 파이프라인 구축:** 가상의 수리최적화 엔진(Optimization Engine)과 연동하기 위한 Celery 및 Redis 기반의 비동기 워커 파이프라인 아키텍처 구현.
* **[v1.0] 결과 시뮬레이션 및 분석 대시보드:** 최적화 엔진이 도출한 플랜 결과(Result)에 대한 다각도 조회, 기존 시나리오와의 갭 분석(Gap Analysis) 및 시뮬레이션 비교 화면 개발.