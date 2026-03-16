from django.urls import reverse

import pytest


@pytest.mark.django_db
class TestDashboardView:
    """
    Dashboard(input_home) 화면 테스트
    """

    def test_dashboard_context_keys(self, auth_client, base_scenario):
        """
        [IN_DASH_001] Dashboard Context 변수명 및 값 검증
        """
        url = reverse("input_data:input_home")
        response = auth_client.get(url)

        assert response.status_code == 200

        # 1. 템플릿이 올바른지 확인
        assert "input_data/input_home.html" in [t.name for t in response.templates]

        # 2. Context Key가 정확한지 확인 (공백 없어야 함)
        context = response.context

        # 실패했던 원인: "total_scenarios " (공백) -> "total_scenarios" (정상)
        assert (
            "total_scenarios" in context
        ), "Context key 'total_scenarios' not found (Check for typos/spaces)"
        assert "recent_scenarios" in context, "Context key 'recent_scenarios' not found"
        assert "last_update" in context

        # 3. 값 검증
        # base_scenario가 1개 있으므로 1이어야 함
        assert context["total_scenarios"] == 1
        assert base_scenario in context["recent_scenarios"]

    def test_dashboard_rendering(self, auth_client, base_scenario):
        """
        [IN_DASH_002] Dashboard HTML 렌더링 시 시나리오 정보 포함 확인
        """
        url = reverse("input_data:input_home")
        response = auth_client.get(url)

        content = response.content.decode("utf-8")

        # 화면에 Scenario ID가 출력되어야 함 (scenario.id 사용 여부 확인)
        assert base_scenario.code in content
        assert base_scenario.description in content
