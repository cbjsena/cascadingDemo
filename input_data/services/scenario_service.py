# input_data/services.py

from django.db import transaction
from django.utils import timezone
from input_data.models import (
    ScenarioInfo,
    # 1. Schedule
    BaseProformaSchedule,
    ProformaSchedule,
    BaseLongRangeSchedule,
    LongRangeSchedule,
    # 2. Vessel
    BaseVesselInfo,
    VesselInfo,
    BaseCharterCost,
    CharterCost,
    BaseVesselCapacity,
    VesselCapacity,
    # 3. Cost & Distance
    BaseDistance,
    Distance,
    BaseCanalFee,
    CanalFee,
    BaseTSCost,
    TSCost,
    # 4. Bunker
    BaseBunkerConsumptionSea,
    BunkerConsumptionSea,
    BaseBunkerConsumptionPort,
    BunkerConsumptionPort,
    BaseBunkerPrice,
    BunkerPrice,
    # 6. Constraints
    BaseFixedVesselDeployment,
    FixedVesselDeployment,
    BaseFixedVesselEvent,
    FixedVesselEvent,
    BasePortConstraint,
    PortConstraint,
)
from django.contrib.auth import get_user_model

User = get_user_model()

MODEL_MAPPING = [
    (BaseProformaSchedule, ProformaSchedule),
    (BaseLongRangeSchedule, LongRangeSchedule),
    (BaseVesselInfo, VesselInfo),
    (BaseCharterCost, CharterCost),
    (BaseVesselCapacity, VesselCapacity),
    (BaseDistance, Distance),
    (BaseCanalFee, CanalFee),
    (BaseTSCost, TSCost),
    (BaseBunkerConsumptionSea, BunkerConsumptionSea),
    (BaseBunkerConsumptionPort, BunkerConsumptionPort),
    (BaseBunkerPrice, BunkerPrice),
    (BaseFixedVesselDeployment, FixedVesselDeployment),
    (BaseFixedVesselEvent, FixedVesselEvent),
    (BasePortConstraint, PortConstraint),
]

@transaction.atomic
def get_system_user():
    """
    초기 데이터 적재 / 배치 작업용 시스템 유저
    """
    user, created = User.objects.get_or_create(
        username="cascading",
        defaults={
            "email": "yukaris@cyberlogitec.com",
            "is_active": False,
        },
    )
    if created:
        user.set_password("qwer123$")
        user.save(update_fields=["password"])

    return user

@transaction.atomic
def create_scenario_from_base(target_id, description="Base Scenario", user=None):
    """
    Base 데이터를 복사하여 새로운 시나리오를 생성하는 서비스 함수.
    - user: 이 작업을 수행한 사용자 (created_by에 저장)
    - base_year_month: 202601 고정
    """

    # [수정 사항 1] Base Year Month 202601 적용
    BASE_YEAR_MONTH = "202601"
    now = timezone.now()

    if user is None:
        user = get_system_user()

    # 1. 기존 시나리오가 있다면 삭제 (Reset)
    if ScenarioInfo.objects.filter(id=target_id).exists():
        ScenarioInfo.objects.filter(id=target_id).delete()

    # 2. 시나리오 마스터(ScenarioInfo) 생성
    scenario = ScenarioInfo(
        id=target_id,
        description=description,
        base_year_month=BASE_YEAR_MONTH,
        status="T",
    )

    if user:
        scenario.created_by = user
        scenario.updated_by = user

    scenario.save()

    result_summary = {}

    # 3. 데이터 복사 (Base -> Scenario)
    for base_model, sce_model in MODEL_MAPPING:
        table_name = sce_model._meta.db_table
        base_objects = base_model.objects.all()

        if not base_objects.exists():
            result_summary[table_name] = 0
            continue

        new_objects = []
        # ID를 제외한 데이터 필드 목록 추출
        fields = [f.name for f in base_model._meta.fields if f.name != "id"]

        for base_obj in base_objects:
            # Base 모델의 데이터를 딕셔너리로 추출
            data = {field: getattr(base_obj, field) for field in fields}

            # Scenario FK 연결
            data["scenario"] = scenario

            # [수정 사항 3] created_by / updated_by / timestamps 설정
            # (bulk_create는 auto_now를 자동으로 처리하지 않을 수 있으므로 명시적 할당)
            if user:
                data["created_by"] = user
                data["updated_by"] = user

            data["created_at"] = now
            data["updated_at"] = now

            new_objects.append(sce_model(**data))

        # Bulk Create 실행
        sce_model.objects.bulk_create(new_objects)
        result_summary[table_name] = len(new_objects)

    return scenario, result_summary
