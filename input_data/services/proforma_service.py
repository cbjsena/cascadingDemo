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
from common.utils.csv_manager import CsvManager
from common.utils.excel_manager import ExcelManager
from input_data.models import Distance, ProformaSchedule, ScenarioInfo


class ProformaService:
    """
    Proforma Schedule 관련 비즈니스 로직 처리 클래스
    Time Line 계산 방식: 첫 번째 포트 ETB를 기준으로 누적 시간(Elapsed Time) 관리
    """

    def __init__(self):
        # ExcelManager 인스턴스 초기화
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
        """
        [리팩토링] Grid 역시 Config를 기반으로 동적 파싱 가능
        """
        # HTML name은 보통 name="key[]" 형태이므로 Config 키에 '[]'를 붙여서 가져옴
        grid_data = {}
        row_count = 0

        # 1. 모든 컬럼 데이터 리스트 추출
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
                if key in [
                    "pilot_in",
                    "work_hours",
                    "pilot_out",
                    "dist",
                    "eca_dist",
                    "spd",
                    "sea_time",
                ]:
                    row[key] = self._to_float(val)
                elif key in ["no", "etb_no", "etd_no"]:
                    row[key] = int(val) if str(val).isdigit() else 0
                else:
                    row[key] = val
            rows.append(row)

        return rows

    def calculate_schedule(self, rows, header_info):
        """
        [수정된 로직]
        1. Row 0: ETB 절대 시간 기준점 설정
        2. Row 1~N:
           - 사용자가 입력한 ETB Day/Time을 '절대 시간'으로 변환
           - (현재 ETB - 이전 ETD - Pilots) = Sea Time 역산
           - 이전 행의 Sea Time/Speed 업데이트
           - 현재 행의 ETD = ETB + Work Hours 계산
        """
        scenario_id = header_info.get("scenario_id")
        if not rows:
            return rows

        # [1] 기준점 설정 (Row 0)
        start_day_str = rows[0].get("etb_day", "SUN")
        start_time_str = rows[0].get("etb_time", "0000")
        base_abs_hours = self._get_abs_hours_from_day_time(
            start_day_str, start_time_str
        )

        # 현재 행의 도착 시간(ETB) 누적 변수
        # (Row 0은 기준점이므로 바로 설정)
        current_etb_abs = base_abs_hours

        # [2] 순차 계산 루프
        for i in range(len(rows)):
            curr = rows[i]

            # --- 2.0 거리 업데이트 (이전 로직 유지) ---
            if i < len(rows) - 1:
                next_row = rows[i + 1]
                if curr.get("port_code") and next_row.get("port_code"):
                    dist_obj = Distance.objects.filter(
                        scenario_id=scenario_id,
                        from_port_code=curr["port_code"],
                        to_port_code=next_row["port_code"],
                    ).first()
                    if dist_obj:
                        curr["dist"] = dist_obj.distance
                        curr["eca_dist"] = dist_obj.eca_distance

            # --- 2.1 ETB 확정 (사용자 입력 우선) ---
            if i == 0:
                # 첫 행은 기준점이므로 변경 없음
                current_etb_abs = base_abs_hours
            else:
                # [핵심 변경] 사용자가 입력한 ETB Day/Time을 해석하여 절대 시간 결정
                prev_row = rows[i - 1]

                # 이전 행의 ETD 절대 시간 (이미 계산됨)
                prev_etd_abs = self._get_abs_hours_from_row(
                    prev_row, "etd", base_abs_hours
                )

                # 사용자가 입력한 현재 행의 ETB 정보
                user_day = curr.get("etb_day", const.DEFAULT_ETB_DAY)
                user_time = curr.get("etb_time", const.DEFAULT_TIME)

                # (1) 사용자 입력이 이전 ETD 이후의 가장 가까운 미래가 되도록 절대 시간 계산
                candidate_etb_abs = self._resolve_next_etb(
                    prev_etd_abs, user_day, user_time
                )

                # 1-1 ETB No는 이전 행의 ETD No보다 작을 수 없다
                # 사용자가 억지로 과거 시간을 입력했다면, 최소값(Prev ETD)으로 강제 조정
                if candidate_etb_abs < prev_etd_abs:
                    candidate_etb_abs = prev_etd_abs

                current_etb_abs = candidate_etb_abs

                # (2) 역산: Sea Time = (현재 ETB - 이전 ETD) - Pilots
                prev_pilot_out = self._to_float(prev_row.get("pilot_out", 0))
                curr_pilot_in = self._to_float(curr.get("pilot_in", 0))

                calc_sea_time = (
                    current_etb_abs - prev_etd_abs - prev_pilot_out - curr_pilot_in
                )

                # 방어 코드: 시간이 역전된 경우 (즉, 사용자가 ETB를 ETD보다 과거로 입력함)
                if calc_sea_time < 0:
                    calc_sea_time = 0
                    # 시간을 강제로 밀어버릴지, Sea Time을 0으로 두고 ETB를 수정할지 결정해야 함.
                    # 여기서는 "사용자 ETB 우선"이지만 물리적으로 불가능하면 Sea Time=0으로 둠.

                # (3) 이전 행의 Sea Time 및 Speed 업데이트
                prev_row["sea_time"] = round(calc_sea_time, 2)

                dist = self._to_float(prev_row.get("dist", 0))
                if calc_sea_time > 0.01:
                    prev_row["spd"] = round(dist / calc_sea_time, 2)
                else:
                    prev_row["spd"] = 0

            # --- 2.2 ETB 화면 표시 업데이트 ---
            no, day, time = self._hours_to_display_format(
                current_etb_abs, base_abs_hours
            )
            curr["etb_no"] = no
            curr["etb_day"] = day
            curr["etb_time"] = time

            # --- 2.3 ETD 계산 (ETB + Work Hours) ---
            # ETD는 사용자가 입력하더라도 Work Hours가 우선권(Duration)을 가지는 경우가 많음
            # 여기서는 ETB가 확정되었으므로 Work Hours를 더해 ETD를 재계산함
            work_hours = self._to_float(curr.get("work_hours", 0))
            current_etd_abs = current_etb_abs + work_hours

            no, day, time = self._hours_to_display_format(
                current_etd_abs, base_abs_hours
            )
            curr["etd_no"] = no
            curr["etd_day"] = day
            curr["etd_time"] = time

            # (중요) 다음 루프를 위해 계산된 ETD 값을 Row에 임시 저장할 필요가 있을 수 있음
            # 하지만 _hours_to_display_format으로 변환된 no/day/time을 다시 파싱하는 것보다
            # current_etd_abs 변수를 활용하는 것이 좋으나,
            # 위 루프 구조상 prev_row를 참조하므로 _get_abs_hours_from_row 헬퍼 사용

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
        if not indices:
            return rows
        indices = sorted([int(x) for x in indices], reverse=True)
        for i in indices:
            if 0 <= i < len(rows):
                del rows[i]
        return self.calculate_schedule(rows, {"scenario_id": None})

    @transaction.atomic
    def save_to_db(self, header, rows, user):
        scenario_id_val = header.get("scenario_id")
        lane_code = header.get("lane_code")
        proforma_name = header.get("proforma_name")

        try:
            # 여기서 scenario는 ScenarioInfo 객체여야 함
            scenario_obj = ScenarioInfo.objects.get(id=scenario_id_val)
        except ScenarioInfo.DoesNotExist:
            raise ValueError(msg.SCENARIO_NOT_FOUND.format(scenario_id=scenario_id_val))

        # Effective Date를 Timezone Aware 객체로 변환
        eff_date_str = header.get("effective_date", "")
        effective_date = timezone.now()  # 기본값

        if eff_date_str:
            try:
                # 1. 문자열 -> Naive Datetime 변환 (YYYY-MM-DD)
                # 입력값이 '2026-01-01' 형태라고 가정
                dt = datetime.strptime(str(eff_date_str)[:10], "%Y-%m-%d")
                # 2. Naive -> Aware Datetime 변환
                effective_date = timezone.make_aware(dt)
            except ValueError:
                pass  # 파싱 실패 시 기본값(Now) 사용

        ProformaSchedule.objects.filter(
            scenario=scenario_obj, lane_code=lane_code, proforma_name=proforma_name
        ).delete()

        new_schedules = []
        for row in rows:
            if not row.get("port_code"):
                continue
            port_cd = row["port_code"]
            raw_terminal = row.get("terminal", "")

            if not raw_terminal:
                terminal_code = f"{port_cd}01"
            else:
                terminal_code = raw_terminal

            schedule = ProformaSchedule(
                scenario=scenario_obj,
                lane_code=lane_code,
                proforma_name=proforma_name,
                effective_date=effective_date,
                duration=Decimal(header.get("duration") or 0),
                declared_capacity=header.get("capacity", ""),
                declared_count=int(header.get("count") or 0),
                port_code=port_cd,
                direction=row.get("direction", "E"),
                calling_port_indicator="1",
                calling_port_seq=int(row["no"]),
                turn_port_info_code=row.get("turn_port_info_code", "N"),
                pilot_in_hours=Decimal(row.get("pilot_in") or 0),
                etb_day_code=row.get("etb_day", ""),
                etb_day_time=row.get("etb_time", ""),
                etb_day_number=int(row.get("etb_no") or 0),
                actual_work_hours=Decimal(row.get("work_hours") or 0),
                etd_day_code=row.get("etd_day", ""),
                etd_day_time=row.get("etd_time", ""),
                etd_day_number=int(row.get("etd_no") or 0),
                pilot_out_hours=Decimal(row.get("pilot_out") or 0),
                link_distance=int(float(row.get("dist") or 0)),
                link_eca_distance=int(float(row.get("eca_dist") or 0)),
                link_speed=Decimal(row.get("spd") or 0),
                sea_hours=Decimal(row.get("sea_time") or 0),
                terminal_code=terminal_code,
                created_by=user,
                updated_by=user,
            )
            new_schedules.append(schedule)

        if new_schedules:
            ProformaSchedule.objects.bulk_create(new_schedules)

    def calculate_summary(self, rows):
        """
        [신규] 화면 표시용 Summary 데이터 계산
        """
        if not rows:
            return {}

        # self._to_float()를 사용하여 안전하게 합계 계산
        total_pilot_in = sum(self._to_float(row.get("pilot_in")) for row in rows)
        total_work_hours = sum(self._to_float(row.get("work_hours")) for row in rows)
        total_pilot_out = sum(self._to_float(row.get("pilot_out")) for row in rows)
        total_dist = sum(self._to_float(row.get("dist")) for row in rows)
        total_sea_time = sum(self._to_float(row.get("sea_time")) for row in rows)

        # 평균 속도 = 총 거리 / 총 항해 시간
        avg_speed = 0
        if total_sea_time > 0:
            avg_speed = round(total_dist / total_sea_time, 2)

        return {
            "pilot_in": total_pilot_in,
            "work_hours": total_work_hours,
            "pilot_out": total_pilot_out,
            "dist": total_dist,
            "sea_time": total_sea_time,
            "spd": avg_speed,
        }

    def upload_excel(self, file_obj):
        """엑셀 업로드 및 날짜 포맷팅"""
        # 1. ExcelManager를 통해 파싱 (Config 사용)
        header, rows = self.excel_manager.parse_excel(file_obj, ex_cfg.PROFORMA_CONFIG)

        # 2. 날짜 필드 후처리 (Excel datetime -> HTML input date string)
        # Config에 'effective_date' 키가 있는지 확인하고 처리
        if "effective_date" in header:
            header["effective_date"] = self._format_date_for_input(
                header["effective_date"]
            )

        # 3. 데이터 후처리 (Default Value)
        for row in rows:
            if not row.get("direction"):
                row["direction"] = const.DEFAULT_DIRECTION
            if not row.get("turn_port_info_code"):
                row["turn_port_info_code"] = const.DEFAULT_TURN_INO

            for key in [
                "pilot_in",
                "work_hours",
                "pilot_out",
                "dist",
                "eca_dist",
                "spd",
                "sea_time",
            ]:
                row[key] = self._to_float(row.get(key, 0))

                # float 변환
                for key in [
                    "pilot_in",
                    "work_hours",
                    "pilot_out",
                    "dist",
                    "eca_dist",
                    "spd",
                    "sea_time",
                ]:
                    row[key] = self._to_float(row.get(key, 0))

                # int 변환
                for key in ["no", "etb_no", "etd_no"]:
                    val = row.get(key, 0)
                    row[key] = int(val) if str(val).isdigit() else 0

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

        # ---------------------------------------------------------
        # 2. 사전 계산 (Global Logic)
        # ---------------------------------------------------------
        # (1) SVCE_LANE_STD_YN
        # is_standard = 'N'
        # try:
        #     eff_dt = datetime.strptime(str(header.get('effective_date', ''))[:10], '%Y-%m-%d')
        #     if datetime.now() >= eff_dt:
        #         is_standard = 'Y'
        # except:
        #     is_standard = 'N'

        # (2) STD_SVCE_SPD
        total_dist = sum(self._to_float(r.get("dist", 0)) for r in rows)
        total_sea_time = sum(self._to_float(r.get("sea_time", 0)) for r in rows)
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

    # --- Helper Methods ---
    def _create_default_row(self):
        return {
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

    def _to_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

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
