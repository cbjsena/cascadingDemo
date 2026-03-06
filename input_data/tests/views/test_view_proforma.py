import io

import openpyxl
import pytest

from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone

from common import messages as msg
from common.menus import MenuGroup, MenuItem, MenuSection
from input_data.models import ProformaSchedule, ProformaScheduleDetail


@pytest.mark.django_db
class TestProformaReadViews:
    """
    [그룹 1] 조회 관련 테스트
    범위: 목록(List), 검색(Search), 상세(Detail), 생성화면 진입(Initial)
    """

    def test_proforma_list_view(self, auth_client, sample_schedule):
        """
        [PF_LIST_001] 목록 조회 테스트
        Changed: 메뉴 그룹이 'Schedule'인지 확인
        """
        url = reverse("input_data:proforma_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "input_data/proforma_list.html" in [t.name for t in response.templates]

        # 리스트 데이터 확인
        proforma_list = response.context["proforma_list"]
        assert len(proforma_list) >= 1
        # [수정됨] 딕셔너리 접근(["lane_code"])에서 객체 속성 접근(.lane_id)으로 변경
        assert any(item.lane_id == "TEST_LANE" for item in proforma_list)

        # [Check] 메뉴 그룹 확인
        assert response.context["current_group"] == MenuGroup.SCHEDULE

    def test_proforma_list_search(self, auth_client, base_scenario, user):
        """
        [PF_LIST_002] 검색 기능 테스트
        """
        # 검색 대상이 아닌 데이터 추가 (Master - Detail 분리 구조 적용)
        master = ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_id="OTHER",
            proforma_name="PF_002",
            effective_from_date=timezone.now(),
            duration=14.0,
            declared_capacity="5000",
            declared_count=2,
            created_by=user,
            updated_by=user,
        )

        ProformaScheduleDetail.objects.create(
            proforma=master,
            direction="E",
            port_id="KRPUS",
            calling_port_indicator="1",
            calling_port_seq=1,
            turn_port_info_code="N",
            pilot_in_hours=3.0,
            etb_day_number=0,
            etb_day_code="SUN",
            etb_day_time="0900",
            actual_work_hours=24.0,
            etd_day_number=1,
            etd_day_code="MON",
            etd_day_time="1800",
            pilot_out_hours=3.0,
            link_distance=500,
            link_eca_distance=0,
            link_speed=20.0,
            sea_time_hours=24.0,
            terminal_code="PNC",
            created_by=user,
            updated_by=user,
        )

        url = reverse("input_data:proforma_list")

        # 'OTHER' 검색
        response = auth_client.get(url, {"lane_code": "OTHER"})
        results = response.context["proforma_list"]
        assert len(results) == 1
        assert results[0].lane_id == "OTHER"

        # 'TEST' 검색 (OTHER 제외 확인)
        response = auth_client.get(url, {"lane_code": "TEST"})
        results = response.context["proforma_list"]
        assert not any(item.lane_id == "OTHER" for item in results)

    def test_proforma_detail_view(self, auth_client, sample_schedule):
        """
        [PF_DETAIL_001] 상세 조회 테스트
        Changed: 메뉴 그룹이 'Schedule'인지 확인
        """
        url = reverse("input_data:proforma_detail")
        params = {
            "scenario_id": sample_schedule.scenario.id,
            "lane_code": sample_schedule.lane_id,
            "proforma_name": sample_schedule.proforma_name,
        }
        response = auth_client.get(url, params)

        assert response.status_code == 200
        assert "input_data/proforma_detail.html" in [t.name for t in response.templates]

        header = response.context["header"]
        assert header["lane_code"] == "TEST_LANE"
        # [Check] 메뉴 그룹 확인
        assert response.context["current_group"] == MenuGroup.SCHEDULE
        assert len(response.context["rows"]) == 1

    def test_proforma_view_initial(self, auth_client, base_scenario):
        """
        [PF_CREATE_001] 생성 화면 초기 진입
        Changed: Creation 섹션의 Schedule 그룹인지 확인
        """
        url = reverse("input_data:proforma_create")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert len(response.context["rows"]) == 0
        assert "scenarios" in response.context

        # [Check] 메뉴 섹션과 그룹, 모델 확인
        assert response.context["current_section"] == MenuSection.CREATION
        assert response.context["current_group"] == MenuGroup.SCHEDULE
        assert response.context["current_model"] == MenuItem.PROFORMA_CREATE

    def test_proforma_edit_mode_load(self, auth_client, sample_schedule):
        """
        [PF_CREATE_002] 수정 모드 데이터 로드
        """
        url = reverse("input_data:proforma_create")
        params = {
            "scenario_id": sample_schedule.scenario.id,
            "lane_code": sample_schedule.lane_id,
            "proforma_name": sample_schedule.proforma_name,
        }
        response = auth_client.get(url, params)

        assert response.status_code == 200

        header = response.context["header"]
        rows = response.context["rows"]
        assert header["scenario_id"] == sample_schedule.scenario.id
        assert rows[0]["port_code"] == "KRPUS"


@pytest.mark.django_db
class TestProformaGridActions:
    """
    [그룹 2] 그리드 조작 (View Integration)
    Controller가 Service를 잘 호출하는지 확인
    """

    def test_action_add_row(self, auth_client, base_scenario):
        """[PF_GRID_001] 행 추가"""
        url = reverse("input_data:proforma_create")
        data = {
            "action": "add_row",
            "scenario_id": base_scenario.id,
            "port_code[]": [],
        }
        response = auth_client.post(url, data)
        rows = response.context["rows"]
        assert len(rows) == 1
        assert rows[0]["etb_day"] == "SUN"  # Default Value

    def test_action_insert_row(self, auth_client, base_scenario):
        """[PF_GRID_002] 행 삽입"""
        url = reverse("input_data:proforma_create")
        # A, B 사이에 삽입 요청
        data = {
            "action": "insert_row",
            "scenario_id": base_scenario.id,
            "selected_index": 0,
            "port_code[]": ["A", "B"],
            "direction[]": ["E", "E"],
            "etb_no[]": ["0", "2"],
            "etd_no[]": ["1", "3"],
        }
        response = auth_client.post(url, data)
        rows = response.context["rows"]

        assert len(rows) == 3
        assert rows[0]["port_code"] == "A"
        assert rows[1]["port_code"] == ""  # New Row
        assert rows[2]["port_code"] == "B"

    def test_action_delete_row(self, auth_client, base_scenario):
        """
        [PF_GRID_003] 선택 행 삭제
        """
        url = reverse("input_data:proforma_create")
        # index 1 (B) 삭제
        data = {
            "action": "delete_row",
            "scenario_id": base_scenario.id,
            "row_check": ["1"],
            "port_code[]": ["A", "B", "C"],
            "etb_no[]": ["0", "1", "2"],
            "etd_no[]": ["0", "1", "2"],
        }
        response = auth_client.post(url, data)
        rows = response.context["rows"]

        assert len(rows) == 2
        assert rows[0]["port_code"] == "A"
        assert rows[1]["port_code"] == "C"

    def test_action_new(self, auth_client, base_scenario):
        """
        [PF_GRID_004] 화면 초기화
        """
        url = reverse("input_data:proforma_create")
        data = {"action": "new", "port_code[]": ["A", "B"]}
        response = auth_client.post(url, data)
        # 리다이렉트 또는 빈 Rows 반환 확인
        if response.status_code == 302:
            assert True
        else:
            assert len(response.context["rows"]) == 0


@pytest.mark.django_db
class TestProformaCalculation:
    """
    [그룹 3] 계산 및 저장 (View Integration)
    """

    def test_action_calculate(self, auth_client, base_scenario):
        """
        [PF_CALC_001/002] 계산 요청
        View가 Service를 호출해 계산된 rows를 반환하는지 확인
        """
        url = reverse("input_data:proforma_create")
        data = {
            "action": "calculate",
            "scenario_id": base_scenario.id,
            "port_code[]": ["A", "B"],
            "etb_day[]": ["SUN", "MON"],  # 필수 데이터
            "etb_time[]": ["0000", "0000"],
        }
        response = auth_client.post(url, data)
        assert response.status_code == 200

        rows = response.context["rows"]
        assert len(rows) == 2
        # 계산 결과 메시지 확인
        messages = list(get_messages(response.wsgi_request))
        assert any(msg.SCHEDULE_CALCULATED in str(m) for m in messages)

    def test_action_save_full(self, auth_client, base_scenario):
        """
        [PF_SAVE_001] 저장 요청 및 리다이렉트 (Master-Detail)
        """
        url = reverse("input_data:proforma_create")
        data = {
            "action": "save",
            "scenario_id": base_scenario.id,
            "lane_code": "TEST_SAVE",
            "proforma_name": "PF_SAVE",
            "effective_from_date": ["2026-01-01"],
            "capacity": ["5000"],
            "count": ["2"],
            "duration": ["49"],
            "port_code[]": ["KRPUS"],
            "direction[]": ["E"],
            "pilot_in[]": ["2.000"],
            "work_hours[]": ["2.000"],
            "pilot_out[]": ["2.000"],
            "etb_no[]": ["0"],
            "etb_day[]": ["SUN"],
            "etb_time[]": ["0000"],
            "dist[]": ["0"],
        }

        response = auth_client.post(url, data, follow=True)

        assert response.status_code == 200
        messages = list(get_messages(response.wsgi_request))
        assert any(msg.SCHEDULE_SAVE_SUCCESS in str(m) for m in messages)

        # Master와 Detail이 모두 생성되었는지 확인
        assert ProformaSchedule.objects.filter(lane_id="TEST_SAVE").exists()
        assert ProformaScheduleDetail.objects.filter(port_id="KRPUS").exists()


@pytest.mark.django_db
class TestProformaFileOperations:
    """
    [그룹 5] 파일 처리 테스트
    범위: Export(Excel, CSV), Upload, Template
    """

    def test_action_export_excel(self, auth_client, base_scenario):
        """
        [PF_FILE_001] 엑셀 다운로드
        """
        url = reverse("input_data:proforma_create")
        data = {
            "action": "export",
            "scenario_id": base_scenario.id,
            "lane_code": "EXP_LANE",
            "proforma_name": "EXP_PF",
            "port_code[]": ["A"],
        }
        response = auth_client.post(url, data)

        assert response.status_code == 200
        assert "spreadsheetml.sheet" in response["Content-Type"]
        assert "EXP_LANE_EXP_PF.xlsx" in response["Content-Disposition"]

    def test_action_csv(self, auth_client, base_scenario):
        """
        [PF_FILE_002] DB 입력용 CSV 다운로드
        """
        url = reverse("input_data:proforma_create")
        data = {
            "action": "csv",
            "scenario_id": base_scenario.id,
            "lane_code": "CSV_LANE",
            "proforma_name": "CSV_PF",
            "port_code[]": ["A"],
            "turn_port_info_code[]": ["N"],
        }
        response = auth_client.post(url, data)

        assert response.status_code == 200
        assert "text/csv" in response["Content-Type"]
        content = response.content.decode("utf-8")
        assert "CSV_LANE" in content

    def test_upload_excel(self, auth_client, base_scenario):
        """
        [PF_FILE_003] 엑셀 업로드
        """
        # 엑셀 파일 생성 (In-Memory)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Proforma Schedule"

        # 헤더 & 데이터 작성 (Config에 맞춰서)
        ws["A2"] = "Scenario ID"
        ws["A3"] = base_scenario.id
        ws["C2"] = "Lane"
        ws["C3"] = "UP_LANE"
        ws["B6"] = "Port\nCode"
        ws["B7"] = "UP_PORT"

        f = io.BytesIO()
        wb.save(f)
        f.seek(0)
        f.name = "upload_test.xlsx"

        url = reverse("input_data:proforma_upload")
        data = {"excel_file": f}
        response = auth_client.post(url, data)

        assert response.status_code == 200
        # 파싱 결과 Context 확인
        assert response.context["header"]["lane_code"] == "UP_LANE"
        assert response.context["rows"][0]["port_code"] == "UP_PORT"

    def test_template_download(self, auth_client):
        """
        [PF_FILE_004] 템플릿 다운로드
        """
        url = reverse("input_data:proforma_template")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "spreadsheetml.sheet" in response["Content-Type"]
        assert "Proforma_Template.xlsx" in response["Content-Disposition"]
