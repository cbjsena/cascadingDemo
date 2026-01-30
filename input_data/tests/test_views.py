import pytest
from django.urls import reverse
from input_data.models import InputDataSnapshot, ProformaSchedule, Distance
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


@pytest.mark.django_db
class TestProformaScenarios:
    """
    [Proforma Schedule] 기능별 상세 테스트 시나리오 구현
    Target: input_data.views.proforma.proforma_create
    """

    def test_proforma_view_get_001(self, auth_client, base_snapshot):
        """[PROFORMA_VIEW_001] 화면 진입 및 기본 컨텍스트 확인"""
        # Given
        url = reverse("input_data:proforma_create")

        # When
        response = auth_client.get(url)

        # Then
        assert response.status_code == 200
        assert "snapshots" in response.context
        assert "rows" in response.context
        assert "header" in response.context
        # 기본 스냅샷이 목록에 있는지 확인
        assert base_snapshot in response.context["snapshots"]

    def test_proforma_action_add_row(self, auth_client):
        """[PROFORMA_ACTION_ADD] 최하단 행 추가 확인"""
        # Given
        url = reverse("input_data:proforma_create")

        # When
        data = {
            "action": "add_row",
            "port_code[]": [],  # 초기엔 아무것도 없음
        }
        response = auth_client.post(url, data)

        # Then
        assert response.status_code == 200
        rows = response.context["rows"]

        # 행이 1개 생성되고 번호가 1번인지 확인
        assert len(rows) == 1
        assert rows[0]['no'] == 1

    def test_proforma_action_insert_row(self, auth_client):
        """[PROFORMA_ACTION_INSERT] 중간 행 삽입 및 재정렬 확인"""
        # Given: 2개의 행(A, B)이 있는 상태 가정
        url = reverse("input_data:proforma_create")

        data = {
            "action": "insert_row",
            "selected_index": "0",  # 첫 번째 행(A) 선택 -> 그 뒤에 삽입

            # 현재 화면 데이터 상태 (A, B)
            "port_code[]": ["PORT_A", "PORT_B"],
            # 필수 필드 더미 데이터 채우기 (IndexError 방지)
            "direction[]": ["E", "E"], "turn_info[]": ["N", "N"], "pilot_in[]": ["0", "0"],
            "etb_no[]": ["0", "0"], "etb_day[]": ["", ""], "etb_time[]": ["", ""],
            "work_hours[]": ["0", "0"], "etd_no[]": ["0", "0"], "etd_day[]": ["", ""], "etd_time[]": ["", ""],
            "pilot_out[]": ["0", "0"], "dist[]": ["0", "0"], "eca_dist[]": ["0", "0"],
            "spd[]": ["0", "0"], "sea_time[]": ["0", "0"], "terminal[]": ["", ""]
        }

        # When
        response = auth_client.post(url, data)

        # Then
        rows = response.context["rows"]

        # 총 3개 행 확인 (A, New, B)
        assert len(rows) == 3
        assert rows[0]['port_code'] == "PORT_A"
        assert rows[1]['port_code'] == ""  # 중간에 삽입된 빈 행
        assert rows[2]['port_code'] == "PORT_B"  # 뒤로 밀린 행

        # 번호 재정렬 확인 (1, 2, 3)
        assert rows[1]['no'] == 2
        assert rows[2]['no'] == 3

    def test_proforma_action_delete_row(self, auth_client):
        """[PROFORMA_ACTION_DELETE] 선택 행 삭제 및 재정렬 확인"""
        # Given: 3개의 행(A, B, C) 가정
        url = reverse("input_data:proforma_create")

        data = {
            "action": "delete_row",
            "row_check": ["1"],  # Index 1 (B) 행 삭제 요청

            "port_code[]": ["A", "B", "C"],
            # 더미 데이터 (3개씩)
            "direction[]": ["E"] * 3, "turn_info[]": ["N"] * 3, "pilot_in[]": ["0"] * 3,
            "etb_no[]": ["0"] * 3, "etb_day[]": [""] * 3, "etb_time[]": [""] * 3,
            "work_hours[]": ["0"] * 3, "etd_no[]": ["0"] * 3, "etd_day[]": [""] * 3, "etd_time[]": [""] * 3,
            "pilot_out[]": ["0"] * 3, "dist[]": ["0"] * 3, "eca_dist[]": ["0"] * 3,
            "spd[]": ["0"] * 3, "sea_time[]": ["0"] * 3, "terminal[]": [""] * 3
        }

        # When
        response = auth_client.post(url, data)

        # Then
        rows = response.context["rows"]

        # 1개 삭제되어 2개 남음
        assert len(rows) == 2
        # B가 삭제되고 A, C만 남음
        assert rows[0]['port_code'] == "A"
        assert rows[1]['port_code'] == "C"
        # 번호 재정렬 확인 (1, 2)
        assert rows[1]['no'] == 2

    def test_proforma_action_new(self, auth_client):
        """[PROFORMA_ACTION_NEW] 화면 초기화 확인"""
        # Given
        url = reverse("input_data:proforma_create")
        data = {
            "action": "new",
            "port_code[]": ["EXISTING_DATA"],  # 기존 데이터가 있어도
        }

        # When
        response = auth_client.post(url, data)

        # Then
        rows = response.context["rows"]
        # 모든 행이 삭제되어야 함
        assert len(rows) == 0
        # 메시지 확인
        messages_list = list(response.context['messages'])
        assert any(msg.SCHEDULE_NEW_STARTED in m.message for m in messages_list)

    def test_proforma_data_dist_integration(self, auth_client, base_snapshot):
        """[PROFORMA_DATA_DIST] 거리 데이터 자동 연동 확인"""
        # Given: DB에 거리 정보 생성 (A -> B : 100 miles, ECA : 20)
        Distance.objects.create(
            data_id=base_snapshot,
            from_port_code="PORT_A",
            to_port_code="PORT_B",
            distance=100,
            eca_distance=20
        )

        url = reverse("input_data:proforma_create")

        # When: 화면에서 포트만 입력하고 'calculate' 요청 (거리는 0으로 보냄)
        data = {
            "action": "calculate",
            "data_id": base_snapshot.data_id,
            "port_code[]": ["PORT_A", "PORT_B"],
            "dist[]": ["0", "0"],
            "eca_dist[]": ["0", "0"],

            # 필수 더미
            "direction[]": ["E"] * 2, "turn_info[]": ["N"] * 2, "pilot_in[]": ["0"] * 2,
            "etb_no[]": ["0"] * 2, "etb_day[]": [""] * 2, "etb_time[]": [""] * 2,
            "work_hours[]": ["0"] * 2, "etd_no[]": ["0"] * 2, "etd_day[]": [""] * 2, "etd_time[]": [""] * 2,
            "pilot_out[]": ["0"] * 2, "spd[]": ["0"] * 2, "sea_time[]": ["0"] * 2, "terminal[]": [""] * 2
        }
        response = auth_client.post(url, data)

        # Then
        rows = response.context["rows"]
        # 두 번째 행(B)의 거리가 DB값으로 업데이트 되었는지 확인
        assert rows[1]['port_code'] == "PORT_B"
        assert int(rows[0]['dist']) == 100
        assert int(rows[0]['eca_dist']) == 20

    def test_proforma_calc_only(self, auth_client, base_snapshot):
        """[PROFORMA_CALC_ONLY] 저장 없이 계산만 수행 (DB 저장 X)"""
        url = reverse("input_data:proforma_create")

        # Given: 계산 가능한 데이터 (A->B, 100km, 5시간 소요)
        data = {
            "action": "calculate",
            "data_id": base_snapshot.data_id,
            "lane_code": "CALC_TEST",
            "proforma_name": "CALC_ONLY_PF",

            # Row 1 (A) 출발 12:00 -> Row 2 (B) 도착 17:00 (5시간)
            # Distance 100 -> Speed 20
            "port_code[]": ["PORT_A", "PORT_B"],

            "etd_no[]": ["0", "0"], "etd_time[]": ["1200", "0000"],  # A 출발
            "etb_no[]": ["0", "0"], "etb_time[]": ["0000", "1700"],  # B 도착

            "dist[]": ["0", "100"],

            # 더미
            "direction[]": ["E"] * 2, "turn_info[]": ["N"] * 2, "pilot_in[]": ["0"] * 2,
            "etb_day[]": [""] * 2, "work_hours[]": ["0"] * 2, "etd_day[]": [""] * 2,
            "pilot_out[]": ["0"] * 2, "eca_dist[]": ["0"] * 2, "spd[]": ["0"] * 2, "sea_time[]": ["0"] * 2,
            "terminal[]": [""] * 2
        }

        # When
        response = auth_client.post(url, data)

        # Then 1: 화면 계산 결과 확인
        rows = response.context["rows"]
        # Row 0 (A)에서 B까지 가는 속도/시간
        assert float(rows[0]['sea_time']) == 5.0
        assert float(rows[0]['spd']) == 20.0

        # Then 2: DB 저장 안됨 확인
        assert ProformaSchedule.objects.filter(proforma_name="CALC_ONLY_PF").count() == 0

        # Then 3: 성공 메시지가 아닌 일반 Info 메시지 확인
        messages_list = list(response.context['messages'])
        assert any(msg.SCHEDULE_CALCULATED in m.message for m in messages_list)

    def test_proforma_save_full(self, auth_client, base_snapshot):
        """[PROFORMA_SAVE_FULL] 계산 수행 및 DB 저장 확인"""
        url = reverse("input_data:proforma_create")

        # Given: 동일한 데이터로 Save 요청
        data = {
            "action": "save",
            "data_id": base_snapshot.data_id,
            "lane_code": "SAVE_TEST",
            "proforma_name": "SAVE_FULL_PF",

            "port_code[]": ["PORT_A", "PORT_B"],
            "dist[]": ["0", "100"],

            # 필수 더미
            "etd_no[]": ["0", "0"], "etd_time[]": ["1200", "0000"], "etb_no[]": ["0", "0"],
            "etb_time[]": ["0000", "1700"],
            "direction[]": ["E"] * 2, "turn_info[]": ["N"] * 2, "pilot_in[]": ["0"] * 2,
            "etb_day[]": [""] * 2, "work_hours[]": ["0"] * 2, "etd_day[]": [""] * 2,
            "pilot_out[]": ["0"] * 2, "eca_dist[]": ["0"] * 2, "spd[]": ["0"] * 2, "sea_time[]": ["0"] * 2,
            "terminal[]": [""] * 2
        }

        # When
        response = auth_client.post(url, data)

        # Then
        assert response.status_code == 200

        # 1. 화면에 계산 결과 유지
        rows = response.context["rows"]
        assert float(rows[0]['sea_time']) == 5.0  # 계산도 수행됨을 확인

        # 2. DB에 저장됨 확인
        saved_qs = ProformaSchedule.objects.filter(
            data_id=base_snapshot,
            proforma_name="SAVE_FULL_PF"
        )
        assert saved_qs.count() == 2
        assert saved_qs.first().vessel_service_lane_code == "SAVE_TEST"

        # 3. 저장 성공 메시지 확인
        messages_list = list(response.context['messages'])
        assert any(msg.SCHEDULE_SAVE_SUCCESS in m.message for m in messages_list)