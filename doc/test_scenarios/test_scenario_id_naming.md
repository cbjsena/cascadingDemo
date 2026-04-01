# 테스트 시나리오 ID 명명 규칙 (v2)

---

## 1. 형식

```
{APP}_{MENU}_{TYPE}_{NNN}
```

| 세그먼트 | 필수 | 설명 | 예시 |
|---------|------|------|------|
| **APP** | ✅ | Django 앱 식별자 (2~3자) | `IN`, `SIM`, `RPT` |
| **MENU** | ✅ | 메뉴/모듈 식별자 (2~4자) | `PF`, `CV`, `MTR` |
| **TYPE** | ✅ | 테스트 계층 | `DIS`, `SVC`, `MDL`, `CMD`, `API` |
| **NNN** | ✅ | 3자리 일련번호 | `001`, `002`, ... |

> 화면 CRUD 테스트: `IN_PF_DIS_001`
> 비화면 테스트: `IN_PF_SVC_001`, `IN_SCE_MDL_001`

---

## 2. APP 코드표

| APP | Django 앱 | 설명 | 상태 |
|-----|----------|------|------|
| `IN` | `input_data` | 데이터 입력/관리 | 현재 |
| `AP` | `api` | 내부 데이터 통신 API | 현재 |
| `CM` | `common` | 공통 인프라 (DB Doc, Auth 등) | 현재 |
| `SIM` | `simulation` | 시뮬레이션 실행 | 현재 |
| `RPT` | (미정) | 결과 분석/리포트 (Phase 5) | 예정 |

---

## 3. MENU 코드표

### AP (api) — 내부 데이터 통신 API
| MENU | 대상 | 비고 |
|------|------|------|
| `DST` | Distance API | 포트 간 거리 조회 |
| `PF` | Proforma API | Lane/PF 목록, 상세 조회 |
| `VSL` | Vessel API | 선박 목록, 점유 확인, 옵션 |
| `BVL` | Base Vessel API | BaseVesselInfo 마스터 목록 |

### SIM (simulation) — 시뮬레이션 실행
| MENU | 대상 | 비고 |
|------|------|------|
| `RUN` | Simulation Run | 목록 / 생성 / 실행 / 상세 / 삭제 |
| `TSK` | Simulation Task | Celery 비동기 실행 로직 (엔진 호출) |

### CM (common) — 공통 인프라
| MENU | 대상 | 비고 |
|------|------|------|
| `DOC` | DB Comment / Table Definition | CLI + Signal |
| `AUTH` | 인증 / 접근 제어 | |

### IN (input_data) — 데이터 입력/관리

#### Dashboard & Scenario
| MENU | 대상 | 비고 |
|------|------|------|
| `DASH` | Dashboard | 홈 화면 |
| `SCE` | Scenario | List / Create / Delete / Clone |

#### Master 그룹
| MENU | 대상 | 비고 |
|------|------|------|
| `MST` | Master 공통 | 메뉴 구조, CSV 공통 |
| `MTR` | Trade Info | |
| `MPT` | Port Info | |
| `MLN` | Lane Info | |
| `MWP` | Week Period | |

#### Schedule 그룹
| MENU | 대상 | 비고 |
|------|------|------|
| `PF` | Proforma Schedule | Creation + 조회 통합 |
| `LPM` | Lane Proforma Mapping | 편집 + 조회 통합 |
| `CS` | Cascading Schedule | CascadingSchedule (슬롯) |
| `CV` | Cascading Vessel | CascadingVesselPosition (선박) |
| `LRS` | Long Range Schedule | |

#### Vessel 그룹
| MENU | 대상 | 비고 |
|------|------|------|
| `VI` | Vessel Info | |
| `CC` | Charter Cost | |
| `VC` | Vessel Capacity | |

#### Cost 그룹
| MENU | 대상 | 비고 |
|------|------|------|
| `CF` | Canal Fee | |
| `DST` | Distance | |
| `TSC` | TS Cost | |

#### Bunker 그룹
| MENU | 대상 | 비고 |
|------|------|------|
| `BCS` | Bunker Consumption Sea | |
| `BCP` | Bunker Consumption Port | |
| `BP` | Bunker Price | |

#### 공통
| MENU | 대상 | 비고 |
|------|------|------|
| `CSV` | CSV Import/Export | 시나리오 기반 CSV 공통 |

---

## 4. TYPE 키워드

| TYPE | 의미 | 사용 시점 |
|------|------|----------|
| `DIS` | Display (화면) | 목록, 필터, 추가, 삭제, 검색 등 화면 CRUD |
| `SVC` | Service | 비즈니스 로직 (서비스 계층) |
| `MDL` | Model | DB 모델 (FK, Unique, Cascade) |
| `CMD` | Command | Management Command (CLI) |
| `API` | API | AJAX 엔드포인트 |

---

## 5. 전체 매핑표 (현재 → 신규)

### CM (common)
| 현재 ID | 신규 ID | 기능명 |
|---------|---------|--------|
| `TEST_DOC_01` | `CM_DOC_DIS_001` | DB 코멘트 (PostgreSQL) |
| `TEST_DOC_02` | `CM_DOC_DIS_002` | DB 코멘트 (SQLite 스킵) |
| `TEST_DOC_03` | `CM_DOC_DIS_003` | 정의서 생성 (PostgreSQL) |
| `TEST_DOC_04` | `CM_DOC_DIS_004` | 정의서 생성 (Non-PG 스킵) |
| `TEST_DOC_05` | `CM_DOC_DIS_005` | 정의서 생성 (빈 데이터) |
| `INPUT_ACCESS_001` | `CM_AUTH_DIS_001` | 비로그인 사용자 접근 차단 |

### IN — Dashboard & Scenario
| 현재 ID | 신규 ID | 기능명 |
|---------|---------|--------|
| `DASHBOARD_001` | `IN_DASH_DIS_001` | Dashboard Context |
| `DASHBOARD_002` | `IN_DASH_DIS_002` | Dashboard Rendering |
| `SCE_DASHBOARD_LINK_001` | `IN_DASH_DIS_003` | Dashboard Proforma 링크 검증 |
| `INPUT_SCENARIO_LIST_001` | `IN_SCE_DIS_001` | 시나리오 목록 조회 |
| `INPUT_SCENARIO_CREATE_001` | `IN_SCE_DIS_002` | 신규 시나리오 생성 |
| `INPUT_SCENARIO_CREATE_002` | `IN_SCE_DIS_003` | code 자동 증분 생성 |
| `INPUT_SCENARIO_CLONE_001` | `IN_SCE_DIS_004` | 시나리오 복제 |
| `INPUT_SCENARIO_DELETE_001` | `IN_SCE_DIS_005` | 시나리오 삭제 (성공) |
| `INPUT_SCENARIO_DELETE_002` | `IN_SCE_DIS_006` | 타인 시나리오 삭제 (권한 없음) |
| `INPUT_SCENARIO_DELETE_003` | `IN_SCE_DIS_007` | 관리자 삭제 (성공) |
| `MODEL_SCE_001` | `IN_SCE_MDL_001` | Scenario 모델 Default |
| `MODEL_SCE_002` | `IN_SCE_MDL_002` | Scenario Cascade Delete |
| `SCE_SVC_001` | `IN_SCE_SVC_001` | 시나리오 기본 생성 (일반 테이블) |
| `SCE_SVC_002` | `IN_SCE_SVC_002` | 기존 시나리오 덮어쓰기 |
| `SCE_SVC_003` | `IN_SCE_SVC_003` | 시스템 유저 자동 할당 |
| `SCE_SVC_004` | `IN_SCE_SVC_004` | Proforma Master-Detail 분리 |
| `SCE_SVC_005` | `IN_SCE_SVC_005` | Cascading Vessel Position 생성 |
| `SCE_SVC_006` | `IN_SCE_SVC_006` | Cascading Schedule Base 복사 |
| `SCE_FILTER_001` | `IN_SCE_SVC_007` | VesselInfo V### 필터 |
| `SCE_FILTER_002` | `IN_SCE_SVC_008` | VesselCapacity V### 필터 |
| `CMD_INIT_001` | `IN_SCE_CMD_001` | BaseDataLoader 정상 로드 |
| `CMD_INIT_002` | `IN_SCE_CMD_002` | 빈 값 처리 |
| `CMD_INIT_003` | `IN_SCE_CMD_003` | 날짜 포맷 호환성 |
| `CMD_INIT_004` | `IN_SCE_CMD_004` | 잘못된 데이터 행 처리 |
| `CMD_INIT_005` | `IN_SCE_CMD_005` | 파일 없음 처리 |
| `CMD_INIT_BASE_001` | `IN_SCE_CMD_006` | init_base_data (분리) |
| `CMD_INIT_BASE_002` | `IN_SCE_CMD_007` | init_base_data (상속) |
| `CMD_INIT_MASTER_001` | `IN_MST_CMD_001` | init_master_data 프롬프트 |
| `CMD_INIT_MASTER_002` | `IN_MST_CMD_002` | init_master_data --force |
| `CMD_INIT_MASTER_003` | `IN_MST_CMD_003` | init_master_data 삭제 순서 |
| `CMD_INIT_MASTER_004` | `IN_MST_CMD_004` | init_master_data 후 연계 |

### IN — Master 그룹
| 현재 ID | 신규 ID | 기능명 |
|---------|---------|--------|
| `MASTER_TRADE_001` | `IN_MTR_DIS_001` | Trade 목록 조회 |
| `MASTER_TRADE_002` | `IN_MTR_DIS_002` | Trade AJAX 검색 |
| `MASTER_TRADE_003` | `IN_MTR_DIS_003` | Trade 추가 |
| `MASTER_TRADE_004` | `IN_MTR_DIS_004` | Trade 삭제 |
| `MASTER_TRADE_005` | `IN_MTR_DIS_005` | Trade FK 참조 시 삭제 불가 |
| `MASTER_PORT_001` | `IN_MPT_DIS_001` | Port 목록 조회 |
| `MASTER_PORT_002` | `IN_MPT_DIS_002` | Port Continent 필터 |
| `MASTER_PORT_003` | `IN_MPT_DIS_003` | Port 추가 |
| `MASTER_LANE_001` | `IN_MLN_DIS_001` | Lane 목록 조회 |
| `MASTER_LANE_002` | `IN_MLN_DIS_002` | Lane AJAX 검색 |
| `MASTER_LANE_003` | `IN_MLN_DIS_003` | Lane 추가 |
| `MASTER_WEEK_PERIOD_001` | `IN_MWP_DIS_001` | Week Period 목록 조회 |
| `MASTER_WEEK_PERIOD_002` | `IN_MWP_DIS_002` | Week Period AJAX 검색 |
| `MASTER_WEEK_PERIOD_003` | `IN_MWP_DIS_003` | Week Period 추가 |
| `MASTER_MENU_001` | `IN_MST_DIS_001` | Master 메뉴 사이드바 |
| `MASTER_MENU_002` | `IN_MST_DIS_002` | Master Context 구조 |
| `MASTER_MENU_003` | `IN_MST_DIS_003` | Week Period 메뉴 링크 |
| `MASTER_CSV_001` | `IN_MST_DIS_004` | Master CSV 다운로드 |
| `MASTER_CSV_002` | `IN_MST_DIS_005` | Master CSV 업로드 |
| `MASTER_CSV_003` | `IN_MST_DIS_006` | Master CSV 파일 미선택 |

### IN — Schedule 그룹 (Proforma)
| 현재 ID | 신규 ID | 기능명 |
|---------|---------|--------|
| `PF_LIST_001` | `IN_PF_DIS_001` | 목록 조회 |
| `PF_LIST_002` | `IN_PF_DIS_002` | 목록 검색 |
| `PF_DETAIL_001` | `IN_PF_DIS_003` | 상세 조회 |
| `PF_CREATE_001` | `IN_PF_DIS_004` | 생성 화면 진입 |
| `PF_CREATE_002` | `IN_PF_DIS_005` | 수정 진입 |
| `PF_GRID_001` | `IN_PF_DIS_006` | 행 추가 |
| `PF_GRID_002` | `IN_PF_DIS_007` | 행 삽입 |
| `PF_GRID_003` | `IN_PF_DIS_008` | 행 삭제 |
| `PF_GRID_004` | `IN_PF_DIS_009` | 초기화 |
| `PF_CALC_001` | `IN_PF_DIS_010` | 거리 연동 |
| `PF_CALC_002` | `IN_PF_DIS_011` | 역산 로직 |
| `PF_LOGIC_001` | `IN_PF_DIS_012` | ETB 우선순위 |
| `PF_LOGIC_002` | `IN_PF_DIS_013` | 자동 보정 |
| `PF_SAVE_001` | `IN_PF_DIS_014` | 저장 |
| `PF_FILE_001` | `IN_PF_DIS_015` | 엑셀 다운 |
| `PF_FILE_002` | `IN_PF_DIS_016` | CSV 다운 |
| `PF_FILE_003` | `IN_PF_DIS_017` | 엑셀 업로드 |
| `PF_FILE_004` | `IN_PF_DIS_018` | 템플릿 다운 |
| `PF_FILE_CALC_001` | `IN_PF_DIS_019` | 대량 계산 정합성 |
| `PF_LIST_DETAIL_LINK_001` | `IN_PF_DIS_020` | Detail 링크 검증 |
| `PF_DETAIL_INVALID_001` | `IN_PF_DIS_021` | 파라미터 누락 처리 |
| `MODEL_PF_001` | `IN_PF_MDL_001` | Proforma Master-Detail FK |
| `MODEL_PF_002` | `IN_PF_MDL_002` | Proforma Master Unique |
| `MODEL_PF_003` | `IN_PF_MDL_003` | Proforma Detail Unique |

### IN — Schedule 그룹 (LPM, CS, CV, LRS)
| 현재 ID | 신규 ID | 기능명 |
|---------|---------|--------|
| `LPM_VIEW_001` | `IN_LPM_DIS_001` | 편집 화면 초기 진입 |
| `LPM_VIEW_002` | `IN_LPM_DIS_002` | 시나리오 선택 |
| `LPM_VIEW_003` | `IN_LPM_DIS_003` | 기존 매핑 체크 상태 |
| `LPM_VIEW_004` | `IN_LPM_DIS_004` | 겹침 구간 처리 |
| `LPM_ACT_001` | `IN_LPM_DIS_005` | 저장 |
| `LPM_ACT_002` | `IN_LPM_DIS_006` | 수정 (덮어쓰기) |
| `LPM_ACT_003` | `IN_LPM_DIS_007` | 전체 해제 |
| `LPM_LIST_001` | `IN_LPM_DIS_008` | 조회 화면 |
| `LPM_LIST_002` | `IN_LPM_DIS_009` | 초기 진입 |
| `CS_CREATE_001` | `IN_CS_DIS_001` | 생성 초기 진입 |
| `CS_CREATE_002` | `IN_CS_DIS_002` | 슬롯 저장 |
| `CS_CREATE_003` | `IN_CS_DIS_003` | 수정 (덮어쓰기) |
| `CS_LIST_001` | `IN_CS_DIS_004` | 목록 조회 |
| `MODEL_CS_001` | `IN_CS_MDL_001` | CascadingSchedule 생성 |
| `MODEL_CS_002` | `IN_CS_MDL_002` | CascadingSchedule Unique |
| `MODEL_CS_003` | `IN_CS_MDL_003` | CascadingSchedule Cascade Delete |
| `CASCADING_VIEW_001` | `IN_CV_DIS_001` | Vessel Creation 초기 진입 |
| `CASCADING_VIEW_002` | `IN_CV_DIS_002` | Load Info API |
| `CASCADING_VIEW_003` | `IN_CV_DIS_003` | Edit 모드 Load |
| `CASCADING_ACT_001` | `IN_CV_DIS_004` | Save (생성) |
| `CASCADING_ACT_002` | `IN_CV_DIS_005` | Save (수정) |
| `CASCADING_ACT_003` | `IN_CV_DIS_006` | Create LRS |
| `CASCADING_ACT_004` | `IN_CV_DIS_007` | Validation - Own Vessels |
| `CASCADING_ACT_005` | `IN_CV_DIS_008` | Save 후 Position 확인 |
| `CASCADING_ACT_006` | `IN_CV_DIS_009` | 에러 시 데이터 복구 |
| `CASCADING_VESSEL_INFO_001` | `IN_CV_DIS_010` | Vessel Info 조회 |
| `CASCADING_DETAIL_001` | `IN_CV_DIS_011` | Detail 조회 |
| `CASCADING_DETAIL_002` | `IN_CV_DIS_012` | Edit 모드 전환 |
| `CASCADING_DETAIL_003` | `IN_CV_DIS_013` | Edit 링크 lane 검증 |
| `CASCADING_EXISTING_001` | `IN_CV_DIS_014` | 기존 데이터 존재 알림 |
| `CASCADING_API_001` | `IN_CV_API_001` | 선박 선택 UI 연동 |
| `CASCADING_SVC_001` | `IN_CV_SVC_001` | 서비스 로직 |
| `CASCADING_SVC_002` | `IN_CV_SVC_002` | vessel_position 복사 |
| `MODEL_CVP_001` | `IN_CV_MDL_001` | Position 생성 |
| `MODEL_CVP_002` | `IN_CV_MDL_002` | Position 조회 |
| `MODEL_CVP_003` | `IN_CV_MDL_003` | Position Unique |
| `MODEL_CVP_004` | `IN_CV_MDL_004` | Position Cascade Delete |
| `LRS_LIST_001` | `IN_LRS_DIS_001` | 목록 조회 및 필터 |
| `LRS_LIST_002` | `IN_LRS_DIS_002` | Edit 버튼 노출 |
| `LRS_LIST_003` | `IN_LRS_DIS_003` | 목록 검색 (결과 없음) |
| `LRS_SVC_001` | `IN_LRS_SVC_001` | 기본 생성 |
| `LRS_SVC_002` | `IN_LRS_SVC_002` | Validation (Duration 0) |
| `LRS_SVC_HEAD_Y` | `IN_LRS_SVC_003` | 가상포트 (Head) |
| `LRS_SVC_TAIL_Y` | `IN_LRS_SVC_004` | 가상포트 (Tail) |
| `LRS_SVC_DATE` | `IN_LRS_SVC_005` | 날짜 연속성 |
| `LRS_SVC_DUP` | `IN_LRS_SVC_006` | 중복 방지 |
| `LRS_SVC_MID_Y` | `IN_LRS_SVC_007` | 가상 포트 (Middle Y) |

### IN — Vessel 그룹
| 현재 ID | 신규 ID | 기능명 |
|---------|---------|--------|
| `VESSEL_INFO_001` | `IN_VI_DIS_001` | 목록 조회 |
| `VESSEL_INFO_002` | `IN_VI_DIS_002` | 시나리오 필터 |
| `VESSEL_INFO_003` | `IN_VI_DIS_003` | 검색 |
| `VESSEL_INFO_004` | `IN_VI_DIS_004` | Add Row 저장 |
| `VESSEL_INFO_005` | `IN_VI_DIS_005` | Delete |
| `VESSEL_INFO_006` | `IN_VI_DIS_006` | 시나리오 미선택 Add Row 거부 |
| `VESSEL_INFO_007` | `IN_VI_DIS_007` | 중복 vessel_code 방지 |
| `VESSEL_INFO_008` | `IN_VI_DIS_008` | 전체 필드 모달 저장 |
| `VESSEL_ONCHANGE_001` | `IN_VI_DIS_009` | Scenario onchange submit |
| `CHARTER_COST_001` | `IN_CC_DIS_001` | 목록 조회 |
| `CHARTER_COST_002` | `IN_CC_DIS_002` | 시나리오 필터 |
| `CHARTER_COST_003` | `IN_CC_DIS_003` | Add Row 저장 |
| `VESSEL_CAP_001` | `IN_VC_DIS_001` | 목록 조회 |
| `VESSEL_CAP_002` | `IN_VC_DIS_002` | 시나리오 필터 + 검색 |
| `VESSEL_CAP_003` | `IN_VC_DIS_003` | Add Row 저장 |

### IN — Cost 그룹
| 현재 ID | 신규 ID | 기능명 |
|---------|---------|--------|
| `CANAL_FEE_001` | `IN_CF_DIS_001` | 목록 조회 |
| `CANAL_FEE_002` | `IN_CF_DIS_002` | 시나리오 필터 |
| `CANAL_FEE_003` | `IN_CF_DIS_003` | 검색 필터링 |
| `CANAL_FEE_004` | `IN_CF_DIS_004` | 모달 추가 저장 |
| `CANAL_FEE_005` | `IN_CF_DIS_005` | 삭제 |
| `DISTANCE_001` | `IN_DST_DIS_001` | 목록 조회 |
| `DISTANCE_002` | `IN_DST_DIS_002` | 시나리오 필터 |
| `DISTANCE_003` | `IN_DST_DIS_003` | 검색 필터링 |
| `DISTANCE_004` | `IN_DST_DIS_004` | 모달 추가 저장 |
| `DISTANCE_005` | `IN_DST_DIS_005` | 삭제 |
| `TS_COST_001` | `IN_TSC_DIS_001` | 목록 조회 |
| `TS_COST_002` | `IN_TSC_DIS_002` | 시나리오 필터 |
| `TS_COST_003` | `IN_TSC_DIS_003` | 검색 필터링 |
| `TS_COST_004` | `IN_TSC_DIS_004` | 모달 추가 저장 |
| `TS_COST_005` | `IN_TSC_DIS_005` | 삭제 |
| `TS_COST_006` | `IN_TSC_DIS_006` | 중복 저장 방지 |
| `TS_COST_007` | `IN_TSC_DIS_007` | Base Year Month 필터링 |

### IN — Bunker 그룹
| 현재 ID | 신규 ID | 기능명 |
|---------|---------|--------|
| `BUNKER_SEA_001` | `IN_BCS_DIS_001` | 목록 조회 |
| `BUNKER_SEA_002` | `IN_BCS_DIS_002` | 시나리오 필터 |
| `BUNKER_SEA_003` | `IN_BCS_DIS_003` | 검색 |
| `BUNKER_SEA_004` | `IN_BCS_DIS_004` | 모달 추가 저장 |
| `BUNKER_SEA_005` | `IN_BCS_DIS_005` | 삭제 |
| `BUNKER_SEA_006` | `IN_BCS_DIS_006` | 중복 저장 방지 |
| `BUNKER_PORT_001` | `IN_BCP_DIS_001` | 목록 조회 |
| `BUNKER_PORT_002` | `IN_BCP_DIS_002` | 시나리오 필터 |
| `BUNKER_PORT_003` | `IN_BCP_DIS_003` | 모달 추가 저장 |
| `BUNKER_PORT_004` | `IN_BCP_DIS_004` | 삭제 |
| `BUNKER_PRICE_001` | `IN_BP_DIS_001` | 목록 조회 |
| `BUNKER_PRICE_002` | `IN_BP_DIS_002` | 시나리오 필터 |
| `BUNKER_PRICE_003` | `IN_BP_DIS_003` | 검색 |
| `BUNKER_PRICE_004` | `IN_BP_DIS_004` | 모달 추가 저장 |
| `BUNKER_PRICE_005` | `IN_BP_DIS_005` | 삭제 |

### IN — CSV 공통
| 현재 ID | 신규 ID | 기능명 |
|---------|---------|--------|
| `CSV_DOWNLOAD_001` | `IN_CSV_DIS_001` | CSV 다운로드 기본 검증 |
| `CSV_DOWNLOAD_002` | `IN_CSV_DIS_002` | CSV 다운로드 시나리오 미선택 |
| `CSV_DOWNLOAD_003` | `IN_CSV_DIS_003` | CSV Scenario Code 컬럼 검증 |
| `CSV_UPLOAD_001` | `IN_CSV_DIS_004` | CSV 업로드 저장 검증 |
| `CSV_UPLOAD_002` | `IN_CSV_DIS_005` | CSV 업로드 파일 미선택 |
| `CSV_UPLOAD_003` | `IN_CSV_DIS_006` | CSV 업로드 시나리오 미선택 |

---

## 6. 규칙 요약

| # | 규칙 |
|---|------|
| 1 | 형식: **`{APP}_{MENU}_{TYPE}_{NNN}`** (4단계 고정) |
| 2 | APP: 앱별 2~3자 고정 코드 (`IN`, `CM`, `SIM`, `RPT`) |
| 3 | MENU: 메뉴별 2~4자 고정 코드 (코드표 참조) |
| 4 | TYPE: **필수** — `DIS`(화면), `SVC`(서비스), `MDL`(모델), `CMD`(커맨드), `API` |
| 5 | NNN: 3자리 일련번호, **APP+MENU+TYPE 범위 내** 순차 부여 |
| 6 | 화면 CRUD 테스트는 `DIS` 사용 → `IN_PF_DIS_001` |
| 7 | 접두사만으로 **앱 → 메뉴 → 계층** 즉시 식별 가능 |
| 8 | 향후 앱 추가 시 APP 코드만 추가하면 기존 ID와 충돌 없음 |
