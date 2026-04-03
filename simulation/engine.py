"""
가짜(Mock) 시뮬레이션 엔진.

실제 최적화 엔진이 없을 때 대용으로 동작합니다.
1. 시나리오에 연결된 각 데이터 테이블의 레코드 수를 집계하여 반환합니다.
2. 6초 간격으로 progress를 10%씩 올려 총 60초에 완료합니다.
"""

import logging
import time
from typing import Any

from input_data.models import (
    BunkerConsumptionPort,
    BunkerConsumptionSea,
    BunkerPrice,
    CanalFee,
    CascadingSchedule,
    CascadingVesselPosition,
    CharterCost,
    FixedScheduleChange,
    FixedVesselDeployment,
    LaneProformaMapping,
    LongRangeSchedule,
    PortConstraint,
    ProformaSchedule,
    TSCost,
    VesselCapacity,
    VesselInfo,
)
from simulation.models import SimulationRun, SimulationStatus

logger = logging.getLogger(__name__)


class MockEngineCanceledError(Exception):
    """모니터링 화면에서 중단 요청이 들어온 경우 발생"""


# 시나리오 FK를 갖는 데이터 모델 목록 (표시 이름, 모델)
SCENARIO_DATA_MODELS: list[tuple[str, Any]] = [
    ("Proforma Schedule", ProformaSchedule),
    ("Cascading Vessel Position", CascadingVesselPosition),
    ("Cascading Schedule", CascadingSchedule),
    ("Lane-Proforma Mapping", LaneProformaMapping),
    ("Long Range Schedule", LongRangeSchedule),
    ("Vessel Info", VesselInfo),
    ("Charter Cost", CharterCost),
    ("Vessel Capacity", VesselCapacity),
    ("Canal Fee", CanalFee),
    ("T/S Cost", TSCost),
    ("Bunker Consumption (Sea)", BunkerConsumptionSea),
    ("Bunker Consumption (Port)", BunkerConsumptionPort),
    ("Bunker Price", BunkerPrice),
    ("Fixed Vessel Deployment", FixedVesselDeployment),
    ("Fixed Schedule Change", FixedScheduleChange),
    ("Port Constraint", PortConstraint),
]

# 엔진 설정
STEP_INTERVAL_SEC = 6  # 각 단계 간격 (초)
STEP_INCREMENT = 10  # 단계당 진행률 증가분 (%)
TOTAL_STEPS = 10  # 총 단계 수 (10 × 10% = 100%)


def _collect_scenario_data_counts(scenario_id: int) -> dict[str, int]:
    """시나리오에 연결된 각 데이터 테이블의 레코드 수를 집계합니다."""
    counts: dict[str, int] = {}
    for label, model_cls in SCENARIO_DATA_MODELS:
        try:
            counts[label] = model_cls.objects.filter(scenario_id=scenario_id).count()
        except Exception:
            counts[label] = 0
    return counts


def _ensure_not_canceled(simulation_id: int) -> None:
    current_status = (
        SimulationRun.objects.filter(pk=simulation_id)
        .values_list("simulation_status", flat=True)
        .first()
    )
    if current_status == SimulationStatus.CANCELED:
        raise MockEngineCanceledError("Canceled by user")


def run_mock_engine(simulation: SimulationRun) -> dict[str, Any]:
    """
    가짜 엔진 실행.

    Parameters
    ----------
    simulation : SimulationRun
        실행할 시뮬레이션 객체 (select_related('scenario') 필수)

    Returns
    -------
    dict
        엔진 실행 결과 (objective_value, execution_time, model_status, data_summary 등)
    """
    scenario = simulation.scenario
    start_time = time.time()
    _ensure_not_canceled(simulation.id)

    # ── 1단계: 시나리오 데이터 수량 집계 ──
    logger.info(
        "[MockEngine] Simulation %s – 시나리오 %s 데이터 수량 집계 시작",
        simulation.code,
        scenario.code,
    )
    data_counts = _collect_scenario_data_counts(scenario.id)
    total_records = sum(data_counts.values())

    logger.info(
        "[MockEngine] 시나리오 %s 데이터 수량 집계 완료 – 총 %d건",
        scenario.code,
        total_records,
    )
    for label, cnt in data_counts.items():
        logger.info("  ├─ %-30s : %6d건", label, cnt)

    # 데이터 수량 정보를 model_status에 저장 (10% 시점)
    # summary_lines = [f"{label}: {cnt}건" for label, cnt in data_counts.items()]
    # data_summary_text = f"총 {total_records}건 | " + ", ".join(summary_lines)

    simulation.model_status = f"데이터 수집 완료 ({total_records}건)"
    simulation.save(update_fields=["model_status", "updated_at"])

    # ── 2단계: 6초 간격으로 progress 10%씩 증가 (10% → 100%) ──
    for step in range(1, TOTAL_STEPS + 1):
        _ensure_not_canceled(simulation.id)
        progress = step * STEP_INCREMENT

        time.sleep(STEP_INTERVAL_SEC)
        _ensure_not_canceled(simulation.id)

        simulation.progress = progress
        if step < TOTAL_STEPS:
            simulation.model_status = f"최적화 진행 중… ({progress}%)"
        else:
            simulation.model_status = "최적화 완료"

        simulation.save(update_fields=["progress", "model_status", "updated_at"])

        logger.info(
            "[MockEngine] Simulation %s – progress %d%% (step %d/%d)",
            simulation.code,
            progress,
            step,
            TOTAL_STEPS,
        )

    elapsed = time.time() - start_time

    return {
        "objective_value": 12345.67,
        "execution_time": round(elapsed, 2),
        "model_status": "MOCK_COMPLETED",
        "progress": 100,
        "data_summary": data_counts,
        "total_records": total_records,
    }
