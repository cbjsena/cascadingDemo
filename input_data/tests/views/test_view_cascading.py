"""
Cascading View Tests
CASCADING_VIEW_*, CASCADING_ACT_*, CASCADING_VESSEL_INFO_*, CASCADING_DETAIL_* 시나리오 테스트
"""

import pytest

from django.urls import reverse

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

        assert response.status_code == 200

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
