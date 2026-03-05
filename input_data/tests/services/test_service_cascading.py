"""
Cascading Service Tests
CASCADING_SVC_* 시나리오에 대한 서비스 로직 테스트
"""

from datetime import date

import pytest

from django.utils import timezone

from input_data.models import (
    CascadingSchedule,
    ProformaScheduleDetail,
)


@pytest.mark.django_db
class TestCascadingService:
    """
    Cascading 서비스 로직 테스트
    Scenarios: CASCADING_SVC_001, CASCADING_SVC_002
    """

    def test_cascading_svc_001_service_logic(self, cascading_with_details):
        """
        [CASCADING_SVC_001] Cascading 서비스 로직
        get_cascading_data가 변경된 필드명으로 정확한 데이터를 반환하는지 검증
        """
        # When: 서비스 호출 (직접 import하여 사용)
        from input_data.services.cascading_service import CascadingService

        cascading_service = CascadingService()

        result = cascading_service.get_cascading_data(
            scenario_id=cascading_with_details.scenario.id,
            lane_code=cascading_with_details.proforma.lane_code,
            proforma_name=cascading_with_details.proforma.proforma_name,
        )

        # Then: header 딕셔너리에 변경된 필드명 포함
        header = result.get("header", {})
        assert "own_vessel_count" in header
        assert "effective_start_date" in header
        assert header["own_vessel_count"] == 2

        # required_count만큼의 rows 반환 (details로 변경됨)
        rows = result.get("details", [])
        assert len(rows) >= cascading_with_details.proforma.declared_count

    def test_cascading_svc_002_proforma_start_etb_calculation(
        self, sample_schedule, user
    ):
        """
        [CASCADING_SVC_002] proforma_start_etb_date 계산
        ProformaScheduleDetail의 첫 번째 포트 정보와 effective_start_date로
        proforma_start_etb_date가 정확히 계산되는지 검증
        """
        # Given: ProformaScheduleDetail에 첫 번째 포트 정보 (일요일) 추가
        ProformaScheduleDetail.objects.filter(proforma=sample_schedule).update(
            calling_port_seq=1, etb_day_code="SUN"  # 일요일
        )

        # When: scenario service의 _copy_cascading_to_scenario 함수 실행
        from input_data.models import BaseCascadingSchedule
        from input_data.services.scenario_service import _copy_cascading_to_scenario

        # BaseCascadingSchedule 데이터 생성
        BaseCascadingSchedule.objects.create(
            lane_code=sample_schedule.lane_code,
            proforma_name=sample_schedule.proforma_name,
            effective_start_date=date(2026, 2, 15),  # 토요일
            effective_end_date=date(2027, 2, 15),
            vessel_code="V001",
            initial_start_date=date(2026, 2, 16),
        )

        result = _copy_cascading_to_scenario(
            sample_schedule.scenario, user, timezone.now()
        )

        # Then: proforma_start_etb_date가 정확히 계산됨
        assert result["sce_schedule_cascading"] == 1

        cascading = CascadingSchedule.objects.filter(
            scenario=sample_schedule.scenario
        ).first()
        assert cascading is not None

        # proforma_start_etb_date 확인
        expected_date = date(2026, 2, 15)
        assert cascading.proforma_start_etb_date == expected_date
