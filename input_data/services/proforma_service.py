import csv
import io
import math
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from common import (
    constants as const,
    csv_configs as csv_cfg,
    excel_configs as ex_cfg,
    messages as msg,
)
from common.utils import safe_float, safe_int, safe_round, safe_sum
from common.utils.csv_manager import CsvManager
from common.utils.excel_manager import ExcelManager
from input_data.models import ProformaSchedule, ProformaScheduleDetail, ScenarioInfo
from input_data.services.common_service import get_distance_between_ports


class ProformaService:
    """
    Proforma Schedule 관련 비즈니스 로직 처리 클래스
    Time Line 계산 방식: 첫 번째 포트 ETB를 기준으로 누적 시간(Elapsed Time) 관리
    """

    def __init__(self):
        # 인스턴스 초기화
        self.excel_manager = ExcelManager()
        self.csv_manager = CsvManager()

    def parse_header(self, request):
        """
        [Config 기반 동적 파싱]
        Basic Information 영역의 데이터를 HTML name(Key)을 기준으로 추출
        항목이 변경되어도 Config만 수정
        """
        header_data = {}
        for item in ex_cfg.PROFORMA_CONFIG["basic_headers"]:
            key = item[2]
            header_data[key] = request.POST.get(key)
        return header_data

    def parse_rows(self, request):
        """역시 Config를 기반으로 Grid 동적 파싱 가능
        HTML name은 보통 name="key[]" 형태이므로 Config 키에 '[]'를 붙여서 가져옴"""
        grid_data = {}
        row_count = 0

        # 1. 컬럼별 리스트 추출
        for _, key, _ in ex_cfg.PROFORMA_CONFIG["grid_headers"]:
            values = request.POST.getlist(f"{key}[]")
            grid_data[key] = values
            if values:
                row_count = len(values)

        # 2. Row 단위로 변환
        rows = []
        for i in range(row_count):
            row = {}
            for _, key, _ in ex_cfg.PROFORMA_CONFIG["grid_headers"]:
                # 리스트 범위 체크
                val = grid_data[key][i] if i < len(grid_data[key]) else ""

                # 숫자형 필드 안전 변환 (필요시)
                if key in ["pilot_in", "work_hours", "pilot_out"]:
                    # Pilot In, Work Hours, Pilot Out은 소수점 한자리로 제한
                    row[key] = safe_round(val, 1)
                elif key in [
                    "dist",
                    "eca_dist",
                    "spd",
                    "sea_time",
                ]:
                    row[key] = safe_float(val)
                elif key in ["port_seq", "etb_no", "etd_no"]:
                    row[key] = safe_int(val)
                else:
                    row[key] = val
            rows.append(row)

        return rows

    def calculate_schedule(self, rows, header_info):
        """
        [스케줄 계산 핵심 로직]
        1. 기준점 설정: 첫 번째 행의 ETB Day/Time
        2. Distance 조회: Current Port -> Next Port 거리 검색
        3. ETB 계산: 사용자 입력 'etb_no'가 존재하고 유효(이전 ETD 이후)하면 우선 사용.
           그렇지 않을 경우(시간 역전 등)에만 자동 보정 로직 수행.
        4. Sea Time 역산 (Back-calculation):
           - Formula: (Next ETB - Current ETD) - (Current Pilot Out + Next Pilot In)
        5. Speed 계산:
           - Formula: Distance / Sea Time
        6. ETD 계산:
           - Formula: Current ETB + Work Hours
        """
        if not rows:
            return rows

        # [1] 기준점(Anchor) 설정 (Row 0)
        start_day_str = rows[0].get("etb_day", "SUN")
        start_time_str = rows[0].get("etb_time", "0000")
        base_abs_hours = self._get_abs_hours_from_day_time(
            start_day_str, start_time_str
        )

        # 현재 행의 ETB 절대 시간 (누적값)
        # (Row 0은 기준점이므로 바로 설정)
        current_etb_abs = base_abs_hours

        # [2] 순차 계산 루프
        for i in range(len(rows)):
            curr = rows[i]

            # ----------------------------------------------------------------
            # Step A. Distance & ECA Distance 자동 검색 (Current -> Next)
            # ----------------------------------------------------------------
            if i < len(rows) - 1:
                next_row = rows[i + 1]
                # 포트 코드가 변경되었거나 거리가 0일 때 재검색
                # (항상 검색하여 최신화하려면 조건 제거)
                if curr.get("port_code") and next_row.get("port_code"):
                    dist, eca_dist = get_distance_between_ports(
                        origin=curr.get("port_code"),
                        destination=next_row.get("port_code"),
                    )

                    curr["dist"] = dist
                    curr["eca_dist"] = eca_dist

            # ----------------------------------------------------------------
            # Step B. ETB 확정 (사용자 입력 No 우선 적용)
            # ----------------------------------------------------------------
            if i == 0:
                # 첫 행은 기준점이므로 변경 없음
                current_etb_abs = base_abs_hours
            else:
                # 사용자가 입력한 ETB Day/Time을 해석하여 절대 시간 결정
                prev_row = rows[i - 1]

                # 이전 항구의 ETD 절대 시간 가져오기
                prev_etd_abs = self._get_abs_hours_from_row(
                    prev_row, "etd", base_abs_hours
                )

                # 사용자 입력값 가져오기
                user_no = int(curr.get("etb_no") or 0)
                user_time = curr.get("etb_time", const.DEFAULT_TIME)

                # 1. 사용자가 입력한 etb_no 기반으로 절대 시간 계산
                candidate_etb_abs = self._get_abs_hours_with_no(
                    base_abs_hours, user_no, user_time
                )

                # 2. 유효성 검증
                # 사용자가 입력한 시간(Day 10)이 이전 ETD(Day 2)보다 미래라면 그대로 사용
                # 만약 사용자가 실수로 과거(Day 1)를 입력했다면, 그때만 자동 로직(Resolve Next) 수행
                if candidate_etb_abs >= prev_etd_abs:
                    current_etb_abs = candidate_etb_abs
                else:
                    # 입력값이 논리적으로 불가능(과거)할 때 -> 요일 기반 자동 찾기 or Prev ETD로 보정
                    # 여기서는 요일 기반으로 '가장 가까운 미래'를 찾아줌 (기존 로직 활용)
                    user_day = curr.get("etb_day", const.DEFAULT_ETB_DAY)
                    current_etb_abs = self._resolve_next_etb(
                        prev_etd_abs, user_day, user_time
                    )

                    # 그래도 혹시 모르니 Min 값 보정
                    if current_etb_abs < prev_etd_abs:
                        current_etb_abs = prev_etd_abs

                # ------------------------------------------------------------
                # Step C. Sea Time & Speed 역산 (Previous Row Update)
                # ------------------------------------------------------------
                # Sea Time = (Berth to Berth) - (Prev Pilot Out) - (Curr Pilot In)
                prev_pilot_out = safe_float(prev_row.get("pilot_out", 0))
                curr_pilot_in = safe_float(curr.get("pilot_in", 0))

                calc_sea_time = (
                    current_etb_abs - prev_etd_abs - prev_pilot_out - curr_pilot_in
                )

                # 방어 코드: 시간이 역전된 경우 (즉, 사용자가 ETB를 ETD보다 과거로 입력함)
                if calc_sea_time < 0:
                    calc_sea_time = 0
                    # 시간을 강제로 밀어버릴지, Sea Time을 0으로 두고 ETB를 수정할지 결정해야 함.
                    # 여기서는 "사용자 ETB 우선"이지만 물리적으로 불가능하면 Sea Time=0으로 둠.

                # 이전 행(Leg)의 Sea Time 업데이트
                prev_row["sea_time"] = round(calc_sea_time, 2)

                # 이전 행(Leg)의 Speed 업데이트 (Speed = Dist / Time)
                dist = safe_float(prev_row.get("dist", 0))
                if calc_sea_time > 0.01:
                    prev_row["spd"] = round(dist / calc_sea_time, 2)
                else:
                    prev_row["spd"] = 0.0

            # ----------------------------------------------------------------
            # Step D. 현재 행의 ETB 값(No, Day, Time) 갱신
            # ----------------------------------------------------------------
            # 계산된 절대 시간을 다시 No, Day, Time으로 변환하여 화면에 표시
            no, day, time = self._hours_to_display_format(
                current_etb_abs, base_abs_hours
            )
            curr["etb_no"] = no
            curr["etb_day"] = day
            curr["etb_time"] = time

            # ----------------------------------------------------------------
            # Step E. 현재 행의 ETD 계산 (ETB + Work Hours)
            # ----------------------------------------------------------------
            work_hours = safe_float(curr.get("work_hours", 0))
            current_etd_abs = current_etb_abs + work_hours

            no, day, time = self._hours_to_display_format(
                current_etd_abs, base_abs_hours
            )
            curr["etd_no"] = no
            curr["etd_day"] = day
            curr["etd_time"] = time
            curr["port_seq"] = i + 1
        return rows

    def add_row(self, rows, scenario_id):
        """
        최하단 행 추가
        - 이전 행이 있다면: Previous ETD + 24h(Sea Time) = New ETB
        """
        new_row = self._create_default_row()

        if rows:
            # 기준점(Row 0) 절대 시간 계산 (No 계산을 위해 필요)
            start_day = rows[0].get("etb_day", "SUN")
            start_time = rows[0].get("etb_time", "0000")
            base_abs_hours = self._get_abs_hours_from_day_time(start_day, start_time)

            # 마지막 행(직전 행) 기준으로 새 행 시간 계산
            last_row = rows[-1]
            self._calculate_new_row_times(new_row, last_row, base_abs_hours)
        else:
            # 첫 번째 행인 경우 기본값 유지 (SUN 00:00)
            pass

        rows.append(new_row)

        # 전체 재계산 (거리 등 동기화)
        return self.calculate_schedule(rows, {"scenario_id": scenario_id})

    def insert_row(self, rows, index):
        """
        중간 삽입
        - 선택된 행(index)의 바로 뒤에 삽입
        - Selected ETD + 24h = New ETB
        """
        new_row = self._create_default_row()

        if rows and 0 <= index < len(rows):
            # 기준점(Row 0) 절대 시간 계산
            start_day = rows[0].get("etb_day", "SUN")
            start_time = rows[0].get("etb_time", "0000")
            base_abs_hours = self._get_abs_hours_from_day_time(start_day, start_time)

            # 선택된 행(prev_row) 기준으로 새 행 시간 계산
            prev_row = rows[index]
            self._calculate_new_row_times(new_row, prev_row, base_abs_hours)

            # 삽입
            rows.insert(index + 1, new_row)
        else:
            # 인덱스 오류 시 맨 뒤 추가
            return self.add_row(rows, None)

        return self.calculate_schedule(rows, {"scenario_id": None})

    def delete_rows(self, rows, indices):
        """행 삭제"""
        if not indices:
            return rows
        indices = sorted([int(x) for x in indices], reverse=True)
        for i in indices:
            if 0 <= i < len(rows):
                del rows[i]
        return self.calculate_schedule(rows, {"scenario_id": None})

    @transaction.atomic
    def save_schedule(self, header, rows, user):
        """스케줄 DB 저장 (Master - Detail 분리)"""
        scenario_id_val = header.get("scenario_id")
        lane_code = header.get("lane_code")
        proforma_name = header.get("proforma_name")

        try:
            scenario_obj = ScenarioInfo.objects.get(id=scenario_id_val)
        except ScenarioInfo.DoesNotExist as e:
            raise ValueError(msg.ITEM_NOT_FOUND.format(item=proforma_name)) from e

        # Effective Date를 Timezone Aware 객체로 변환
        eff_from_date_str = header.get("effective_from_date", "")
        effective_from_date = timezone.now()

        if eff_from_date_str:
            try:
                dt = datetime.strptime(str(eff_from_date_str)[:10], "%Y-%m-%d")
                effective_from_date = timezone.make_aware(dt)
            except ValueError:
                pass

        # 1. 기존 데이터 삭제 (Master 삭제 시 ON_DELETE=CASCADE로 Detail도 자동 삭제됨)
        ProformaSchedule.objects.filter(
            scenario=scenario_obj, lane_id=lane_code, proforma_name=proforma_name
        ).delete()

        # 2. Master(헤더) 신규 생성
        master = ProformaSchedule.objects.create(
            scenario=scenario_obj,
            lane_id=lane_code,
            proforma_name=proforma_name,
            effective_from_date=effective_from_date,
            duration=Decimal(header.get("duration") or 0),
            declared_capacity=header.get("capacity", ""),
            declared_count=int(header.get("count") or 0),
            created_by=user,
            updated_by=user,
        )

        # 3. Detail(기항지) 신규 생성
        new_details = []
        indicator_map = {}

        for row in rows:
            if not row.get("port_code"):
                continue

            port_cd = row["port_code"]
            direction = row.get("direction", "E")

            key = (port_cd, direction)
            current_count = indicator_map.get(key, 0) + 1
            indicator_map[key] = current_count

            calling_port_indicator = str(current_count)
            raw_terminal = row.get("terminal", "")
            terminal_code = raw_terminal if raw_terminal else f"{port_cd}01"

            detail = ProformaScheduleDetail(
                proforma=master,  # [핵심] 생성된 Master 객체를 FK로 연결
                direction=direction,
                port_id=port_cd,
                calling_port_indicator=calling_port_indicator,
                calling_port_seq=int(row.get("port_seq") or 0),
                turn_port_info_code=row.get("turn_port_info_code", "N"),
                pilot_in_hours=Decimal(row.get("pilot_in") or 0),
                etb_day_number=int(row.get("etb_no") or 0),
                etb_day_code=row.get("etb_day", ""),
                etb_day_time=row.get("etb_time", ""),
                actual_work_hours=Decimal(row.get("work_hours") or 0),
                etd_day_number=int(row.get("etd_no") or 0),
                etd_day_code=row.get("etd_day", ""),
                etd_day_time=row.get("etd_time", ""),
                pilot_out_hours=Decimal(row.get("pilot_out") or 0),
                link_distance=int(float(row.get("dist") or 0)),
                link_eca_distance=int(float(row.get("eca_dist") or 0)),
                link_speed=Decimal(row.get("spd") or 0),
                sea_time_hours=Decimal(row.get("sea_time") or 0),
                terminal_code=terminal_code,
                created_by=user,
                updated_by=user,
            )
            new_details.append(detail)

        # Detail 일괄 저장
        if new_details:
            ProformaScheduleDetail.objects.bulk_create(new_details)

    def calculate_summary(self, rows):
        """
        [신규] 화면 표시용 Summary 데이터 계산
        """
        if not rows:
            return {}

        # safe_sum을 사용하여 안전하게 합계 계산
        total_pilot_in = safe_sum(row.get("pilot_in") for row in rows)
        total_work_hours = safe_sum(row.get("work_hours") for row in rows)
        total_pilot_out = safe_sum(row.get("pilot_out") for row in rows)
        total_dist = safe_sum(row.get("dist") for row in rows)
        total_sea_time = safe_sum(row.get("sea_time") for row in rows)

        # 평균 속도 = 총 거리 / 총 항해 시간
        avg_speed = 0
        if total_sea_time > 0:
            avg_speed = round(total_dist / total_sea_time, 2)

        return {
            "pilot_in": safe_round(total_pilot_in, 1),
            "work_hours": safe_round(total_work_hours, 1),
            "pilot_out": safe_round(total_pilot_out, 1),
            "dist": total_dist,
            "sea_time": total_sea_time,
            "spd": avg_speed,
        }

    def upload_excel(self, file_obj):
        """엑셀 업로드 및 날짜 포맷팅"""
        # 1. ExcelManager를 통해 파싱 (Config 사용)
        header, rows = self.excel_manager.parse_excel(file_obj, ex_cfg.PROFORMA_CONFIG)

        # 2. 날짜 필드 후처리 (Excel datetime -> HTML input date string)
        # Config에 'effective_from_date' 키가 있는지 확인하고 처리
        if "effective_from_date" in header:
            header["effective_from_date"] = self._format_date_for_input(
                header["effective_from_date"]
            )

        # 3. 데이터 후처리 (Default Value)
        for row in rows:
            if not row.get("direction"):
                row["direction"] = const.DEFAULT_DIRECTION
            if not row.get("turn_port_info_code"):
                row["turn_port_info_code"] = const.DEFAULT_TURN_INO

            # 소수점 첫째자리로 제한되는 필드들
            for key in ["pilot_in", "work_hours", "pilot_out"]:
                row[key] = safe_round(row.get(key), 1)

            # 일반 float 변환 필드들
            for key in ["dist", "eca_dist", "spd", "sea_time"]:
                row[key] = safe_float(row.get(key))

            # int 변환
            for key in ["port_seq", "etb_no", "etd_no"]:
                row[key] = safe_int(row.get(key))

        # 4. 계산
        # calc_header = {"scenario_id": header.get("scenario_id")}
        # calculated_rows = self.calculate_schedule(rows, calc_header)

        return header, rows

    def generate_template(self):
        """
        Proforma 템플릿 엑셀 생성 (ExcelManager 위임)
        """
        # Config만 넘기면 됨
        return self.excel_manager.create_template(ex_cfg.PROFORMA_CONFIG)

    def export_proforma(self, header, rows):
        """
        [신규] 화면의 데이터를 엑셀로 Export
        """
        # 1. ExcelManager에 데이터 주입
        # header와 rows는 이미 parse_header/parse_rows를 통해 딕셔너리 리스트 형태임
        output = self.excel_manager.create_template(
            config=ex_cfg.PROFORMA_CONFIG, header_data=header, rows_data=rows
        )
        return output

    def export_grid_csv(self, rows):
        """
        [신규] Grid 데이터만 CSV로 다운로드
        Basic Info는 제외하고 테이블 형태 데이터만 출력
        """
        # 공통 CsvManager 사용
        # Config의 grid_headers 정보만 넘겨주면 됨
        return self.csv_manager.create_csv(
            data_rows=rows, headers_config=ex_cfg.PROFORMA_CONFIG["grid_headers"]
        )

    def generate_db_csv(self, header, rows):
        """
        [리팩토링] csv_configs를 활용한 DB CSV 생성
        """
        output = io.StringIO()
        output.write("\ufeff")
        writer = csv.writer(output)

        # 1. Config에서 헤더 추출 및 작성
        # csv_cfg.PROFORMA_DB_MAP = [('Header', 'key'), ...]
        headers = [item[0] for item in csv_cfg.PROFORMA_DB_MAP]
        writer.writerow(headers)

        if not rows:
            return output.getvalue()

        # (2) STD_SVCE_SPD
        total_dist = safe_sum(r.get("dist", 0) for r in rows)
        total_sea_time = safe_sum(r.get("sea_time", 0) for r in rows)
        std_speed = round(total_dist / total_sea_time, 2) if total_sea_time > 0 else 0

        # (3) Counter
        port_call_counter = {}

        # ---------------------------------------------------------
        # 3. Row Iteration
        # ---------------------------------------------------------
        for i, row in enumerate(rows):
            if not row.get("port_code"):
                continue

            # --- Row Logic ---
            # CLG_PORT_INDC_SEQ
            dir_cd = row.get("direction", "")
            port_cd = row.get("port_code", "")
            call_key = (dir_cd, port_cd)
            port_call_counter[call_key] = port_call_counter.get(call_key, 0) + 1

            # TURN_PORT_SYS_CD
            turn_par = row.get("turn_port_info_code", "N")
            if i == len(rows) - 1:
                turn_sys = "F"
            elif turn_par == "Y":
                turn_sys = "Y"
            else:
                turn_sys = "N"

            # ---------------------------------------------------------
            # 4. Context 통합 (Header + Row + Calculated)
            # ---------------------------------------------------------
            # 하나의 딕셔너리에 모든 정보를 모읍니다.
            row_context = {}

            # 1) Basic Header 정보 (lane_code, duration 등)
            row_context.update(header)

            # 2) Grid Row 정보 (port_code, dist 등)
            row_context.update(row)

            # 3) Calculated 정보 (계산된 로직 결과)
            row_context.update(
                {
                    # 'is_standard': is_standard,
                    "std_speed": std_speed,
                    "clg_seq": port_call_counter[call_key],
                    "turn_sys": turn_sys,
                }
            )

            # ---------------------------------------------------------
            # 5. Config 기반 매핑 및 쓰기
            # ---------------------------------------------------------
            # Config에 정의된 순서대로 row_context에서 값을 꺼냅니다.
            row_values = []
            for _, key in csv_cfg.PROFORMA_DB_MAP:
                val = row_context.get(key, "")
                if val is None:
                    val = ""
                row_values.append(str(val))

            writer.writerow(row_values)

        return output.getvalue()

    def get_schedule_data(self, scenario_id, lane_code, proforma_name):
        """
        [DB -> View] DB -> View: Master/Detail 조회하여 화면용 Header/Rows 반환
        """
        # 1. Master 조회
        master = (
            ProformaSchedule.objects.select_related("scenario")
            .filter(
                scenario_id=scenario_id,
                lane_id=lane_code,
                proforma_name=proforma_name,
            )
            .first()
        )

        if not master:
            return {}, []

        # 2. Header 구성
        header = {
            "scenario_id": master.scenario_id,
            "scenario_code": master.scenario.code,  # 시나리오 코드 추가
            "lane_code": master.lane_id,
            "proforma_name": master.proforma_name,
            "effective_from_date": (
                master.effective_from_date.strftime("%Y-%m-%d")
                if master.effective_from_date
                else ""
            ),
            "duration": master.duration,
            "capacity": master.declared_capacity,
            "count": master.declared_count,
        }

        # 3. Detail 기반 Rows 구성 (related_name 'details' 활용)
        rows = []
        details_qs = master.details.all().order_by("calling_port_seq")
        for obj in details_qs:
            row = {
                "port_seq": obj.calling_port_seq,
                "port_code": obj.port_id or "",
                "direction": obj.direction or const.DEFAULT_DIRECTION,
                "turn_port_info_code": obj.turn_port_info_code
                or const.DEFAULT_TURN_INO,
                "pilot_in": safe_round(obj.pilot_in_hours, 1),  # null 안전 처리
                "etb_no": safe_int(obj.etb_day_number),
                "etb_day": obj.etb_day_code or const.DEFAULT_ETB_DAY,
                "etb_time": obj.etb_day_time or const.DEFAULT_TIME,
                "work_hours": safe_round(obj.actual_work_hours, 1),  # null 안전 처리
                "etd_no": safe_int(obj.etd_day_number),
                "etd_day": obj.etd_day_code or const.DEFAULT_ETD_DAY,
                "etd_time": obj.etd_day_time or const.DEFAULT_TIME,
                "pilot_out": safe_round(obj.pilot_out_hours, 1),  # null 안전 처리
                "dist": safe_float(obj.link_distance),
                "eca_dist": safe_float(obj.link_eca_distance),
                "spd": safe_float(obj.link_speed),
                "sea_time": safe_float(obj.sea_time_hours),
                "terminal": obj.terminal_code or "",
            }
            rows.append(row)

        return header, rows

    # --- Helper Methods ---
    def _create_default_row(self):
        return {
            "port_seq": 0,
            "port_code": "",
            "direction": const.DEFAULT_DIRECTION,
            "turn_port_info_code": const.DEFAULT_TURN_INO,
            "pilot_in": const.DEFAULT_PILOT_IN,
            "etb_no": 0,
            "etb_day": const.DEFAULT_ETB_DAY,
            "etb_time": const.DEFAULT_TIME,
            "work_hours": const.DEFAULT_WORK_HOURS,
            "etd_no": 0,
            "etd_day": const.DEFAULT_ETD_DAY,
            "etd_time": const.DEFAULT_TIME,
            "pilot_out": const.DEFAULT_PILOT_OUT,
            "dist": 0,
            "eca_dist": 0,
            "spd": 0,
            "sea_time": 0,
            "terminal": "",
        }

    def _get_abs_hours_from_day_time(self, day_str, time_str):
        """
        요일 + 시간을 -> 절대적인 시간(Hours)으로 변환
        여기서 구해진 값은 '타임라인상의 좌표' 역할만 하며,
        No 계산을 위한 기준점(Base)이 됨.
        """
        if day_str in const.DAYS:
            day_idx = const.DAYS.index(day_str)
        else:
            day_idx = 0  # Default SUN

        t_str = str(time_str).zfill(4)
        if not t_str.isdigit():
            t_str = "0000"
        h = int(t_str[:2])
        m = int(t_str[2:])

        # ex) TUE 12:00 -> 2*24 + 12 + 0 = 60.0
        return (day_idx * 24) + h + (m / 60.0)

    def _get_abs_hours_from_row(self, row, prefix, base_hours):
        """Row에 저장된 No/Day/Time 정보를 바탕으로 절대 시간 복원"""
        # 저장된 No는 base_hours 대비 경과 일수
        no = int(float(row.get(f"{prefix}_no") or 0))

        # 저장된 Time
        t_str = str(row.get(f"{prefix}_time", "0000")).zfill(4)
        h = int(t_str[:2])
        m = int(t_str[2:])
        time_part = h + (m / 60.0)

        # 절대 시간 = (Base의 시작일 00:00) + (No * 24) + Time
        # 주의: base_hours 자체는 (BaseDay * 24 + BaseTime)임.
        # No는 "Base 도착 이후 며칠 지났는가"를 의미함.

        # 여기서 중요한 점: No/Day/Time은 화면 표시용이라서 정확한 절대 시간을 담지 못할 수 있음 (특히 주차 변경 시)
        # 따라서 _hours_to_display_format의 역연산이 필요함.

        # Base Hours에서 '일(Day)' 단위만 추출
        base_days_part = math.floor(base_hours / 24.0)

        # 전체 절대 일수 = Base 일수 + 경과 일수(No)
        total_days = base_days_part + no

        return (total_days * 24.0) + time_part

    def _resolve_next_etb(self, prev_etd_abs, user_day, user_time):
        """
        이전 ETD(절대시간) 이후, 사용자가 입력한 요일/시간이
        가장 빨리 도래하는 절대 시간을 계산
        """
        # 사용자 입력 시간을 0주차 절대 시간으로 변환 (예: TUE 12:00 -> 36.0)
        input_base_abs = self._get_abs_hours_from_day_time(user_day, user_time)

        # 이전 ETD가 몇 주차인지 대략 계산
        # prev_etd_abs가 200시간이라면 (약 1주+@)

        # 1주일(168시간) 단위로 더해가며 prev_etd_abs보다 큰 최소값 찾기
        # (단, user input이 prev_etd보다 과거라면 다음 주차로 넘김)

        # 대략적인 시작 주차 계산
        weeks = math.floor(prev_etd_abs / 168.0)
        candidate = input_base_abs + (weeks * 168.0)

        # 만약 후보가 이전 ETD보다 작으면 1주 더함
        if candidate < prev_etd_abs:
            candidate += 168.0

        # [예외 처리] 만약 차이가 너무 크거나(예: 한 바퀴 돌아옴) 논리적으로 맞지 않으면
        # 사용자가 "바로 다음 요일"을 의도했다고 보고 조정
        # 하지만 기본적으로는 "가장 가까운 미래의 해당 요일"로 처리

        return candidate

    def _hours_to_display_format(self, total_hours, base_hours):
        # 1. Day & Time
        total_days_abs = math.floor(total_hours / 24.0)
        day_idx = total_days_abs % 7
        day_str = const.DAYS[day_idx]

        rem_hours = total_hours % 24
        h = math.floor(rem_hours)
        m = round((rem_hours - h) * 60)
        time_str = f"{h:02d}{m:02d}"

        # 2. No (Elapsed Days from Base)
        base_days_part = math.floor(base_hours / 24.0)
        no = total_days_abs - base_days_part

        if no < 0 and no > -0.01:
            no = 0

        return no, day_str, time_str

    def _calculate_new_row_times(self, new_row, prev_row, base_abs_hours):
        """
        이전 행의 ETD를 기준으로 새 행의 ETB/ETD를 자동 설정
        - New ETB = Prev ETD + 24h (Sea Time)
        - New ETD = New ETB + 24h (Work Hours)
        """
        # 1. 이전 행의 ETD 절대 시간 복원
        prev_etd_abs = self._get_abs_hours_from_row(prev_row, "etd", base_abs_hours)

        # 2. 새 행 ETB 계산
        new_etb_abs = (
            prev_etd_abs
            + const.DEFAULT_SEA_TIME
            + const.DEFAULT_PILOT_IN
            + const.DEFAULT_PILOT_OUT
        )

        # 3. 새 행 ETD 계산
        new_etd_abs = new_etb_abs + const.DEFAULT_WORK_HOURS

        # 4. 값 포맷팅 및 주입
        no, day, time = self._hours_to_display_format(new_etb_abs, base_abs_hours)
        new_row["etb_no"] = no
        new_row["etb_day"] = day
        new_row["etb_time"] = time

        no, day, time = self._hours_to_display_format(new_etd_abs, base_abs_hours)
        new_row["etd_no"] = no
        new_row["etd_day"] = day
        new_row["etd_time"] = time

        # 5. 기본 Sea Time 표시
        # (calculate_schedule에서 역산될 수도 있지만 초기값으로 넣어둠)
        prev_row["sea_time"] = const.DEFAULT_SEA_TIME

    def _format_date_for_input(self, val):
        """YYYY-MM-DD 문자열로 변환 (HTML input type='date' 호환용)"""
        if not val:
            return ""

        # datetime 객체인 경우
        if hasattr(val, "strftime"):
            return val.strftime("%Y-%m-%d")

        # 문자열인 경우 (2026/02/06 등) -> 2026-02-06
        s_val = str(val).strip().replace("/", "-").replace(".", "-")

        # YYYY-MM-DD (10자리) 추출
        if len(s_val) >= 10:
            return s_val[:10]
        return s_val

    # No와 Time을 이용해 절대 시간을 계산하는 메서드 추가
    def _get_abs_hours_with_no(self, base_hours, no, time_str):
        """
        Base Hours(기준점)에 경과 일수(No)와 시간을 더해 절대 시간 반환
        """
        t_str = str(time_str).zfill(4)
        h = int(t_str[:2])
        m = int(t_str[2:])
        time_part = h + (m / 60.0)

        # Base의 '일(Day)' 부분 추출 (예: SUN 00:00이 기준이라면 0일)
        base_days_part = math.floor(base_hours / 24.0)

        # 전체 절대 일수 = Base 일수 + 사용자 입력 No
        total_days = base_days_part + no

        return (total_days * 24.0) + time_part
