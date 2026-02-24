from datetime import timedelta

import pytest

from django.urls import reverse
from django.utils import timezone

from input_data.models import (
    CascadingSchedule,
    CascadingScheduleDetail,
    LongRangeSchedule,
)


@pytest.mark.django_db
class TestCascadingView:
    """
    Cascading 생성 화면 및 동작 테스트
    Scenarios: CASCADING_VIEW_*, CASCADING_ACT_*
    """

    def test_cascading_view_001_page_load(self, auth_client):
        """[CASCADING_VIEW_001] 생성 화면 초기 진입"""
        url = reverse("input_data:cascading_create")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "input_data/cascading_create.html" in [
            t.name for t in response.templates
        ]
        assert "scenarios" in response.context

    def test_cascading_view_002_load_existing_data(
        self, auth_client, sample_schedule, user
    ):
        """[CASCADING_VIEW_002] GET 파라미터 전달 시 기존 Cascading 데이터 Load"""
        # 1. Given: DB에 이미 저장된 Cascading 데이터 존재
        cascading = CascadingSchedule.objects.create(
            scenario=sample_schedule.scenario,
            proforma=sample_schedule,
            cascading_seq=1,
            own_vessels=1,
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timedelta(days=30)).date(),
            created_by=user,
        )
        CascadingScheduleDetail.objects.create(
            cascading=cascading,
            vessel_code="V_LOAD_TEST",
            initial_start_date=timezone.now().date(),
            created_by=user,
        )

        # 2. When: 파라미터를 포함하여 GET 요청
        url = reverse("input_data:cascading_create")
        response = auth_client.get(
            url,
            {
                "scenario_id": sample_schedule.scenario.id,
                "lane_code": sample_schedule.lane_code,
                "proforma_name": sample_schedule.proforma_name,
            },
        )

        # 3. Then: 데이터가 Context에 잘 담겨오는지 확인
        assert response.status_code == 200
        preserved_data = response.context.get("preserved_data", {})
        restored_rows = response.context.get("restored_rows", [])

        assert preserved_data.get("own_vessels") == 1
        assert len(restored_rows) == 1
        assert restored_rows[0]["vessel_code"] == "V_LOAD_TEST"

    def test_cascading_act_001_save_only(self, auth_client, pf_complex_data):
        """[CASCADING_ACT_001] Save Cascading 버튼 클릭 시 (LRS 생성 안 함)"""
        url = reverse("input_data:cascading_create")
        start_date = timezone.now().date()

        data = {
            "action": "save",  # 핵심: Save 액션
            "scenario_id": pf_complex_data.id,
            "lane_code": "TEST_LANE",
            "proforma_name": "PF_COMPLEX",
            "apply_start_date": start_date.strftime("%Y-%m-%d"),
            "apply_end_date": (start_date + timedelta(days=30)).strftime("%Y-%m-%d"),
            "vessel_code[]": ["V_SAVE_ONLY"],
            "vessel_start_date[]": [start_date.strftime("%Y-%m-%d")],
        }

        response = auth_client.post(url, data, follow=True)

        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert any("saved successfully" in str(m) for m in messages)

        # Cascading은 생성되었으나, LRS는 생성되지 않아야 함
        assert CascadingScheduleDetail.objects.filter(
            vessel_code="V_SAVE_ONLY"
        ).exists()
        assert not LongRangeSchedule.objects.filter(vessel_code="V_SAVE_ONLY").exists()

    def test_cascading_act_002_create_lrs(self, auth_client, pf_complex_data):
        """[CASCADING_ACT_002] Create LRS 버튼 클릭 시 (LRS 생성까지 완료)"""
        url = reverse("input_data:cascading_create")
        start_date = timezone.now().date()

        data = {
            "action": "create_lrs",  # 핵심: Create LRS 액션
            "scenario_id": pf_complex_data.id,
            "lane_code": "TEST_LANE",
            "proforma_name": "PF_COMPLEX",
            "apply_start_date": start_date.strftime("%Y-%m-%d"),
            "apply_end_date": (start_date + timedelta(days=30)).strftime("%Y-%m-%d"),
            "vessel_code[]": ["V_LRS"],
            "vessel_start_date[]": [start_date.strftime("%Y-%m-%d")],
        }

        response = auth_client.post(url, data, follow=True)

        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert any("created successfully" in str(m) for m in messages)

        # Cascading과 LRS 모두 생성되어야 함
        assert CascadingScheduleDetail.objects.filter(vessel_code="V_LRS").exists()
        # (단, LRS 로직이 모의 호출되었다면 LRS도 존재. 실제 엔진이 구동되므로 존재해야 함)
        assert LongRangeSchedule.objects.filter(vessel_code="V_LRS").exists()

    def test_cascading_act_003_error_restore(self, auth_client, pf_complex_data):
        """[CASCADING_ACT_003] 에러 시 입력 데이터 복구 검증"""
        url = reverse("input_data:cascading_create")

        # 필수 값인 'proforma_name' 누락
        data = {
            "action": "create_lrs",
            "scenario_id": pf_complex_data.id,
            "lane_code": "TEST_LANE",
            "apply_start_date": "2024-01-01",
            "apply_end_date": "2024-12-31",
            "vessel_code[]": ["V_RESTORE_1", "V_RESTORE_2"],
            "vessel_start_date[]": ["2024-01-01", "2024-02-01"],
            "vessel_capacity[]": ["1000", "2000"],
            "lane_code_list[]": ["L1", "L2"],
        }

        response = auth_client.post(url, data)

        # Redirect(302) 되지 않고 200 반환됨
        assert response.status_code == 200
        assert "restored_rows" in response.context
        assert response.context["is_error_state"] is True

        restored = response.context["restored_rows"]
        assert len(restored) == 2
        assert restored[0]["vessel_code"] == "V_RESTORE_1"
