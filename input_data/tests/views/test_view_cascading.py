"""
Cascading View Tests
CASCADING_VIEW_*, CASCADING_ACT_*, CASCADING_VESSEL_INFO_*, CASCADING_DETAIL_* 시나리오 테스트
"""

import pytest

from django.urls import reverse

from input_data.models import CascadingVesselPosition, LaneProformaMapping


@pytest.mark.django_db
class TestCascadingView:
    """
    Cascading 생성 화면, 조회 화면 및 동작 테스트
    """

    # ==========================================================================
    # 1. View (화면 진입)
    # ==========================================================================
    def test_cascading_view_001_page_load(self, auth_client):
        """
        [CASCADING_VIEW_001] Cascading Vessel Creation 초기 진입
        생성 화면 초기 진입 시 빈 껍데기로 정상 로드되는지 확인
        """
        url = reverse("input_data:cascading_vessel_create")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "input_data/cascading_vessel_create.html" in [
            t.name for t in response.templates
        ]
        assert response.context["is_edit_mode"] is False
        assert response.context["preserved_data"] == {}
        assert len(response.context["restored_rows"]) == 0

    def test_cascading_view_003_edit_mode_load(
        self, auth_client, cascading_with_details
    ):
        """
        [CASCADING_VIEW_003] Edit 모드 데이터 Load
        기존 CascadingVesselPosition 데이터가 정확히 로드되는지 검증
        """
        first_pos = cascading_with_details[0]

        url = reverse("input_data:cascading_vessel_create")
        response = auth_client.get(
            url,
            {
                "scenario_id": first_pos.scenario.id,
                "lane_code": first_pos.proforma.lane_id,
                "proforma_name": first_pos.proforma.proforma_name,
            },
        )

        assert response.status_code == 200
        assert response.context["is_edit_mode"] is True

        preserved_data = response.context["preserved_data"]
        assert preserved_data["own_vessel_count"] == 2

        restored_rows = response.context["restored_rows"]
        assert len(restored_rows) >= 2

        checked_vessels = [row for row in restored_rows if row.get("is_checked")]
        assert len(checked_vessels) == 2

    # ==========================================================================
    # 2. Action (저장/수정/LRS)
    # ==========================================================================
    def test_cascading_act_001_save_creation(self, auth_client, cascading_form_data):
        """
        [CASCADING_ACT_001] Save Cascading (생성)
        CascadingVesselPosition에 정상 저장되는지 검증
        """
        url = reverse("input_data:cascading_vessel_create")
        form_data = cascading_form_data.copy()
        form_data["action"] = "save"

        response = auth_client.post(url, data=form_data)

        assert response.status_code == 302

        positions = CascadingVesselPosition.objects.all()
        assert positions.count() == 3

        proforma = positions.first().proforma
        assert proforma.own_vessel_count == 3

        vessel_codes = list(positions.values_list("vessel_code", flat=True))
        assert "V001" in vessel_codes
        assert "V002" in vessel_codes
        assert "V003" in vessel_codes

        # vessel_position_date 검증
        for pos in positions:
            assert pos.vessel_position_date is not None

    def test_cascading_act_002_save_modification(
        self, auth_client, cascading_with_details, cascading_form_data
    ):
        """
        [CASCADING_ACT_002] Save Cascading (수정)
        기존 CascadingVesselPosition 수정 시 덮어쓰기 로직 검증
        """
        first_pos = cascading_with_details[0]
        assert first_pos.proforma.own_vessel_count == 2

        url = reverse("input_data:cascading_vessel_create")
        form_data = cascading_form_data.copy()
        form_data.update(
            {
                "action": "save",
                "own_vessel_count": 5,
                "vessel_code[]": ["V001", "V002", "V003", "V004", "V005"],
                "vessel_capacity[]": ["5000"] * 5,
                "vessel_start_date[]": [
                    "2026-02-15",
                    "2026-02-22",
                    "2026-03-01",
                    "2026-03-08",
                    "2026-03-15",
                ],
                "lane_code_list[]": ["TEST_LANE"] * 5,
            }
        )

        response = auth_client.post(url, data=form_data)

        assert response.status_code == 302

        positions = CascadingVesselPosition.objects.filter(
            scenario=first_pos.scenario, proforma=first_pos.proforma
        )
        assert positions.count() == 5

        first_pos.proforma.refresh_from_db()
        assert first_pos.proforma.own_vessel_count == 5

        # vessel_position이 1~5 순번으로 저장됨
        position_nums = list(
            positions.order_by("vessel_position").values_list(
                "vessel_position", flat=True
            )
        )
        assert position_nums == [1, 2, 3, 4, 5]

    def test_cascading_act_003_create_lrs(self, auth_client, cascading_form_data):
        """
        [CASCADING_ACT_003] Create LRS
        저장 및 LRS 생성 엔진 구동 동시 수행
        """
        url = reverse("input_data:cascading_vessel_create")
        form_data = cascading_form_data.copy()
        form_data["action"] = "create_lrs"

        response = auth_client.post(url, data=form_data)

        assert response.status_code == 302

        positions = CascadingVesselPosition.objects.all()
        assert positions.count() > 0

    def test_cascading_act_004_validation_own_vessels(
        self, auth_client, cascading_invalid_form_data
    ):
        """
        [CASCADING_ACT_004] Validation - Own Vessels
        서버 측에서 own_vessel_count를 실제 vessel_code[] 개수로 산출하여 저장
        """
        url = reverse("input_data:cascading_vessel_create")
        form_data = cascading_invalid_form_data.copy()
        form_data["action"] = "save"

        response = auth_client.post(url, data=form_data)

        assert response.status_code == 302
        positions = CascadingVesselPosition.objects.all()
        assert positions.count() == 2
        proforma = positions.first().proforma
        assert proforma.own_vessel_count == 2

    def test_cascading_act_005_save_position_data(
        self, auth_client, cascading_form_data
    ):
        """
        [CASCADING_ACT_005] Save 후 Position 데이터 확인
        vessel_position, vessel_position_date가 정확한지 검증
        """
        url = reverse("input_data:cascading_vessel_create")
        form_data = cascading_form_data.copy()
        form_data["action"] = "save"

        response = auth_client.post(url, data=form_data)
        assert response.status_code == 302

        positions = CascadingVesselPosition.objects.all().order_by("vessel_position")
        assert positions.count() == 3

        for i, pos in enumerate(positions):
            assert pos.vessel_position == i + 1
            assert pos.vessel_position_date is not None

    def test_cascading_act_006_error_data_recovery(self, auth_client, sample_schedule):
        """
        [CASCADING_ACT_006] 에러 시 데이터 복구
        필수값 누락/에러 발생 시 입력값이 보존되는지 검증
        """
        url = reverse("input_data:cascading_vessel_create")

        incomplete_data = {
            "scenario_id": sample_schedule.scenario.id,
            "lane_code": sample_schedule.lane_id,
            "proforma_name": sample_schedule.proforma_name,
            "own_vessel_count": 2,
            "action": "save",
        }

        response = auth_client.post(url, data=incomplete_data)

        if response.status_code == 200:
            preserved_data = response.context.get("preserved_data", {})
            assert preserved_data.get("own_vessel_count") == "2"
        else:
            assert response.status_code == 302

    # ==========================================================================
    # 3. Cascading Vessel Info (대시보드)
    # ==========================================================================
    def test_cascading_vessel_info_001_view(self, auth_client, multiple_cascading_data):
        """
        [CASCADING_VESSEL_INFO_001] Cascading Vessel Info 조회
        Scenario 선택 시 Lane별 Cascading 결과 대시보드 표시 검증
        """
        url = reverse("input_data:cascading_vessel_info")
        response = auth_client.get(
            url,
            {
                "scenario_id": multiple_cascading_data[0].scenario.id,
            },
        )

        assert response.status_code == 200

        dashboard_data = response.context["dashboard_data"]
        assert len(dashboard_data) == 2

        assert "slot_headers" in response.context

    # ==========================================================================
    # 4. Cascading Vessel Detail
    # ==========================================================================
    def test_cascading_vessel_detail_001_detail_view(
        self, auth_client, cascading_with_details
    ):
        """
        [CASCADING_DETAIL_001] Cascading Vessel Detail 조회
        특정 Scenario+Proforma의 CascadingVesselPosition 정보가 정상 출력되는지 검증
        """
        first_pos = cascading_with_details[0]
        url = reverse(
            "input_data:cascading_vessel_detail",
            kwargs={
                "scenario_id": first_pos.scenario.id,
                "proforma_id": first_pos.proforma.id,
            },
        )
        response = auth_client.get(url)

        assert response.status_code == 200

        positions = response.context["positions"]
        assert positions.count() == 2

        content = response.content.decode()
        assert str(first_pos.proforma.own_vessel_count) in content

        edit_url = reverse("input_data:cascading_vessel_create")
        assert edit_url in content

    def test_cascading_vessel_detail_002_edit_mode_transition(
        self, auth_client, cascading_with_details
    ):
        """
        [CASCADING_DETAIL_002] Edit 모드 전환
        Detail 화면에서 Edit 버튼 클릭 시 Create 화면으로 이동 검증
        """
        first_pos = cascading_with_details[0]

        detail_url = reverse(
            "input_data:cascading_vessel_detail",
            kwargs={
                "scenario_id": first_pos.scenario.id,
                "proforma_id": first_pos.proforma.id,
            },
        )
        response = auth_client.get(detail_url)
        assert response.status_code == 200

        edit_url = reverse("input_data:cascading_vessel_create")
        edit_response = auth_client.get(
            edit_url,
            {
                "scenario_id": first_pos.scenario.id,
                "lane_code": first_pos.proforma.lane_id,
                "proforma_name": first_pos.proforma.proforma_name,
            },
        )

        assert edit_response.status_code == 200
        assert edit_response.context["is_edit_mode"] is True

        restored_rows = edit_response.context["restored_rows"]
        checked_rows = [row for row in restored_rows if row.get("is_checked")]
        assert len(checked_rows) == 2


@pytest.mark.django_db
class TestCascadingScheduleView:
    """
    CascadingSchedule (슬롯 선택) 관련 뷰 테스트
    Scenarios: CS_CREATE_001, CS_CREATE_002, CS_CREATE_003, CS_LIST_001
    """

    def test_cs_create_001_page_load(self, auth_client):
        """
        [CS_CREATE_001] Cascading Creation 초기 진입
        생성 화면 초기 진입 시 정상 로드 확인
        """
        url = reverse("input_data:cascading_create")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "input_data/cascading_create.html" in [
            t.name for t in response.templates
        ]

    def test_cs_create_002_save_slots(self, auth_client, sample_schedule):
        """
        [CS_CREATE_002] Cascading Creation 슬롯 저장
        시나리오 선택 후 특정 proforma의 슬롯 1을 선택하여 저장
        """
        from input_data.models import CascadingSchedule

        url = reverse("input_data:cascading_create")
        form_data = {
            "scenario_id": sample_schedule.scenario.id,
            f"slots_{sample_schedule.id}[]": ["1"],
        }

        response = auth_client.post(url, data=form_data)

        assert response.status_code == 302

        schedules = CascadingSchedule.objects.filter(
            scenario=sample_schedule.scenario, proforma=sample_schedule
        )
        assert schedules.count() == 1
        assert schedules.first().vessel_position == 1
        assert schedules.first().vessel_position_date is not None

    def test_cs_create_003_overwrite(self, auth_client, sample_schedule, user):
        """
        [CS_CREATE_003] Cascading Creation 수정 (덮어쓰기)
        기존 데이터 삭제 후 재생성 확인
        """
        from input_data.models import CascadingSchedule

        # Given: 기존 데이터 1건
        CascadingSchedule.objects.create(
            scenario=sample_schedule.scenario,
            proforma=sample_schedule,
            vessel_position=1,
            vessel_position_date="2026-02-15",
            created_by=user,
        )
        assert (
            CascadingSchedule.objects.filter(
                scenario=sample_schedule.scenario, proforma=sample_schedule
            ).count()
            == 1
        )

        # When: 슬롯 1,2 선택하여 저장
        url = reverse("input_data:cascading_create")
        form_data = {
            "scenario_id": sample_schedule.scenario.id,
            f"slots_{sample_schedule.id}[]": ["1", "2"],
        }
        response = auth_client.post(url, data=form_data)

        # Then: 기존 1건 삭제 후 2건 재생성
        assert response.status_code == 302
        schedules = CascadingSchedule.objects.filter(
            scenario=sample_schedule.scenario, proforma=sample_schedule
        ).order_by("vessel_position")
        assert schedules.count() == 2
        assert list(schedules.values_list("vessel_position", flat=True)) == [1, 2]

    def test_cs_list_001_schedule_list(self, auth_client, sample_schedule, user):
        """
        [CS_LIST_001] Cascading Schedule 목록 조회
        Scenario 선택 시 대시보드에 슬롯 선택 결과 표시 검증
        """
        from input_data.models import CascadingSchedule

        # Given: CascadingSchedule 데이터 생성
        CascadingSchedule.objects.create(
            scenario=sample_schedule.scenario,
            proforma=sample_schedule,
            vessel_position=1,
            vessel_position_date="2026-02-15",
            created_by=user,
        )

        url = reverse("input_data:cascading_schedule_list")
        response = auth_client.get(url, {"scenario_id": sample_schedule.scenario.id})

        assert response.status_code == 200
        dashboard_data = response.context["dashboard_data"]
        assert len(dashboard_data) >= 1

        # 슬롯 표시 확인
        first_row = dashboard_data[0]
        assert first_row["selected_count"] == 1
        assert first_row["declared_count"] == sample_schedule.declared_count


# ==========================================================================
# Lane Proforma Mapping Tests
# ==========================================================================
@pytest.mark.django_db
class TestLaneProformaMappingView:
    """
    Lane Proforma Mapping 편집/조회 화면 테스트
    """

    # ------------------------------------------------------------------
    # Detail → Edit 전환 시 데이터 유지 (이전 버그 재현 방지)
    # ------------------------------------------------------------------
    def test_cascading_detail_003_edit_link_has_correct_lane_id(
        self, auth_client, cascading_with_details
    ):
        """
        [CASCADING_DETAIL_003] Detail 화면 Edit 링크의 lane 파라미터 검증
        Edit 링크에 lane_id가 올바르게 포함되어 Edit 화면에서 데이터가 유지되는지 확인
        (기존 버그: proforma.lane_code 사용 → AttributeError → 빈 값 전달 → 데이터 초기화)
        """
        first_pos = cascading_with_details[0]

        # 1. Detail 화면 로드
        detail_url = reverse(
            "input_data:cascading_vessel_detail",
            kwargs={
                "scenario_id": first_pos.scenario.id,
                "proforma_id": first_pos.proforma.id,
            },
        )
        response = auth_client.get(detail_url)
        assert response.status_code == 200

        # 2. Edit 링크에 lane_id 값이 포함되는지 확인
        content = response.content.decode()
        lane_id = first_pos.proforma.lane_id
        assert f"lane_code={lane_id}" in content

        # 3. Edit 링크를 따라갔을 때 Edit 모드로 데이터가 정상 로드되는지 확인
        edit_url = reverse("input_data:cascading_vessel_create")
        edit_response = auth_client.get(
            edit_url,
            {
                "scenario_id": first_pos.scenario.id,
                "lane_code": lane_id,
                "proforma_name": first_pos.proforma.proforma_name,
            },
        )
        assert edit_response.status_code == 200
        assert edit_response.context["is_edit_mode"] is True

        # 4. 기존 선박 배정 정보가 로드되었는지 확인
        restored_rows = edit_response.context["restored_rows"]
        checked_rows = [r for r in restored_rows if r.get("is_checked")]
        assert len(checked_rows) == 2
        vessel_codes = {r["vessel_code"] for r in checked_rows}
        assert "V001" in vessel_codes
        assert "V002" in vessel_codes

    # ------------------------------------------------------------------
    # 1. View (화면 진입)
    # ------------------------------------------------------------------
    def test_lpm_view_001_page_load(self, auth_client):
        """
        [LPM_VIEW_001] Lane Proforma Mapping 편집 화면 초기 진입
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

    def test_lpm_view_002_scenario_selection(self, auth_client, lane_proforma_scenario):
        """
        [LPM_VIEW_002] 시나리오 선택 시 Lane별 Proforma 목록 표시
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

    def test_lpm_view_003_with_existing_mapping(
        self, auth_client, lane_proforma_with_mapping
    ):
        """
        [LPM_VIEW_003] 기존 매핑이 있을 때 체크 상태 표시
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
        [LPM_VIEW_004] 겹침 구간 처리 - 타임라인 기간 분할 검증
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
        # 마지막 셀의 effective가 False인지 확인 (시나리오 끝까지 가면 안 됨)
        pf1_cells = pf1_item["cells"]
        pf1_effective_cells = [c for c in pf1_cells if c["effective"]]
        pf1_in_range_cells = [c for c in pf1_cells if c["in_range"]]
        # effective 셀 수 < in_range 셀 수 (6102에 의해 잘렸으므로)
        assert len(pf1_effective_cells) < len(pf1_in_range_cells)

        # 6102의 effective는 시작일 이후부터
        pf2_cells = pf2_item["cells"]
        pf2_effective_cells = [c for c in pf2_cells if c["effective"]]
        assert len(pf2_effective_cells) > 0

    # ------------------------------------------------------------------
    # 2. Action (저장)
    # ------------------------------------------------------------------
    def test_lpm_act_001_save_mapping(self, auth_client, lane_proforma_scenario):
        """
        [LPM_ACT_001] Proforma 매핑 저장
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

    def test_lpm_act_002_overwrite_mapping(
        self, auth_client, lane_proforma_with_mapping
    ):
        """
        [LPM_ACT_002] 매핑 수정 (덮어쓰기)
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

    def test_lpm_act_003_clear_all_mapping(
        self, auth_client, lane_proforma_with_mapping
    ):
        """
        [LPM_ACT_003] 매핑 전체 해제
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

    # ------------------------------------------------------------------
    # 3. List (조회 - readonly)
    # ------------------------------------------------------------------
    def test_lpm_list_001_readonly_view(self, auth_client, lane_proforma_with_mapping):
        """
        [LPM_LIST_001] Lane Proforma Mapping 조회 화면
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

    def test_lpm_list_002_readonly_no_form_submit(self, auth_client):
        """
        [LPM_LIST_002] 조회 화면 초기 진입
        시나리오 미선택 시 빈 화면 정상 로드 및 readonly 플래그 확인
        """
        url = reverse("input_data:lane_proforma_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert response.context["is_readonly"] is True
        assert response.context["mapping_data"] == []
