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
        self.center_align = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )
        self.thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )
        self.header_fill = PatternFill(
            start_color="E2E3E5", end_color="E2E3E5", fill_type="solid"
        )
        self.summary_fill = PatternFill(
            start_color="FFF2CC", end_color="FFF2CC", fill_type="solid"
        )

    def create_template(self, config, header_data=None, rows_data=None):
        """
        엑셀 생성 (템플릿 or 데이터 익스포트)
        :param header_data: (Optional) Basic Info에 채울 실제 데이터
        :param rows_data: (Optional) Grid에 채울 실제 데이터 리스트
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = config.get("sheet_title", "Sheet1")

        # -------------------------------------------------------
        # 1. Basic Info 작성
        # -------------------------------------------------------
        self._write_section_title(ws, "A1", "Basic Information")

        # 데이터 소스 결정 (파라미터 > Config 예시 > 빈 값)
        basic_source = header_data if header_data else config.get("basic_examples", {})

        for item in config["basic_headers"]:
            # 튜플 언패킹 (4개 or 3개)
            if len(item) == 4:
                h_loc, text, key, width = item
            else:
                h_loc, text, key = item
                width = 3

            # 값 가져오기
            val = basic_source.get(key, "")
            self._write_merged_header_value(ws, h_loc, text, val, width)

        # -------------------------------------------------------
        # 2. Grid Headers 작성
        # -------------------------------------------------------
        grid_start_row = config.get("start_row_grid", 6)
        self._write_section_title(ws, f"A{grid_start_row - 1}", "Port Schedule")

        for idx, (text, _, _) in enumerate(config["grid_headers"], start=1):
            cell = ws.cell(row=grid_start_row, column=idx, value=text)
            self._apply_header_style(cell)

        # -------------------------------------------------------
        # 3. Grid Data (Rows) 작성
        # -------------------------------------------------------
        data_start_row = config.get("start_row_data", 7)

        # 실제 데이터가 있으면 그것을 사용, 없으면 빈 행(10줄) 생성
        target_rows = rows_data if rows_data else range(10)

        # Grid 예시 데이터 (rows_data가 없을 때 첫 줄에만 사용)
        grid_examples = config.get("grid_examples", {}) if not rows_data else {}

        for i, row_item in enumerate(target_rows):
            curr_row = data_start_row + i

            # No. 컬럼 (A열) - 데이터가 있어도 순번은 i+1로 재부여하거나 데이터의 no 사용
            # 여기서는 편의상 자동 증가값 사용
            cell_no = ws.cell(row=curr_row, column=1, value=i + 1)
            self._apply_body_style(cell_no)

            # 나머지 컬럼 채우기
            for idx, (_, key, col_idx) in enumerate(config["grid_headers"]):
                if col_idx == 1:
                    continue  # No 컬럼 스킵

                cell = ws.cell(row=curr_row, column=col_idx)

                # 값 결정 로직
                val = ""
                if rows_data:
                    # Case A: 실제 데이터 Export
                    # 딕셔너리에서 키로 값 조회 (없으면 '')
                    raw_val = row_item.get(key, "")

                    # 시간 포맷 등 필요한 변환이 있다면 여기서 처리 가능
                    # (현재는 raw_val 그대로 씀)
                    val = raw_val

                elif i == 0 and grid_examples:
                    # Case B: 템플릿의 첫 줄 예시
                    val = grid_examples.get(key, "")

                cell.value = val
                self._apply_body_style(cell)

        # -------------------------------------------------------
        # 4. Summary Row & Styles
        # -------------------------------------------------------
        row_count = len(target_rows)
        end_row = data_start_row + row_count - 1

        if "summary_cols" in config and row_count > 0:
            self._write_summary(
                ws,
                end_row + 1,
                data_start_row,
                end_row,
                config["summary_cols"],
                len(config["grid_headers"]),
            )

        col_widths = config.get("col_widths", [])
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
        for item in config["basic_headers"]:
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
        start_row = config.get("start_row_data", 7)

        for row_idx in range(start_row, start_row + 100):
            # Key Column (2번째 컬럼, Port Code) 체크
            check_val = ws.cell(row=row_idx, column=2).value

            # 종료 조건
            if (
                not check_val
                or str(check_val).strip() == ""
                or str(check_val) == "Summary"
            ):
                break

            row_data = {}
            for _, key, col_idx in config["grid_headers"]:
                val = ws.cell(row=row_idx, column=col_idx).value

                if "time" in key:
                    val = self._parse_time(val)
                else:
                    val = val if val is not None else ""

                row_data[key] = val
            rows.append(row_data)

        return header_data, rows

    # --- Internal Helpers ---
    def _write_section_title(self, ws, loc, text):
        cell = ws[loc]
        cell.value = text
        cell.font = Font(bold=True, size=12)

    def _write_merged_header_value(self, ws, h_loc, text, value="", width=3):
        # Header Cell
        cell = ws[h_loc]

        # Header Cell 쓰기
        cell.value = text
        self._apply_header_style(cell)

        # [핵심] 병합 범위 계산: 현재 컬럼 + width - 1
        end_col_idx = cell.column + width - 1

        ws.merge_cells(
            start_row=cell.row,
            start_column=cell.column,
            end_row=cell.row,
            end_column=end_col_idx,
        )

        # Value Cell (Row + 1) 쓰기
        v_row = cell.row + 1
        v_cell = ws.cell(row=v_row, column=cell.column)
        v_cell.value = value
        self._apply_body_style(v_cell)

        ws.merge_cells(
            start_row=v_row,
            start_column=v_cell.column,
            end_row=v_row,
            end_column=end_col_idx,
        )

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
            speed_cell = ws.cell(
                row=row_idx,
                column=16,
                value=f"=IF({sea_col}{row_idx}>0, {dist_col}{row_idx}/{sea_col}{row_idx}, 0)",
            )
            self._apply_summary_style(speed_cell)

        for c in range(1, total_cols + 1):
            if not ws.cell(row=row_idx, column=c).value:
                self._apply_summary_style(ws.cell(row=row_idx, column=c))

    def _adjust_widths(self, ws, col_widths):
        if not col_widths:
            return
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
        return cell.value if cell.value is not None else ""

    def _parse_time(self, val):
        if val is None:
            return "0000"
        if hasattr(val, "strftime"):
            return val.strftime("%H%M")
        s = str(val).replace(":", "").replace(".", "").strip()
        return s.zfill(4)[:4] if s.isdigit() else "0000"
