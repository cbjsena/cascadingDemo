import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from input_data.models import ScenarioInfo, ProformaSchedule
from common import messages as msg

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
        [INPUT_SCENARIO_LIST_001] 시나리오 목록 조회 및 기본값 확인
        """
        url = reverse('input_data:scenario_list')
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "input_data/scenario_list.html" in [t.name for t in response.templates]

        # Context Data 검증
        scenarios = response.context.get("scenarios")
        assert scenarios is not None
        assert base_scenario in scenarios

        # 기본값(오늘 날짜 기준 채번 등) 존재 여부
        assert "default_scenario_id" in response.context
        assert "default_base_ym" in response.context

    def test_anonymous_access_control(self, client):
        """
        [INPUT_ACCESS_001] 비로그인 사용자 접근 차단
        """
        urls = [
            reverse('input_data:scenario_list'),
            reverse('input_data:scenario_create'),
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
        [INPUT_SCENARIO_CREATE_001] 신규 시나리오 생성 (성공)
        """
        url = reverse('input_data:scenario_create')
        data = {
            "scenario_id": "NEW_SCENARIO_2026",
            "description": "Test Create",
            "base_year_month": "202602"
        }

        response = auth_client.post(url, data)

        # Redirect 확인
        assert response.status_code == 302
        assert response.url == reverse('input_data:scenario_list')

        # DB 저장 확인
        obj = ScenarioInfo.objects.get(id="NEW_SCENARIO_2026")
        assert obj.description == "Test Create"
        assert obj.created_by == user

    def test_scenario_create_duplicate_fail(self, auth_client, base_scenario):
        """
        [INPUT_SCENARIO_CREATE_002] 중복 ID 생성 시도 (실패)
        """
        url = reverse('input_data:scenario_create')
        data = {
            "scenario_id": base_scenario.id,  # 이미 존재하는 ID
            "description": "Duplicate"
        }

        # Follow Redirect to check messages
        response = auth_client.post(url, data, follow=True)

        # 데이터 개수 변동 없음
        assert ScenarioInfo.objects.filter(id=base_scenario.id).count() == 1

        # 에러 메시지 확인
        messages = list(get_messages(response.wsgi_request))
        assert any("already exists" in str(m) for m in messages)

    # ==========================================================================
    # 3. 복제 (Clone)
    # ==========================================================================
    def test_scenario_clone_success(self, auth_client, scenario_with_data):
        """
        [INPUT_SCENARIO_CLONE_001] 기존 시나리오 복제 (성공)
        """
        # Given: scenario_with_data에는 하위 Proforma 데이터가 1건 있음
        source_id = scenario_with_data.id
        new_id = "CLONED_SCENARIO"

        url = reverse('input_data:scenario_create')
        data = {
            "scenario_id": new_id,
            "source_scenario_id": source_id,
            "description": "Cloned"
        }

        # [수정] follow=True 추가하여 에러 메시지 확인 가능하도록 함
        response = auth_client.post(url, data, follow=True)

        # 만약 생성이 안되었다면 에러 메시지가 있을 것임
        if response.status_code == 200 and not ScenarioInfo.objects.filter(id=new_id).exists():
            messages = list(get_messages(response.wsgi_request))
            # 에러 메시지 출력 (pytest -s 옵션 사용 시 보임)
            print("Messages:", [str(m) for m in messages])

        # 1. 시나리오 생성 확인
        cloned_scenario = ScenarioInfo.objects.get(id=new_id)
        assert cloned_scenario.description == "Cloned"

        # 2. 하위 데이터 복제 확인
        # 원본 데이터 개수
        orig_count = ProformaSchedule.objects.filter(scenario_id=source_id).count()
        # 복제된 데이터 개수
        cloned_count = ProformaSchedule.objects.filter(scenario_id=new_id).count()

        assert orig_count > 0
        assert orig_count == cloned_count

    # ==========================================================================
    # 4. 삭제 (Delete)
    # ==========================================================================
    def test_scenario_delete_success(self, auth_client, scenario_with_data):
        """
        [INPUT_SCENARIO_DELETE_001] 시나리오 삭제 (성공 & Cascade)
        """
        target_id = scenario_with_data.id
        url = reverse('input_data:scenario_delete', args=[target_id])

        response = auth_client.post(url)

        assert response.status_code == 302
        # 데이터 삭제 확인
        assert not ScenarioInfo.objects.filter(id=target_id).exists()
        # Cascade 확인
        assert not ProformaSchedule.objects.filter(scenario_id=target_id).exists()

    def test_scenario_delete_permission_denied(self, auth_client, other_user):
        """
        [INPUT_SCENARIO_DELETE_002] 타인 시나리오 삭제 시도 (권한 없음)
        """
        # 타인(other_user) 소유의 시나리오 생성
        other_scenario = ScenarioInfo.objects.create(
            id="OTHER_USER_SCENARIO",
            created_by=other_user
        )

        url = reverse('input_data:scenario_delete', args=[other_scenario.id])

        # auth_client(test_user)가 삭제 시도
        response = auth_client.post(url, follow=True)

        # 삭제되지 않아야 함
        assert ScenarioInfo.objects.filter(id="OTHER_USER_SCENARIO").exists()

        # 권한 에러 메시지
        messages = list(get_messages(response.wsgi_request))
        msg_texts = [str(m) for m in messages]
        assert any(msg.PERMISSION_DENIED in str(m) for m in messages)

    def test_scenario_delete_by_superuser(self, client, admin_user, other_user):
        """
        [INPUT_SCENARIO_DELETE_003] 관리자(Superuser)의 삭제 (성공)
        """
        # 타인 소유 시나리오
        target = ScenarioInfo.objects.create(
            id="TARGET_FOR_ADMIN",
            created_by=other_user
        )

        # 관리자 로그인
        client.force_login(admin_user)
        url = reverse('input_data:scenario_delete', args=[target.id])

        response = client.post(url)

        assert response.status_code == 302
        assert not ScenarioInfo.objects.filter(id="TARGET_FOR_ADMIN").exists()