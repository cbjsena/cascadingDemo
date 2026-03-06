from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from common import constants
from input_data.configs import MODEL_MAPPING, SCENARIO_CREATION_FILTERS
from input_data.models import (
    BaseProformaSchedule,
    ProformaSchedule,
    ProformaScheduleDetail,
    ScenarioInfo,
)


@transaction.atomic
def get_system_user():
    """
    초기 데이터 적재 / 배치 작업용 시스템 유저
    """
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username="cascading",
        defaults={
            "email": "yukaris@cyberlogitec.com",
            "is_active": True,
            "is_staff": True,
            "is_superuser": True,
        },
    )
    if created:
        user.set_password("qwer123$")
        user.save(update_fields=["password"])

    return user


@transaction.atomic
def create_scenario_from_base(
    description="Base Scenario", user=None, base_year_week=None
):
    """
    Base 데이터를 복사하여 새로운 시나리오를 생성하는 서비스 함수.
    - description: 시나리오 설명
    - user: 이 작업을 수행한 사용자 (created_by에 저장)
    - base_year_week: 기준 주차 (YYYY-WXX 형식)
    """

    now = timezone.now()

    if user is None:
        user = get_system_user()

    # base_year_week 기본값 설정 (현재 주차, YYYYWK 형식)
    if not base_year_week:
        base_year_week = constants.DEFAULT_BASE_YEAR_WEEK
        # iso = now.date().isocalendar()
        # base_year_week = f"{iso[0]}{iso[1]:02d}"

    # 시나리오 마스터(ScenarioInfo) 생성 (code는 save()에서 자동 생성)
    scenario = ScenarioInfo(
        description=description,
        base_year_week=base_year_week,
        scenario_type="BASELINE",  # 기본 데이터에서 생성되는 시나리오는 BASELINE
        status="ACTIVE",
    )

    if user:
        scenario.created_by = user
        scenario.updated_by = user

    scenario.save()

    result_summary = {}

    # 3. Proforma 모델 특수 처리 (Master / Detail 분리 로직 호출)
    proforma_summary = _copy_proforma_to_scenario(scenario, user, now)
    result_summary.update(proforma_summary)

    # 4. Cascading 모델 특수 처리 (proforma FK 매핑 필요)
    cascading_summary = _copy_cascading_to_scenario(scenario, user, now)
    result_summary.update(cascading_summary)

    cascading_schedule_summary = _copy_cascading_schedule_to_scenario(
        scenario, user, now
    )
    result_summary.update(cascading_schedule_summary)

    # 5. 나머지 일반 데이터 복사 (Base -> Scenario 1:1 복사)
    for base_model, sce_model in MODEL_MAPPING:
        # Proforma 계열은 이미 위(_copy_proforma_to_scenario)에서
        # Cascading 계열은 이미 위에서 proforma FK 매핑 처리했으므로 건너뜁니다!
        if sce_model.__name__ in [
            "ProformaSchedule",
            "ProformaScheduleDetail",
            "CascadingVesselPosition",
            "CascadingSchedule",
        ]:
            continue

        table_name = sce_model._meta.db_table
        filter_kwargs = SCENARIO_CREATION_FILTERS.get(sce_model)

        if filter_kwargs:
            # 조건이 있는 경우 filter() 사용
            base_objects = base_model.objects.filter(**filter_kwargs)
        else:
            # 조건이 없으면 전체 데이터 가져오기
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

            if user:
                data["created_by"] = user
                data["updated_by"] = user
            # (bulk_create는 auto_now를 자동으로 처리하지 않을 수 있으므로 명시적 할당)
            data["created_at"] = now
            data["updated_at"] = now

            new_objects.append(sce_model(**data))

        # Bulk Create 실행
        if new_objects:
            sce_model.objects.bulk_create(new_objects)
        result_summary[table_name] = len(new_objects)

    return scenario, result_summary


def _copy_proforma_to_scenario(scenario, user, now):
    """
    [Proforma 전용 처리 함수]
    Flat 구조의 BaseProformaSchedule을 Master(ProformaSchedule)와
    Detail(ProformaScheduleDetail)로 분리하여 복사합니다.
    """
    summary = {"sce_proforma_schedule": 0, "sce_proforma_schedule_detail": 0}

    base_qs = BaseProformaSchedule.objects.all()
    if not base_qs.exists():
        return summary

    # 1. Master(Header) 추출 및 생성
    master_cache = {}
    masters_to_create = []

    for base in base_qs:
        master_key = (base.lane_id, base.proforma_name)
        if master_key not in master_cache:
            master = ProformaSchedule(
                scenario=scenario,
                lane_id=base.lane_id,
                proforma_name=base.proforma_name,
                effective_from_date=base.effective_from_date,
                duration=base.duration,
                declared_capacity=base.declared_capacity,
                declared_count=base.declared_count,
                own_vessel_count=base.own_vessel_count,
                created_by=user,
                updated_by=user,
                created_at=now,
                updated_at=now,
            )
            master_cache[master_key] = master
            masters_to_create.append(master)

    if masters_to_create:
        ProformaSchedule.objects.bulk_create(masters_to_create)
        summary["sce_proforma_schedule"] = len(masters_to_create)

    # DB에 생성된 Master 객체들을 다시 조회하여 PK(id)를 확보합니다.
    # (bulk_create는 DB 종류에 따라 PK를 반환하지 않을 수 있으므로 안전한 방식 채택)
    created_masters = ProformaSchedule.objects.filter(scenario=scenario)
    master_db_map = {(m.lane_id, m.proforma_name): m for m in created_masters}

    # 2. Detail 추출 및 생성
    details_to_create = []

    for base in base_qs:
        # DB에서 PK를 발급받은 실제 Master 객체를 매핑
        real_master = master_db_map.get((base.lane_id, base.proforma_name))

        detail = ProformaScheduleDetail(
            proforma=real_master,  # 외래키 연결
            direction=base.direction,
            port_id=base.port_id,
            calling_port_indicator=base.calling_port_indicator,
            calling_port_seq=base.calling_port_seq,
            turn_port_info_code=base.turn_port_info_code,
            pilot_in_hours=base.pilot_in_hours,
            etb_day_number=base.etb_day_number,
            etb_day_code=base.etb_day_code,
            etb_day_time=base.etb_day_time,
            actual_work_hours=base.actual_work_hours,
            etd_day_number=base.etd_day_number,
            etd_day_code=base.etd_day_code,
            etd_day_time=base.etd_day_time,
            pilot_out_hours=base.pilot_out_hours,
            link_distance=base.link_distance,
            link_eca_distance=base.link_eca_distance,
            link_speed=base.link_speed,
            sea_time_hours=base.sea_time_hours,
            terminal_code=base.terminal_code,
            created_by=user,
            updated_by=user,
            created_at=now,
            updated_at=now,
        )
        details_to_create.append(detail)

    if details_to_create:
        ProformaScheduleDetail.objects.bulk_create(details_to_create)
        summary["sce_proforma_schedule_detail"] = len(details_to_create)

    return summary


def _copy_cascading_to_scenario(scenario, user, now):
    """
    [Cascading 전용 처리 함수]
    BaseCascadingVesselPosition을 CascadingVesselPosition으로 복사합니다.
    Base에는 lane_code/proforma_name(문자열)이, Sce에는 proforma(FK)가 있으므로
    Proforma 매핑만 수행하고 나머지 필드는 그대로 복사합니다.
    """
    from input_data.models import (
        BaseCascadingVesselPosition,
        CascadingVesselPosition,
    )

    summary = {"sce_schedule_cascading_vessel_position": 0}

    base_qs = BaseCascadingVesselPosition.objects.all()
    if not base_qs.exists():
        return summary

    # Proforma 매핑 캐시 (lane_code, proforma_name) -> ProformaSchedule
    proforma_map = {
        (p.lane_id, p.proforma_name): p
        for p in ProformaSchedule.objects.filter(scenario=scenario)
    }

    positions_to_create = []

    for base in base_qs:
        proforma = proforma_map.get((base.lane_id, base.proforma_name))
        if not proforma:
            continue

        positions_to_create.append(
            CascadingVesselPosition(
                scenario=scenario,
                proforma=proforma,
                vessel_code=base.vessel_code,
                vessel_position=base.vessel_position,
                vessel_position_date=base.vessel_position_date,
                created_by=user,
                updated_by=user,
                created_at=now,
                updated_at=now,
            )
        )

    if positions_to_create:
        CascadingVesselPosition.objects.bulk_create(positions_to_create)
        summary["sce_schedule_cascading_vessel_position"] = len(positions_to_create)

    return summary


def _copy_cascading_schedule_to_scenario(scenario, user, now):
    """
    [Cascading Schedule 전용 처리 함수]
    BaseCascadingSchedule을 CascadingSchedule로 복사합니다.
    Base에는 lane_code/proforma_name(문자열)이, Sce에는 proforma(FK)가 있으므로
    Proforma 매핑만 수행하고 나머지 필드는 그대로 복사합니다.
    """
    from input_data.models import (
        BaseCascadingSchedule,
        CascadingSchedule,
    )

    summary = {"sce_schedule_cascading": 0}

    base_qs = BaseCascadingSchedule.objects.all()
    if not base_qs.exists():
        return summary

    proforma_map = {
        (p.lane_id, p.proforma_name): p
        for p in ProformaSchedule.objects.filter(scenario=scenario)
    }

    schedules_to_create = []

    for base in base_qs:
        proforma = proforma_map.get((base.lane_id, base.proforma_name))
        if not proforma:
            continue

        schedules_to_create.append(
            CascadingSchedule(
                scenario=scenario,
                proforma=proforma,
                vessel_position=base.vessel_position,
                vessel_position_date=base.vessel_position_date,
                created_by=user,
                updated_by=user,
                created_at=now,
                updated_at=now,
            )
        )

    if schedules_to_create:
        CascadingSchedule.objects.bulk_create(schedules_to_create)
        summary["sce_schedule_cascading"] = len(schedules_to_create)

    return summary
