from datetime import timedelta

import pytest

from django.http import QueryDict
from django.utils import timezone

from input_data.models import CascadingSchedule, CascadingScheduleDetail


@pytest.mark.django_db
class TestCascadingService:
    """
    CascadingService DB 저장 및 로드 비즈니스 로직 검증
    [Scenarios] CASCADING_SVC_001, CASCADING_ACT_001
    """

    def test_cascading_svc_001_save_and_overwrite(
        self, cascading_service, sample_schedule, user
    ):
        """
        [CASCADING_ACT_001] Save Cascading (Service)
        기존 데이터가 있을 경우 삭제(Cascade) 후 올바르게 Master-Detail을 덮어쓰는지 검증
        첫 행(Row)의 ETB를 initial_etb_date로 정확하게 파싱하여 저장하는지 확인
        """
        start_date = timezone.now().date()
        initial_etb = start_date + timedelta(days=2)  # 첫번째 배 투입일 (요일 보정됨)
        end_date = start_date + timedelta(days=30)
        scenario = sample_schedule.scenario

        # 1. Given: 기존 데이터 존재
        old_master = CascadingSchedule.objects.create(
            scenario=scenario,
            proforma=sample_schedule,
            cascading_seq=1,
            own_vessels=1,
            initial_etb_date=start_date,
            effective_start_date=start_date,
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
            "cascading_seq": "1",  # 덮어쓰기
            "effective_start_date": start_date.strftime("%Y-%m-%d"),
            "effective_end_date": end_date.strftime("%Y-%m-%d"),
        }

        # QueryDict 몽키패치
        qdict = QueryDict(mutable=True)
        qdict.update(post_data)
        qdict.setlist("vessel_code[]", ["NEW_VESSEL_1", "NEW_VESSEL_2"])
        qdict.setlist(
            "vessel_start_date[]",
            [
                initial_etb.strftime("%Y-%m-%d"),
                (initial_etb + timedelta(days=7)).strftime("%Y-%m-%d"),
            ],
        )

        # 2. When: 저장 서비스 호출
        cascading_service.save_cascading(qdict, user)

        # 3. Then
        masters = CascadingSchedule.objects.filter(
            scenario=scenario, proforma=sample_schedule
        )
        assert masters.count() == 1

        new_master = masters.first()
        assert new_master.own_vessels == 2
        assert (
            new_master.initial_etb_date == initial_etb
        )  # [핵심] 첫번째 날짜 추출 검증

        details = CascadingScheduleDetail.objects.filter(cascading=new_master).order_by(
            "id"
        )
        assert details.count() == 2
        assert not CascadingScheduleDetail.objects.filter(
            vessel_code="OLD_VESSEL"
        ).exists()
        assert details[0].vessel_code == "NEW_VESSEL_1"

    def test_cascading_svc_001_get_data(self, cascading_service, sample_schedule, user):
        """
        [CASCADING_SVC_001] Cascading 서비스 로직
        서비스의 get_cascading_data가 effective_start_date를 기준으로 전체 슬롯과 매핑을 정확히 해주는지 검증
        """
        start_date = timezone.now().date()
        scenario = sample_schedule.scenario

        # sample_schedule has declared_count=2
        master = CascadingSchedule.objects.create(
            scenario=scenario,
            proforma=sample_schedule,
            cascading_seq=1,
            own_vessels=1,
            initial_etb_date=start_date,
            effective_start_date=start_date,
            effective_end_date=start_date,
            created_by=user,
        )

        # 1번째 주차에만 배정 (2번째는 빔)
        CascadingScheduleDetail.objects.create(
            cascading=master,
            vessel_code="V1",
            initial_start_date=start_date,
            created_by=user,
        )

        # When: Edit 데이터 조회
        result = cascading_service.get_cascading_data(
            scenario.id, sample_schedule.lane_code, sample_schedule.proforma_name, 1
        )

        # Then
        assert result is not None
        assert result["header"]["required_count"] == 2  # 전체 슬롯
        assert result["header"]["own_vessel_count"] == 1
        assert result["header"]["effective_start_date"] == start_date.strftime(
            "%Y-%m-%d"
        )

        rows = result["details"]
        assert len(rows) == 2  # declared_count 만큼 반환되어야 함
        assert rows[0]["is_checked"] is True
        assert rows[0]["vessel_code"] == "V1"
        assert rows[1]["is_checked"] is False  # 2주차는 배정되지 않았으므로 비어있음
        assert rows[1]["vessel_code"] == ""
