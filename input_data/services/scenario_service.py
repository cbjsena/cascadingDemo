from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from common.constants import DEFAULT_BASE_YEAR_MONTH
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
def create_scenario_from_base(scenario_name, description="Base Scenario", user=None):
    """
    Base 데이터를 복사하여 새로운 시나리오를 생성하는 서비스 함수.
    - scenario_name: 생성할 시나리오의 이름 (name 필드)
    - description: 시나리오 설명
    - user: 이 작업을 수행한 사용자 (created_by에 저장)
    """

    now = timezone.now()

    if user is None:
        user = get_system_user()

    # 1. 기존 시나리오가 있다면 삭제 (Reset)
    if ScenarioInfo.objects.filter(name=scenario_name).exists():
        ScenarioInfo.objects.filter(name=scenario_name).delete()

    # 2. 시나리오 마스터(ScenarioInfo) 생성
    scenario = ScenarioInfo(
        name=scenario_name,
        description=description,
        base_year_month=DEFAULT_BASE_YEAR_MONTH,
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

    # 4. Cascading 모델 특수 처리 (proforma_start_etb_date 계산 포함)
    cascading_summary = _copy_cascading_to_scenario(scenario, user, now)
    result_summary.update(cascading_summary)

    # 5. 나머지 일반 데이터 복사 (Base -> Scenario 1:1 복사)
    for base_model, sce_model in MODEL_MAPPING:
        # Proforma 계열은 이미 위(_copy_proforma_to_scenario)에서
        # Cascading 계열은 이미 위(_copy_cascading_to_scenario)에서
        # Master-Detail로 분리 처리했으므로 일반 복사 루프에서는 건너뜁니다!
        if sce_model.__name__ in [
            "ProformaSchedule",
            "ProformaScheduleDetail",
            "CascadingSchedule",
            "CascadingScheduleDetail",
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
        master_key = (base.lane_code, base.proforma_name)
        if master_key not in master_cache:
            master = ProformaSchedule(
                scenario=scenario,
                lane_code=base.lane_code,
                proforma_name=base.proforma_name,
                effective_from_date=base.effective_from_date,
                duration=base.duration,
                declared_capacity=base.declared_capacity,
                declared_count=base.declared_count,
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
    master_db_map = {(m.lane_code, m.proforma_name): m for m in created_masters}

    # 2. Detail 추출 및 생성
    details_to_create = []

    for base in base_qs:
        # DB에서 PK를 발급받은 실제 Master 객체를 매핑
        real_master = master_db_map.get((base.lane_code, base.proforma_name))

        detail = ProformaScheduleDetail(
            proforma=real_master,  # 외래키 연결
            direction=base.direction,
            port_code=base.port_code,
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
    Flat 구조의 BaseCascadingSchedule을 Master(CascadingSchedule)와
    Detail(CascadingScheduleDetail)로 분리하여 복사합니다.
    proforma_start_etb_date는 ProformaScheduleDetail의 첫 번째 포트 ETB 정보로 계산합니다.
    """
    from datetime import timedelta

    from input_data.models import (
        BaseCascadingSchedule,
        CascadingSchedule,
        CascadingScheduleDetail,
        ProformaScheduleDetail,
    )

    summary = {"sce_schedule_cascading": 0, "sce_schedule_cascading_detail": 0}

    base_qs = BaseCascadingSchedule.objects.all()
    if not base_qs.exists():
        return summary

    # 요일 매핑 (ProformaScheduleDetail etb_day_code -> Python datetime weekday)
    DAY_MAP = {"SUN": 6, "MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5}

    def calculate_proforma_start_etb_date(proforma, effective_start_date):
        """
        ProformaScheduleDetail에서 calling_port_seq=1인 포트의 etb_day_code와
        effective_start_date를 이용하여 proforma_start_etb_date를 계산
        """
        try:
            # 첫 번째 포트 찾기 (calling_port_seq = 1)
            first_port = ProformaScheduleDetail.objects.filter(
                proforma=proforma, calling_port_seq=1
            ).first()

            if not first_port:
                return effective_start_date  # 첫 번째 포트가 없으면 effective_start_date 사용

            target_day_code = first_port.etb_day_code
            target_weekday = DAY_MAP.get(target_day_code)

            if target_weekday is None:
                return (
                    effective_start_date  # 잘못된 요일 코드면 effective_start_date 사용
                )

            # effective_start_date부터 target_weekday에 해당하는 날짜 찾기
            current_date = effective_start_date
            current_weekday = current_date.weekday()

            # 같은 요일이면 그대로 사용
            if current_weekday == target_weekday:
                return current_date

            # 다음 해당 요일 찾기 (최대 7일 이내)
            days_ahead = (target_weekday - current_weekday) % 7
            if days_ahead == 0:
                days_ahead = 7  # 다음 주 같은 요일

            return current_date + timedelta(days=days_ahead)

        except Exception as e:
            print(f"Error calculating proforma_start_etb_date: {e}")
            return effective_start_date

    # 1. Master(Header) 추출 및 생성
    master_cache = {}
    masters_to_create = []

    # Proforma 매핑을 위한 캐시 (scenario의 proforma들)
    proforma_map = {
        (p.lane_code, p.proforma_name): p
        for p in ProformaSchedule.objects.filter(scenario=scenario)
    }

    for base in base_qs:
        master_key = (base.lane_code, base.proforma_name, base.cascading_seq)
        if master_key not in master_cache:
            # 해당하는 Proforma 찾기
            proforma = proforma_map.get((base.lane_code, base.proforma_name))
            if not proforma:
                continue  # Proforma가 없으면 스킵

            # proforma_start_etb_date 계산
            calculated_start_etb_date = calculate_proforma_start_etb_date(
                proforma, base.effective_start_date
            )

            master = CascadingSchedule(
                scenario=scenario,
                proforma=proforma,
                cascading_seq=base.cascading_seq,
                own_vessel_count=base.own_vessel_count,
                proforma_start_etb_date=calculated_start_etb_date,  # 계산된 값 사용
                effective_start_date=base.effective_start_date,
                effective_end_date=base.effective_end_date,
                created_by=user,
                updated_by=user,
                created_at=now,
                updated_at=now,
            )
            master_cache[master_key] = master
            masters_to_create.append(master)

    if masters_to_create:
        CascadingSchedule.objects.bulk_create(masters_to_create)
        summary["sce_schedule_cascading"] = len(masters_to_create)

    # DB에 생성된 Master 객체들을 다시 조회하여 PK(id)를 확보합니다.
    created_masters = CascadingSchedule.objects.filter(scenario=scenario)
    master_db_map = {
        (m.proforma.lane_code, m.proforma.proforma_name, m.cascading_seq): m
        for m in created_masters
    }

    # 2. Detail 추출 및 생성
    details_to_create = []

    for base in base_qs:
        # DB에서 PK를 발급받은 실제 Master 객체를 매핑
        real_master = master_db_map.get(
            (base.lane_code, base.proforma_name, base.cascading_seq)
        )
        if not real_master:
            continue  # Master가 없으면 스킵

        detail = CascadingScheduleDetail(
            cascading=real_master,  # 외래키 연결
            vessel_code=base.vessel_code,
            initial_start_date=base.initial_start_date,
            created_by=user,
            updated_by=user,
            created_at=now,
            updated_at=now,
        )
        details_to_create.append(detail)

    if details_to_create:
        CascadingScheduleDetail.objects.bulk_create(details_to_create)
        summary["sce_schedule_cascading_detail"] = len(details_to_create)

    return summary
