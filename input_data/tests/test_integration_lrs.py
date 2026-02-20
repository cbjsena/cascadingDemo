from datetime import datetime

import pytest

from django.urls import reverse
from django.utils import timezone

from input_data.models import LongRangeSchedule, ScenarioInfo


@pytest.mark.django_db
class TestLrsListIntegration:
    """
    [Integration Test] LRS List 화면과 API 간의 연동 로직 검증
    - 화면의 Javascript가 호출하는 API URL과 파라미터를 그대로 시뮬레이션
    """

    @pytest.fixture(autouse=True)
    def setup_integration_data(self, db, auth_client, user):
        self.client = auth_client
        self.user = user

        # 1. 시나리오 생성
        self.scenario = ScenarioInfo.objects.create(
            id="INT_SCENARIO",
            description="Integration Test",
            status="T",
            created_by=user,
            updated_by=user,
        )

        # 2. 데이터 세팅
        # - Lane A에는 'VESSEL_A' 배정
        LongRangeSchedule.objects.create(
            scenario=self.scenario,
            lane_code="LANE_A",
            vessel_code="VESSEL_A",
            voyage_number="0001",
            direction="E",
            port_code="PUS",
            calling_port_seq=1,
            etb=timezone.now(),
            created_by=user,
            updated_by=user,
        )
        # - Lane B에는 'VESSEL_B' 배정
        LongRangeSchedule.objects.create(
            scenario=self.scenario,
            lane_code="LANE_B",
            vessel_code="VESSEL_B",
            voyage_number="0001",
            direction="E",
            port_code="TYO",
            calling_port_seq=1,
            etb=timezone.now(),
            created_by=user,
            updated_by=user,
        )

    def test_lrs_list_vessel_filtering_by_lane(self):
        """
        [LRS_INT_001] 화면에서 Lane 선택 시 해당 Lane의 선박만 가져오는지 검증
        Target API: api:vessel_options (List 화면 검색용)
        """
        # 프론트엔드에서 호출하는 URL (common_api.js -> loadVesselOptions)
        url = reverse("api:vessel_options")

        # --- Step 1. Lane A 선택 시뮬레이션 ---
        response_a = self.client.get(
            url, {"scenario_id": self.scenario.id, "lane_code": "LANE_A"}
        )

        assert response_a.status_code == 200
        options_a = response_a.json()["options"]

        # 검증: VESSEL_A는 있고, VESSEL_B는 없어야 함
        assert "VESSEL_A" in options_a
        assert "VESSEL_B" not in options_a

        # --- Step 2. Lane B 선택 시뮬레이션 ---
        response_b = self.client.get(
            url, {"scenario_id": self.scenario.id, "lane_code": "LANE_B"}
        )

        options_b = response_b.json()["options"]

        # 검증: VESSEL_B는 있고, VESSEL_A는 없어야 함
        assert "VESSEL_B" in options_b
        assert "VESSEL_A" not in options_b

    def test_lrs_list_vessel_all_load(self):
        """
        [LRS_INT_002] Lane 미선택(초기 진입/해제) 시 전체 선박 조회 검증
        """
        url = reverse("api:vessel_options")

        # --- Step 1. 시나리오만 선택 (Lane 파라미터 없음) ---
        response = self.client.get(
            url,
            {
                "scenario_id": self.scenario.id
                # lane_code 없음
            },
        )

        assert response.status_code == 200
        options = response.json()["options"]

        # 검증: 모든 선박이 다 나와야 함
        assert "VESSEL_A" in options
        assert "VESSEL_B" in options


@pytest.mark.django_db
class TestLrsIntegrationMissingScenarios:
    """
    [LRS_INT_003] 보완 시나리오 테스트
    """

    def test_lrs_int_003_vessel_lane_check(self, auth_client, user, pf_complex_data):
        """[LRS_INT_003] 선박 기간 점유 점검 API (Lane Check)"""
        url = reverse("api:vessel_lane_check")

        # 1. Given: V_01 선박이 2024년 1월에 LANE_A에 이미 배정된 스케줄 생성
        LongRangeSchedule.objects.create(
            scenario=pf_complex_data,
            lane_code="LANE_A",
            vessel_code="V_01",
            voyage_number="0001",
            port_code="PUS",
            calling_port_seq=1,
            etb=timezone.make_aware(datetime(2026, 1, 15)),
            created_by=user,
            updated_by=user,
        )

        # 2. When: JS에서 1월 1일 ~ 1월 30일 기간에 V_01을 선택하고 API 호출
        response = auth_client.get(
            url,
            {
                "scenario_id": pf_complex_data.id,
                "vessel_code": "V_01",
                "start_date": "2026-01-01",
                "end_date": "2026-01-30",
            },
        )

        # 3. Then
        assert response.status_code == 200
        data = response.json()

        # 이미 LANE_A에 배정되어 있다는 것을 응답으로 반환해야 함
        assert data.get("lane_code") == "LANE_A"
