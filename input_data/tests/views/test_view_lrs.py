import pytest

from django.urls import reverse


@pytest.mark.django_db
class TestLongRangeListView:
    """
    Long Range Schedule 목록 조회 화면 테스트
    Scenarios: LRS_LIST_*
    """

    def test_lrs_list_001_search(self, auth_client, lrs_integration_data):
        """[LRS_LIST_001] 목록 페이지 검색 필터"""
        url = reverse("input_data:long_range_list")

        response = auth_client.get(
            url,
            {
                "scenario_id": lrs_integration_data.id,
                "lane_code": "LANE_A",
                "vessel_code": "VESSEL_A",
            },
        )

        assert response.status_code == 200
        lrs_list = response.context["lrs_list"]
        assert len(lrs_list) >= 1
        assert lrs_list[0].vessel_code == "VESSEL_A"

    def test_lrs_list_002_edit_button_visibility(
        self, auth_client, lrs_integration_data
    ):
        """[LRS_LIST_002] 3가지 필수 검색 조건이 있을 때 Edit 링크가 존재하는지 확인"""
        url = reverse("input_data:long_range_list")

        # 시나리오, 레인, 프로포마 이름이 모두 지정되어야 Edit 화면(Cascading)으로 돌아갈 수 있음
        response = auth_client.get(
            url,
            {
                "scenario_id": lrs_integration_data.id,
                "lane_code": "LANE_A",
                "proforma_name": "PF_INT",
            },
        )

        assert response.status_code == 200
        # 응답 HTML 텍스트 내에 cascading/create 로 가는 링크가 포함되어 있는지 검증
        content = response.content.decode("utf-8")
        assert "cascading/create/" in content
        assert lrs_integration_data.id in content

    def test_lrs_list_003_empty_result(self, auth_client, lrs_integration_data):
        """[LRS_LIST_003] 존재하지 않는 데이터 검색 시 빈 목록 표출 검증"""
        url = reverse("input_data:long_range_list")

        # DB에 없는 'GHOST'라는 선박 코드로 검색
        response = auth_client.get(
            url,
            {
                "scenario_id": lrs_integration_data.id,
                "vessel_code": "GHOST",
            },
        )

        assert response.status_code == 200

        # 1. 목록이 비어 있어야 함
        lrs_list = response.context["lrs_list"]
        assert len(lrs_list) == 0

        # 2. 검색 조건 폼 상태가 유지되어야 함
        search_params = response.context["search_params"]
        assert search_params["vessel_code"] == "GHOST"
