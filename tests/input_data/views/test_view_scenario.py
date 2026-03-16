from django.contrib.messages import get_messages
from django.urls import reverse

import pytest

from common import constants, messages as msg
from input_data.models import ProformaSchedule, ProformaScheduleDetail, ScenarioInfo


@pytest.mark.django_db
class TestScenarioView:
    """
    시나리오(Scenario) 관리 View 테스트
    [범위] 목록 조회, 생성, 복제, 삭제, 접근 제어
    """

    # ==========================================================================
    # 1. 목록 조회 & 접근 제어
    # ==========================================================================
    def test_scenario_list_view(self, auth_client, base_scenario):
        """
        [IN_SCE_DIS_001] 시나리오 목록 조회 및 기본값 확인
        """
        url = reverse("input_data:scenario_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "input_data/scenario_list.html" in [t.name for t in response.templates]

        # Context Data 검증
        scenarios = response.context.get("scenarios")
        assert scenarios is not None
        assert base_scenario in scenarios

        # 기본값 (ID는 자동 생성)
        assert "default_base_week" in response.context

    def test_anonymous_access_control(self, client):
        """
        [CM_AUTH_DIS_001] 비로그인 사용자 접근 차단
        """
        urls = [
            reverse("input_data:scenario_list"),
            reverse("input_data:scenario_create"),
            # delete는 인자 필요하므로 생략하거나 임의 ID로 테스트
        ]
        for url in urls:
            response = client.get(url)
            assert response.status_code == 302
            assert "/accounts/login/" in response.url

    # ==========================================================================
    # 2. 생성 (Create)
    # ==========================================================================
    def test_scenario_create_success(self, auth_client, user):
        """
        [IN_SCE_DIS_002] 신규 시나리오 생성 (성공)
        """
        url = reverse("input_data:scenario_create")
        data = {
            "description": "Test Create",
            "base_year_week": constants.DEFAULT_BASE_YEAR_WEEK,
            "scenario_type": "WHAT_IF",
        }

        response = auth_client.post(url, data)

        # Redirect 확인
        assert response.status_code == 302
        assert response.url == reverse("input_data:scenario_list")

        # DB 저장 확인 (자동 생성된 code로 조회)
        obj = ScenarioInfo.objects.filter(description="Test Create").first()
        assert obj is not None
        assert obj.code.startswith("SC")  # 자동 생성된 코드 확인
        assert obj.created_by == user
        assert obj.id is not None  # ID가 자동 할당됨

    def test_scenario_create_code_auto_increment(self, auth_client, user):
        """
        [IN_SCE_DIS_003] code 자동 채번 검증
        """
        url = reverse("input_data:scenario_create")

        # 첫 번째 생성
        response1 = auth_client.post(url, {"description": "First"})
        assert response1.status_code == 302

        # 두 번째 생성
        response2 = auth_client.post(url, {"description": "Second"})
        assert response2.status_code == 302

        # 생성된 시나리오들 확인
        scenarios = ScenarioInfo.objects.filter(created_by=user).order_by("id")
        assert scenarios.count() >= 2

        # code가 다른지 확인
        codes = list(scenarios.values_list("code", flat=True))
        assert len(codes) == len(set(codes))  # 모두 유니크

    # ==========================================================================
    # 3. 복제 (Clone)
    # ==========================================================================
    def test_scenario_clone_success(self, auth_client, scenario_with_data):
        """
        [IN_SCE_DIS_004] 기존 시나리오 복제 (성공)
        """
        # Given: scenario_with_data에는 하위 Proforma Master/Detail 데이터가 각 1건씩 있음
        source_id = scenario_with_data.id
        initial_count = ScenarioInfo.objects.count()

        url = reverse("input_data:scenario_create")
        data = {
            "source_scenario_id": source_id,
            "description": "Cloned Scenario",
        }

        # [수정] follow=True 추가하여 에러 메시지 확인 가능하도록 함
        response = auth_client.post(url, data, follow=True)

        assert response.status_code == 200
        # 시나리오가 1개 추가되었는지 확인
        assert ScenarioInfo.objects.count() == initial_count + 1

        # 1. 시나리오 생성 확인 (description으로 조회)
        cloned_scenario = ScenarioInfo.objects.filter(
            description="Cloned Scenario"
        ).first()
        assert cloned_scenario is not None
        assert cloned_scenario.code.startswith("SC")  # 자동 생성된 코드

        # 1-1. 복사 시 원본 시나리오가 base_scenario로 자동 설정되었는지 검증
        assert cloned_scenario.base_scenario == scenario_with_data
        assert cloned_scenario.base_scenario.id == source_id

        # 2. 하위 데이터 복제 확인 (Master & Detail 모두 검증)
        orig_master_count = ProformaSchedule.objects.filter(
            scenario_id=source_id
        ).count()
        cloned_master_count = ProformaSchedule.objects.filter(
            scenario_id=cloned_scenario.id  # 자동 할당된 ID 사용
        ).count()

        orig_detail_count = ProformaScheduleDetail.objects.filter(
            proforma__scenario_id=source_id
        ).count()
        cloned_detail_count = ProformaScheduleDetail.objects.filter(
            proforma__scenario_id=cloned_scenario.id  # 자동 할당된 ID 사용
        ).count()

        assert orig_master_count > 0
        assert orig_master_count == cloned_master_count
        assert orig_detail_count > 0
        assert orig_detail_count == cloned_detail_count

    # ==========================================================================
    # 4. 삭제 (Delete)
    # ==========================================================================
    def test_scenario_delete_success(self, auth_client, scenario_with_data):
        """
        [IN_SCE_DIS_005] 시나리오 삭제 (성공 & Cascade)
        """
        target_id = scenario_with_data.id
        url = reverse("input_data:scenario_delete", args=[target_id])

        response = auth_client.post(url)

        assert response.status_code == 302
        # 데이터 삭제 확인
        assert not ScenarioInfo.objects.filter(id=target_id).exists()
        # Cascade 확인 (Master & Detail 모두 삭제되어야 함)
        assert not ProformaSchedule.objects.filter(scenario_id=target_id).exists()
        assert not ProformaScheduleDetail.objects.filter(
            proforma__scenario_id=target_id
        ).exists()

    def test_scenario_delete_permission_denied(self, auth_client, other_user):
        """
        [IN_SCE_DIS_006] 타인 시나리오 삭제 시도 (권한 없음)
        """
        # 타인(other_user) 소유의 시나리오 생성
        other_scenario = ScenarioInfo.objects.create(
            code="SC_OTHER_USER", created_by=other_user
        )

        url = reverse("input_data:scenario_delete", args=[other_scenario.id])

        # auth_client(test_user)가 삭제 시도
        response = auth_client.post(url, follow=True)

        # 삭제되지 않아야 함
        assert ScenarioInfo.objects.filter(code="SC_OTHER_USER").exists()

        # 권한 에러 메시지
        messages = list(get_messages(response.wsgi_request))
        assert any(msg.PERMISSION_DENIED in str(m) for m in messages)

    def test_scenario_delete_by_superuser(self, client, admin_user, other_user):
        """
        [IN_SCE_DIS_007] 관리자(Superuser)의 삭제 (성공)
        """
        # 타인 소유 시나리오
        target = ScenarioInfo.objects.create(
            code="SC_TARGET_ADMIN", created_by=other_user
        )

        # 관리자 로그인
        client.force_login(admin_user)
        url = reverse("input_data:scenario_delete", args=[target.id])

        response = client.post(url)

        assert response.status_code == 302
        assert not ScenarioInfo.objects.filter(code="SC_TARGET_ADMIN").exists()


@pytest.mark.django_db
class TestScenarioDashboardView:
    """
    Scenario Dashboard 화면 테스트
    """

    def test_dashboard_lane_link_not_empty(self, auth_client, sample_schedule):
        """
        [IN_DASH_DIS_003] Dashboard에서 Proforma 링크의 lane_code 파라미터가
        비어있지 않은지 검증.
        Bug Fix: .values() 딕셔너리에서 item.lane_code(없는 키) → item.lane_id
        """
        scenario = sample_schedule.scenario
        url = reverse("input_data:scenario_dashboard", args=[scenario.id])
        response = auth_client.get(url)

        assert response.status_code == 200
        content = response.content.decode("utf-8")

        # lane_code= 뒤에 값이 비어있으면 안 됨
        assert "lane_code=&" not in content, (
            "Dashboard link has empty lane_code parameter. "
            "Template should use item.lane_id instead of item.lane_code"
        )

        # lane_code=TEST_LANE 이 포함되어 있어야 함
        assert f"lane_code={sample_schedule.lane_id}" in content
