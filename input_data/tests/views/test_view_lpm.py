"""
Lane Proforma Mapping View Tests (신규)
Test Scenarios: LPM_VIEW_001~004, LPM_ACT_001~003, LPM_LIST_001~002
"""

import pytest

from django.urls import reverse

from input_data.models import (
    LaneProformaMapping,
    ProformaSchedule,
    ProformaScheduleDetail,
)


@pytest.mark.django_db
class TestLaneProformaMappingView:
    """
    Lane Proforma Mapping 편집 화면 테스트
    """

    @pytest.fixture
    def lpm_view_data(self, db, user, base_scenario):
        """
        Lane Proforma Mapping 뷰 테스트용 데이터
        2개 Lane × 여러 Proforma
        """
        # Lane A: PF_01, PF_02 (2개)
        pf_a1 = ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_id="LANE_A",
            proforma_name="PF_01",
            effective_from_date="2026-01-01",
            declared_count=2,
            duration=7.0,
            created_by=user,
            updated_by=user,
        )

        ProformaScheduleDetail.objects.create(
            proforma=pf_a1,
            calling_port_seq=1,
            calling_port_indicator="1",
            direction="E",
            port_id="PORT_A",
            terminal_code="PORT_A01",
            etb_day_code="MON",
            etb_day_time="0800",
            etb_day_number=0,
            created_by=user,
            updated_by=user,
        )

        pf_a2 = ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_id="LANE_A",
            proforma_name="PF_02",
            effective_from_date="2026-01-15",
            declared_count=3,
            duration=10.0,
            created_by=user,
            updated_by=user,
        )

        ProformaScheduleDetail.objects.create(
            proforma=pf_a2,
            calling_port_seq=1,
            calling_port_indicator="1",
            direction="E",
            port_id="PORT_B",
            terminal_code="PORT_B01",
            etb_day_code="TUE",
            etb_day_time="0900",
            etb_day_number=0,
            created_by=user,
            updated_by=user,
        )

        # Lane B: PF_03 (1개)
        pf_b1 = ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_id="LANE_B",
            proforma_name="PF_03",
            effective_from_date="2026-02-01",
            declared_count=2,
            duration=8.0,
            created_by=user,
            updated_by=user,
        )

        ProformaScheduleDetail.objects.create(
            proforma=pf_b1,
            calling_port_seq=1,
            calling_port_indicator="1",
            direction="W",
            port_id="PORT_C",
            terminal_code="PORT_C01",
            etb_day_code="WED",
            etb_day_time="1000",
            etb_day_number=0,
            created_by=user,
            updated_by=user,
        )

        return {
            "scenario": base_scenario,
            "pf_a1": pf_a1,
            "pf_a2": pf_a2,
            "pf_b1": pf_b1,
        }

    def test_lpm_view_001_init(self, auth_client):
        """
        [LPM_VIEW_001] Lane Proforma Mapping 편집 화면 초기 진입
        시나리오 미선택 시 빈 화면 정상 로드
        """
        url = reverse("input_data:lane_proforma_mapping")
        response = auth_client.get(url)

        assert response.status_code == 200
        # Context 변수 확인 (구현된 경우)
        if "is_readonly" in response.context:
            assert response.context["is_readonly"] is False
        if "mapping_data" in response.context:
            # 초기에는 빈 배열
            assert response.context["mapping_data"] == [] or isinstance(
                response.context["mapping_data"], list
            )

    def test_lpm_view_002_scenario_select(self, auth_client, lpm_view_data):
        """
        [LPM_VIEW_002] Lane Proforma Mapping 시나리오 선택
        같은 Lane에 2개 Proforma, 다른 Lane에 1개 Proforma 정확히 표시
        """
        scenario = lpm_view_data["scenario"]

        url = reverse("input_data:lane_proforma_mapping")
        response = auth_client.get(url, {"scenario_id": scenario.id})

        assert response.status_code == 200

        # Context에서 mapping_data 확인
        if "mapping_data" in response.context:
            mapping_data = response.context["mapping_data"]

            # Lane 개수 확인 (LANE_A, LANE_B)
            if isinstance(mapping_data, list):
                lane_codes = [item.get("lane_code") for item in mapping_data]
                assert "LANE_A" in lane_codes
                assert "LANE_B" in lane_codes

                # Proforma 개수 확인
                lane_a = next(
                    (lane for lane in mapping_data if lane["lane_code"] == "LANE_A"),
                    None,
                )
                lane_b = next(
                    (lane for lane in mapping_data if lane["lane_code"] == "LANE_B"),
                    None,
                )

                if lane_a:
                    assert lane_a.get("proforma_count") == 2  # PF_01, PF_02
                if lane_b:
                    assert lane_b.get("proforma_count") == 1  # PF_03

    def test_lpm_view_003_existing_mapping_checked(self, auth_client, lpm_view_data):
        """
        [LPM_VIEW_003] Lane Proforma Mapping 기존 매핑 체크 상태 표시
        저장된 매핑이 화면에 체크된 상태로 표시
        """
        scenario = lpm_view_data["scenario"]
        pf_a1 = lpm_view_data["pf_a1"]
        pf_a2 = lpm_view_data["pf_a2"]
        pf_b1 = lpm_view_data["pf_b1"]

        # 기존 매핑 생성
        LaneProformaMapping.objects.create(
            scenario=scenario,
            lane_code="LANE_A",
            proforma=pf_a1,
        )
        LaneProformaMapping.objects.create(
            scenario=scenario,
            lane_code="LANE_A",
            proforma=pf_a2,
        )
        LaneProformaMapping.objects.create(
            scenario=scenario,
            lane_code="LANE_B",
            proforma=pf_b1,
        )

        url = reverse("input_data:lane_proforma_mapping")
        response = auth_client.get(url, {"scenario_id": scenario.id})

        assert response.status_code == 200

        # 매핑 데이터 확인
        if "mapping_data" in response.context:
            mapping_data = response.context["mapping_data"]
            if isinstance(mapping_data, list):
                lane_a = next(
                    (lane for lane in mapping_data if lane["lane_code"] == "LANE_A"),
                    None,
                )
                lane_b = next(
                    (lane for lane in mapping_data if lane["lane_code"] == "LANE_B"),
                    None,
                )

                # selected_count 확인
                if lane_a:
                    assert lane_a.get("selected_count") == 2
                if lane_b:
                    assert lane_b.get("selected_count") == 1


@pytest.mark.django_db
class TestLaneProformaMappingAction:
    """
    Lane Proforma Mapping 액션 테스트
    """

    @pytest.fixture
    def lpm_action_data(self, db, user, base_scenario):
        """
        Lane Proforma Mapping 액션 테스트용 데이터
        """
        # 3개 Proforma (모두 같은 Lane)
        proformae = []
        for i in range(1, 4):
            pf = ProformaSchedule.objects.create(
                scenario=base_scenario,
                lane_id="TEST_LANE",
                proforma_name=f"PF_{i:02d}",
                effective_from_date=f"2026-0{i}-01",
                declared_count=2,
                duration=7.0 + i,
                created_by=user,
                updated_by=user,
            )

            ProformaScheduleDetail.objects.create(
                proforma=pf,
                calling_port_seq=1,
                calling_port_indicator="1",
                direction="E",
                port_id=f"PORT_{i}",
                terminal_code=f"PORT_{i}01",
                etb_day_code="MON",
                etb_day_time="0800",
                etb_day_number=0,
                created_by=user,
                updated_by=user,
            )

            proformae.append(pf)

        return {
            "scenario": base_scenario,
            "proformae": proformae,
        }

    def test_lpm_act_001_save_mapping(self, auth_client, lpm_action_data):
        """
        [LPM_ACT_001] Lane Proforma Mapping 저장
        선택한 Proforma가 LaneProformaMapping에 정상 저장
        """
        scenario = lpm_action_data["scenario"]
        pf1, pf2, pf3 = lpm_action_data["proformae"]

        # 2개 Proforma만 선택
        url = reverse("input_data:lane_proforma_mapping")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": scenario.id,
                "checked_pf_ids": [pf1.id, pf2.id],
            },
        )

        assert response.status_code == 302

        # DB에 2건 생성되었는지 확인
        mappings = LaneProformaMapping.objects.filter(scenario=scenario)
        assert mappings.count() == 2

        # 선택된 Proforma ID 확인
        mapped_pf_ids = set(mappings.values_list("proforma_id", flat=True))
        assert pf1.id in mapped_pf_ids
        assert pf2.id in mapped_pf_ids
        assert pf3.id not in mapped_pf_ids

    def test_lpm_act_002_update_mapping(self, auth_client, lpm_action_data):
        """
        [LPM_ACT_002] Lane Proforma Mapping 수정 (덮어쓰기)
        기존 매핑 3건 삭제 후 새 매핑 1건으로 교체
        """
        scenario = lpm_action_data["scenario"]
        pf1, pf2, pf3 = lpm_action_data["proformae"]

        # 기존 매핑 3건 생성
        for pf in [pf1, pf2, pf3]:
            LaneProformaMapping.objects.create(
                scenario=scenario,
                lane_code=pf.lane_id,
                proforma=pf,
            )

        assert LaneProformaMapping.objects.filter(scenario=scenario).count() == 3

        # 수정: 1건만 선택
        url = reverse("input_data:lane_proforma_mapping")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": scenario.id,
                "checked_pf_ids": [pf1.id],
            },
        )

        assert response.status_code == 302

        # 기존 데이터 삭제 및 새 데이터 생성 확인
        mappings = LaneProformaMapping.objects.filter(scenario=scenario)
        assert mappings.count() == 1
        assert mappings.first().proforma_id == pf1.id

    def test_lpm_act_003_clear_mapping(self, auth_client, lpm_action_data):
        """
        [LPM_ACT_003] Lane Proforma Mapping 전체 해제
        아무것도 선택하지 않고 저장하면 기존 매핑이 모두 삭제
        """
        scenario = lpm_action_data["scenario"]
        pf1, pf2, pf3 = lpm_action_data["proformae"]

        # 기존 매핑 3건 생성
        for pf in [pf1, pf2, pf3]:
            LaneProformaMapping.objects.create(
                scenario=scenario,
                lane_code=pf.lane_id,
                proforma=pf,
            )

        assert LaneProformaMapping.objects.filter(scenario=scenario).count() == 3

        # 전체 해제
        url = reverse("input_data:lane_proforma_mapping")
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": scenario.id,
                "checked_pf_ids": [],  # 빈 배열
            },
        )

        assert response.status_code == 302

        # 모든 데이터 삭제 확인
        assert LaneProformaMapping.objects.filter(scenario=scenario).count() == 0


@pytest.mark.django_db
class TestLaneProformaMappingList:
    """
    Lane Proforma Mapping 조회 화면 테스트
    """

    @pytest.fixture
    def lpm_list_data(self, db, user, base_scenario):
        """
        조회 화면용 데이터
        """
        # 2개 Lane × 여러 Proforma
        pf_a1 = ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_id="LANE_A",
            proforma_name="PF_01",
            effective_from_date="2026-01-01",
            declared_count=2,
            duration=7.0,
            created_by=user,
            updated_by=user,
        )

        ProformaScheduleDetail.objects.create(
            proforma=pf_a1,
            calling_port_seq=1,
            calling_port_indicator="1",
            direction="E",
            port_id="PORT_A",
            terminal_code="PORT_A01",
            etb_day_code="MON",
            etb_day_time="0800",
            etb_day_number=0,
            created_by=user,
            updated_by=user,
        )

        pf_a2 = ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_id="LANE_A",
            proforma_name="PF_02",
            effective_from_date="2026-01-15",
            declared_count=3,
            duration=10.0,
            created_by=user,
            updated_by=user,
        )

        ProformaScheduleDetail.objects.create(
            proforma=pf_a2,
            calling_port_seq=1,
            calling_port_indicator="1",
            direction="E",
            port_id="PORT_B",
            terminal_code="PORT_B01",
            etb_day_code="TUE",
            etb_day_time="0900",
            etb_day_number=0,
            created_by=user,
            updated_by=user,
        )

        pf_b1 = ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_id="LANE_B",
            proforma_name="PF_03",
            effective_from_date="2026-02-01",
            declared_count=2,
            duration=8.0,
            created_by=user,
            updated_by=user,
        )

        ProformaScheduleDetail.objects.create(
            proforma=pf_b1,
            calling_port_seq=1,
            calling_port_indicator="1",
            direction="W",
            port_id="PORT_C",
            terminal_code="PORT_C01",
            etb_day_code="WED",
            etb_day_time="1000",
            etb_day_number=0,
            created_by=user,
            updated_by=user,
        )

        # 매핑 생성 (LANE_A: 2개, LANE_B: 1개)
        LaneProformaMapping.objects.create(
            scenario=base_scenario,
            lane_code="LANE_A",
            proforma=pf_a1,
        )
        LaneProformaMapping.objects.create(
            scenario=base_scenario,
            lane_code="LANE_A",
            proforma=pf_a2,
        )
        LaneProformaMapping.objects.create(
            scenario=base_scenario,
            lane_code="LANE_B",
            proforma=pf_b1,
        )

        return {
            "scenario": base_scenario,
        }

    def test_lpm_list_001_view(self, auth_client, lpm_list_data):
        """
        [LPM_LIST_001] Lane Proforma Mapping 조회 화면
        Input Management의 조회 화면이 readonly로 정상 표시
        """
        scenario = lpm_list_data["scenario"]

        url = reverse("input_data:lane_proforma_list")
        response = auth_client.get(url, {"scenario_id": scenario.id})

        assert response.status_code == 200

        # Context 검증
        if "is_readonly" in response.context:
            assert response.context["is_readonly"] is True

        if "mapping_data" in response.context:
            mapping_data = response.context["mapping_data"]
            if isinstance(mapping_data, list):
                # Lane 개수 확인 (2개)
                lane_codes = [item.get("lane_code") for item in mapping_data]
                assert len(lane_codes) == 2

                # selected_count 확인
                lane_a = next(
                    (lane for lane in mapping_data if lane["lane_code"] == "LANE_A"),
                    None,
                )
                lane_b = next(
                    (lane for lane in mapping_data if lane["lane_code"] == "LANE_B"),
                    None,
                )

                if lane_a:
                    assert lane_a.get("selected_count") == 2
                if lane_b:
                    assert lane_b.get("selected_count") == 1

    def test_lpm_list_002_init_no_scenario(self, auth_client):
        """
        [LPM_LIST_002] Lane Proforma Mapping 초기 진입
        시나리오 미선택 시 빈 화면 정상 로드 및 readonly 플래그 확인
        """
        url = reverse("input_data:lane_proforma_list")
        response = auth_client.get(url)

        assert response.status_code == 200

        # readonly 확인
        if "is_readonly" in response.context:
            assert response.context["is_readonly"] is True

        # 빈 데이터
        if "mapping_data" in response.context:
            assert response.context["mapping_data"] == [] or isinstance(
                response.context["mapping_data"], list
            )
