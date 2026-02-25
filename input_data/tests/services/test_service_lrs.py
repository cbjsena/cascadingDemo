from datetime import timedelta

import pytest

from django.http.request import QueryDict
from django.utils import timezone

from input_data.models import (
    LongRangeSchedule,
    ProformaSchedule,
    ProformaScheduleDetail,
)


@pytest.mark.django_db
class TestLongRangeService:
    """
    Long Range Schedule(LRS) 엔진 스케줄링 로직 집중 테스트
    Scenarios: LRS_SVC_001, LRS_SVC_HEAD_Y, LRS_SVC_MID_Y, LRS_SVC_TAIL_Y
    """

    def test_lrs_svc_001_basic_creation(self, lrs_service, sample_schedule, user):
        """[LRS_SVC_001] 기본 LRS 생성 엔진 테스트 (단일 선박, 가상포트 없음)"""
        # Given
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)

        qdict = QueryDict(mutable=True)
        qdict.update(
            {
                "scenario_id": sample_schedule.scenario.id,
                "lane_code": sample_schedule.lane_code,
                "proforma_name": sample_schedule.proforma_name,
                "effective_start_date": start_date.strftime("%Y-%m-%d"),
                "effective_end_date": end_date.strftime("%Y-%m-%d"),
            }
        )
        qdict.setlist("vessel_code[]", ["V_TEST"])
        qdict.setlist("vessel_start_date[]", [start_date.strftime("%Y-%m-%d")])

        # When: 엔진 구동
        lrs_service.generate_lrs(qdict, user)

        # Then: 스케줄이 생성되었는지 확인
        schedules = LongRangeSchedule.objects.filter(
            scenario=sample_schedule.scenario, vessel_code="V_TEST"
        ).order_by("etb")

        assert schedules.count() > 0
        assert schedules.first().port_code == "KRPUS"

    def test_lrs_svc_head_tail_y_logic(self, lrs_service, pf_complex_data):
        """
        [LRS_SVC_HEAD_Y] Head Y: 첫 포트 연속 Y -> 가상 포트 생성 (Voyage -1, 반대 방향)
        [LRS_SVC_TAIL_Y] Tail Y: 마지막 포트 Y -> 가상 포트 미생성 (Loop 방지)
        """
        # Given: 부모 Master와 분리된 Detail 리스트 가져오기
        rows = list(
            ProformaScheduleDetail.objects.filter(
                proforma__scenario=pf_complex_data, proforma__lane_code="TEST_LANE"
            ).order_by("calling_port_seq")
        )

        # When: 시퀀스 확장 엔진 내부 메서드 직접 호출
        expanded = lrs_service._get_expanded_sequence(rows)

        # Then: Head Y 검증
        head_virtual = expanded[0]
        head_actual = expanded[1]

        assert head_virtual["obj"].port_code == "PORT_A"
        assert head_virtual["voyage_offset"] == -1
        assert head_virtual["direction"] == "W"  # 원본 'E'의 반대

        assert head_actual["obj"].port_code == "PORT_A"
        assert head_actual["voyage_offset"] == 0
        assert head_actual["direction"] == "E"

        # Tail Y 검증 (마지막 포트는 Y여도 Virtual을 만들지 않음)
        tail_actual = expanded[-1]
        assert tail_actual["obj"].port_code == "PORT_C"
        assert tail_actual["voyage_offset"] == 0

        # 총 확장 길이 검증 (PORT A: Virtual+Actual, PORT B: Actual, PORT C: Actual)
        assert len(expanded) == 4

    def test_lrs_svc_mid_y_virtual_port(self, lrs_service, pf_complex_data, user):
        """
        [LRS_SVC_MID_Y] 가상 포트 생성 (Middle Y)
        기항지 순서가 N -> Y -> N 일 때 중간 포트에서 가상 포트 정상 생성 검증
        """
        start_date = timezone.now().date()

        # 1. Given: Master-Detail N -> Y -> N 데이터 수동 생성
        master = ProformaSchedule.objects.create(
            scenario=pf_complex_data,
            lane_code="LANE_MID",
            proforma_name="PF_MID_Y",
            effective_from_date=timezone.now(),
            declared_count=2,
            duration=10.0,
            created_by=user,
            updated_by=user,
        )

        ProformaScheduleDetail.objects.create(
            proforma=master,
            terminal_code="PORT_A01",
            etb_day_code="SUN",
            etb_day_time="0800",
            etb_day_number=0,
            port_code="PORT_A",
            calling_port_indicator="1",
            calling_port_seq=1,
            direction="E",
            turn_port_info_code="N",
            created_by=user,
        )
        ProformaScheduleDetail.objects.create(
            proforma=master,
            terminal_code="PORT_B01",
            etb_day_code="MON",
            etb_day_time="0800",
            etb_day_number=0,
            port_code="PORT_B",
            calling_port_indicator="2",
            calling_port_seq=2,
            direction="E",
            turn_port_info_code="Y",
            created_by=user,  # 중간 Y
        )
        ProformaScheduleDetail.objects.create(
            proforma=master,
            terminal_code="PORT_C01",
            etb_day_code="SAT",
            etb_day_time="0800",
            etb_day_number=0,
            port_code="PORT_C",
            calling_port_indicator="3",
            calling_port_seq=3,
            direction="W",
            turn_port_info_code="N",
            created_by=user,
        )

        qdict = QueryDict(mutable=True)
        qdict.update(
            {
                "scenario_id": pf_complex_data.id,
                "lane_code": "LANE_MID",
                "proforma_name": "PF_MID_Y",
                "effective_start_date": start_date.strftime("%Y-%m-%d"),
                "effective_end_date": (start_date + timedelta(days=15)).strftime(
                    "%Y-%m-%d"
                ),
            }
        )
        qdict.setlist("vessel_code[]", ["V_MID"])
        qdict.setlist("vessel_start_date[]", [start_date.strftime("%Y-%m-%d")])

        # 2. When: 엔진 구동
        lrs_service.generate_lrs(qdict, user)

        # 3. Then: PORT_B(Seq=2)에서 가상 포트가 만들어졌는지 LRS 결과로 확인
        mid_ports = LongRangeSchedule.objects.filter(
            scenario=pf_complex_data,
            lane_code="LANE_MID",
            vessel_code="V_MID",
            port_code="PORT_B",
            voyage_number="0001",
        ).order_by("calling_port_seq")

        # 실제 포트와 파생된 가상 포트로 인해 동일한 Seq에 총 2개의 데이터가 생성되어야 함
        assert mid_ports.count() == 2

        # 방향(Direction)을 추출하여 원본 방향(E)과 파생된 반대 방향(W)이 모두 존재하는지 검증
        directions = [p.direction for p in mid_ports]
        assert "E" in directions  # 원본(Actual) 포트의 방향
        assert "W" in directions  # 반대(Virtual) 포트의 방향

    def test_lrs_svc_002_duration_zero_validation(
        self, lrs_service, pf_complex_data, user
    ):
        """
        [LRS_SVC_002] Validation 예외 (Duration 0)
        Proforma Schedule의 운항 일수(Duration)가 0이거나 없을 때 방어 로직 검증
        """
        start_date = timezone.now().date()

        # Duration이 0인 Proforma 생성
        master = ProformaSchedule.objects.create(
            scenario=pf_complex_data,
            lane_code="LANE_DUR0",
            proforma_name="PF_DUR_ZERO",
            effective_from_date=timezone.now(),
            declared_count=1,
            duration=0,  # Duration 0
            created_by=user,
            updated_by=user,
        )

        ProformaScheduleDetail.objects.create(
            proforma=master,
            terminal_code="PORT_X01",
            etb_day_code="SUN",
            etb_day_time="0800",
            etb_day_number=0,
            port_code="PORT_X",
            calling_port_indicator="1",
            calling_port_seq=1,
            direction="E",
            turn_port_info_code="N",
            created_by=user,
        )

        qdict = QueryDict(mutable=True)
        qdict.update(
            {
                "scenario_id": pf_complex_data.id,
                "lane_code": "LANE_DUR0",
                "proforma_name": "PF_DUR_ZERO",
                "effective_start_date": start_date.strftime("%Y-%m-%d"),
                "effective_end_date": (start_date + timedelta(days=15)).strftime(
                    "%Y-%m-%d"
                ),
            }
        )
        qdict.setlist("vessel_code[]", ["V_DUR0"])
        qdict.setlist("vessel_start_date[]", [start_date.strftime("%Y-%m-%d")])

        # ValueError 예외 발생 검증
        with pytest.raises(ValueError):
            lrs_service.generate_lrs(qdict, user)

        # DB에 LRS 데이터가 생성되지 않아야 함
        assert not LongRangeSchedule.objects.filter(
            scenario=pf_complex_data, lane_code="LANE_DUR0"
        ).exists()

    def test_lrs_svc_date_continuity(self, lrs_service, sample_schedule, user):
        """
        [LRS_SVC_DATE] 날짜 연속성
        항차 간 날짜 증가 검증 (Voyage 2 Start = Voyage 1 Start + Duration)
        """
        start_date = timezone.now().date()
        # 충분한 기간을 주어 여러 항차가 생성되도록 함
        end_date = start_date + timedelta(days=60)

        qdict = QueryDict(mutable=True)
        qdict.update(
            {
                "scenario_id": sample_schedule.scenario.id,
                "lane_code": sample_schedule.lane_code,
                "proforma_name": sample_schedule.proforma_name,
                "effective_start_date": start_date.strftime("%Y-%m-%d"),
                "effective_end_date": end_date.strftime("%Y-%m-%d"),
            }
        )
        qdict.setlist("vessel_code[]", ["V_DATE_CNT"])
        qdict.setlist("vessel_start_date[]", [start_date.strftime("%Y-%m-%d")])

        lrs_service.generate_lrs(qdict, user)

        # 항차별로 그룹핑하여 조회
        schedules = LongRangeSchedule.objects.filter(
            scenario=sample_schedule.scenario, vessel_code="V_DATE_CNT"
        ).order_by("voyage_number", "calling_port_seq")

        # 최소 2개 이상의 항차가 생성되어야 함
        voyage_numbers = schedules.values_list("voyage_number", flat=True).distinct()
        assert len(voyage_numbers) >= 2, "Multiple voyages should be created"

        # 항차 간 ETB 날짜가 증가하는지 검증
        voyage_first_etbs = []
        for voyage in sorted(voyage_numbers):
            first_port = schedules.filter(voyage_number=voyage).first()
            if first_port:
                voyage_first_etbs.append((voyage, first_port.etb))

        for i in range(1, len(voyage_first_etbs)):
            prev_etb = voyage_first_etbs[i - 1][1]
            curr_etb = voyage_first_etbs[i][1]
            assert (
                curr_etb > prev_etb
            ), f"Voyage {voyage_first_etbs[i][0]} ETB should be after voyage {voyage_first_etbs[i-1][0]}"

    def test_lrs_svc_dup_prevention(self, lrs_service, sample_schedule, user):
        """
        [LRS_SVC_DUP] 중복 방지
        동일 선박 중복 입력 시 처리 (에러 없이 중복 건너뜀)
        """
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)

        qdict = QueryDict(mutable=True)
        qdict.update(
            {
                "scenario_id": sample_schedule.scenario.id,
                "lane_code": sample_schedule.lane_code,
                "proforma_name": sample_schedule.proforma_name,
                "effective_start_date": start_date.strftime("%Y-%m-%d"),
                "effective_end_date": end_date.strftime("%Y-%m-%d"),
            }
        )
        # 동일한 선박을 중복 입력
        qdict.setlist("vessel_code[]", ["V_DUP", "V_DUP"])
        qdict.setlist(
            "vessel_start_date[]",
            [start_date.strftime("%Y-%m-%d"), start_date.strftime("%Y-%m-%d")],
        )

        # 에러 없이 실행되어야 함
        lrs_service.generate_lrs(qdict, user)

        # V_DUP 선박에 대해 하나의 데이터 세트만 생성되어야 함
        schedules = LongRangeSchedule.objects.filter(
            scenario=sample_schedule.scenario,
            vessel_code="V_DUP",
            voyage_number="0001",
        )

        # 중복 없이 1세트의 항차만 생성되었는지 확인
        port_counts = schedules.values("calling_port_seq").distinct().count()
        total_count = schedules.count()

        # 포트 seq별로 1개씩만 존재해야 함 (중복 없음)
        assert total_count == port_counts, "Duplicate vessel data should be skipped"
