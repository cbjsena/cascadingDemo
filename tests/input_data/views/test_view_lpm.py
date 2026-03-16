"""
Lane Proforma Mapping View Tests
Test Scenarios: IN_LPM_001~004, IN_LPM_005~003, IN_LPM_008~002

※ conftest.py의 lane_proforma_scenario / lane_proforma_with_mapping fixture 사용
"""

from django.urls import reverse

import pytest

from input_data.models import LaneProformaMapping


# ==========================================================================
# 1. View (화면 진입) — IN_LPM_001 ~ 004
# ==========================================================================
@pytest.mark.django_db
class TestLaneProformaMappingView:
    """
    Lane Proforma Mapping 편집 화면 테스트
    """

    def test_lpm_view_001_init(self, auth_client):
        """
        [IN_LPM_001] Lane Proforma Mapping 편집 화면 초기 진입
        시나리오 미선택 시 빈 화면 정상 로드 확인
        """
        url = reverse("input_data:lane_proforma_mapping")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "input_data/lane_proforma_mapping.html" in [
            t.name for t in response.templates
        ]
        assert response.context["mapping_data"] == []
        assert response.context["is_readonly"] is False

    def test_lpm_view_002_scenario_select(self, auth_client, lane_proforma_scenario):
        """
        [IN_LPM_002] 시나리오 선택 시 Lane별 Proforma 목록 표시
        같은 Lane에 2개 Proforma, 다른 Lane에 1개 Proforma가 정확히 표시되는지 확인
        """
        data = lane_proforma_scenario
        url = reverse("input_data:lane_proforma_mapping")
        response = auth_client.get(url, {"scenario_id": data["scenario"].id})

        assert response.status_code == 200
        mapping_data = response.context["mapping_data"]

        # 2개 Lane (FE1, TEST_LANE)
        assert len(mapping_data) == 2

        # Lane별 proforma 수 확인
        lane_dict = {m["lane_code"]: m for m in mapping_data}
        assert lane_dict["TEST_LANE"]["proforma_count"] == 2
        assert lane_dict["FE1"]["proforma_count"] == 1

        # 타임라인 주차가 생성되었는지 확인
        timeline_weeks = response.context["timeline_weeks"]
        assert len(timeline_weeks) > 0

    def test_lpm_view_003_existing_mapping_checked(
        self, auth_client, lane_proforma_with_mapping
    ):
        """
        [IN_LPM_003] 기존 매핑이 있을 때 체크 상태 표시
        저장된 매핑이 화면에 체크된 상태로 표시되는지 확인
        """
        data = lane_proforma_with_mapping
        url = reverse("input_data:lane_proforma_mapping")
        response = auth_client.get(url, {"scenario_id": data["scenario"].id})

        assert response.status_code == 200
        mapping_data = response.context["mapping_data"]

        # TEST_LANE: 2개 모두 선택됨
        test_lane = next(m for m in mapping_data if m["lane_code"] == "TEST_LANE")
        assert test_lane["selected_count"] == 2
        for pf_item in test_lane["proforma_items"]:
            assert pf_item["is_selected"] is True

        # FE1: 1개 선택됨
        fe1_lane = next(m for m in mapping_data if m["lane_code"] == "FE1")
        assert fe1_lane["selected_count"] == 1

    def test_lpm_view_004_timeline_effective_period(
        self, auth_client, lane_proforma_with_mapping
    ):
        """
        [IN_LPM_004] 겹침 구간 처리 - 타임라인 기간 분할 검증
        같은 Lane에 6101(2026-01-01~)과 6102(2026-07-02~)가 선택될 때
        6101의 effective 기간이 6102 시작 전날까지로 잘리는지 확인
        """
        data = lane_proforma_with_mapping
        url = reverse("input_data:lane_proforma_mapping")
        response = auth_client.get(url, {"scenario_id": data["scenario"].id})

        assert response.status_code == 200
        mapping_data = response.context["mapping_data"]

        test_lane = next(m for m in mapping_data if m["lane_code"] == "TEST_LANE")
        pf1_item = next(
            p
            for p in test_lane["proforma_items"]
            if p["proforma"].proforma_name == "6101"
        )
        pf2_item = next(
            p
            for p in test_lane["proforma_items"]
            if p["proforma"].proforma_name == "6102"
        )

        # 6101의 effective는 6102 시작(7/2) 전에 끊어야 함
        pf1_cells = pf1_item["cells"]
        pf1_effective_cells = [c for c in pf1_cells if c["effective"]]
        pf1_in_range_cells = [c for c in pf1_cells if c["in_range"]]
        # effective 셀 수 < in_range 셀 수 (6102에 의해 잘렸으므로)
        assert len(pf1_effective_cells) < len(pf1_in_range_cells)

        # 6102의 effective는 시작일 이후부터
        pf2_cells = pf2_item["cells"]
        pf2_effective_cells = [c for c in pf2_cells if c["effective"]]
        assert len(pf2_effective_cells) > 0


# ==========================================================================
# 2. Action (저장) — IN_LPM_005 ~ 003
# ==========================================================================
@pytest.mark.django_db
class TestLaneProformaMappingAction:
    """
    Lane Proforma Mapping 액션 테스트
    """

    def test_lpm_act_001_save_mapping(self, auth_client, lane_proforma_scenario):
        """
        [IN_LPM_005] Proforma 매핑 저장
        선택한 Proforma가 LaneProformaMapping에 정상 저장되는지 검증
        """
        data = lane_proforma_scenario
        url = reverse("input_data:lane_proforma_mapping")

        form_data = {
            "scenario_id": data["scenario"].id,
            "selected_proformas": [str(data["pf1"].id), str(data["pf3"].id)],
        }
        response = auth_client.post(url, data=form_data)

        assert response.status_code == 302

        mappings = LaneProformaMapping.objects.filter(scenario=data["scenario"])
        assert mappings.count() == 2

        mapped_pf_ids = set(mappings.values_list("proforma_id", flat=True))
        assert data["pf1"].id in mapped_pf_ids
        assert data["pf3"].id in mapped_pf_ids

    def test_lpm_act_002_update_mapping(self, auth_client, lane_proforma_with_mapping):
        """
        [IN_LPM_006] 매핑 수정 (덮어쓰기)
        기존 매핑(3건) 삭제 후 새 매핑(1건)으로 교체되는지 검증
        """
        data = lane_proforma_with_mapping
        assert (
            LaneProformaMapping.objects.filter(scenario=data["scenario"]).count() == 3
        )

        url = reverse("input_data:lane_proforma_mapping")
        form_data = {
            "scenario_id": data["scenario"].id,
            "selected_proformas": [str(data["pf2"].id)],
        }
        response = auth_client.post(url, data=form_data)

        assert response.status_code == 302

        mappings = LaneProformaMapping.objects.filter(scenario=data["scenario"])
        assert mappings.count() == 1
        assert mappings.first().proforma_id == data["pf2"].id

    def test_lpm_act_003_clear_mapping(self, auth_client, lane_proforma_with_mapping):
        """
        [IN_LPM_007] 매핑 전체 해제
        아무것도 선택하지 않고 저장하면 기존 매핑이 모두 삭제되는지 검증
        """
        data = lane_proforma_with_mapping
        url = reverse("input_data:lane_proforma_mapping")
        form_data = {
            "scenario_id": data["scenario"].id,
        }
        response = auth_client.post(url, data=form_data)

        assert response.status_code == 302
        assert (
            LaneProformaMapping.objects.filter(scenario=data["scenario"]).count() == 0
        )


# ==========================================================================
# 3. List (조회 - readonly) — IN_LPM_008 ~ 002
# ==========================================================================
@pytest.mark.django_db
class TestLaneProformaMappingList:
    """
    Lane Proforma Mapping 조회 화면 테스트
    """

    def test_lpm_list_001_view(self, auth_client, lane_proforma_with_mapping):
        """
        [IN_LPM_008] Lane Proforma Mapping 조회 화면
        Input Management 메뉴의 조회 화면이 readonly로 정상 표시되는지 검증
        """
        data = lane_proforma_with_mapping
        url = reverse("input_data:lane_proforma_list")
        response = auth_client.get(url, {"scenario_id": data["scenario"].id})

        assert response.status_code == 200
        assert response.context["is_readonly"] is True

        mapping_data = response.context["mapping_data"]
        assert len(mapping_data) == 2

        # 데이터는 편집 화면과 동일하게 표시됨
        test_lane = next(m for m in mapping_data if m["lane_code"] == "TEST_LANE")
        assert test_lane["selected_count"] == 2

    def test_lpm_list_002_init_no_scenario(self, auth_client):
        """
        [IN_LPM_009] 조회 화면 초기 진입
        시나리오 미선택 시 빈 화면 정상 로드 및 readonly 플래그 확인
        """
        url = reverse("input_data:lane_proforma_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert response.context["is_readonly"] is True
        assert response.context["mapping_data"] == []
