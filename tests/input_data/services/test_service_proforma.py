import csv
import os

from django.conf import settings

import pytest

from input_data.models import BaseDistance, MasterPort, ProformaScheduleDetail
from input_data.services.proforma_service import ProformaService


@pytest.mark.django_db
class TestProformaServiceLogic:
    """
    [Service Layer] ProformaService 비즈니스 로직 집중 검증
    범위: 계산 로직(역산, 보정), 데이터 가공, DB 저장 매핑
    """

    def test_calculate_back_computation(
        self, proforma_service, base_scenario, distance_data
    ):
        """
        [IN_PF_DIS_011] 역산 로직 검증 (ETB 기준 -> Sea Time/Speed 계산)
        Given:
         - Row 1 (PUS): Start Day 0 00:00, Work 10h -> ETD Day 0 10:00. Pilot Out 1h.
         - Row 2 (TYO): ETB Day 2 12:00 (User Input). Pilot In 1h. Dist 500.
        Calculation:
         - Berth Gap = (Day 2 12:00) - (Day 0 10:00) = 50h
         - Sea Time = 50h - 1h(Prev Pilot) - 1h(Curr Pilot) = 48h
         - Speed = 500 / 48 = 10.416... -> 10.42
        """
        rows = [
            {
                "port_seq": 1,
                "port_code": "KRPUS",
                "etb_no": 0,
                "etb_day": "SUN",
                "etb_time": "0000",
                "work_hours": 10.0,
                "pilot_in": 0,
                "pilot_out": 1.0,
                "dist": 0,
                "spd": 0,
                "sea_time": 0,
            },
            {
                "port_seq": 2,
                "port_code": "JPTYO",
                "etb_no": 2,
                "etb_day": "TUE",
                "etb_time": "1200",  # User Input
                "work_hours": 10.0,
                "pilot_in": 1.0,
                "pilot_out": 0,
                "dist": 0,
                "spd": 0,
                "sea_time": 0,
            },
        ]
        header = {"scenario_id": base_scenario.id}

        # When
        calc_rows = proforma_service.calculate_schedule(rows, header)
        row_pus = calc_rows[0]

        # Then
        assert float(row_pus["dist"]) == 500  # 거리 자동 매핑
        assert float(row_pus["sea_time"]) == 48.0  # Sea Time 역산
        assert float(row_pus["spd"]) == pytest.approx(10.42, 0.01)  # Speed 역산

    def test_etb_no_priority(self, proforma_service, base_scenario):
        """
        [IN_PF_DIS_012] ETB No 우선순위 검증
        자동 로직(요일 계산)보다 사용자가 입력한 etb_no(Day 10)가 유지되어야 함.
        """
        rows = [
            {
                "port_seq": 1,
                "port_code": "A",
                "etb_no": 0,
                "etb_day": "SUN",
                "etb_time": "0000",
                "work_hours": 0,
                "pilot_out": 0,
            },
            {
                "port_seq": 2,
                "port_code": "B",
                "etb_no": 10,
                "etb_day": "WED",
                "etb_time": "0000",  # 명시적 Day 10
                "work_hours": 0,
                "pilot_in": 0,
            },
        ]
        header = {"scenario_id": base_scenario.id}

        calc_rows = proforma_service.calculate_schedule(rows, header)

        # Day 10 유지 및 Sea Time 증가 확인 (240h)
        assert int(calc_rows[1]["etb_no"]) == 10
        assert float(calc_rows[0]["sea_time"]) == 240.0

    def test_past_time_correction(self, proforma_service, base_scenario):
        """
        [IN_PF_DIS_013] 과거 시간 입력 시 자동 보정
        상황: Row 0가 2일(48h) 동안 작업하여 Day 2(TUE)에 끝남.
        입력: Row 1에 Day 1(MON)을 입력 (과거 시간 오류).
        기대: Day 2(TUE) 이후 가장 가까운 User Day(WED)인 Day 3으로 보정.
        """
        rows = [
            {
                "port_seq": 1,
                "port_code": "A",
                "etb_no": 0,
                "etb_day": "SUN",
                "etb_time": "0000",
                "work_hours": 48,
                "pilot_out": 0,  # ETD -> TUE 00:00 (Day 2)
            },
            {
                "port_seq": 2,
                "port_code": "B",
                "etb_no": 1,
                "etb_day": "WED",
                "etb_time": "0000",  # Error: Day 1 (MON)
                "work_hours": 0,
                "pilot_in": 0,
            },
        ]
        header = {"scenario_id": base_scenario.id}

        calc_rows = proforma_service.calculate_schedule(rows, header)

        # Prev ETD는 TUE(Day 2). User Input은 WED.
        # TUE 이후 가장 가까운 WED는 Day 3 (WED).
        corrected_no = int(calc_rows[1]["etb_no"])
        assert corrected_no == 3

    def test_save_mapping_and_indicator(self, proforma_service, base_scenario, user):
        """
        [IN_PF_DIS_014 서비스] save_schedule 내부 DB 저장 로직 및 Indicator 생성 검증
        뷰 레벨 테스트: test_view_proforma.py::test_action_save_full 참조
        """
        header = {
            "scenario_id": base_scenario.id,
            "lane_code": "SVC_TEST",
            "proforma_name": "PF_SVC",
            "duration": "14",
            "capacity": "5000",
            "count": "2",
        }
        rows = [
            {"port_seq": 1, "port_code": "KRPUS", "direction": "E", "etb_no": 0},
            {"port_seq": 2, "port_code": "JPTYO", "direction": "E", "etb_no": 2},
            {
                "port_seq": 3,
                "port_code": "KRPUS",
                "direction": "E",
                "etb_no": 5,
            },  # 재기항
        ]

        proforma_service.save_schedule(header, rows, user)

        qs = ProformaScheduleDetail.objects.filter(
            proforma__scenario=base_scenario, proforma__lane_id="SVC_TEST"
        ).order_by("calling_port_seq")

        assert qs.count() == 3

        # Indicator: 첫 방문 "1", 두 번째 "2"
        assert qs[0].calling_port_indicator == "1"
        assert qs[2].calling_port_indicator == "2"

    def test_row_operations(self, proforma_service, base_scenario):
        """
        [IN_PF_DIS_006~003] 행 추가/삽입/삭제 로직 검증
        """
        rows = []
        # Add
        rows = proforma_service.add_row(rows, base_scenario.id)
        assert len(rows) == 1

        # Insert (at 0 -> becomes index 1 due to implementation logic or prepending)
        # Note: insert_row implementation usually inserts *after* index or handles empty
        rows = proforma_service.add_row(rows, base_scenario.id)  # total 2
        rows = proforma_service.insert_row(rows, 0)  # Insert after index 0
        assert len(rows) == 3

        # Delete
        rows = proforma_service.delete_rows(rows, ["1"])
        assert len(rows) == 2


@pytest.mark.django_db
class TestProformaFileCalculation:
    """
    [Service Layer] 파일 기반 대량 데이터 계산 정합성 테스트
    """

    @pytest.fixture
    def service(self):
        return ProformaService()

    def load_csv(self, filename):
        """CSV 파일을 읽어 List of Dict로 반환"""
        # 경로: input_data/tests/views/data/
        file_path = os.path.join(
            settings.BASE_DIR, "tests", "input_data", "services", "data", filename
        )
        data = []
        with open(file_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(dict(row))
        return data

    def setup_distance_data(self, output_rows, base_scenario):
        """
        Output 데이터를 기반으로 DB에 BaseDistance 정보 생성
        (계산 로직이 DB에서 거리를 조회하므로 선행 필요)
        """
        for i in range(len(output_rows) - 1):
            curr = output_rows[i]
            next_row = output_rows[i + 1]

            dist_val = float(curr.get("link_distance") or 0)
            if dist_val > 0:
                # Distance FK 참조 무결성 보장
                MasterPort.objects.get_or_create(
                    port_code=curr["port_code"],
                    defaults={"port_name": curr["port_code"]},
                )
                MasterPort.objects.get_or_create(
                    port_code=next_row["port_code"],
                    defaults={"port_name": next_row["port_code"]},
                )
                BaseDistance.objects.get_or_create(
                    from_port_id=curr["port_code"],
                    to_port_id=next_row["port_code"],
                    defaults={
                        "distance": dist_val,
                        "eca_distance": float(curr.get("link_eca_distance") or 0),
                    },
                )

    def test_calculate_with_files(self, service, base_scenario):
        """
        [IN_PF_DIS_019] CSV 파일 기반 스케줄 계산 정합성 검증
        1. Output CSV를 기반으로 Distance 데이터 적재
        2. Input CSV를 읽어 Service 입력 포맷으로 변환
        3. calculate_schedule 실행
        4. 결과가 Output CSV와 일치하는지 필드별 검증
        """
        # 1. 파일 로드
        input_data = self.load_csv("test_proforma_input.csv")
        output_data = self.load_csv("test_proforma_output.csv")

        # 2. 거리 데이터 세팅 (Output 기준)
        self.setup_distance_data(output_data, base_scenario)

        # 3. Input 데이터 변환 (Service가 기대하는 Key로 매핑)
        rows_to_calc = []
        for row in input_data:
            # CSV 컬럼 -> Service Key 매핑
            mapped_row = {
                "port_seq": int(row["calling_port_seq"]),
                "port_code": row["port_code"],
                "direction": row["direction"],
                "turn_port_info_code": row["turn_port_info_code"],
                "terminal": row.get("terminal_code", ""),
                # Numeric
                "pilot_in": float(row["pilot_in_hours"] or 0),
                "pilot_out": float(row["pilot_out_hours"] or 0),
                "work_hours": float(row["actual_work_hours"] or 0),
                # ETB Input
                "etb_no": int(row["etb_day_number"] or 0),
                "etb_day": row["etb_day_code"],
                "etb_time": str(row["etb_day_time"]).zfill(4),
                # Calculated Fields (초기화)
                "dist": 0,
                "spd": 0,
                "sea_time": 0,
                "etd_no": 0,
                "etd_day": "",
                "etd_time": "",
            }
            rows_to_calc.append(mapped_row)

        header = {"scenario_id": base_scenario.id}

        # 4. 계산 실행
        calculated_rows = service.calculate_schedule(rows_to_calc, header)

        # 5. 검증 및 실패 상세 출력
        assert len(calculated_rows) == len(output_data), "Row count mismatch"

        errors = []
        for i, calc in enumerate(calculated_rows):
            expect = output_data[i]
            row_errors = []

            # (1) ETB 검증
            if int(calc["etb_no"]) != int(expect["etb_day_number"]):
                row_errors.append(
                    f"ETB No: {calc['etb_no']} != {expect['etb_day_number']}"
                )

            # (2) ETD 검증 (Expect 값이 비어있으면 검증 스킵 - 마지막 행 등)
            if expect["etd_day_number"]:
                if int(calc["etd_no"]) != int(expect["etd_day_number"]):
                    row_errors.append(
                        f"ETD No: {calc['etd_no']} != {expect['etd_day_number']}"
                    )

                exp_etd_time = str(expect["etd_day_time"]).zfill(4)

                if calc["etd_time"] != exp_etd_time:
                    row_errors.append(f"ETD Time: {calc['etd_time']} != {exp_etd_time}")

            # (3) Sea Time & Speed 검증 (역산 결과)
            # 마지막 행 등 이동이 없는 경우 제외하고 비교
            expected_dist = float(expect.get("link_distance") or 0)
            if expected_dist > 0:
                # 오차 범위 0.1
                if abs(float(calc["sea_time"]) - float(expect["sea_time_hours"])) > 0.1:
                    row_errors.append(
                        f"SeaTime: {calc['sea_time']} != {expect['sea_time_hours']}"
                    )

                if abs(float(calc["spd"]) - float(expect["link_speed"])) > 0.1:
                    row_errors.append(f"Speed: {calc['spd']} != {expect['link_speed']}")

            if row_errors:
                errors.append(
                    f"[Row {i + 1} {calc['port_code']}] " + ", ".join(row_errors)
                )

        # 에러가 하나라도 있으면 실패 처리하고 전체 에러 메시지 출력
        if errors:
            pytest.fail("\n".join(errors))
