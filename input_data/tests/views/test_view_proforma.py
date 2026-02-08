import pytest
import io
import openpyxl
from django.urls import reverse
from django.contrib.messages import get_messages
from input_data.models import ProformaSchedule, Distance


@pytest.mark.django_db
class TestProformaView:
    """
    Proforma Schedule 상세 화면 View 테스트
    [범위] 행 추가/삭제/삽입, 계산, 저장, 엑셀/CSV Export & Upload
    """

    # ==========================================================================
    # 1. 화면 진입
    # ==========================================================================
    def test_proforma_view_initial(self, auth_client, base_scenario):
        """
        [PROFORMA_VIEW_001] Proforma 생성 화면 조회
        """
        url = reverse('input_data:proforma_create')
        response = auth_client.get(url)

        assert response.status_code == 200
        # Context에 빈 rows와 시나리오 목록이 있는지 확인
        assert "rows" in response.context
        assert len(response.context["rows"]) == 0
        assert "scenarios" in response.context

    # ==========================================================================
    # 2. 행 조작 (Grid Actions)
    # ==========================================================================
    def test_action_add_row(self, auth_client, base_scenario):
        """
        [PROFORMA_ACTION_ADD] 최하단 행 추가
        """
        url = reverse('input_data:proforma_create')
        data = {
            'action': 'add_row',
            'scenario_id': base_scenario.id,
            # 현재 행이 없다는 가정하에 빈 리스트 전송
            'port_code[]': []
        }
        response = auth_client.post(url, data)

        rows = response.context['rows']
        assert len(rows) == 1
        # 기본값 확인 (Service의 _create_default_row 로직)
        assert rows[0]['etb_day'] == 'SUN'

    def test_action_insert_row(self, auth_client, base_scenario):
        """
        [PROFORMA_ACTION_INSERT] 중간 행 삽입
        """
        url = reverse('input_data:proforma_create')
        # 2개의 기존 행이 있다고 가정하고 0번 인덱스 뒤에 삽입 요청
        data = {
            'action': 'insert_row',
            'scenario_id': base_scenario.id,
            'selected_index': 0,

            # 기존 데이터 (List 형태로 전송)
            'port_code[]': ['A', 'B'],
            'direction[]': ['E', 'E'],
            'etb_no[]': ['0', '2'],
            'etd_no[]': ['1', '3'],
        }
        response = auth_client.post(url, data)

        rows = response.context['rows']
        # 2개 -> 3개
        assert len(rows) == 3
        # 0번(A) 뒤인 1번 인덱스에 새 행이 삽입됨
        assert rows[0]['port_code'] == 'A'
        assert rows[1]['port_code'] == ''  # 새 행
        assert rows[2]['port_code'] == 'B'

    def test_action_delete_row(self, auth_client, base_scenario):
        """
        [PROFORMA_ACTION_DELETE] 선택 행 삭제
        """
        url = reverse('input_data:proforma_create')
        # 3개의 행 중 1번 인덱스(B) 삭제
        data = {
            'action': 'delete_row',
            'scenario_id': base_scenario.id,
            'row_check': ['1'],

            'port_code[]': ['A', 'B', 'C'],
            'etb_no[]': ['0', '1', '2'],
            'etd_no[]': ['0', '1', '2'],
        }
        response = auth_client.post(url, data)

        rows = response.context['rows']
        assert len(rows) == 2
        assert rows[0]['port_code'] == 'A'
        assert rows[1]['port_code'] == 'C'

    def test_action_new(self, auth_client, base_scenario):
        """
        [PROFORMA_ACTION_NEW] 화면 초기화
        """
        url = reverse('input_data:proforma_create')
        data = {
            'action': 'new',
            'port_code[]': ['A', 'B']
        }
        response = auth_client.post(url, data)

        rows = response.context['rows']
        assert len(response.context['rows']) == 0

    # ==========================================================================
    # 3. 계산 및 데이터 연동 (Calculation)
    # ==========================================================================
    def test_data_distance_integration(self, auth_client, base_scenario):
        """
        [PROFORMA_DATA_DIST] 거리 데이터 자동 조회
        """
        # Distance DB 데이터 생성 (PUS -> TYO : 500)
        Distance.objects.create(
            scenario=base_scenario,
            from_port_code='PUS', to_port_code='TYO',
            distance=500, eca_distance=100
        )

        url = reverse('input_data:proforma_create')
        # PUS -> TYO 입력 후 계산 요청
        data = {
            'action': 'calculate',
            'scenario_id': base_scenario.id,
            'port_code[]': ['PUS', 'TYO'],
            'dist[]': ['0', '0'],  # 초기값 0
            'etb_day[]': ['SUN', 'MON'],
            'etb_time[]': ['0000', '0000'],
        }
        response = auth_client.post(url, data)

        rows = response.context['rows']
        # 첫 번째 행(PUS->TYO 구간)의 거리가 500으로 업데이트 되었는지 확인
        assert float(rows[0]['dist']) == 500
        assert float(rows[0]['eca_dist']) == 100

    def test_action_calculate_only(self, auth_client, base_scenario):
        """
        [PROFORMA_CALC_ONLY] 저장 없이 계산만 수행
        """
        url = reverse('input_data:proforma_create')
        data = {
            'action': 'calculate',
            'scenario_id': base_scenario.id,
            'port_code[]': ['A', 'B'],
            'dist[]': ['240', '0'],  # 거리 240
            'etb_day[]': ['SUN', 'MON'],
            'etb_time[]': ['0000', '0000'],  # 24시간 차이 -> 속도 10노트 예상
            'pilot_in[]': ['0', '0'],
            'pilot_out[]': ['0', '0']
        }
        response = auth_client.post(url, data)

        rows = response.context['rows']
        # 계산 결과 확인
        assert float(rows[0]['spd']) == 10.0

        # DB 저장 안됨 확인
        assert ProformaSchedule.objects.count() == 0

    # ==========================================================================
    # 4. 저장 (Save)
    # ==========================================================================
    def test_action_save_full(self, auth_client, base_scenario):
        """
        [PROFORMA_SAVE_FULL] 계산 후 DB 저장
        """
        url = reverse('input_data:proforma_create')
        data = {
            'action': 'save',
            # Header
            'scenario_id': base_scenario.id,
            'lane_code': 'TEST',
            'proforma_name': 'PF_SAVED',
            'duration': '10',
            'effective_date': '2026-01-01',
            'capacity': '14000',
            'count': '5',
            # Grid
            'no[]': ['1'],
            'port_code[]': ['PUS'],
            'direction[]': ['E'],
            'turn_port_info_code[]': ['N'],
            # ETB Info (etb_day_number는 Not Null)
            'etb_day[]': ['SUN'],
            'etb_time[]': ['0000'],
            'etb_no[]': ['0'],  # Service에서 etb_day_number로 매핑됨

            # ETD Info (etd_day_number는 Not Null)
            'etd_day[]': ['SUN'],
            'etd_time[]': ['1200'],
            'etd_no[]': ['0'],  # Service에서 etd_day_number로 매핑됨

            # [중요] Terminal Code는 Not Null이므로 반드시 값 전달
            'terminal[]': ['PNC'],

            # Nullable Fields (값이 없으면 Service에서 0 또는 None 처리)
            'pilot_in[]': ['2.0'],
            'work_hours[]': ['12.0'],
            'pilot_out[]': ['2.0'],
            'dist[]': ['100'],
            'spd[]': ['15.0'],
            'sea_time[]': ['5.0'],
        }

        response = auth_client.post(url, data)

        # 1. 성공 메시지 확인
        messages = list(get_messages(response.wsgi_request))
        # 디버깅용: 실패 시 메시지 출력
        if response.status_code == 200 and ProformaSchedule.objects.count() == 0:
            print("Save Failed Messages:", [str(m) for m in messages])

        assert any("saved successfully" in str(m) for m in messages)

        # 2. DB 저장 확인
        assert ProformaSchedule.objects.count() == 1
        obj = ProformaSchedule.objects.first()

        # 3. 주요 필드 값 검증
        assert obj.scenario == base_scenario
        assert obj.port_code == 'PUS'
        assert obj.terminal_code == 'PNC'  # Terminal 저장 확인
        assert obj.declared_capacity == '14000'
        # Timezone Aware 날짜 확인
        assert obj.effective_date.strftime('%Y-%m-%d') == '2026-01-01'

    # ==========================================================================
    # 5. Export / Import / CSV
    # ==========================================================================
    def test_action_export_excel(self, auth_client, base_scenario):
        """
        [PROFORMA_EXPORT_EXCEL] 엑셀 다운로드
        """
        url = reverse('input_data:proforma_create')
        data = {
            'action': 'export',
            'scenario_id': base_scenario.id,
            'lane_code': 'EXP_LANE',
            'proforma_name': 'EXP_PF',
            'port_code[]': ['A']
        }
        response = auth_client.post(url, data)

        assert response.status_code == 200
        assert 'spreadsheetml.sheet' in response['Content-Type']
        assert 'EXP_LANE_EXP_PF_Proforma.xlsx' in response['Content-Disposition']

    def test_action_csv(self, auth_client, base_scenario):
        """
        [PROFORMA_EXPORT_CSV] DB 입력용 CSV 다운로드
        """
        url = reverse('input_data:proforma_create')
        data = {
            'action': 'csv',
            'scenario_id': base_scenario.id,
            'lane_code': 'CSV_LANE',
            'proforma_name': 'CSV_PF',
            'port_code[]': ['A'],
            'turn_port_info_code[]': ['N']
        }
        response = auth_client.post(url, data)

        assert response.status_code == 200
        assert 'text/csv' in response['Content-Type']

        content = response.content.decode('utf-8')
        # 헤더와 데이터 포함 여부 확인
        assert "VSL_SVCE_LANE_CD" in content
        assert "CSV_LANE" in content

    def test_upload_excel(self, auth_client, base_scenario):
        """
        [PROFORMA_UPLOAD] 엑셀 업로드
        """
        # 메모리에 엑셀 파일 생성
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Proforma Schedule"

        # Header (Scenario ID, Lane Code) - Config 좌표 참조
        ws['A2'] = "Scenario ID";
        ws['A3'] = base_scenario.id
        ws['C2'] = "Lane";
        ws['C3'] = "UPLOAD_LANE"

        # Grid Data (Port Code at Col 2, Row 7 based on config)
        ws['B6'] = "Port\nCode"  # Header
        ws['B7'] = "UPLOAD_PORT"  # Data

        f = io.BytesIO()
        wb.save(f)
        f.seek(0)
        f.name = "upload_test.xlsx"

        url = reverse('input_data:proforma_upload')
        data = {'excel_file': f}

        response = auth_client.post(url, data)

        assert response.status_code == 200
        # Context에 파싱 결과가 담겼는지 확인
        assert response.context['header']['lane_code'] == "UPLOAD_LANE"
        rows = response.context['rows']
        assert rows[0]['port_code'] == "UPLOAD_PORT"

    def test_template_download(self, auth_client):
        """
        [PROFORMA_TEMPLATE_DOWNLOAD] 템플릿 다운로드
        """
        url = reverse('input_data:proforma_template')
        response = auth_client.get(url)

        assert response.status_code == 200
        assert 'spreadsheetml.sheet' in response['Content-Type']
        assert 'Proforma_Template.xlsx' in response['Content-Disposition']