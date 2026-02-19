from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from input_data.models import LongRangeSchedule, ProformaSchedule, ScenarioInfo
from common import messages as msg


class LongRangeService:
    """
    Long Range Schedule 생성 및 관리 서비스
    """

    @transaction.atomic
    def create_lrs(self, post_data, user):
        """
        화면 입력을 받아 LRS를 생성 (기존 데이터 삭제 후 생성)
        """
        # 1. Input Parsing
        scenario_id = post_data.get("scenario_id")
        lane_code = post_data.get("lane_code")
        proforma_name = post_data.get("proforma_name")
        start_date_str = post_data.get("apply_start_date")
        end_date_str = post_data.get("apply_end_date")

        # UI에서 넘어오는 배열 데이터
        vessel_codes = post_data.getlist("vessel_code[]")
        vessel_start_dates = post_data.getlist("vessel_start_date[]")

        # Validation
        if not (scenario_id and lane_code and proforma_name and start_date_str and end_date_str):
            raise ValueError("Missing required fields.")

        try:
            scenario = ScenarioInfo.objects.get(id=scenario_id)
        except ScenarioInfo.DoesNotExist:
            raise ValueError(msg.SCENARIO_NOT_FOUND)

        # 2. Base Proforma Fetching
        proforma_rows = list(ProformaSchedule.objects.filter(
            scenario=scenario, lane_code=lane_code, proforma_name=proforma_name
        ).order_by("calling_port_seq"))

        if not proforma_rows:
            raise ValueError("Proforma Schedule not found.")

        # 헤더 정보 (Duration = Round Trip Time)
        # 첫 번째 행의 duration 사용 (모든 행이 동일하다고 가정)
        round_trip_days = float(proforma_rows[0].duration or 0)
        if round_trip_days <= 0:
            raise ValueError("Invalid Proforma Duration (0 or None).")

        # 3. Virtual Port Logic 적용 -> 확장된 시퀀스 생성
        # (실제 DB 저장은 안 하지만, 순서와 Voyage Offset 결정을 위해 필요)
        expanded_sequence = self._get_expanded_sequence(proforma_rows)

        # 4. 기존 LRS 삭제 (해당 시나리오/Lane)
        LongRangeSchedule.objects.filter(
            scenario=scenario, lane_code=lane_code
        ).delete()

        # 5. 선박별 LRS 생성 Loop
        new_lrs_list = []
        lrs_start_date = timezone.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        lrs_end_date = timezone.datetime.strptime(end_date_str, "%Y-%m-%d").date()

        # [중복 방지] 이미 처리한 선박 코드를 추적하기 위한 집합
        processed_vessels = set()

        for i, v_code in enumerate(vessel_codes):
            if not v_code:
                continue

            # 중복 선박 코드 방지 로직
            # 만약 사용자가 UI에서 같은 선박(V003)을 두 번 넣었다면 건너뜀
            if v_code in processed_vessels:
                print(f"[WARN] Duplicate vessel code detected and skipped: {v_code}")
                continue
            processed_vessels.add(v_code)

            v_start_str = vessel_start_dates[i] if i < len(vessel_start_dates) else None
            if not v_start_str:
                continue

            # 선박별 1항차 시작일 (Timezone Aware)
            # 이 날짜는 Proforma의 첫 번째 포트(seq 1)의 ETB 기준
            v_base_dt = timezone.datetime.strptime(v_start_str, "%Y-%m-%d")
            v_base_dt = timezone.make_aware(v_base_dt)
            voyage_num = 1  # 0001 항차부터 시작

            # -------------------------------------------------------------
            # Voyage Loop: LRS 종료일을 넘을 때까지 반복
            # -------------------------------------------------------------
            while True:
                # 현재 항차의 기준 시작 시간 (첫 포트 ETB 기준)
                curr_voy_start_dt = v_base_dt + timedelta(days=(voyage_num - 1) * round_trip_days)

                # 항차 종료 여부 체크 (대략적인 체크)
                if curr_voy_start_dt.date() > lrs_end_date:
                    break

                # 한 항차 내에서의 Port Call Indicator 관리
                indicator_map = {}
                lrs_seq = 1

                # Start Port Berthing Year Week (현재 항차 기준)
                voy_year, voy_week, _ = curr_voy_start_dt.isocalendar()
                start_port_y_w = f"{voy_year}{voy_week:02d}"

                # ---------------------------------------------------------
                # Sequence Loop: 확장된 프로포마(가상포트 포함) 순회
                # ---------------------------------------------------------
                for step in expanded_sequence:
                    pf_obj = step["obj"]
                    # voy_offset: -1 (이전항차), 0 (현재항차), +1 (다음항차) 등
                    # expanded_sequence에서 정의된 offset
                    seq_voy_offset = step.get("voyage_offset", 0)
                    direction = step.get("direction", pf_obj.direction)

                    # 실제 항차 번호 = 현재 루프 항차 + 시퀀스 오프셋
                    real_voy_num = voyage_num + seq_voy_offset

                    if real_voy_num < 1:
                        continue

                    # 날짜 계산
                    # Base (현재항차 시작) + (시퀀스 오프셋 * RTT) + (Proforma상 경과일)
                    # Proforma의 etb_day_number는 첫 포트(0) 기준 경과일
                    pf_elapsed_days = float(pf_obj.etb_day_number or 0)

                    # 기준점으로부터의 총 경과일
                    total_delta_days = (
                            (voyage_num - 1) * round_trip_days  # 현재 항차 시작점
                            + (seq_voy_offset * round_trip_days)  # 가상 포트 오프셋 (이전/다음 항차)
                            + pf_elapsed_days  # 프로포마 내 위치
                    )

                    # ETB 계산
                    real_etb = v_base_dt + timedelta(days=total_delta_days)

                    # 날짜 범위 체크 (LRS 기간 내 포함 여부)
                    if not (lrs_start_date <= real_etb.date() <= lrs_end_date):
                        # 범위 밖이면 생성 안 함 (Skip)
                        continue

                    # ETA, ETD 계산
                    pilot_in = float(pf_obj.pilot_in_hours or 0)
                    work_hours = float(pf_obj.actual_work_hours or 0)
                    # ETA = ETB - PilotIn
                    real_eta = real_etb - timedelta(hours=pilot_in)
                    # ETD = ETB + WorkHours (간소화 로직)
                    # 정확히는 Proforma의 etd_day_number를 써야 하나, LRS에선 간격 유지가 중요
                    # 여기서는 pf_obj.etd_day_number를 사용하여 정합성 확보
                    pf_etd_elapsed = float(pf_obj.etd_day_number or 0)
                    # ETD Delta 재계산 (ETB와 동일한 로직 + ETD 경과일)
                    total_etd_delta = (
                            (voyage_num - 1) * round_trip_days
                            + (seq_voy_offset * round_trip_days)
                            + pf_etd_elapsed
                    )
                    real_etd = v_base_dt + timedelta(days=total_etd_delta)

                    # Calling Port Indicator
                    ind_key = (pf_obj.port_code, direction)
                    curr_ind = indicator_map.get(ind_key, 0) + 1
                    indicator_map[ind_key] = curr_ind

                    # Create Instance
                    lrs = LongRangeSchedule(
                        scenario=scenario,
                        lane_code=lane_code,
                        vessel_code=v_code,
                        voyage_number=f"{real_voy_num:04d}",
                        direction=direction,
                        start_port_berthing_year_week=start_port_y_w,
                        proforma_name=proforma_name,
                        port_code=pf_obj.port_code,
                        calling_port_indicator=str(curr_ind),
                        calling_port_seq=lrs_seq,
                        schedule_change_status_code=None,
                        eta=real_eta,
                        etb=real_etb,
                        etd=real_etd,
                        terminal_code=pf_obj.terminal_code,
                        created_by=user,
                        updated_by=user,
                    )
                    new_lrs_list.append(lrs)
                    lrs_seq += 1

                # 다음 항차로
                voyage_num += 1

        # 디버깅 출력 방식 변경 (Dict 접근 -> Dot 접근)
        print(f"Total objects to create: {len(new_lrs_list)}")
        # for lrs in new_lrs_list:  # 너무 많으니 앞 5개만 출력 for lrs in new_lrs_list[:5]:
        #     print(
        #         f"Vessel: {lrs.vessel_code}/ {lrs.voyage_number}{lrs.direction}/  {lrs.port_code}")

        # 6. Bulk Create
        if new_lrs_list:
            LongRangeSchedule.objects.bulk_create(new_lrs_list)

    def _get_expanded_sequence(self, rows):
        """
        Proforma Rows를 순회하며 Virtual Port 규칙 적용
        마지막 포트인 경우 Y여도 Virtual Port를 생성하지 않음.
        """
        sequence = []

        # 마지막 인덱스 확인
        last_index = len(rows) - 1

        # 1. Start Continuous Y (Head Rule) 체크
        # 시작부터 연속된 Y인 포트들은 '이전 항차(Prev Voyage)'의 가상 포트로 먼저 생성됨
        head_y_indices = []
        for i, row in enumerate(rows):
            if row.turn_port_info_code == "Y":
                head_y_indices.append(i)
            else:
                break

        for i, row in enumerate(rows):
            opp_direction = self._get_opposite_direction(row.direction)

            # [규칙 A] Head Virtual Port (시작 부분 연속 Y)
            # 순서: 가상(Prev Voyage, Opp Dir) -> 실제(Curr Voyage, Orig Dir)
            if i in head_y_indices:
                # 1. Virtual (Prev Voyage)
                sequence.append({
                    "obj": row,
                    "voyage_offset": -1,
                    "direction": opp_direction
                })
                # 2. Actual
                sequence.append({
                    "obj": row,
                    "voyage_offset": 0,
                    "direction": row.direction
                })

            else:
                # [규칙 B] Normal / Tail Virtual Port
                # 순서: 실제(Curr Voyage, Orig Dir) -> (옵션) 가상(Curr Voyage, Opp Dir)

                # 1. Actual (무조건 생성)
                sequence.append({
                    "obj": row,
                    "voyage_offset": 0,
                    "direction": row.direction
                })

                # 2. Virtual (If Y AND NOT Last Port)
                # [수정된 조건] 마지막 행이 아닐 때만 가상 포트 생성
                if row.turn_port_info_code == "Y" and i != last_index:
                    sequence.append({
                        "obj": row,
                        "voyage_offset": 0,
                        "direction": opp_direction
                    })

        return sequence


    def _get_opposite_direction(self, direction):
        return {"E": "W", "W": "E", "S": "N", "N": "S"}.get(direction, direction)