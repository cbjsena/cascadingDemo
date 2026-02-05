import io
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from common import messages as msg

class ExcelManager:
    """
    엑셀 생성 및 파싱 유틸리티
    Config Dictionary를 받아 동작하도록 설계
    """

    def __init__(self):
        # 스타일 정의
        self.bold_font = Font(bold=True)
        self.center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
        self.thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                                  bottom=Side(style='thin'))
        self.header_fill = PatternFill(start_color="E2E3E5", end_color="E2E3E5", fill_type="solid")
        self.summary_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

    def create_template(self, config, row_count=10):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = config.get('sheet_title', 'Sheet1')

        # 1. Basic Info
        self._write_section_title(ws, 'A1', "Basic Information")
        basic_examples = config.get('basic_examples', {})

        for item in config['basic_headers']:
            # [수정] 튜플 길이에 따라 너비(Width) 처리
            if len(item) == 4:
                h_loc, text, key, width = item
            else:
                h_loc, text, key = item
                width = 3  # 기본값 3 (너비 미지정 시)

            example_val = basic_examples.get(key, '')
            self._write_merged_header_value(ws, h_loc, text, example_val, width)

        # 2. Grid Headers
        grid_start_row = config.get('start_row_grid', 6)
        self._write_section_title(ws, f'A{grid_start_row - 1}', "Port Schedule")

        for idx, (text, _, _) in enumerate(config['grid_headers'], start=1):
            cell = ws.cell(row=grid_start_row, column=idx, value=text)
            self._apply_header_style(cell)

        # 3. Empty Rows (With Example for First Row)
        data_start_row = config.get('start_row_data', 7)

        # [수정] Grid 예시 값 가져오기
        grid_examples = config.get('grid_examples', {})

        for i in range(row_count):
            curr_row = data_start_row + i

            # No. 컬럼 (자동 증가)
            cell_no = ws.cell(row=curr_row, column=1, value=i + 1)
            self._apply_body_style(cell_no)

            # 나머지 컬럼 채우기
            for idx, (_, key, col_idx) in enumerate(config['grid_headers']):
                if col_idx == 1: continue  # No 컬럼은 위에서 처리함

                cell = ws.cell(row=curr_row, column=col_idx)

                # [신규] 첫 번째 행(i==0)이고, 예시 데이터가 설정되어 있다면 값 입력
                if i == 0 and grid_examples:
                    val = grid_examples.get(key, '')
                    cell.value = val

                self._apply_body_style(cell)

        # 4. Summary Row (설정 없으면 자동 스킵됨)
        end_row = data_start_row + row_count - 1
        if 'summary_cols' in config:
            self._write_summary(ws, end_row + 1, data_start_row, end_row, config['summary_cols'],
                                len(config['grid_headers']))

        # 5. Width Adjustment
        col_widths = config.get('col_widths', [])
        self._adjust_widths(ws, col_widths)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    def parse_excel(self, file_obj, config):
        try:
            wb = openpyxl.load_workbook(file_obj, data_only=True)
            ws = wb.active
        except Exception as e:
            raise ValueError(msg.INVALID_EXCEL_FILE.format(str(e)))

        # 1. Header Parsing
        header_data = {}
        for item in config['basic_headers']:
            # 슬라이싱을 사용하여 앞의 3개 요소만 언패킹 (좌표, 라벨, 키)
            # 너비(4번째 요소)는 파싱할 때 필요 없음
            h_loc, _, key = item[:3]

            col = openpyxl.utils.coordinate_to_tuple(h_loc)[1]
            header_row_idx = openpyxl.utils.coordinate_to_tuple(h_loc)[0]

            # 값은 헤더 바로 아랫줄(row + 1)에 있다고 가정
            val_cell = ws.cell(row=header_row_idx + 1, column=col)
            header_data[key] = self._get_safe_value(val_cell)

        # 2. Grid Parsing
        rows = []
        start_row = config.get('start_row_data', 7)

        for row_idx in range(start_row, start_row + 100):
            # Key Column (2번째 컬럼, Port Code) 체크
            check_val = ws.cell(row=row_idx, column=2).value

            # 종료 조건
            if not check_val or str(check_val).strip() == '' or str(check_val) == 'Summary':
                break

            row_data = {}
            for _, key, col_idx in config['grid_headers']:
                val = ws.cell(row=row_idx, column=col_idx).value

                if 'time' in key:
                    val = self._parse_time(val)
                else:
                    val = val if val is not None else ''

                row_data[key] = val
            rows.append(row_data)

        return header_data, rows

    # --- Internal Helpers ---
    def _write_section_title(self, ws, loc, text):
        cell = ws[loc]
        cell.value = text
        cell.font = Font(bold=True, size=12)

    def _write_merged_header_value(self, ws, h_loc, text, value='', width=3):
        # Header Cell
        cell = ws[h_loc]

        # Header Cell 쓰기
        cell.value = text
        self._apply_header_style(cell)

        # [핵심] 병합 범위 계산: 현재 컬럼 + width - 1
        end_col_idx = cell.column + width - 1

        ws.merge_cells(start_row=cell.row, start_column=cell.column,
                       end_row=cell.row, end_column=end_col_idx)

        # Value Cell (Row + 1) 쓰기
        v_row = cell.row + 1
        v_cell = ws.cell(row=v_row, column=cell.column)
        v_cell.value = value
        self._apply_body_style(v_cell)

        ws.merge_cells(start_row=v_row, start_column=v_cell.column,
                       end_row=v_row, end_column=end_col_idx)

    def _write_summary(self, ws, row_idx, start, end, sum_cols, total_cols):
        label = ws.cell(row=row_idx, column=2, value="Summary")
        self._apply_summary_style(label)

        for col_idx, col_letter in sum_cols.items():
            formula = f"=SUM({col_letter}{start}:{col_letter}{end})"
            cell = ws.cell(row=row_idx, column=col_idx, value=formula)
            self._apply_summary_style(cell)

        # Speed Formula (Proforma Specific: Dist / SeaTime)
        dist_col = sum_cols.get(14)
        sea_col = sum_cols.get(17)
        if dist_col and sea_col:
            # Speed Column is 16
            speed_cell = ws.cell(row=row_idx, column=16,
                                 value=f"=IF({sea_col}{row_idx}>0, {dist_col}{row_idx}/{sea_col}{row_idx}, 0)")
            self._apply_summary_style(speed_cell)

        for c in range(1, total_cols + 1):
            if not ws.cell(row=row_idx, column=c).value:
                self._apply_summary_style(ws.cell(row=row_idx, column=c))

    def _adjust_widths(self, ws, col_widths):
        if not col_widths: return
        for i, width in enumerate(col_widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = width

    def _apply_header_style(self, cell):
        cell.font = self.bold_font
        cell.alignment = self.center_align
        cell.border = self.thin_border
        cell.fill = self.header_fill

    def _apply_body_style(self, cell):
        cell.alignment = self.center_align
        cell.border = self.thin_border

    def _apply_summary_style(self, cell):
        cell.font = self.bold_font
        cell.alignment = self.center_align
        cell.border = self.thin_border
        cell.fill = self.summary_fill

    def _get_safe_value(self, cell):
        return cell.value if cell.value is not None else ''

    def _parse_time(self, val):
        if val is None: return '0000'
        if hasattr(val, 'strftime'): return val.strftime('%H%M')
        s = str(val).replace(':', '').replace('.', '').strip()
        return s.zfill(4)[:4] if s.isdigit() else '0000'