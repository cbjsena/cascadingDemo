from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from common.constants import DEFAULT_BASE_YEAR_MONTH
from input_data.configs import MODEL_MAPPING, SCENARIO_CREATION_FILTERS
from input_data.models import (
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
def create_scenario_from_base(target_id, description="Base Scenario", user=None):
    """
    Base 데이터를 복사하여 새로운 시나리오를 생성하는 서비스 함수.
    - user: 이 작업을 수행한 사용자 (created_by에 저장)
    """

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
        base_year_month=DEFAULT_BASE_YEAR_MONTH,
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
