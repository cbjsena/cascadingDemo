import pytest

from django.urls import reverse
from django.utils import timezone

from input_data.models import (
    Distance,
    LongRangeSchedule,
    ProformaSchedule,
    ProformaScheduleDetail,  # 새로 추가된 Detail 모델 Import
    VesselCapacity,
)


@pytest.mark.django_db
class TestApiViews:
    """
    [API 앱 통합 테스트]
    Test Scenarios: API_DIST_*, API_PF_*, API_VSL_*
    """

    # --- Test Data Setup (Fixtures) ---
    @pytest.fixture(autouse=True)
    def setup_data(self, db, user, auth_client, base_scenario):
        self.user = user
        self.client = auth_client
        self.scenario = base_scenario  # conftest의 픽스처 재사용

        # 1. Distance (PUS -> TYO : 500)
        Distance.objects.create(
            scenario=self.scenario,
            from_port_code="KRPUS",
            to_port_code="JPTYO",
            distance=500,
            eca_distance=100,
        )

        # 2. Proforma Schedule - [Master-Detail 구조로 분리]

        # --- LANE_A: PF_01 ---
        # 2-1. PF_01 Master 생성
        pf_01_master = ProformaSchedule.objects.create(
            scenario=self.scenario,
            lane_code="LANE_A",
            proforma_name="PF_01",
            effective_from_date=timezone.now(),
            declared_count=2,
            duration=10.0,
            created_by=user,
            updated_by=user,
        )
        # 2-2. PF_01 Detail 생성 (KRPUS)
        ProformaScheduleDetail.objects.create(
            proforma=pf_01_master,
            calling_port_seq=1,
            calling_port_indicator="1",
            direction="E",
            port_code="KRPUS",
            terminal_code="KRPUS01",
            etb_day_code="MON",
            etb_day_time="0800",
            etb_day_number=0,
            created_by=user,
            updated_by=user,
        )

        # --- LANE_B: PF_02 ---
        # 2-3. PF_02 Master 생성
        pf_02_master = ProformaSchedule.objects.create(
            scenario=self.scenario,
            lane_code="LANE_B",
            proforma_name="PF_02",
            effective_from_date=timezone.now(),
            declared_count=3,
            duration=20.0,
            created_by=user,
            updated_by=user,
        )
        # 2-4. PF_02 Detail 생성 (JPTYO)
        ProformaScheduleDetail.objects.create(
            proforma=pf_02_master,
            calling_port_seq=1,
            calling_port_indicator="1",
            direction="W",
            port_code="JPTYO",
            terminal_code="JPTYO01",
            etb_day_code="SUN",
            etb_day_time="0800",
            etb_day_number=0,
            created_by=user,
            updated_by=user,
        )

        # 3. Vessel Capacity (Create 화면용)
        VesselCapacity.objects.create(
            scenario=self.scenario,
            vessel_code="V_CAP_1",
            vessel_capacity=10000,
            reefer_capacity=1000,
            created_by=user,
            updated_by=user,
        )

        # 4. Long Range Schedule (Check & List용)
        # - V_BUSY: LANE_X 점유 (오늘 ~ +10일)
        LongRangeSchedule.objects.create(
            scenario=self.scenario,
            lane_code="LANE_X",
            vessel_code="V_BUSY",
            voyage_number="0001",
            direction="E",
            port_code="PUS",
            calling_port_seq=1,
            etb=timezone.now(),  # 오늘 포함
            created_by=user,
            updated_by=user,
        )
        # - V_LRS_1: LANE_A (검색 필터 테스트용)
        LongRangeSchedule.objects.create(
            scenario=self.scenario,
            lane_code="LANE_A",
            vessel_code="V_LRS_1",
            voyage_number="0001",
            direction="E",
            port_code="PUS",
            calling_port_seq=1,
            etb=timezone.now(),
            created_by=user,
            updated_by=user,
        )

    # =========================================================
    # 1. Common / Distance Tests
    # =========================================================

    def test_api_dist_001_success(self):
        """[API_DIST_001] 거리 조회 (정상)"""
        url = reverse("api:port_distance")
        resp = self.client.get(
            url,
            {
                "scenario_id": self.scenario.id,
                "origin": "KRPUS",
                "destination": "JPTYO",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["distance"] == 500
        assert data["eac_distance"] == 100

    def test_api_dist_002_not_found(self):
        """[API_DIST_002] 거리 조회 (없음) -> 0 반환"""
        url = reverse("api:port_distance")
        resp = self.client.get(
            url,
            {
                "scenario_id": self.scenario.id,
                "origin": "KRPUS",
                "destination": "DDLAX",  # 없는 경로
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["distance"] == 0
        assert data["eac_distance"] == 0

    # =========================================================
    # 2. Proforma Related Tests (Cascade Select)
    # =========================================================

    def test_api_pf_001_lane_list(self):
        """[API_PF_001] Lane 목록 조회"""
        url = reverse("api:proforma_options")
        resp = self.client.get(url, {"scenario_id": self.scenario.id})

        assert resp.status_code == 200
        data = resp.json()
        assert "options" in data
        assert "LANE_A" in data["options"]
        assert "LANE_B" in data["options"]

    def test_api_pf_002_pf_list(self):
        """[API_PF_002] PF 명 목록 조회 (Lane 필터링)"""
        url = reverse("api:proforma_options")
        resp = self.client.get(
            url, {"scenario_id": self.scenario.id, "lane_code": "LANE_A"}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "PF_01" in data["options"]
        assert "PF_02" not in data["options"]  # Lane B 데이터는 없어야 함

    def test_api_pf_003_detail_success(self):
        """[API_PF_003] PF 상세 조회 (성공)"""
        url = reverse("api:proforma_detail")
        resp = self.client.get(
            url,
            {
                "scenario_id": self.scenario.id,
                "lane_code": "LANE_A",
                "proforma_name": "PF_01",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["duration"] == "10.0"
        assert data["declared_count"] == 2
        # Detail 테이블에 있는 월요일(MON) 값을 제대로 가져오는지 확인
        assert data["first_port_day"] == "MON"

    def test_api_pf_004_detail_fail(self):
        """[API_PF_004] PF 상세 조회 (실패 - 존재하지 않음)"""
        url = reverse("api:proforma_detail")
        resp = self.client.get(
            url,
            {
                "scenario_id": self.scenario.id,
                "lane_code": "LANE_A",
                "proforma_name": "INVALID_PF",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert "not found" in data["message"]

    # =========================================================
    # 3. Vessel Related Tests (List, Check, Options)
    # =========================================================

    def test_api_vsl_001_capacity_list(self):
        """[API_VSL_001] 선박 목록 조회 (Capacity - Create 화면용)"""
        url = reverse("api:vessel_list")
        resp = self.client.get(url, {"scenario_id": self.scenario.id})

        assert resp.status_code == 200
        data = resp.json()
        vessels = data["vessels"]

        v_cap = next((v for v in vessels if v["vessel_code"] == "V_CAP_1"), None)
        assert v_cap is not None
        assert v_cap["max_cap"] == 10000

    def test_api_vsl_002_check_busy(self):
        """[API_VSL_002] 점유 확인 (Busy - Lane Code 반환)"""
        url = reverse("api:vessel_lane_check")

        today_str = timezone.now().strftime("%Y-%m-%d")

        resp = self.client.get(
            url,
            {
                "scenario_id": self.scenario.id,
                "vessel_code": "V_BUSY",
                "start_date": today_str,
                "end_date": today_str,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["lane_code"] == "LANE_X"

    def test_api_vsl_003_check_free(self):
        """[API_VSL_003] 점유 확인 (Free - 빈 값 반환)"""
        url = reverse("api:vessel_lane_check")
        today_str = timezone.now().strftime("%Y-%m-%d")

        resp = self.client.get(
            url,
            {
                "scenario_id": self.scenario.id,
                "vessel_code": "V_FREE",
                "start_date": today_str,
                "end_date": today_str,
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["lane_code"] == ""

    def test_api_vsl_004_options_filter(self):
        """[API_VSL_004] 선박 옵션 (검색용 - Lane 필터링)"""
        url = reverse("api:vessel_options")

        resp = self.client.get(
            url, {"scenario_id": self.scenario.id, "lane_code": "LANE_A"}
        )

        assert resp.status_code == 200
        data = resp.json()

        assert "options" in data
        options = data["options"]

        assert "V_LRS_1" in options
        assert "V_BUSY" not in options
