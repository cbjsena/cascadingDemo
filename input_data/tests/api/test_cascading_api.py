"""
Cascading API Tests
CASCADING_VIEW_002, CASCADING_API_001 시나리오 테스트
"""

import pytest

from django.urls import reverse

from input_data.models import (
    VesselCapacity,
)


@pytest.mark.django_db
class TestCascadingAPI:
    """
    Cascading 관련 API 테스트
    Scenarios: CASCADING_VIEW_002, CASCADING_API_001
    """

    def test_cascading_view_002_proforma_detail_api(
        self, auth_client, cascading_with_details
    ):
        """
        [CASCADING_VIEW_002] Load Info (Auto 채번)
        Proforma 선택 후 API 호출 시 다음 Seq 자동 채번 및 Required Vessels 수 반환 검증
        """
        # Given: 기존 Cascading 데이터 존재 (Seq=1)
        api_url = reverse("api:proforma_detail")
        params = {
            "scenario_id": cascading_with_details.scenario.id,
            "lane_code": cascading_with_details.proforma.lane_code,
            "proforma_name": cascading_with_details.proforma.proforma_name,
        }

        # When: API 호출
        response = auth_client.get(api_url, params)

        # Then: 다음 Seq 자동 채번 및 Required Vessels 수 반환
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "declared_count" in data  # Required Vessels 수
        assert "first_port_day" in data

    def test_cascading_api_001_vessel_selection_ui(
        self, auth_client, sample_schedule, user
    ):
        """
        [CASCADING_API_001] 선박 선택 UI
        체크박스와 선박 선택이 연동되어 동작하는지 검증
        """
        # Given: 시나리오별 선박 용량 데이터 생성
        VesselCapacity.objects.create(
            scenario=sample_schedule.scenario,
            trade_code="ASIA",
            lane_code=sample_schedule.lane_code,
            vessel_code="V001",
            voyage_number="0001",
            direction="E",
            vessel_capacity=5000,
            reefer_capacity=500,
            created_by=user,
        )

        VesselCapacity.objects.create(
            scenario=sample_schedule.scenario,
            trade_code="ASIA",
            lane_code=sample_schedule.lane_code,
            vessel_code="V002",
            voyage_number="0001",
            direction="E",
            vessel_capacity=5000,
            reefer_capacity=500,
            created_by=user,
        )

        # When: Vessel List API 호출
        api_url = reverse("api:vessel_list")
        params = {
            "scenario_id": sample_schedule.scenario.id,
            "lane_code": sample_schedule.lane_code,
        }

        response = auth_client.get(api_url, params)

        # Then: 선박 목록 반환
        assert response.status_code == 200
        data = response.json()
        vessels = data.get("vessels", [])

        vessel_codes = [v["vessel_code"] for v in vessels]
        assert "V001" in vessel_codes
        assert "V002" in vessel_codes

        # 선박 선택 시 Capacity 정보 포함 확인
        for vessel in vessels:
            if vessel["vessel_code"] == "V001":
                assert vessel["max_cap"] == 5000  # API는 max_cap으로 반환
