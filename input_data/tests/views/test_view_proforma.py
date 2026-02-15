import io

import openpyxl
import pytest

from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone

from input_data.models import Distance, ProformaSchedule


@pytest.mark.django_db
class TestProformaReadViews:
    """
    [그룹 1] 조회 관련 테스트
    범위: 목록(List), 검색(Search), 상세(Detail), 생성화면 진입(Initial), 수정모드(Edit Load)
    """

    def test_proforma_list_view(self, auth_client, sample_schedule):
        """
        [PF_LIST_001] 목록 조회 테스트
        """
        url = reverse("input_data:proforma_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "input_data/proforma_list.html" in [t.name for t in response.templates]

        # 리스트 데이터 확인
        proforma_list = response.context["proforma_list"]
        assert len(proforma_list) >= 1
        assert any(item["lane_code"] == "TEST_LANE" for item in proforma_list)

    def test_proforma_list_search(self, auth_client, base_scenario, user):
        """
        [PF_LIST_002] 검색 기능 테스트
        """
        # 검색 대상이 아닌 데이터 추가
        ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_code="OTHER",
            proforma_name="PF_002",
            effective_from_date=timezone.now(),
            duration=14.0,
            declared_capacity="5000",
            declared_count=2,
            direction="E",
            port_code="KRPUS",
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
        assert results[0]["lane_code"] == "OTHER"

        # 'TEST' 검색 (OTHER 제외 확인)
        response = auth_client.get(url, {"lane_code": "TEST"})
        results = response.context["proforma_list"]
        assert not any(item["lane_code"] == "OTHER" for item in results)

    def test_proforma_detail_view(self, auth_client, sample_schedule):
        """
        [PF_DETAIL_001] 상세 조회 테스트
        """
        url = reverse("input_data:proforma_detail")
        params = {
            "scenario_id": sample_schedule.scenario.id,
            "lane_code": sample_schedule.lane_code,
            "proforma_name": sample_schedule.proforma_name,
        }
        response = auth_client.get(url, params)

        assert response.status_code == 200
        assert "input_data/proforma_detail.html" in [t.name for t in response.templates]

        header = response.context["header"]
        assert header["lane_code"] == "TEST_LANE"
        assert len(response.context["rows"]) == 1

    def test_proforma_view_initial(self, auth_client, base_scenario):
        """
        [PF_CREATE_001] 생성 화면 초기 진입
        """
        url = reverse("input_data:proforma_create")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert len(response.context["rows"]) == 0
        assert "scenarios" in response.context

    def test_proforma_edit_mode_load(self, auth_client, sample_schedule):
        """
        [PF_CREATE_002] 수정 모드 데이터 로드
        """
        url = reverse("input_data:proforma_create")
        params = {
            "scenario_id": sample_schedule.scenario.id,
            "lane_code": sample_schedule.lane_code,
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
    [그룹 2] 그리드 조작 테스트
    범위: 행 추가(Add), 삽입(Insert), 삭제(Delete), 초기화(New)
    """

    def test_action_add_row(self, auth_client, base_scenario):
        """
        [PF_GRID_001] 최하단 행 추가
        """
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
        """
        [PF_GRID_002] 중간 행 삽입
        """
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
    [그룹 3] 계산 로직 테스트
    범위: 거리 데이터 연동, 단순 계산(Save 없음)
    """

    def test_data_distance_integration(self, auth_client, base_scenario):
        """
        [PF_CALC_001] 거리 데이터 자동 조회
        """
        Distance.objects.create(
            scenario=base_scenario,
            from_port_code="PUS",
            to_port_code="TYO",
            distance=500,
            eca_distance=100,
        )

        url = reverse("input_data:proforma_create")
        data = {
            "action": "calculate",
            "scenario_id": base_scenario.id,
            "port_code[]": ["PUS", "TYO"],
            "dist[]": ["0", "0"],
            "etb_day[]": ["SUN", "MON"],
            "etb_time[]": ["0000", "0000"],
        }
        response = auth_client.post(url, data)
        rows = response.context["rows"]

        assert float(rows[0]["dist"]) == 500
        assert float(rows[0]["eca_dist"]) == 100

    def test_action_calculate_only(self, auth_client, base_scenario):
        """
        [PF_CALC_002] 저장 없이 계산만 수행
        """
        url = reverse("input_data:proforma_create")
        data = {
            "action": "calculate",
            "scenario_id": base_scenario.id,
            "port_code[]": ["A", "B"],
            "dist[]": ["240", "0"],
            "etb_day[]": ["SUN", "MON"],
            "etb_time[]": ["0000", "0000"],  # 24h 차이
            "pilot_in[]": ["0", "0"],
            "pilot_out[]": ["0", "0"],
        }
        response = auth_client.post(url, data)
        rows = response.context["rows"]

        # 속도 계산 확인 (240NM / 24h = 10kts)
        assert float(rows[0]["spd"]) == 10.0
        # DB 저장 안됨 확인
        assert ProformaSchedule.objects.count() == 0


@pytest.mark.django_db
class TestProformaPersistence:
    """
    [그룹 4] 데이터 영속성 테스트
    범위: DB 저장 (Save)
    """

    def test_action_save_full(self, auth_client, base_scenario):
        """
        [PF_SAVE_001] 계산 후 DB 저장 및 리다이렉트
        """
        url = reverse("input_data:proforma_create")
        data = {
            "action": "save",
            "scenario_id": base_scenario.id,
            "lane_code": "TEST",
            "proforma_name": "PF_SAVED",
            "duration": "10",
            "effective_from_date": "2026-01-01",
            "capacity": "14000",
            "count": "5",
            # Grid Data
            "no[]": ["1"],
            "port_code[]": ["KRPUS"],
            "direction[]": ["E"],
            "turn_port_info_code[]": ["N"],
            "etb_no[]": ["0"],
            "etb_day[]": ["SUN"],
            "etb_time[]": ["0000"],
            "etd_no[]": ["0"],
            "etd_day[]": ["SUN"],
            "etd_time[]": ["1200"],
            "terminal[]": ["KRPUS01"],
            # Nullable Fields
            "pilot_in[]": ["2.0"],
            "work_hours[]": ["12.0"],
            "pilot_out[]": ["2.0"],
            "dist[]": ["100"],
            "spd[]": ["15.0"],
            "sea_time[]": ["5.0"],
        }

        # follow=True로 리다이렉트까지 따라감
        response = auth_client.post(url, data, follow=True)

        # 1. 메시지 확인
        messages = list(get_messages(response.wsgi_request))
        assert any("saved successfully" in str(m) for m in messages)

        # 2. DB 저장 확인
        assert ProformaSchedule.objects.count() == 1
        obj = ProformaSchedule.objects.first()
        assert obj.port_code == "KRPUS"
        assert obj.effective_from_date.strftime("%Y-%m-%d") == "2026-01-01"

        # 3. 리다이렉트 쿼리 스트링 확인 (UX: 계속 편집 모드 유지)
        assert "lane_code=TEST" in response.request["QUERY_STRING"]


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
        ws["C3"] = "UPLOAD_LANE"
        ws["B6"] = "Port\nCode"
        ws["B7"] = "UPLOAD_PORT"

        f = io.BytesIO()
        wb.save(f)
        f.seek(0)
        f.name = "upload_test.xlsx"

        url = reverse("input_data:proforma_upload")
        data = {"excel_file": f}
        response = auth_client.post(url, data)

        assert response.status_code == 200
        # 파싱 결과 Context 확인
        assert response.context["header"]["lane_code"] == "UPLOAD_LANE"
        assert response.context["rows"][0]["port_code"] == "UPLOAD_PORT"

    def test_template_download(self, auth_client):
        """
        [PF_FILE_004] 템플릿 다운로드
        """
        url = reverse("input_data:proforma_template")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "spreadsheetml.sheet" in response["Content-Type"]
        assert "Proforma_Template.xlsx" in response["Content-Disposition"]
