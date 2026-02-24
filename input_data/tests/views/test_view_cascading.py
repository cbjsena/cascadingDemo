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
    Cascading 생성 화면, 조회 화면 및 동작 테스트
    Scenarios: CASCADING_VIEW_*, CASCADING_ACT_*, CASCADING_LIST_*, CASCADING_DETAIL_*
    """

    def test_cascading_view_001_page_load(self, auth_client):
        """
        [CASCADING_VIEW_001] Cascading 초기 진입
        생성 화면 초기 진입 시 빈 껍데기로 정상 로드되는지 확인
        """
        url = reverse("input_data:cascading_create")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "input_data/cascading_create.html" in [
            t.name for t in response.templates
        ]
        assert response.context["is_edit_mode"] is False
        assert response.context["preserved_data"] == {}
        assert len(response.context["restored_rows"]) == 0

    def test_cascading_view_003_edit_mode_load(
        self, auth_client, sample_schedule, user
    ):
        """
        [CASCADING_VIEW_003] Edit 모드 데이터 Load
        Detail 화면에서 넘어온 파라미터로 수정 모드 진입 시 전체 슬롯 중 배정된 행만 매핑되는지 검증
        """
        # Given: DB에 이미 저장된 Cascading 데이터 (Seq=1)
        start_date = timezone.now().date()
        cascading = CascadingSchedule.objects.create(
            scenario=sample_schedule.scenario,
            proforma=sample_schedule,
            cascading_seq=1,
            own_vessels=1,
            initial_etb_date=start_date,
            effective_start_date=start_date,
            effective_end_date=start_date + timedelta(days=30),
            created_by=user,
        )

        # sample_schedule은 declared_count가 2입니다. (총 2개의 슬롯 생성 예상)
        CascadingScheduleDetail.objects.create(
            cascading=cascading,
            vessel_code="V_LOAD_TEST",
            initial_start_date=start_date,
            created_by=user,
        )

        # When: 수정 모드 파라미터를 포함하여 GET 요청
        url = reverse("input_data:cascading_create")
        response = auth_client.get(
            url,
            {
                "scenario_id": sample_schedule.scenario.id,
                "lane_code": sample_schedule.lane_code,
                "proforma_name": sample_schedule.proforma_name,
                "cascading_seq": cascading.cascading_seq,
            },
        )

        # Then: 데이터 검증
        assert response.status_code == 200
        assert response.context["is_edit_mode"] is True

        preserved = response.context["preserved_data"]
        restored = response.context["restored_rows"]

        assert preserved["cascading_seq"] == 1
        assert preserved["required_count"] == 2

        # 2줄(slots)이 생성되며, 첫 줄만 체크되어 있고 두 번째 줄은 비어있어야 함
        assert len(restored) == 2
        assert restored[0]["is_checked"] is True
        assert restored[0]["vessel_code"] == "V_LOAD_TEST"
        assert restored[1]["is_checked"] is False
        assert restored[1]["vessel_code"] == ""

    def test_cascading_act_001_save_post(self, auth_client, sample_schedule):
        """
        [CASCADING_ACT_001] Save Cascading
        변경된 모델 컬럼명(effective_*, initial_etb_date)에 맞춰 DB에 정상 저장되는지 검증
        """
        url = reverse("input_data:cascading_create")
        start_date = timezone.now().date()
        initial_etb = start_date + timedelta(days=2)  # 요일 보정된 첫 배 투입일 가정

        data = {
            "action": "save",
            "scenario_id": sample_schedule.scenario.id,
            "lane_code": sample_schedule.lane_code,
            "proforma_name": sample_schedule.proforma_name,
            "cascading_seq": "2",
            "own_vessel_count": "1",
            "effective_start_date": start_date.strftime("%Y-%m-%d"),
            "effective_end_date": (start_date + timedelta(days=30)).strftime(
                "%Y-%m-%d"
            ),
            "vessel_code[]": ["V_SAVE", ""],
            "vessel_start_date[]": [initial_etb.strftime("%Y-%m-%d"), ""],
        }

        response = auth_client.post(url, data, follow=True)

        assert response.status_code == 200

        # 새로 채번된 Seq=2 데이터가 정확한 컬럼명으로 저장되었는지 확인
        new_cascade = CascadingSchedule.objects.get(
            scenario=sample_schedule.scenario, cascading_seq=2
        )
        assert new_cascade.own_vessels == 1
        assert new_cascade.effective_start_date == start_date
        assert new_cascade.initial_etb_date == initial_etb

    def test_cascading_act_002_create_lrs(self, auth_client, pf_complex_data):
        """
        [CASCADING_ACT_002] Create LRS
        저장 및 LRS 생성 엔진 구동 동시 수행
        """
        url = reverse("input_data:cascading_create")
        start_date = timezone.now().date()

        data = {
            "action": "create_lrs",
            "scenario_id": "TEST_SCENARIO_001",  # base_scenario id
            "lane_code": "TEST_LANE",
            "proforma_name": "PF_COMPLEX",
            "cascading_seq": "1",
            "own_vessel_count": "1",
            "effective_start_date": start_date.strftime("%Y-%m-%d"),
            "effective_end_date": (start_date + timedelta(days=30)).strftime(
                "%Y-%m-%d"
            ),
            "vessel_code[]": ["V_LRS", ""],
            "vessel_start_date[]": [start_date.strftime("%Y-%m-%d"), ""],
        }

        response = auth_client.post(url, data, follow=True)

        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert any("created successfully" in str(m) for m in messages)

        # Cascading Detail과 LRS 테이블 모두에 해당 선박이 존재해야 함
        assert CascadingScheduleDetail.objects.filter(vessel_code="V_LRS").exists()
        assert LongRangeSchedule.objects.filter(vessel_code="V_LRS").exists()

    def test_cascading_act_003_error_recovery(self, auth_client, sample_schedule):
        """
        [CASCADING_ACT_003] 에러 시 데이터 복구
        필수값 누락/에러 발생 시 변경된 필드(effective_... 등)의 입력값이 보존되는지 검증
        """
        url = reverse("input_data:cascading_create")

        # 고의로 proforma_name을 누락시켜 에러 유발
        data = {
            "action": "save",
            "scenario_id": sample_schedule.scenario.id,
            "lane_code": sample_schedule.lane_code,
            "cascading_seq": "3",
            "own_vessel_count": "1",
            "effective_start_date": "2026-12-01",
            "effective_end_date": "2026-12-31",
        }

        response = auth_client.post(url, data)

        # 리다이렉트 없이 폼 렌더링
        assert response.status_code == 200
        assert response.context.get("is_error_state") is True

        # 보존 데이터 확인
        preserved = response.context["preserved_data"]
        assert preserved["cascading_seq"] == "3"
        assert preserved["effective_start_date"] == "2026-12-01"

    def test_cascading_list_001_view(self, auth_client, sample_schedule, user):
        """
        [CASCADING_LIST_001] Cascading 목록 조회
        동적 Select 필터 기반의 목록 화면 표출 및 정확한 필터링 검증
        """
        CascadingSchedule.objects.create(
            scenario=sample_schedule.scenario,
            proforma=sample_schedule,
            cascading_seq=1,
            own_vessels=1,
            initial_etb_date=timezone.now().date(),
            effective_start_date=timezone.now().date(),
            effective_end_date=timezone.now().date(),
            created_by=user,
        )

        url = reverse("input_data:cascading_list")
        response = auth_client.get(
            url,
            {
                "scenario_id": sample_schedule.scenario.id,
                "lane_code": sample_schedule.lane_code,
            },
        )

        assert response.status_code == 200
        qs = response.context["cascading_list"]

        assert qs.count() == 1
        assert qs.first().proforma.lane_code == "TEST_LANE"
        assert (
            response.context["search_params"]["scenario_id"]
            == sample_schedule.scenario.id
        )

    def test_cascading_detail_001_view(self, auth_client, sample_schedule, user):
        """
        [CASCADING_DETAIL_001] Cascading 상세 조회
        특정 Cascading의 Master 정보와 할당된 선박 내역을 조회하고 Edit 파라미터를 검증
        """
        cascading = CascadingSchedule.objects.create(
            scenario=sample_schedule.scenario,
            proforma=sample_schedule,
            cascading_seq=1,
            own_vessels=1,
            initial_etb_date=timezone.now().date(),
            effective_start_date=timezone.now().date(),
            effective_end_date=timezone.now().date(),
            created_by=user,
        )
        CascadingScheduleDetail.objects.create(
            cascading=cascading,
            vessel_code="VSL1",
            initial_start_date=timezone.now().date(),
            created_by=user,
        )

        url = reverse("input_data:cascading_detail", args=[cascading.pk])
        response = auth_client.get(url)

        assert response.status_code == 200

        # Master와 Detail 객체 로드 검증
        loaded = response.context["cascading"]
        assert loaded.cascading_seq == 1

        details = response.context["details"]
        assert len(details) == 1
        assert details[0].vessel_code == "VSL1"
