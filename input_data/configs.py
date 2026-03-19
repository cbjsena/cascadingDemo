from input_data.models import (
    BaseBunkerConsumptionPort,
    BaseBunkerConsumptionSea,
    BaseBunkerPrice,
    BaseCanalFee,
    BaseCascadingSchedule,
    BaseCascadingVesselPosition,
    BaseCharterCost,
    BaseFixedScheduleChange,
    BaseFixedVesselDeployment,
    BaseLongRangeSchedule,
    BasePortConstraint,
    BaseProformaSchedule,
    BaseTSCost,
    BaseVesselCapacity,
    BaseVesselInfo,
    BunkerConsumptionPort,
    BunkerConsumptionSea,
    BunkerPrice,
    CanalFee,
    CascadingSchedule,
    CascadingVesselPosition,
    CharterCost,
    FixedScheduleChange,
    FixedVesselDeployment,
    LongRangeSchedule,
    PortConstraint,
    ProformaSchedule,
    TSCost,
    VesselCapacity,
    VesselInfo,
)

# ---------------------------------------------------------
# 1. Base <-> Scenario 모델 매핑
# ---------------------------------------------------------
MODEL_MAPPING = [
    (BaseProformaSchedule, ProformaSchedule),
    (BaseCascadingSchedule, CascadingSchedule),
    (BaseCascadingVesselPosition, CascadingVesselPosition),
    (BaseLongRangeSchedule, LongRangeSchedule),
    (BaseVesselInfo, VesselInfo),
    (BaseCharterCost, CharterCost),
    (BaseVesselCapacity, VesselCapacity),
    # (BaseDistance, Distance),
    (BaseCanalFee, CanalFee),
    (BaseTSCost, TSCost),
    (BaseBunkerConsumptionSea, BunkerConsumptionSea),
    (BaseBunkerConsumptionPort, BunkerConsumptionPort),
    (BaseBunkerPrice, BunkerPrice),
    (BaseFixedVesselDeployment, FixedVesselDeployment),
    (BaseFixedScheduleChange, FixedScheduleChange),
    (BasePortConstraint, PortConstraint),
]


# ---------------------------------------------------------
# 2. 시나리오 생성 시 필터 조건 (Default Scenario Creation Filters)
# Key: Scenario Model Class
# Value: filter(**kwargs)
# ---------------------------------------------------------
SCENARIO_CREATION_FILTERS = {
    # VesselInfo: V### 형태 (V + 3자리 숫자) 선박만 복제
    VesselInfo: {"vessel_code__regex": r"^V\d{3}$"},
    ProformaSchedule: {
        "proforma_name__gte": "3000",  # 3000보다 크거나 같고 (Greater Than or Equal)
        "proforma_name__lt": "7000",  # 7000보다 작은 (Less Than)
    },
    VesselCapacity: {
        "vessel_code__regex": r"^V\d{3}$",
    },
    # ProformaSchedule: {"lane_code__in": ["FP1", "EC2"]},
}
