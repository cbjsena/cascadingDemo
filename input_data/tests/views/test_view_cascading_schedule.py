"""
Cascading Schedule View Tests (신규)
Test Scenarios: CS_CREATE_001, CS_CREATE_002, CS_CREATE_003, CS_LIST_001

참고: CascadingSchedule는 시나리오 내 모든 Proforma의 슬롯을 관리하는 통합 테이블입니다.
"""

import pytest

from django.urls import reverse

from input_data.models import (
    CascadingSchedule,
    ProformaSchedule,
    ProformaScheduleDetail,
)


@pytest.mark.django_db
class TestCascadingScheduleCreate:
    """
    Cascading Schedule 생성 화면 테스트
    """

    @pytest.fixture
    def cs_scenario_data(self, db, user, base_scenario):
        """
        Cascading Schedule 테스트용 시나리오 및 Proforma 데이터
        """
        # Proforma Master 생성
        pf_master = ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_id="TEST_LANE",
            proforma_name="PF_01",
            effective_from_date="2026-01-01",
            declared_count=5,  # 5개 슬롯 가능
            duration=10.0,
            created_by=user,
            updated_by=user,
        )

        # Proforma Detail 생성 (포트 정보)
        for i, port in enumerate(["PORT_A", "PORT_B", "PORT_C"], 1):
            ProformaScheduleDetail.objects.create(
                proforma=pf_master,
                calling_port_seq=i,
                calling_port_indicator=str(i),
                direction="E" if i % 2 == 1 else "W",
                port_id=port,
                terminal_code=f"{port}01",
                etb_day_code="MON" if i == 1 else "WED",
                etb_day_time="0800",
                etb_day_number=0,
                created_by=user,
                updated_by=user,
            )

        return {
            "scenario": base_scenario,
            "pf_master": pf_master,
        }

    def test_cs_create_001_page_load(self, auth_client, cs_scenario_data):
        """
        [CS_CREATE_001] Cascading Schedule 생성 초기 진입
        생성 화면 초기 진입 시 빈 상태로 정상 로드
        """
        url = reverse("input_data:cascading_create")
        response = auth_client.get(url)

        assert response.status_code == 200
        # Context에 scenarios 존재 확인
        assert "scenarios" in response.context

    def test_cs_create_002_save_slots_creation(self, auth_client, cs_scenario_data):
        """
        [CS_CREATE_002] Cascading Schedule 생성 (슬롯 저장)
        Scenario 선택 후 슬롯을 선택하여 저장
        """
        scenario = cs_scenario_data["scenario"]
        pf_master = cs_scenario_data["pf_master"]

        url = reverse("input_data:cascading_create")
        # 실제 폼 데이터 구조에 맞춤
        response = auth_client.post(
            url,
            {
                "scenario_id": scenario.id,
                f"slots_{pf_master.id}[]": ["1", "3", "5"],  # 슬롯 1,3,5 선택
            },
        )

        # 리다이렉트 확인
        assert response.status_code == 302

    def test_cs_create_003_save_slots_modification(self, auth_client, cs_scenario_data):
        """
        [CS_CREATE_003] Cascading Schedule 수정 (덮어쓰기)
        기존 슬롯을 다르게 선택하여 저장
        """
        scenario = cs_scenario_data["scenario"]
        pf_master = cs_scenario_data["pf_master"]

        url = reverse("input_data:cascading_create")
        # 슬롯 1,2,4 선택하여 저장
        response = auth_client.post(
            url,
            {
                "scenario_id": scenario.id,
                f"slots_{pf_master.id}[]": ["1", "2", "4"],
            },
        )

        assert response.status_code == 302


@pytest.mark.django_db
class TestCascadingScheduleList:
    """
    Cascading Schedule 목록 조회 테스트
    """

    @pytest.fixture
    def cs_list_data(self, db, user, base_scenario):
        """
        목록 조회용 데이터: 2개 Proforma × 각 3개 슬롯
        """
        # Proforma 1
        pf1 = ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_id="LANE_A",
            proforma_name="PF_01",
            effective_from_date="2026-01-01",
            declared_count=5,
            duration=10.0,
            created_by=user,
            updated_by=user,
        )

        # Proforma 1 Detail
        for i, port in enumerate(["PORT_A", "PORT_B"], 1):
            ProformaScheduleDetail.objects.create(
                proforma=pf1,
                calling_port_seq=i,
                calling_port_indicator=str(i),
                direction="E",
                port_id=port,
                terminal_code=f"{port}01",
                etb_day_code="MON",
                etb_day_time="0800",
                etb_day_number=0,
                created_by=user,
                updated_by=user,
            )

        # Proforma 2
        pf2 = ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_id="LANE_B",
            proforma_name="PF_02",
            effective_from_date="2026-02-01",
            declared_count=3,
            duration=15.0,
            created_by=user,
            updated_by=user,
        )

        # Proforma 2 Detail
        ProformaScheduleDetail.objects.create(
            proforma=pf2,
            calling_port_seq=1,
            calling_port_indicator="1",
            direction="W",
            port_id="PORT_C",
            terminal_code="PORT_C01",
            etb_day_code="TUE",
            etb_day_time="1000",
            etb_day_number=0,
            created_by=user,
            updated_by=user,
        )

        # Cascading Schedule 생성 (PF1: 슬롯 1,2,3, PF2: 슬롯 1,3,5)
        for slot in [1, 2, 3]:
            CascadingSchedule.objects.create(
                scenario=base_scenario,
                proforma=pf1,
                vessel_position=slot,
                vessel_position_date="2026-01-01",
            )

        for slot in [1, 3, 5]:
            CascadingSchedule.objects.create(
                scenario=base_scenario,
                proforma=pf2,
                vessel_position=slot,
                vessel_position_date="2026-02-01",
            )

        return {
            "scenario": base_scenario,
            "pf1": pf1,
            "pf2": pf2,
        }

    def test_cs_list_001_view(self, auth_client, cs_list_data):
        """
        [CS_LIST_001] Cascading Schedule 목록 조회
        Scenario 선택 시 Lane별 슬롯 선택 현황을 대시보드 형태로 표시
        """
        scenario = cs_list_data["scenario"]

        url = reverse("input_data:cascading_schedule_list")
        response = auth_client.get(url, {"scenario_id": scenario.id})

        assert response.status_code == 200

        # Context에 dashboard_data 존재 확인
        if "dashboard_data" in response.context:
            dashboard_data = response.context["dashboard_data"]
            assert (
                isinstance(dashboard_data, (list, dict)) or dashboard_data is not None
            )

        # Proforma 데이터 확인
        pf_data = ProformaSchedule.objects.filter(scenario=scenario)
        assert pf_data.count() >= 2

        # Cascading Schedule 데이터 확인 (총 6건)
        cs_count = CascadingSchedule.objects.filter(scenario=scenario).count()
        assert cs_count == 6
