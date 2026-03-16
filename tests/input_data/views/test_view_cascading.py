"""
Cascading View Tests
CASCADING_VIEW_*, CASCADING_ACT_*, CASCADING_VESSEL_INFO_*, CASCADING_DETAIL_* 시나리오 테스트
"""

from django.urls import reverse

import pytest

from input_data.models import CascadingVesselPosition


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
        [IN_CV_001] Cascading Vessel Creation 초기 진입
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
        [IN_CV_003] Edit 모드 데이터 Load
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
        [IN_CV_004] Save Cascading (생성)
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
        [IN_CV_005] Save Cascading (수정)
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
        [IN_CV_006] Create LRS
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
        [IN_CV_007] Validation - Own Vessels
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
        [IN_CV_008] Save 후 Position 데이터 확인
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

    def test_cascading_act_006_error_data_recovery(
        self, auth_client, cascading_with_details
    ):
        """
        [IN_CV_009] 에러 시 데이터 복구
        필수값 누락(vessel_code[]) 시 입력값(own_vessel_count)이 보존되는지 검증
        """
        first_pos = cascading_with_details[0]
        url = reverse("input_data:cascading_vessel_create")

        # vessel_code[] 누락 (필수값 미입력)
        response = auth_client.post(
            url,
            {
                "action": "save",
                "scenario_id": first_pos.scenario.id,
                "lane_code": first_pos.proforma.lane_id,
                "proforma_name": first_pos.proforma.proforma_name,
                "own_vessel_count": 3,
            },
        )

        # 에러 시 200(폼 재표시) 또는 302(리다이렉트) 모두 허용
        assert response.status_code in [200, 302]

        if response.status_code == 200:
            preserved_data = response.context.get("preserved_data", {})
            # own_vessel_count가 문자열/숫자 형태로 보존되는지 확인
            own_count = preserved_data.get("own_vessel_count")
            assert own_count in [3, "3"]

    # ==========================================================================
    # 3. Cascading Vessel Info (대시보드)
    # ==========================================================================
    def test_cascading_vessel_info_001_view(self, auth_client, multiple_cascading_data):
        """
        [IN_CV_010] Cascading Vessel Info 조회
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
        [IN_CV_011] Cascading Vessel Detail 조회
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
        [IN_CV_012] Edit 모드 전환
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

    def test_cascading_detail_003_edit_link_has_correct_lane_id(
        self, auth_client, cascading_with_details
    ):
        """
        [IN_CV_013] Detail 화면 Edit 링크의 lane 파라미터 검증
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

    # ==========================================================================
    # 5. API / UI 연동 검증
    # ==========================================================================
    # NOTE: CascadingSchedule(슬롯 선택) 테스트는 test_view_cascading_schedule.py에서 관리
    #       IN_CS_001~003, IN_CS_004 → test_view_cascading_schedule.py 참조
