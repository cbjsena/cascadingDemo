import io
import math
from decimal import Decimal
from django.db import transaction
import openpyxl  # [필수] openpyxl 설치 필요 (pip install openpyxl)
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

from input_data.models import Distance, InputDataSnapshot, ProformaSchedule
from common import messages as msg
from common import excel_configs as ex_cfg
from common.utils.excel_manager import ExcelManager
from common import constants as const


class ProformaService:
    """
    Proforma Schedule 관련 비즈니스 로직 처리 클래스
    Time Line 계산 방식: 첫 번째 포트 ETB를 기준으로 누적 시간(Elapsed Time) 관리
    """

    def __init__(self):
        # ExcelManager 인스턴스 초기화
        self.excel_manager = ExcelManager()

    def parse_header(self, request):
        """
        [Config 기반 동적 파싱]
        Basic Information 영역의 데이터를 HTML name(Key)을 기준으로 추출
        항목이 변경되어도 Config만 수정
        """
        header_data = {}
        for item in ex_cfg.PROFORMA_CONFIG['basic_headers']:
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
        for _, key, _ in ex_cfg.PROFORMA_CONFIG['grid_headers']:
            values = request.POST.getlist(f"{key}[]")
            grid_data[key] = values
            if values:
                row_count = len(values)

        # 2. Row 단위로 변환
        rows = []
        for i in range(row_count):
            row = {}
            for _, key, _ in ex_cfg.PROFORMA_CONFIG['grid_headers']:
                # 리스트 범위 체크
                val = grid_data[key][i] if i < len(grid_data[key]) else ''

                # 숫자형 필드 안전 변환 (필요시)
                if key in ['pilot_in', 'work_hours', 'pilot_out', 'dist', 'eca_dist', 'spd', 'sea_time']:
                    row[key] = self._to_float(val)
                elif key in ['no', 'etb_no', 'etd_no']:
                    row[key] = int(val) if str(val).isdigit() else 0
                else:
                    row[key] = val
            rows.append(row)

        return rows

    def add_row(self, rows, data_id):
        """최하단에 행 추가"""
        new_row = self._create_default_row()

        # 1. 초기 상태에서 ETD 계산 (기본값 기반)
        self._calc_etd_from_etb(new_row)

        if rows:
            last_row = rows[-1]

            # 2. 이전 행 ETD 재계산 및 Sea Time 설정
            self._calc_etd_from_etb(last_row)
            last_row['sea_time'] = const.DEFAULT_SEA_TIME

            # 3. 새 행 ETB 계산 = 이전 ETD + Sea Time
            prev_etd_total = self._get_total_hours(
                last_row.get('etd_no', 0),
                last_row.get('etd_time', '0000')
            )

            new_etb_total = prev_etd_total + const.DEFAULT_SEA_TIME
            no, day, time = self._hours_to_tuple(new_etb_total)

            new_row['etb_no'] = no
            new_row['etb_day'] = day  # 계산된 요일 반영
            new_row['etb_time'] = time

            # 4. 새 행 ETD 재계산 (변경된 ETB 기준)
            self._calc_etd_from_etb(new_row)

        rows.append(new_row)
        return self._reindex_rows(rows)

    def insert_row(self, rows, index):
        """중간 삽입"""
        new_row = self._create_default_row()
        self._calc_etd_from_etb(new_row)  # 초기화

        if 0 <= index < len(rows):
            prev_row = rows[index]

            # 1. 이전 행 시간 재계산
            self._calc_etd_from_etb(prev_row)
            prev_row['sea_time'] = const.DEFAULT_SEA_TIME

            # 2. 새 행 ETB 계산
            prev_etd_total = self._get_total_hours(prev_row['etd_no'], prev_row['etd_time'])
            new_etb_total = prev_etd_total + const.DEFAULT_SEA_TIME

            no, day, time = self._hours_to_tuple(new_etb_total)
            new_row['etb_no'] = no
            new_row['etb_day'] = day
            new_row['etb_time'] = time

            # 3. 새 행 ETD 재계산
            self._calc_etd_from_etb(new_row)

            rows.insert(index + 1, new_row)
        else:
            return self.add_row(rows, None)

        return self._reindex_rows(rows)

    def insert_row(self, rows, index):
        """
        중간 삽입: 선택된 행(index)의 바로 다음에 새 행을 추가함
        - 로직 1: 기본값 적용 (Pilot, WorkHours 등)
        - 로직 2: 새 행 ETB = 선택된 행 ETD + 24시간(Sea Time)
        - 로직 3: 새 행 ETD = 새 행 ETB + 24시간(Work Hours)
        """
        new_row = self._create_default_row()
        self._calc_etd_from_etb(new_row) # 초기화

        # 유효한 인덱스인지 확인 (index는 선택된 행의 0-based index)
        if 0 <= index < len(rows):
            prev_row = rows[index]  # 선택된 행이 '이전 행'이 됨

            # 1. 이전 행 시간 재계산
            self._calc_etd_from_etb(prev_row)
            prev_row['sea_time'] = const.DEFAULT_SEA_TIME

            # 2. 새 행 ETB 계산
            prev_etd_total = self._get_total_hours(prev_row['etd_no'], prev_row['etd_time'])
            new_etb_total = prev_etd_total + const.DEFAULT_SEA_TIME

            no, day, time = self._hours_to_tuple(new_etb_total)
            new_row['etb_no'] = no
            new_row['etb_day'] = day
            new_row['etb_time'] = time

            # 3. 새 행 ETD 재계산
            self._calc_etd_from_etb(new_row)

            # 선택된 행 *다음* 위치(index + 1)에 삽입
            rows.insert(index + 1, new_row)

        else:
            # 인덱스가 없거나 이상하면 맨 뒤에 추가 (Add Row 로직)
            return self.add_row(rows, None)

        return self._reindex_rows(rows)

    def delete_rows(self, rows, indices):
        """선택된 행 삭제"""
        if not indices:
            return rows
        # 인덱스 역순 정렬 후 삭제
        indices = sorted([int(x) for x in indices], reverse=True)
        for i in indices:
            if 0 <= i < len(rows):
                del rows[i]
        return self._reindex_rows(rows)

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
        data_id = header_info.get('data_id')
        if not rows:
            return rows

        # [1] 기준점 설정 (Row 0)
        start_day_str = rows[0].get('etb_day', 'SUN')
        start_time_str = rows[0].get('etb_time', '0000')
        base_abs_hours = self._get_abs_hours_from_day_time(start_day_str, start_time_str)

        # 현재 행의 도착 시간(ETB) 누적 변수
        # (Row 0은 기준점이므로 바로 설정)
        current_etb_abs = base_abs_hours

        # [2] 순차 계산 루프
        for i in range(len(rows)):
            curr = rows[i]

            # --- 2.0 거리 업데이트 (이전 로직 유지) ---
            if i < len(rows) - 1:
                next_row = rows[i + 1]
                if curr.get('port_code') and next_row.get('port_code'):
                    dist_obj = Distance.objects.filter(
                        data_id=data_id,
                        from_port_code=curr['port_code'],
                        to_port_code=next_row['port_code']
                    ).first()
                    if dist_obj:
                        curr['dist'] = dist_obj.distance
                        curr['eca_dist'] = dist_obj.eca_distance

            # --- 2.1 ETB 확정 (사용자 입력 우선) ---
            if i == 0:
                # 첫 행은 기준점이므로 변경 없음
                current_etb_abs = base_abs_hours
            else:
                # [핵심 변경] 사용자가 입력한 ETB Day/Time을 해석하여 절대 시간 결정
                prev_row = rows[i - 1]

                # 이전 행의 ETD 절대 시간 (이미 계산됨)
                prev_etd_abs = self._get_abs_hours_from_row(prev_row, 'etd', base_abs_hours)

                # 사용자가 입력한 현재 행의 ETB 정보
                user_day = curr.get('etb_day', const.DEFAULT_ETB_DAY)
                user_time = curr.get('etb_time', const.DEFAULT_TIME)

                # (1) 사용자 입력이 이전 ETD 이후의 가장 가까운 미래가 되도록 절대 시간 계산
                candidate_etb_abs = self._resolve_next_etb(prev_etd_abs, user_day, user_time)

                # 1-1 ETB No는 이전 행의 ETD No보다 작을 수 없다
                # 사용자가 억지로 과거 시간을 입력했다면, 최소값(Prev ETD)으로 강제 조정
                if candidate_etb_abs < prev_etd_abs:
                    candidate_etb_abs = prev_etd_abs

                current_etb_abs = candidate_etb_abs

                # (2) 역산: Sea Time = (현재 ETB - 이전 ETD) - Pilots
                prev_pilot_out = self._to_float(prev_row.get('pilot_out', 0))
                curr_pilot_in = self._to_float(curr.get('pilot_in', 0))

                calc_sea_time = current_etb_abs - prev_etd_abs - prev_pilot_out - curr_pilot_in

                # 방어 코드: 시간이 역전된 경우 (즉, 사용자가 ETB를 ETD보다 과거로 입력함)
                if calc_sea_time < 0:
                    calc_sea_time = 0
                    # 시간을 강제로 밀어버릴지, Sea Time을 0으로 두고 ETB를 수정할지 결정해야 함.
                    # 여기서는 "사용자 ETB 우선"이지만 물리적으로 불가능하면 Sea Time=0으로 둠.

                # (3) 이전 행의 Sea Time 및 Speed 업데이트
                prev_row['sea_time'] = round(calc_sea_time, 2)

                dist = self._to_float(prev_row.get('dist', 0))
                if calc_sea_time > 0.01:
                    prev_row['spd'] = round(dist / calc_sea_time, 2)
                else:
                    prev_row['spd'] = 0

            # --- 2.2 ETB 화면 표시 업데이트 ---
            no, day, time = self._hours_to_display_format(current_etb_abs, base_abs_hours)
            curr['etb_no'] = no
            curr['etb_day'] = day
            curr['etb_time'] = time

            # --- 2.3 ETD 계산 (ETB + Work Hours) ---
            # ETD는 사용자가 입력하더라도 Work Hours가 우선권(Duration)을 가지는 경우가 많음
            # 여기서는 ETB가 확정되었으므로 Work Hours를 더해 ETD를 재계산함
            work_hours = self._to_float(curr.get('work_hours', 0))
            current_etd_abs = current_etb_abs + work_hours

            no, day, time = self._hours_to_display_format(current_etd_abs, base_abs_hours)
            curr['etd_no'] = no
            curr['etd_day'] = day
            curr['etd_time'] = time

            # (중요) 다음 루프를 위해 계산된 ETD 값을 Row에 임시 저장할 필요가 있을 수 있음
            # 하지만 _hours_to_display_format으로 변환된 no/day/time을 다시 파싱하는 것보다
            # current_etd_abs 변수를 활용하는 것이 좋으나,
            # 위 루프 구조상 prev_row를 참조하므로 _get_abs_hours_from_row 헬퍼 사용

        return rows

    def add_row(self, rows, data_id):
        """
        최하단 행 추가
        - 이전 행이 있다면: Previous ETD + 24h(Sea Time) = New ETB
        """
        new_row = self._create_default_row()

        if rows:
            # 기준점(Row 0) 절대 시간 계산 (No 계산을 위해 필요)
            start_day = rows[0].get('etb_day', 'SUN')
            start_time = rows[0].get('etb_time', '0000')
            base_abs_hours = self._get_abs_hours_from_day_time(start_day, start_time)

            # 마지막 행(직전 행) 기준으로 새 행 시간 계산
            last_row = rows[-1]
            self._calculate_new_row_times(new_row, last_row, base_abs_hours)
        else:
            # 첫 번째 행인 경우 기본값 유지 (SUN 00:00)
            pass

        rows.append(new_row)

        # 전체 재계산 (거리 등 동기화)
        return self.calculate_schedule(rows, {'data_id': data_id})

    def insert_row(self, rows, index):
        """
        중간 삽입
        - 선택된 행(index)의 바로 뒤에 삽입
        - Selected ETD + 24h = New ETB
        """
        new_row = self._create_default_row()

        if rows and 0 <= index < len(rows):
            # 기준점(Row 0) 절대 시간 계산
            start_day = rows[0].get('etb_day', 'SUN')
            start_time = rows[0].get('etb_time', '0000')
            base_abs_hours = self._get_abs_hours_from_day_time(start_day, start_time)

            # 선택된 행(prev_row) 기준으로 새 행 시간 계산
            prev_row = rows[index]
            self._calculate_new_row_times(new_row, prev_row, base_abs_hours)

            # 삽입
            rows.insert(index + 1, new_row)
        else:
            # 인덱스 오류 시 맨 뒤 추가
            return self.add_row(rows, None)

        return self.calculate_schedule(rows, {'data_id': None})

    def delete_rows(self, rows, indices):
        if not indices: return rows
        indices = sorted([int(x) for x in indices], reverse=True)
        for i in indices:
            if 0 <= i < len(rows):
                del rows[i]
        return self.calculate_schedule(rows, {'data_id': None})

    @transaction.atomic
    def save_to_db(self, header, rows, user):
        # 기존과 동일
        data_id = header.get('data_id')
        lane_code = header.get('lane_code')
        proforma_name = header.get('proforma_name')

        try:
            snapshot = InputDataSnapshot.objects.get(data_id=data_id)
        except InputDataSnapshot.DoesNotExist:
            raise ValueError(msg.SNAPSHOT_NOT_FOUND.format(data_id=data_id))

        ProformaSchedule.objects.filter(
            data_id=snapshot,
            vessel_service_lane_code=lane_code,
            proforma_name=proforma_name
        ).delete()

        new_schedules = []
        for row in rows:
            if not row.get('port_code'): continue

            schedule = ProformaSchedule(
                data_id=snapshot,
                vessel_service_lane_code=lane_code,
                proforma_name=proforma_name,
                duration=Decimal(header.get('duration') or 0),
                standard_service_speed=Decimal(header.get('std_speed') or 0),
                declared_capacity=header.get('capacity', ''),
                declared_count=int(header.get('count') or 0),
                service_lane_standard=True,
                port_code=row['port_code'],
                direction=row.get('direction', 'E'),
                calling_port_indicator_seq="1",
                calling_port_seq=int(row['no']),
                turn_port_pair_code=row.get('turn_info', 'N'),
                turn_port_system_code='N',
                pilot_in_hours=Decimal(row.get('pilot_in') or 0),
                etb_day_code=row.get('etb_day', ''),
                etb_day_time=row.get('etb_time', ''),
                etb_day_number=int(row.get('etb_no') or 0),
                actual_work_hours=Decimal(row.get('work_hours') or 0),
                etd_day_code=row.get('etd_day', ''),
                etd_day_time=row.get('etd_time', ''),
                etd_day_number=int(row.get('etd_no') or 0),
                pilot_out_hours=Decimal(row.get('pilot_out') or 0),
                link_distance=int(float(row.get('dist') or 0)),
                link_eca_distance=int(float(row.get('eca_dist') or 0)),
                link_speed=Decimal(row.get('spd') or 0),
                sea_hours=Decimal(row.get('sea_time') or 0),
                created_by=user,
                updated_by=user
            )
            new_schedules.append(schedule)

        if new_schedules:
            ProformaSchedule.objects.bulk_create(new_schedules)

    # --- Helper Methods ---

    def _create_default_row(self):
        return {
            'port_code': '', 'direction': const.DEFAULT_DIRECTION,
            'turn_info': const.DEFAULT_TURN_INO, 'pilot_in': const.DEFAULT_PILOT_IN,
            'etb_no': 0,
            'etb_day': const.DEFAULT_ETB_DAY,
            'etb_time': const.DEFAULT_TIME,
            'work_hours': const.DEFAULT_WORK_HOURS,
            'etd_no': 0,
            'etd_day': const.DEFAULT_ETD_DAY,
            'etd_time': const.DEFAULT_TIME,
            'pilot_out': const.DEFAULT_PILOT_OUT,
            'dist': 0, 'eca_dist': 0, 'spd': 0, 'sea_time': 0, 'terminal': ''
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
        if not t_str.isdigit(): t_str = "0000"
        h = int(t_str[:2])
        m = int(t_str[2:])

        # ex) TUE 12:00 -> 2*24 + 12 + 0 = 60.0
        return (day_idx * 24) + h + (m / 60.0)

    def _get_abs_hours_from_row(self, row, prefix, base_hours):
        """Row에 저장된 No/Day/Time 정보를 바탕으로 절대 시간 복원"""
        # 저장된 No는 base_hours 대비 경과 일수
        no = int(float(row.get(f'{prefix}_no') or 0))

        # 저장된 Time
        t_str = str(row.get(f'{prefix}_time', '0000')).zfill(4)
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

        if no < 0 and no > -0.01: no = 0

        return no, day_str, time_str

    def _calculate_new_row_times(self, new_row, prev_row, base_abs_hours):
        """
        이전 행의 ETD를 기준으로 새 행의 ETB/ETD를 자동 설정
        - New ETB = Prev ETD + 24h (Sea Time)
        - New ETD = New ETB + 24h (Work Hours)
        """
        # 1. 이전 행의 ETD 절대 시간 복원
        prev_etd_abs = self._get_abs_hours_from_row(prev_row, 'etd', base_abs_hours)

        # 2. 새 행 ETB 계산
        new_etb_abs = prev_etd_abs + const.DEFAULT_SEA_TIME + const.DEFAULT_PILOT_IN + const.DEFAULT_PILOT_OUT

        # 3. 새 행 ETD 계산
        new_etd_abs = new_etb_abs + const.DEFAULT_WORK_HOURS

        # 4. 값 포맷팅 및 주입
        no, day, time = self._hours_to_display_format(new_etb_abs, base_abs_hours)
        new_row['etb_no'] = no
        new_row['etb_day'] = day
        new_row['etb_time'] = time

        no, day, time = self._hours_to_display_format(new_etd_abs, base_abs_hours)
        new_row['etd_no'] = no
        new_row['etd_day'] = day
        new_row['etd_time'] = time

        # 5. 기본 Sea Time 표시
        # (calculate_schedule에서 역산될 수도 있지만 초기값으로 넣어둠)
        prev_row['sea_time'] = const.DEFAULT_SEA_TIME

    def calculate_summary(self, rows):
        """
        [신규] 화면 표시용 Summary 데이터 계산
        """
        if not rows:
            return {}

        # self._to_float()를 사용하여 안전하게 합계 계산
        total_pilot_in = sum(self._to_float(row.get('pilot_in')) for row in rows)
        total_work_hours = sum(self._to_float(row.get('work_hours')) for row in rows)
        total_pilot_out = sum(self._to_float(row.get('pilot_out')) for row in rows)
        total_dist = sum(self._to_float(row.get('dist')) for row in rows)
        total_sea_time = sum(self._to_float(row.get('sea_time')) for row in rows)

        # 평균 속도 = 총 거리 / 총 항해 시간
        avg_speed = 0
        if total_sea_time > 0:
            avg_speed = round(total_dist / total_sea_time, 2)

        return {
            'pilot_in': total_pilot_in,
            'work_hours': total_work_hours,
            'pilot_out': total_pilot_out,
            'dist': total_dist,
            'sea_time': total_sea_time,
            'spd': avg_speed
        }

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
            config=ex_cfg.PROFORMA_CONFIG,
            header_data=header,
            rows_data=rows
        )
        return output

    def upload_excel(self, file_obj):
        """엑셀 업로드 및 날짜 포맷팅"""
        # 1. ExcelManager를 통해 파싱 (Config 사용)
        header, rows = self.excel_manager.parse_excel(file_obj, ex_cfg.PROFORMA_CONFIG)

        # 2. 날짜 필드 후처리 (Excel datetime -> HTML input date string)
        # Config에 'effective_date' 키가 있는지 확인하고 처리
        if 'effective_date' in header:
            header['effective_date'] = self._format_date_for_input(header['effective_date'])

        # 3. 데이터 후처리 (Default Value)
        for row in rows:
            if not row.get('direction'): row['direction'] = const.DEFAULT_DIRECTION
            if not row.get('turn_info'): row['turn_info'] = const.DEFAULT_TURN_INO

            for key in ['pilot_in', 'work_hours', 'pilot_out', 'dist', 'eca_dist', 'spd', 'sea_time']:
                row[key] = self._to_float(row.get(key, 0))

                # float 변환
                for key in ['pilot_in', 'work_hours', 'pilot_out', 'dist', 'eca_dist', 'spd', 'sea_time']:
                    row[key] = self._to_float(row.get(key, 0))

                # int 변환
                for key in ['no', 'etb_no', 'etd_no']:
                    val = row.get(key, 0)
                    row[key] = int(val) if str(val).isdigit() else 0

        # 4. 계산
        calc_header = {'data_id': header.get('data_id')}
        calculated_rows = self.calculate_schedule(rows, calc_header)

        return header, calculated_rows

    def _format_date_for_input(self, val):
        """YYYY-MM-DD 문자열로 변환 (HTML input type='date' 호환용)"""
        if not val: return ''

        # datetime 객체인 경우
        if hasattr(val, 'strftime'):
            return val.strftime('%Y-%m-%d')

        # 문자열인 경우 (2026/02/06 등) -> 2026-02-06
        s_val = str(val).strip().replace('/', '-').replace('.', '-')

        # YYYY-MM-DD (10자리) 추출
        if len(s_val) >= 10:
            return s_val[:10]
        return s_val

    def _to_float(self, val):
        try:
            return float(val)
        except:
            return 0.0