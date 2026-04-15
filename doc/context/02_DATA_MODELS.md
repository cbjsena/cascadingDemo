# 02. Data Models & Database — Cascading Opt Demo

> **목적**: 모델 구조, 테이블 관계, 데이터 패턴을 빠르게 이해하기 위한 컨텍스트 문서  
> **최종 갱신**: 2026-04-15

---

## 1. 모델 설계 원칙 — Dual Table Strategy

모든 데이터는 **Base(기준)** 테이블과 **Scenario(시나리오)** 테이블 쌍으로 존재한다.

| 구분 | 접두사 | 목적 | FK |
|------|--------|------|----|
| Base | `base_*` | 변경 불가 원본 데이터 | 시나리오 FK 없음 |
| Scenario | `sce_*` | 시나리오별 복제·수정 데이터 | `scenario_id` FK 보유 |

**추상 모델 패턴**: `AbsXxx(models.Model)` → `BaseXxx(AbsXxx)` + `Xxx(AbsXxx, ScenarioBaseModel)`

---

## 2. 공통 베이스 모델

### CommonModel (abstract)
```
- created_at: DateTimeField (auto_now_add)
- created_by: FK(User, nullable)
- updated_at: DateTimeField (auto_now)
- updated_by: FK(User, nullable)
```
모든 커스텀 모델의 조상. Audit 필드 제공.

### ScenarioBaseModel(CommonModel) (abstract)
```
- scenario: FK(ScenarioInfo, CASCADE)
```
시나리오 의존 데이터의 공통 조상. CommonModel 상속.

---

## 3. 전체 모델 목록

### 3.1 Master 테이블 (시나리오 독립)

| 모델 | DB 테이블 | PK | 설명 |
|------|-----------|-----|------|
| MasterTrade | `master_trade` | trade_code (CharField) | 항로(Trade) 정보 |
| MasterPort | `master_port` | port_code (CharField) | 항구(Port/Location) 정보 |
| MasterLane | `master_lane` | lane_code (CharField) | 서비스 라인(Lane) 정보 |
| BaseWeekPeriod | `base_week_period` | auto id | 주차(Year-Week) 기간 정보 |

### 3.2 ScenarioInfo (시나리오 메인)

| DB 테이블 | `sce_scenario_info` |
|-----------|---------------------|
| PK | id (AutoField) |
| code | 자동생성: `SCYYYYMMDD_NNN` (concurrent safe retry) |
| scenario_type | BASELINE / WHAT_IF / OPTIMIZATION / SENSITIVITY / COMPARISON |
| status | DRAFT / ACTIVE / ARCHIVED / BASELINE |
| base_year_week | YYYYWK (계획 시작 주차) |
| planning_horizon_months | 기본 12개월 |
| tags | 콤마 구분 태그 |
| base_scenario | 자기참조 FK (비교 기준) |

### 3.3 Schedule 그룹

| 모델 (Base / Sce) | DB 테이블 | 설명 |
|--------------------|-----------|------|
| BaseProformaSchedule / ProformaSchedule | `base_schedule_proforma` / `sce_schedule_proforma` | Proforma 스케줄 헤더 (Lane+Proforma 단위) |
| — / ProformaScheduleDetail | `sce_schedule_proforma_detail` | Proforma 기항지 상세 (Master-Detail) |
| BaseCascadingVesselPosition / CascadingVesselPosition | `base_schedule_cascading_vessel_position` / `sce_schedule_cascading_vessel_position` | Proforma 슬롯별 선박 배치 |
| BaseCascadingSchedule / CascadingSchedule | `base_schedule_cascading` / `sce_schedule_cascading` | Proforma 슬롯 선택 (vessel_code 없음) |
| — / LaneProformaMapping | `sce_lane_proforma_mapping` | Lane↔Proforma 매핑 (시나리오별) |
| BaseLongRangeSchedule / LongRangeSchedule | `base_schedule_long_range` / `sce_schedule_long_range` | Long Range Schedule (VVD 기반) |

### 3.4 Vessel 그룹

| 모델 (Base / Sce) | DB 테이블 | 설명 |
|--------------------|-----------|------|
| BaseVesselInfo / VesselInfo | `base_vessel_info` / `sce_vessel_info` | 선박 기본 정보 (소유/용선, 인도/반납, 도크) |
| BaseCharterCost / CharterCost | `base_vessel_charter_cost` / `sce_vessel_charter_cost` | 용선료 기간별 단가 |
| BaseVesselCapacity / VesselCapacity | `base_vessel_capacity` / `sce_vessel_capacity` | VVD별 선박 용량(TEU, Reefer) |

### 3.5 Cost & Distance 그룹

| 모델 (Base / Sce) | DB 테이블 | 설명 |
|--------------------|-----------|------|
| BaseCanalFee / CanalFee | `base_cost_canal_fee` / `sce_cost_canal_fee` | 운하 통과료 |
| BaseDistance | `base_cost_distance` | 항구 간 거리/ECA거리 (시나리오 독립) |
| BaseTSCost / TSCost | `base_cost_ts_cost` / `sce_cost_ts_cost` | T/S 비용 |

### 3.6 Bunker 그룹

| 모델 (Base / Sce) | DB 테이블 | 설명 |
|--------------------|-----------|------|
| BaseBunkerConsumptionSea / BunkerConsumptionSea | `base_bunker_consumption_sea` / `sce_bunker_consumption_sea` | 해상 연료 소비량 (용량×속도) |
| BaseBunkerConsumptionPort / BunkerConsumptionPort | `base_bunker_consumption_port` / `sce_bunker_consumption_port` | 항구 체류/유휴 연료 소비량 |
| BaseBunkerPrice / BunkerPrice | `base_bunker_price` / `sce_bunker_price` | 연료 단가 (Trade+Lane+Type) |

### 3.7 Constraint 그룹

| 모델 (Base / Sce) | DB 테이블 | 설명 |
|--------------------|-----------|------|
| BaseFixedVesselDeployment / FixedVesselDeployment | `base_constraint_fixed_deployment` / `sce_constraint_fixed_deployment` | Lane별 선박 투입/제외 제약 |
| BaseFixedScheduleChange / FixedScheduleChange | `base_constraint_fixed_schedule_change` / `sce_constraint_fixed_schedule_change` | 선박 스케줄 변경 이벤트 (Phase In/Out 등) |
| BasePortConstraint / PortConstraint | `base_constraint_port` / `sce_constraint_port` | 항만 입항 선박 크기 제한 |

### 3.8 SimulationRun

| DB 테이블 | `simulation_run` |
|-----------|------------------|
| PK | id (AutoField) |
| code | 자동생성: `SMYYYYMMDD_NNN` (concurrent safe retry) |
| scenario | FK(ScenarioInfo, CASCADE) |
| algorithm_type | EXACT(MIP) / EFFICIENT(Metaheuristic) / FAST(Greedy) |
| solver_type | cplex / gurobi / xpress / ortools / meta_* / greedy_* |
| simulation_status | SNAPSHOTTING → SNAPSHOT_DONE → PENDING → RUNNING → SUCCESS / FAILED / CANCELED |
| progress | 0~100 (%) |
| task_id | Celery Task ID |
| model_start_time / model_end_time | 실행 시간 |
| objective_value | 목적함수 값 |
| execution_time | 실행 시간(초) |

**Status Flow**:
```
SNAPSHOTTING → SNAPSHOT_DONE → PENDING → RUNNING → SUCCESS
                                                  → FAILED
                                       → CANCELED (어느 단계에서든)
```

**Properties**:
- `is_processing`: SNAPSHOTTING, SNAPSHOT_DONE, PENDING, RUNNING 중 하나
- `is_running`: RUNNING만
- `is_success`, `is_failure`: 각각 SUCCESS, FAILED
- `can_modify`: is_processing가 아닌 경우 (삭제/수정 가능)
- `can_view_result`: SUCCESS인 경우

---

## 4. 시나리오 생성 흐름 (Base → Scenario 복제)

`input_data/configs.py`의 `MODEL_MAPPING`에 정의된 15쌍의 Base→Sce 모델을 복제한다.

**필터 조건** (`SCENARIO_CREATION_FILTERS`):
- VesselInfo: `vessel_code` regex `^V\d{3}$`
- ProformaSchedule: `proforma_name` 3000~6999
- VesselCapacity: `vessel_code` regex `^V\d{3}$`

---

## 5. 코드 자동생성 패턴

ScenarioInfo와 SimulationRun 모두 동일한 패턴:
```python
# save() 메서드 내부
prefix = f"SC{today_str}_"  # 또는 SM
for attempt in range(max_retries=10):
    last_code = Model.objects.filter(code__startswith=prefix).aggregate(Max("code"))
    new_num = last_num + 1 if last_code else 1
    self.code = f"{prefix}{new_num:03d}"
    with transaction.atomic():
        super().save()  # IntegrityError 시 재시도
```

