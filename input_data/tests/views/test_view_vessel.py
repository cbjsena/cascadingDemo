"""
Vessel 화면 테스트
Test Scenarios: VESSEL_INFO_001~006, CHARTER_COST_001~003,
                VESSEL_CAP_001~003, VESSEL_ONCHANGE_001
"""

import pytest

from django.urls import reverse
from django.utils import timezone

from input_data.models import (
    BaseVesselInfo,
    CharterCost,
    ScenarioInfo,
    VesselCapacity,
    VesselInfo,
)


@pytest.fixture
def vessel_scenario(db, user):
    """Vessel 테스트용 시나리오 2개"""
    s1 = ScenarioInfo.objects.create(
        code="SC_VSL_01",
        description="Vessel Test 1",
        scenario_type="WHAT_IF",
        status="ACTIVE",
        created_by=user,
        updated_by=user,
    )
    s2 = ScenarioInfo.objects.create(
        code="SC_VSL_02",
        description="Vessel Test 2",
        scenario_type="WHAT_IF",
        status="ACTIVE",
        created_by=user,
        updated_by=user,
    )
    return s1, s2


@pytest.fixture
def vessel_data(db, vessel_scenario, user):
    """VesselInfo 테스트 데이터"""
    s1, s2 = vessel_scenario
    v1 = VesselInfo.objects.create(
        scenario=s1,
        vessel_code="V001",
        vessel_name="TestShip1",
        own_yn="O",
        created_by=user,
        updated_by=user,
    )
    v2 = VesselInfo.objects.create(
        scenario=s1,
        vessel_code="V002",
        vessel_name="TestShip2",
        own_yn="C",
        created_by=user,
        updated_by=user,
    )
    v3 = VesselInfo.objects.create(
        scenario=s2,
        vessel_code="V003",
        vessel_name="TestShip3",
        own_yn="O",
        created_by=user,
        updated_by=user,
    )
    return {"s1": s1, "s2": s2, "v1": v1, "v2": v2, "v3": v3}


@pytest.fixture
def base_vessel_data(db):
    """Base Vessel Info 테스트 데이터 (Add Row select용)"""
    BaseVesselInfo.objects.create(
        vessel_code="V001", vessel_name="Base Ship 1", own_yn="O"
    )
    BaseVesselInfo.objects.create(
        vessel_code="V002", vessel_name="Base Ship 2", own_yn="C"
    )


@pytest.mark.django_db
class TestVesselInfoView:
    """Vessel Info 목록/필터/추가/삭제 테스트"""

    def test_vessel_info_list(self, auth_client, vessel_data):
        """
        [VESSEL_INFO_001] Vessel Info 목록 조회 및 시나리오 드롭다운 검증
        """
        url = reverse("input_data:vessel_info_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "scenarios" in response.context
        assert "search_params" in response.context
        assert len(response.context["scenarios"]) >= 2

    def test_vessel_info_scenario_filter(self, auth_client, vessel_data):
        """
        [VESSEL_INFO_002] 시나리오 선택 시 해당 데이터만 표시
        """
        s1 = vessel_data["s1"]
        url = reverse("input_data:vessel_info_list")
        response = auth_client.get(url, {"scenario_id": s1.id})

        items = response.context["items"]
        codes = [item.vessel_code for item in items]
        assert "V001" in codes
        assert "V002" in codes
        assert "V003" not in codes  # s2의 데이터는 안 보여야 함

    def test_vessel_info_search(self, auth_client, vessel_data):
        """
        [VESSEL_INFO_003] 코드/이름 검색 필터링
        """
        s1 = vessel_data["s1"]
        url = reverse("input_data:vessel_info_list")
        response = auth_client.get(
            url,
            {
                "scenario_id": s1.id,
                "search": "V001",
            },
        )

        items = response.context["items"]
        codes = [item.vessel_code for item in items]
        assert "V001" in codes
        assert "V002" not in codes

    def test_vessel_info_add_row_save(self, auth_client, vessel_data, base_vessel_data):
        """
        [VESSEL_INFO_004] Add Row 저장 (Base Vessel Select 기반)
        """
        s1 = vessel_data["s1"]
        url = reverse("input_data:vessel_info_list")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": s1.id,
                "new_vessel_code_0": "V001",
                "new_vessel_name_0": "Base Ship 1",
                "new_own_yn_0": "O",
            },
        )

        assert response.status_code == 302
        assert f"scenario_id={s1.id}" in response.url
        assert VesselInfo.objects.filter(scenario=s1, vessel_code="V001").exists()

    def test_vessel_info_duplicate_vessel_code(
        self, auth_client, vessel_data, base_vessel_data
    ):
        """
        [VESSEL_INFO_007] 동일 scenario+vessel_code 중복 저장 시 skip + 경고 메시지
        """
        from django.contrib.messages import get_messages

        s1 = vessel_data["s1"]
        # V001은 vessel_data fixture에서 이미 s1에 존재
        url = reverse("input_data:vessel_info_list")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": s1.id,
                "new_vessel_code_0": "V001",
                "new_vessel_name_0": "Base Ship 1",
                "new_own_yn_0": "O",
            },
            follow=True,
        )

        msgs = [str(m) for m in get_messages(response.wsgi_request)]
        assert any("skipped" in m for m in msgs)
        # 기존 데이터가 덮어써지지 않았는지 확인 (이름 변경 안 됨)
        obj = VesselInfo.objects.get(scenario=s1, vessel_code="V001")
        assert obj.vessel_name == "TestShip1"  # 원래 이름 유지

    def test_vessel_info_add_with_all_fields(
        self, auth_client, vessel_data, base_vessel_data
    ):
        """
        [VESSEL_INFO_008] 모달에서 전체 필드(Delivery/Redelivery/Dock) 입력하여 저장
        """
        s1 = vessel_data["s1"]
        url = reverse("input_data:vessel_info_list")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": s1.id,
                "new_vessel_code_0": "V099",
                "new_vessel_name_0": "Full Field Ship",
                "new_own_yn_0": "C",
                "new_delivery_port_0": "KRPUS",
                "new_delivery_date_0": "2026-06-01",
                "new_redelivery_port_0": "CNSHA",
                "new_redelivery_date_0": "2027-06-01",
                "new_dock_port_0": "SGSIN",
                "new_dock_in_0": "2026-09-01",
                "new_dock_out_0": "2026-09-15",
            },
        )

        assert response.status_code == 302
        obj = VesselInfo.objects.get(scenario=s1, vessel_code="V099")
        assert obj.delivery_port_code == "KRPUS"
        assert obj.delivery_date is not None
        assert obj.redelivery_port_code == "CNSHA"
        assert obj.next_dock_port_code == "SGSIN"
        assert obj.next_dock_in_date is not None
        assert obj.next_dock_out_date is not None

    def test_vessel_info_delete(self, auth_client, vessel_data):
        """
        [VESSEL_INFO_005] 선택 Vessel 삭제
        """
        v1 = vessel_data["v1"]
        s1 = vessel_data["s1"]
        url = reverse("input_data:vessel_info_list")
        response = auth_client.post(
            url,
            {
                "action": "delete",
                "scenario_id": s1.id,
                "selected_pks": [v1.pk],
            },
        )

        assert response.status_code == 302
        assert f"scenario_id={s1.id}" in response.url
        assert not VesselInfo.objects.filter(pk=v1.pk).exists()

    def test_vessel_info_no_scenario_add_row_blocked(self, auth_client):
        """
        [VESSEL_INFO_006] 시나리오 미선택 시 JS alert (서버측은 빈 scenario_id)
        Save 시 scenario_id 없으면 생성 안 됨
        """
        url = reverse("input_data:vessel_info_list")
        before_count = VesselInfo.objects.count()

        auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": "",  # 빈 값
                "new_vessel_code_0": "V_NO_SCE",
                "new_vessel_name_0": "No Scenario",
                "new_own_yn_0": "O",
            },
        )

        # scenario_id 없으면 생성 안 되어야 함
        assert VesselInfo.objects.count() == before_count

    def test_vessel_info_onchange_auto_submit(self, auth_client, vessel_data):
        """
        [VESSEL_ONCHANGE_001] Scenario select onchange 자동 submit 확인
        (서버 관점: scenario_id 파라미터가 URL에 반영되면 정상)
        """
        s1 = vessel_data["s1"]
        url = reverse("input_data:vessel_info_list")
        response = auth_client.get(url, {"scenario_id": s1.id})

        assert response.status_code == 200
        ctx = response.context
        assert ctx["search_params"]["scenario_id"] == str(s1.id)

        # HTML에 onchange="this.form.submit()" 포함 확인
        content = response.content.decode("utf-8")
        assert 'onchange="this.form.submit()"' in content


@pytest.mark.django_db
class TestCharterCostView:
    """Charter Cost 목록/필터/추가 테스트"""

    @pytest.fixture
    def charter_data(self, db, vessel_scenario, user):
        s1, s2 = vessel_scenario
        today = timezone.now().date()
        c1 = CharterCost.objects.create(
            scenario=s1,
            vessel_code="V001",
            hire_from_date=today,
            hire_to_date=today,
            hire_rate=10000.00,
            created_by=user,
            updated_by=user,
        )
        c2 = CharterCost.objects.create(
            scenario=s2,
            vessel_code="V002",
            hire_from_date=today,
            hire_to_date=today,
            hire_rate=20000.00,
            created_by=user,
            updated_by=user,
        )
        return {"s1": s1, "s2": s2, "c1": c1, "c2": c2}

    def test_charter_cost_list(self, auth_client, charter_data):
        """
        [CHARTER_COST_001] Charter Cost 목록 조회
        """
        url = reverse("input_data:charter_cost_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "scenarios" in response.context

    def test_charter_cost_scenario_filter(self, auth_client, charter_data):
        """
        [CHARTER_COST_002] 시나리오 선택 시 필터링
        """
        s1 = charter_data["s1"]
        url = reverse("input_data:charter_cost_list")
        response = auth_client.get(url, {"scenario_id": s1.id})

        items = response.context["items"]
        codes = [item.vessel_code for item in items]
        assert "V001" in codes
        assert "V002" not in codes

    def test_charter_cost_add_row_save(
        self, auth_client, charter_data, base_vessel_data
    ):
        """
        [CHARTER_COST_003] 새 Charter Cost 추가 후 DB 저장
        """
        s1 = charter_data["s1"]
        url = reverse("input_data:charter_cost_list")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": s1.id,
                "new_vessel_code_0": "V001",
                "new_hire_from_0": "2026-01-01",
                "new_hire_to_0": "2026-12-31",
                "new_hire_rate_0": "15000.50",
            },
        )

        assert response.status_code == 302
        assert CharterCost.objects.filter(scenario=s1, vessel_code="V001").exists()


@pytest.mark.django_db
class TestVesselCapacityView:
    """Vessel Capacity 목록/필터/추가 테스트"""

    @pytest.fixture
    def capacity_data(self, db, vessel_scenario, user):
        s1, s2 = vessel_scenario
        cap1 = VesselCapacity.objects.create(
            scenario=s1,
            trade_id="ASIA",
            lane_id="FP1",
            vessel_code="V001",
            voyage_number="0001",
            direction="E",
            vessel_capacity=5000,
            reefer_capacity=100,
            created_by=user,
            updated_by=user,
        )
        return {"s1": s1, "s2": s2, "cap1": cap1}

    def test_vessel_capacity_list(self, auth_client, capacity_data):
        """
        [VESSEL_CAP_001] Vessel Capacity 목록 조회
        """
        url = reverse("input_data:vessel_capacity_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "scenarios" in response.context

    def test_vessel_capacity_scenario_filter_search(self, auth_client, capacity_data):
        """
        [VESSEL_CAP_002] 시나리오 + vessel/lane 코드 검색
        """
        s1 = capacity_data["s1"]
        url = reverse("input_data:vessel_capacity_list")
        response = auth_client.get(
            url,
            {
                "scenario_id": s1.id,
                "search": "V001",
            },
        )

        items = response.context["items"]
        assert len(items) >= 1
        assert items[0].vessel_code == "V001"

    def test_vessel_capacity_add_row_save(self, auth_client, capacity_data):
        """
        [VESSEL_CAP_003] 새 Vessel Capacity 추가 후 DB 저장
        """
        s1 = capacity_data["s1"]
        url = reverse("input_data:vessel_capacity_list")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": s1.id,
                "new_trade_code_0": "ASIA",
                "new_lane_code_0": "FP1",
                "new_vessel_code_0": "V099",
                "new_voyage_number_0": "0001",
                "new_direction_0": "E",
                "new_vessel_capacity_0": "8000",
                "new_reefer_capacity_0": "200",
            },
        )

        assert response.status_code == 302
        assert VesselCapacity.objects.filter(scenario=s1, vessel_code="V099").exists()
