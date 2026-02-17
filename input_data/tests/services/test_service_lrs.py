from datetime import timedelta

import pytest

from django.utils import timezone

from input_data.models import LongRangeSchedule, ProformaSchedule
from input_data.services.long_range_service import LongRangeService


@pytest.mark.django_db
class TestLongRangeService:
    """
    Long Range Schedule 생성 서비스 로직 테스트
    [범위] 기본 생성, 가상 포트 규칙(Head/Tail Y), 날짜 계산
    """

    @pytest.fixture
    def lrs_service(self):
        return LongRangeService()

    @pytest.fixture
    def pf_head_y(self, base_scenario, user):
        """Head가 Y인 Proforma 데이터 (Y - N)"""
        # 1. Port A (Y) - Start
        ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_code="TEST_Y",
            proforma_name="PF_Y",
            effective_from_date=timezone.now(),
            turn_port_info_code="Y",
            duration=10.0,
            declared_capacity="5000",
            declared_count=2,
            direction="E",
            port_code="PORT_A",
            calling_port_indicator="1",
            calling_port_seq=1,
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
        # 2. Port B (N) - End
        ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_code="TEST_Y",
            proforma_name="PF_Y",
            effective_from_date=timezone.now(),
            turn_port_info_code="N",
            duration=10.0,
            declared_capacity="5000",
            declared_count=2,
            direction="E",
            port_code="PORT_B",
            calling_port_indicator="1",
            calling_port_seq=1,
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
        return base_scenario

    def test_create_lrs_basic(self, lrs_service, sample_schedule, user):
        """[LRS_SVC_001] 기본 LRS 생성 테스트"""
        # Given
        post_data = {
            "scenario_id": sample_schedule.scenario.id,
            "lane_code": sample_schedule.lane_code,
            "proforma_name": sample_schedule.proforma_name,
            "apply_end_date": (timezone.now() + timedelta(days=30)).strftime(
                "%Y-%m-%d"
            ),
        }
        # MultiValueDict imitation for list data
        from django.http.request import QueryDict

        qdict = QueryDict(mutable=True)
        qdict.update(post_data)
        qdict.setlist("vessel_code[]", ["V_001"])
        qdict.setlist("vessel_start_date[]", [timezone.now().strftime("%Y-%m-%d")])

        # When
        lrs_service.create_lrs(qdict, user)

        # Then
        lrs_qs = LongRangeSchedule.objects.filter(lane_code=sample_schedule.lane_code)
        assert lrs_qs.exists()
        assert lrs_qs.first().vessel_code == "V_001"
        assert lrs_qs.first().voyage_number == "0001"

    def test_virtual_port_head_y(self, lrs_service, pf_head_y, user):
        """[LRS_SVC_HEAD_Y] Head가 Y일 때 가상 포트 생성 규칙 검증"""
        # Given: PF_Y (Port A[Y], Port B[N])
        rows = ProformaSchedule.objects.filter(lane_code="TEST_Y").order_by(
            "calling_port_seq"
        )

        # When: 확장 시퀀스 조회
        expanded = lrs_service._get_expanded_sequence(rows)

        # Then
        # 예상:
        # 1. Port A (Virtual): Voyage -1, Direction W (E의 반대)
        # 2. Port A (Real):    Voyage 0,  Direction E
        # 3. Port B (Real):    Voyage 0,  Direction E

        assert len(expanded) == 3

        # Check 1st (Virtual)
        assert expanded[0]["obj"].port_code == "PORT_A"
        assert expanded[0]["voyage_offset"] == -1
        assert expanded[0]["direction"] == "W"

        # Check 2nd (Real)
        assert expanded[1]["obj"].port_code == "PORT_A"
        assert expanded[1]["voyage_offset"] == 0
        assert expanded[1]["direction"] == "E"

    def test_date_calculation_loop(self, lrs_service, sample_schedule, user):
        """[LRS_SVC_DATE] 항차 반복 시 날짜 증가 검증"""
        # Given: Duration 14일
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=40)  # 약 3항차 생성 예상

        from django.http.request import QueryDict

        qdict = QueryDict(mutable=True)
        qdict.update(
            {
                "scenario_id": sample_schedule.scenario.id,
                "lane_code": sample_schedule.lane_code,
                "proforma_name": sample_schedule.proforma_name,
                "apply_end_date": end_date.strftime("%Y-%m-%d"),
            }
        )
        qdict.setlist("vessel_code[]", ["V_TEST"])
        qdict.setlist("vessel_start_date[]", [start_date.strftime("%Y-%m-%d")])

        # When
        lrs_service.create_lrs(qdict, user)

        # Then
        lrs_qs = LongRangeSchedule.objects.filter(vessel_code="V_TEST").order_by("etb")

        # Voyage 1
        voy1 = lrs_qs.filter(voyage_number="0001").first()
        # Voyage 2
        voy2 = lrs_qs.filter(voyage_number="0002").first()

        assert voy1 is not None
        assert voy2 is not None

        # Voyage 2 Start ~ Voyage 1 Start + Duration (14 days)
        # 허용 오차(seconds) 고려하여 date() 비교 or delta 비교
        diff = voy2.etb - voy1.etb
        assert diff.days == 14
