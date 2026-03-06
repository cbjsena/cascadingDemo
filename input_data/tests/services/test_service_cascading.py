"""
Cascading Service Tests
CASCADING_SVC_* 시나리오에 대한 서비스 로직 테스트
"""

from datetime import date

import pytest

from django.utils import timezone

from input_data.models import (
    CascadingVesselPosition,
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
        get_cascading_data가 CascadingVesselPosition 기반으로 정확한 데이터를 반환하는지 검증
        """
        from input_data.services.cascading_service import CascadingService

        cascading_service = CascadingService()

        first_pos = cascading_with_details[0]

        result = cascading_service.get_cascading_data(
            scenario_id=first_pos.scenario.id,
            lane_code=first_pos.proforma.lane_code,
            proforma_name=first_pos.proforma.proforma_name,
        )

        # Then: header에 필수 필드 포함
        header = result.get("header", {})
        assert "own_vessel_count" in header
        assert "from_year_week" in header
        assert "to_year_week" in header
        assert header["own_vessel_count"] == 2

        # details에 declared_count만큼의 rows 반환
        rows = result.get("details", [])
        assert len(rows) >= first_pos.proforma.declared_count

        # 저장된 position은 is_checked=True, 미배정은 False
        checked_rows = [r for r in rows if r.get("is_checked")]
        assert len(checked_rows) == 2

    def test_cascading_svc_002_vessel_position_copy(self, sample_schedule, user):
        """
        [CASCADING_SVC_002] vessel_position / vessel_position_date 복사 검증
        BaseCascadingVesselPosition에서 CascadingVesselPosition으로 복사 시
        vessel_position과 vessel_position_date가 그대로 복사되는지 검증
        """
        from input_data.models import BaseCascadingVesselPosition
        from input_data.services.scenario_service import _copy_cascading_to_scenario

        # Given: BaseCascadingVesselPosition 데이터 생성
        BaseCascadingVesselPosition.objects.create(
            lane_code=sample_schedule.lane_code,
            proforma_name=sample_schedule.proforma_name,
            vessel_code="V001",
            vessel_position=1,
            vessel_position_date=date(2026, 2, 15),
        )
        BaseCascadingVesselPosition.objects.create(
            lane_code=sample_schedule.lane_code,
            proforma_name=sample_schedule.proforma_name,
            vessel_code="V002",
            vessel_position=2,
            vessel_position_date=date(2026, 2, 22),
        )

        # When: _copy_cascading_to_scenario 실행
        result = _copy_cascading_to_scenario(
            sample_schedule.scenario, user, timezone.now()
        )

        # Then: CascadingVesselPosition 2건 생성, 필드값 그대로 복사
        assert result["sce_schedule_cascading_vessel_position"] == 2

        positions = CascadingVesselPosition.objects.filter(
            scenario=sample_schedule.scenario
        ).order_by("vessel_position")

        assert positions.count() == 2

        pos1 = positions[0]
        assert pos1.vessel_code == "V001"
        assert pos1.vessel_position == 1
        assert pos1.vessel_position_date == date(2026, 2, 15)

        pos2 = positions[1]
        assert pos2.vessel_code == "V002"
        assert pos2.vessel_position == 2
        assert pos2.vessel_position_date == date(2026, 2, 22)
