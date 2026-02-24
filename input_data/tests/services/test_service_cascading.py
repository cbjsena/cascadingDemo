from datetime import timedelta

import pytest

from django.utils import timezone

from input_data.models import CascadingSchedule, CascadingScheduleDetail


@pytest.mark.django_db
class TestCascadingService:
    """
    CascadingService DB 저장 및 로드 비즈니스 로직 검증
    [Scenarios] CASCADING_SVC_001
    """

    def test_cascading_svc_001_save_and_overwrite(
        self, cascading_service, sample_schedule, user
    ):
        """
        [CASCADING_SVC_001] Cascading 저장 엔진
        기존 데이터가 있을 경우 삭제(Cascade) 후 올바르게 Master-Detail을 덮어쓰는지 검증
        """
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)
        scenario = sample_schedule.scenario

        # 1. Given: 이미 저장된 낡은 Cascading 데이터가 1건 존재한다고 가정
        old_master = CascadingSchedule.objects.create(
            scenario=scenario,
            proforma=sample_schedule,
            cascading_seq=1,
            own_vessels=1,
            start_date=start_date,
            created_by=user,
        )
        CascadingScheduleDetail.objects.create(
            cascading=old_master,
            vessel_code="OLD_VESSEL",
            initial_start_date=start_date,
            created_by=user,
        )

        # 새로운 화면 입력 데이터 모형
        post_data = {
            "scenario_id": scenario.id,
            "lane_code": sample_schedule.lane_code,
            "proforma_name": sample_schedule.proforma_name,
            "apply_start_date": start_date.strftime("%Y-%m-%d"),
            "apply_end_date": end_date.strftime("%Y-%m-%d"),
        }

        # Django QueryDict의 getlist() 동작을 흉내내기 위해 딕셔너리에 메서드 몽키패치 또는 QueryDict 사용
        from django.http import QueryDict

        qdict = QueryDict(mutable=True)
        qdict.update(post_data)
        qdict.setlist("vessel_code[]", ["NEW_VESSEL_1", "NEW_VESSEL_2"])
        qdict.setlist(
            "vessel_start_date[]",
            [
                start_date.strftime("%Y-%m-%d"),
                (start_date + timedelta(days=7)).strftime("%Y-%m-%d"),
            ],
        )

        # 2. When: 저장 서비스 호출
        cascading_service.save_cascading(qdict, user)

        # 3. Then
        # (1) Master는 1개만 존재해야 함 (기존 것 삭제됨)
        masters = CascadingSchedule.objects.filter(
            scenario=scenario, proforma=sample_schedule
        )
        assert masters.count() == 1
        assert masters.first().own_vessels == 2

        # (2) Detail은 2개가 생성되어야 하며, 옛날 데이터(OLD_VESSEL)는 지워져야 함
        details = CascadingScheduleDetail.objects.filter(
            cascading=masters.first()
        ).order_by("id")
        assert details.count() == 2
        assert not CascadingScheduleDetail.objects.filter(
            vessel_code="OLD_VESSEL"
        ).exists()
        assert details[0].vessel_code == "NEW_VESSEL_1"
        assert details[1].vessel_code == "NEW_VESSEL_2"

    def test_cascading_svc_002_get_data(self, cascading_service, sample_schedule, user):
        """저장된 Cascading 데이터를 화면 양식에 맞게 잘 불러오는지 검증"""
        start_date = timezone.now().date()
        scenario = sample_schedule.scenario

        master = CascadingSchedule.objects.create(
            scenario=scenario,
            proforma=sample_schedule,
            cascading_seq=1,
            own_vessels=1,
            start_date=start_date,
            end_date=start_date,
            created_by=user,
        )
        CascadingScheduleDetail.objects.create(
            cascading=master,
            vessel_code="V1",
            initial_start_date=start_date,
            created_by=user,
        )

        # When: 데이터 조회
        result = cascading_service.get_cascading_data(
            scenario.id, sample_schedule.lane_code, sample_schedule.proforma_name
        )

        # Then
        assert result is not None
        assert result["header"]["own_vessels"] == 1
        assert len(result["details"]) == 1
        assert result["details"][0]["vessel_code"] == "V1"
