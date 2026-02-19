import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from input_data.models import LongRangeSchedule


@pytest.mark.django_db
class TestLongRangeView:
    """
    LRS 화면 통합 테스트
    Scenarios: LRS_VIEW_001, LRS_VIEW_002, LRS_VIEW_003
    """

    def test_lrs_view_001_page_load(self, auth_client):
        """[LRS_VIEW_001] 생성 화면 진입"""
        url = reverse("input_data:long_range_create")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "input_data/long_range_create.html" in [t.name for t in response.templates]
        assert "scenarios" in response.context

    def test_lrs_view_002_create_post(self, auth_client, pf_complex_data):
        """[LRS_VIEW_002] POST 요청으로 생성 성공"""
        url = reverse("input_data:long_range_create")

        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)

        # Form Data
        data = {
            "scenario_id": pf_complex_data.id,
            "lane_code": "TEST_LANE",
            "proforma_name": "PF_COMPLEX",
            "apply_start_date": start_date.strftime("%Y-%m-%d"),
            "apply_end_date": end_date.strftime("%Y-%m-%d"),
            "own_vessel_count": "1",
            "vessel_code[]": ["V_VW_TEST"],
            "vessel_start_date[]": [start_date.strftime("%Y-%m-%d")],
            "vessel_capacity[]": ["9999"],
            "lane_code_list[]": ["TEST_LANE"]
        }

        response = auth_client.post(url, data, follow=True)

        # 1. Redirect 확인
        assert response.status_code == 200

        # 2. 메시지 확인
        messages = list(response.context['messages'])
        assert any("successfully" in str(m) for m in messages)

        # 3. DB 저장 확인
        assert LongRangeSchedule.objects.filter(vessel_code="V_VW_TEST").exists()

    def test_lrs_view_003_list_search(self, auth_client, pf_complex_data, user):
        """[LRS_VIEW_003] 목록 페이지 검색 필터"""
        # 1. 데이터 사전 생성
        LongRangeSchedule.objects.create(
            scenario=pf_complex_data,
            lane_code="TEST_LANE",
            proforma_name="PF_COMPLEX",
            vessel_code="V_SCH_TGT",
            voyage_number="0001",
            port_code="PORT_A",
            direction="E",
            calling_port_seq=1,
            etb=timezone.now(),
            created_by=user, updated_by=user
        )

        url = reverse("input_data:long_range_list")

        # 2. 검색 요청
        response = auth_client.get(url, {
            "scenario_id": pf_complex_data.id,
            "lane_code": "TEST_LANE",
            "vessel_code": "V_SCH_TGT"
        })

        # 3. 결과 확인
        assert response.status_code == 200
        lrs_list = response.context["lrs_list"]
        assert len(lrs_list) >= 1
        assert lrs_list[0].vessel_code == "V_SCH_TGT"


@pytest.mark.django_db
class TestLongRangeViewMissingScenarios:
    """
    [LRS_VIEW_004, LRS_VIEW_005] 보완 시나리오 테스트
    """

    def test_lrs_view_004_error_restore_data(self, auth_client, pf_complex_data):
        """[LRS_VIEW_004] 에러 시 입력 데이터 복구 검증"""
        url = reverse("input_data:long_range_create")

        # 1. Given: 필수 값인 'proforma_name'을 고의로 누락하고 동적 배열 데이터 전송
        data = {
            "scenario_id": pf_complex_data.id,
            "lane_code": "TEST_LANE",
            # "proforma_name": 누락하여 Exception 유발
            "apply_start_date": "2024-01-01",
            "apply_end_date": "2024-12-31",
            "vessel_code[]": ["V_RESTORE_1", "V_RESTORE_2"],
            "vessel_start_date[]": ["2024-01-01", "2024-02-01"],
            "vessel_capacity[]": ["1000", "2000"],
            "lane_code_list[]": ["L1", "L2"]
        }

        # 2. When
        response = auth_client.post(url, data)

        # 3. Then
        assert response.status_code == 200  # 에러가 나서 Redirect(302) 되지 않고 폼을 다시 렌더링함

        # Context에 복구된 데이터가 정확히 들어있는지 검증
        context = response.context
        assert "restored_rows" in context

        restored = context["restored_rows"]
        assert len(restored) == 2
        # Zip으로 묶인 복구 데이터 구조 검증
        assert restored[0]["vessel_code"] == "V_RESTORE_1"
        assert restored[1]["capacity"] == "2000"

    def test_lrs_view_005_list_search_empty(self, auth_client, user, pf_complex_data):
        """[LRS_VIEW_005] 목록 검색 (결과 없음 및 검색어 유지)"""
        # 기존 데이터 하나 생성
        LongRangeSchedule.objects.create(
            scenario=pf_complex_data, lane_code="LANE_A", vessel_code="V_EXIST",
            voyage_number="0001", port_code="PUS", calling_port_seq=1,
            created_by=user, updated_by=user
        )

        url = reverse("input_data:long_range_list")

        # 1. When: 존재하지 않는 GHOST 선박 검색
        response = auth_client.get(url, {"scenario_id": pf_complex_data.id, "vessel_code": "GHOST"})

        # 2. Then
        assert response.status_code == 200
        context = response.context

        # 목록은 0개여야 함
        assert len(context["lrs_list"]) == 0

        # 폼의 검색어는 그대로 유지되어야 함
        assert context["search_params"]["vessel_code"] == "GHOST"