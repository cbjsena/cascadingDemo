import pytest

from django.urls import reverse

from input_data.models import (
    CascadingSchedule,
    CascadingScheduleDetail,
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
        self, auth_client, cascading_with_details
    ):
        """
        [CASCADING_VIEW_003] Edit 모드 데이터 Load
        Detail 화면에서 넘어온 파라미터로 수정 모드 진입 시 기존 데이터가 정확히 로드되는지 검증
        """
        # When: 수정 모드 파라미터를 포함하여 GET 요청
        url = reverse("input_data:cascading_create")
        response = auth_client.get(
            url,
            {
                "scenario_id": cascading_with_details.scenario.id,
                "lane_code": cascading_with_details.proforma.lane_code,
                "proforma_name": cascading_with_details.proforma.proforma_name,
                "cascading_seq": cascading_with_details.cascading_seq,
            },
        )

        # Then: 데이터 검증
        assert response.status_code == 200
        assert response.context["is_edit_mode"] is True

        # preserved_data에 기존 데이터가 로드됨
        preserved_data = response.context["preserved_data"]
        assert preserved_data["own_vessel_count"] == 2
        assert preserved_data["effective_start_date"] is not None

        # restored_rows에 기존 선박 정보가 체크되고 선택된 상태로 표시
        restored_rows = response.context["restored_rows"]
        assert len(restored_rows) >= 2  # proforma의 declared_count

        # 기존 선박들이 체크된 상태인지 확인
        checked_vessels = [row for row in restored_rows if row.get("is_checked")]
        assert len(checked_vessels) == 2

    def test_cascading_act_001_save_creation(self, auth_client, cascading_form_data):
        """
        [CASCADING_ACT_001] Save Cascading (생성)
        새로운 Cascading 생성 시 변경된 모델 필드명에 맞춰 DB에 정상 저장되는지 검증
        """
        url = reverse("input_data:cascading_create")
        form_data = cascading_form_data.copy()
        form_data["action"] = "save"

        response = auth_client.post(url, data=form_data)

        # 저장 성공 및 리다이렉트 확인
        assert response.status_code == 302

        # DB에 저장된 데이터 검증
        cascading = CascadingSchedule.objects.first()
        assert cascading is not None
        assert cascading.own_vessel_count == 3
        assert cascading.proforma_start_etb_date is not None  # 자동 계산됨

        # Detail 데이터 검증
        details = CascadingScheduleDetail.objects.filter(cascading=cascading)
        assert details.count() == 3

        vessel_codes = list(details.values_list("vessel_code", flat=True))
        assert "V001" in vessel_codes
        assert "V002" in vessel_codes
        assert "V003" in vessel_codes

    def test_cascading_act_002_save_modification(
        self, auth_client, cascading_with_details, cascading_form_data
    ):
        """
        [CASCADING_ACT_002] Save Cascading (수정)
        기존 Cascading 수정 시 덮어쓰기 로직 검증
        """
        # Given: 기존 Cascading 데이터 존재 (Own Vessels=2)
        assert cascading_with_details.own_vessel_count == 2

        # When: Own Vessels를 5로 변경하여 수정
        url = reverse("input_data:cascading_create")
        form_data = cascading_form_data.copy()
        form_data.update(
            {
                "action": "save",
                "own_vessel_count": 5,  # 3에서 5로 변경
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

        # Then: 기존 Cascading이 삭제 후 재생성됨
        assert response.status_code == 302

        # 새로운 데이터로 저장됨
        cascading = CascadingSchedule.objects.first()
        assert cascading.own_vessel_count == 5

        # Detail 테이블도 새로운 선박 배정으로 갱신됨
        details = CascadingScheduleDetail.objects.filter(cascading=cascading)
        assert details.count() == 5

    def test_cascading_act_003_create_lrs(self, auth_client, cascading_form_data):
        """
        [CASCADING_ACT_003] Create LRS
        저장 및 LRS 생성 엔진 구동 동시 수행
        """
        url = reverse("input_data:cascading_create")
        form_data = cascading_form_data.copy()
        form_data["action"] = "create_lrs"

        response = auth_client.post(url, data=form_data)

        # 저장 성공 확인
        assert response.status_code == 302

        # Cascading DB 저장 확인
        cascading = CascadingSchedule.objects.first()
        assert cascading is not None

        # LongRangeSchedule 자동 생성 확인 (실제 LRS 생성 로직은 별도 서비스에서 처리)
        # 여기서는 Cascading 저장만 검증

    def test_cascading_act_004_validation_own_vessels(
        self, auth_client, cascading_invalid_form_data
    ):
        """
        [CASCADING_ACT_004] Validation - Own Vessels
        Own Vessels 수와 실제 선택된 선박 수의 일치 검증은 JavaScript(프론트엔드)에서 수행된다.
        서버 측에서는 own_vessel_count를 실제 vessel_code[] 개수로 산출하여 저장하므로,
        폼에 own_vessel_count=3을 보내도 실제 선박 2대만 보내면 2로 저장되는지 확인한다.
        """
        url = reverse("input_data:cascading_create")
        form_data = cascading_invalid_form_data.copy()
        form_data["action"] = "save"

        response = auth_client.post(url, data=form_data)

        # 서버는 에러 없이 저장하되, own_vessel_count는 실제 선박 수(2)로 산출됨
        assert response.status_code == 302
        cascading = CascadingSchedule.objects.first()
        assert cascading is not None
        assert cascading.own_vessel_count == 2  # 폼의 3이 아니라 실제 2로 저장
        assert CascadingScheduleDetail.objects.filter(cascading=cascading).count() == 2

    def test_cascading_act_005_auto_end_date(self, auth_client, cascading_form_data):
        """
        [CASCADING_ACT_005] Auto End Date
        Start Date 선택 시 End Date가 1년 후로 자동 설정되는지 검증 (JavaScript 로직)
        """
        # 이 테스트는 주로 프론트엔드 JavaScript 로직을 검증하므로,
        # 서버 측에서는 1년 후 날짜로 저장되는지만 확인
        url = reverse("input_data:cascading_create")
        form_data = cascading_form_data.copy()
        form_data["action"] = "save"

        response = auth_client.post(url, data=form_data)
        assert response.status_code == 302  # 저장 성공 시 리다이렉트

        # 저장 성공 확인
        cascading = CascadingSchedule.objects.first()
        assert cascading is not None
        assert cascading.effective_start_date.strftime("%Y-%m-%d") == "2026-02-15"
        assert cascading.effective_end_date.strftime("%Y-%m-%d") == "2027-02-15"

    def test_cascading_act_006_error_data_recovery(self, auth_client, sample_schedule):
        """
        [CASCADING_ACT_006] 에러 시 데이터 복구
        필수값 누락/에러 발생 시 입력값이 보존되는지 검증
        """
        url = reverse("input_data:cascading_create")

        # 불완전한 폼 데이터 (vessel_code[] 누락)
        incomplete_data = {
            "scenario_id": sample_schedule.scenario.id,
            "lane_code": sample_schedule.lane_code,
            "proforma_name": sample_schedule.proforma_name,
            "cascading_seq": 1,
            "own_vessel_count": 2,
            "effective_start_date": "2026-02-15",
            "effective_end_date": "2027-02-15",
            # vessel_code[] 누락으로 에러 유발
            "action": "save",
        }

        response = auth_client.post(url, data=incomplete_data)

        # View 구현에 따라 에러 시 리다이렉트 또는 200 응답
        if response.status_code == 200:
            # 에러 상태로 200 응답한 경우 - preserved_data에 입력값 유지 확인
            preserved_data = response.context.get("preserved_data", {})
            assert preserved_data.get("effective_start_date") == "2026-02-15"
            assert preserved_data.get("own_vessel_count") == "2"  # POST 데이터는 문자열
        else:
            # 리다이렉트된 경우 (에러가 발생했지만 redirect 처리)
            assert response.status_code == 302

    def test_cascading_list_001_list_view(self, auth_client, multiple_cascading_data):
        """
        [CASCADING_LIST_001] Cascading 목록 조회
        동적 Select 필터 기반의 목록 화면 표출 및 새 컬럼 표시 검증
        """
        url = reverse("input_data:cascading_list")
        response = auth_client.get(
            url,
            {
                "scenario_id": multiple_cascading_data[
                    0
                ].scenario.id,  # scenario_name 대신 scenario_id 사용
                "lane_code": "TEST_LANE",
            },
        )

        assert response.status_code == 200

        # 검색 조건에 맞는 데이터만 표출
        cascading_list = response.context["cascading_list"]
        assert len(cascading_list) == 2  # multiple_cascading_data에서 2개 생성

        # 새 컬럼들이 정상 렌더링되는지 확인 (템플릿에서 처리)
        content = response.content.decode()
        assert "Initial ETB Date" in content  # 템플릿의 실제 헤더명
        assert "Own Vessels" in content  # 템플릿의 실제 헤더명

    def test_cascading_detail_001_detail_view(
        self, auth_client, cascading_with_details
    ):
        """
        [CASCADING_DETAIL_001] Cascading 상세 조회
        특정 Cascading의 Master 정보 표시 시 새 필드들이 정상 출력되는지 검증
        """
        url = reverse(
            "input_data:cascading_detail", kwargs={"pk": cascading_with_details.id}
        )
        response = auth_client.get(url)

        assert response.status_code == 200

        # Context 데이터 검증
        cascading = response.context["cascading"]
        assert cascading.id == cascading_with_details.id

        # 새 필드들이 정상 출력되는지 확인
        content = response.content.decode()
        assert str(cascading.own_vessel_count) in content

        # Edit 버튼의 href에 올바른 파라미터 포함
        edit_url = reverse("input_data:cascading_create")
        assert edit_url in content
        assert f"scenario_id={cascading.scenario.id}" in content
        assert f"cascading_seq={cascading.cascading_seq}" in content

    def test_cascading_detail_002_edit_mode_transition(
        self, auth_client, cascading_with_details
    ):
        """
        [CASCADING_DETAIL_002] Edit 모드 전환
        Detail 화면에서 Edit 버튼 클릭 시 Create 화면으로 정확한 파라미터와 함께 이동하는지 검증
        """
        # Detail 화면에서 Edit URL 파라미터 확인
        detail_url = reverse(
            "input_data:cascading_detail", kwargs={"pk": cascading_with_details.id}
        )
        response = auth_client.get(detail_url)

        assert response.status_code == 200

        # Edit URL 생성 및 이동
        edit_url = reverse("input_data:cascading_create")
        edit_response = auth_client.get(
            edit_url,
            {
                "scenario_id": cascading_with_details.scenario.id,
                "lane_code": cascading_with_details.proforma.lane_code,
                "proforma_name": cascading_with_details.proforma.proforma_name,
                "cascading_seq": cascading_with_details.cascading_seq,
            },
        )

        # Create 화면으로 이동 확인
        assert edit_response.status_code == 200
        assert edit_response.context["is_edit_mode"] is True

        # 기존 선박 배정 정보가 체크된 상태로 로드
        restored_rows = edit_response.context["restored_rows"]
        checked_rows = [row for row in restored_rows if row.get("is_checked")]
        assert len(checked_rows) == 2  # cascading_with_details의 선박 수
