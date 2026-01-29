import pytest
from django.urls import reverse
from input_data.models import InputDataSnapshot, ProformaSchedule
from common import messages as msg


@pytest.mark.django_db
class TestSnapshotScenarios:
    """
    [Input Data Snapshot] 기능별 테스트 시나리오
    """

    def test_input_snap_list_001(self, auth_client, base_snapshot):
        """[INPUT_SNAP_LIST_001] 스냅샷 목록 조회 및 기본값 확인"""
        # Given: base_snapshot exists, user logged in (auth_client)
        url = reverse("input_data:snapshot_list")

        # When
        response = auth_client.get(url)

        # Then
        assert response.status_code == 200
        assert "snapshots" in response.context
        assert base_snapshot in response.context["snapshots"]
        # 자동 채번 로직 검증 (yyyyMMdd + Seq)
        assert "default_data_id" in response.context
        assert "default_base_ym" in response.context
        assert response.context["default_data_id"].startswith("202")  # 연도로 시작하는지 대략 확인

    def test_input_snap_create_001(self, auth_client, test_user):
        """[INPUT_SNAP_CREATE_001] 신규 스냅샷 생성 (성공)"""
        # Given
        url = reverse("input_data:snapshot_create")
        new_id = "NEW_TEST_SNAPSHOT"
        data = {
            "data_id": new_id,
            "description": "Created via Test",
            "base_year_month": "202601"
        }

        # When
        response = auth_client.post(url, data, follow=True)

        # Then
        assert response.status_code == 200  # Redirect followed
        assert InputDataSnapshot.objects.filter(data_id=new_id).exists()

        created_obj = InputDataSnapshot.objects.get(data_id=new_id)
        assert created_obj.created_by == test_user  # 작성자 자동 할당 확인

        # 성공 메세지 확인
        messages_list = list(response.context['messages'])
        assert len(messages_list) > 0
        assert msg.SNAPSHOT_CREATE_SUCCESS.format(data_id=new_id) in [m.message for m in messages_list]

    def test_input_snap_create_002(self, auth_client, base_snapshot):
        """[INPUT_SNAP_CREATE_002] 중복 ID 생성 시도 (실패)"""
        # Given: base_snapshot already exists
        url = reverse("input_data:snapshot_create")
        data = {
            "data_id": base_snapshot.data_id,  # Duplicate ID
            "description": "Duplicate Attempt"
        }

        # When
        response = auth_client.post(url, data, follow=True)

        # Then
        # 리다이렉트는 되지만, 데이터 개수는 늘지 않아야 함
        assert response.status_code == 200
        assert InputDataSnapshot.objects.filter(data_id=base_snapshot.data_id).count() == 1

        # 에러 메세지 확인
        messages_list = list(response.context['messages'])
        assert any(msg.SNAPSHOT_ID_DUPLICATE.format(data_id=base_snapshot.data_id) in m.message for m in messages_list)

    def test_input_snap_clone_001(self, auth_client, snapshot_with_data):
        """[INPUT_SNAP_CLONE_001] 기존 스냅샷 복제 (성공)"""
        # Given: snapshot_with_data has children (ProformaSchedule)
        source_child_count = ProformaSchedule.objects.filter(data_id=snapshot_with_data).count()
        assert source_child_count > 0

        url = reverse("input_data:snapshot_create")
        new_id = "CLONED_SNAPSHOT"
        data = {
            "data_id": new_id,
            "source_data_id": snapshot_with_data.data_id,  # Copy Source
            "description": "Cloned Description"
        }

        # When
        response = auth_client.post(url, data, follow=True)

        # Then
        assert response.status_code == 200
        assert InputDataSnapshot.objects.filter(data_id=new_id).exists()

        # 하위 데이터 복제 검증
        target_snapshot = InputDataSnapshot.objects.get(data_id=new_id)
        target_child_count = ProformaSchedule.objects.filter(data_id=target_snapshot).count()

        assert target_child_count == source_child_count

        # 메세지 확인
        messages_list = list(response.context['messages'])
        expected_msg = msg.SNAPSHOT_CLONE_SUCCESS.format(data_id=new_id, source_id=snapshot_with_data.data_id)
        assert any(expected_msg in m.message for m in messages_list)

    def test_input_snap_delete_001(self, auth_client, snapshot_with_data):
        """[INPUT_SNAP_DELETE_001] 스냅샷 삭제 (성공 & Cascade)"""
        # Given
        target_id = snapshot_with_data.data_id
        url = reverse("input_data:snapshot_delete", args=[target_id])

        # When
        response = auth_client.post(url, follow=True)

        # Then
        assert response.status_code == 200
        assert not InputDataSnapshot.objects.filter(data_id=target_id).exists()

        # Cascade 삭제 확인 (하위 데이터도 없어야 함)
        assert not ProformaSchedule.objects.filter(data_id_id=target_id).exists()

        # 메세지 확인
        messages_list = list(response.context['messages'])
        assert any(msg.SNAPSHOT_DELETE_SUCCESS.format(data_id=target_id) in m.message for m in messages_list)

    def test_input_snap_delete_002(self, auth_client, snapshot_of_other):
        """[INPUT_SNAP_DELETE_002] 타인 스냅샷 삭제 시도 (권한 없음)"""
        # Given:
        # - snapshot_of_other (작성자: other_user)
        # - auth_client (로그인: test_user) -> 작성자가 아님
        target_id = snapshot_of_other.data_id
        url = reverse("input_data:snapshot_delete", args=[target_id])

        # When
        response = auth_client.post(url, follow=True)

        # Then
        assert response.status_code == 200

        # 1. 스냅샷이 삭제되지 않았는지 확인
        assert InputDataSnapshot.objects.filter(data_id=target_id).exists()

        # 2. 에러 메세지 확인 ("permission" 키워드 포함 여부)
        messages_list = list(response.context['messages'])
        assert any(msg.PERMISSION_DENIED in str(m) for m in messages_list)


    def test_input_snap_delete_003(self, admin_client, snapshot_of_other):
        """[INPUT_SNAP_DELETE_003] 관리자(Superuser)의 타인 스냅샷 삭제 (성공)"""
        # Given:
        # - snapshot_of_other (작성자: other_user)
        # - admin_client (로그인: admin_user[Superuser]) -> 작성자는 아니지만 관리자
        target_id = snapshot_of_other.data_id
        url = reverse("input_data:snapshot_delete", args=[target_id])

        # When
        response = admin_client.post(url, follow=True)

        # Then
        assert response.status_code == 200

        # 1. 스냅샷 삭제 확인
        assert not InputDataSnapshot.objects.filter(data_id=target_id).exists()

        # 2. 성공 메세지 확인
        messages_list = list(response.context['messages'])
        assert any(msg.SNAPSHOT_DELETE_SUCCESS.format(data_id=target_id) in m.message for m in messages_list)

    def test_input_access_001(self, client):
        """[INPUT_ACCESS_001] 비로그인 사용자 접근 차단"""
        # Given: Unauthenticated client
        urls = [
            reverse("input_data:snapshot_list"),
            reverse("input_data:snapshot_create"),
        ]

        # When & Then
        for url in urls:
            response = client.get(url)
            assert response.status_code == 302
            assert "/accounts/login/" in response.url