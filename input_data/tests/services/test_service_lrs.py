from datetime import timedelta

import pytest

from django.http.request import QueryDict
from django.utils import timezone

from input_data.models import LongRangeSchedule, ProformaSchedule


@pytest.mark.django_db
class TestLongRangeService:
    """
    Long Range Schedule 서비스 로직 테스트
    Scenarios: LRS_SVC_001, LRS_SVC_HEAD_Y, LRS_SVC_TAIL_Y, LRS_SVC_DATE, LRS_SVC_DUP
    """

    def test_lrs_svc_001_basic_creation(self, lrs_service, sample_schedule, user):
        """[LRS_SVC_001] 기본 LRS 생성 테스트 (단일 선박)"""
        # Given
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)

        # Mock Request Data
        qdict = QueryDict(mutable=True)
        qdict.update(
            {
                "scenario_id": sample_schedule.scenario.id,
                "lane_code": sample_schedule.lane_code,
                "proforma_name": sample_schedule.proforma_name,
                "apply_start_date": start_date.strftime("%Y-%m-%d"),
                "apply_end_date": end_date.strftime("%Y-%m-%d"),
            }
        )
        # Form List Data
        qdict.setlist("vessel_code[]", ["V_BASIC"])
        qdict.setlist("vessel_start_date[]", [start_date.strftime("%Y-%m-%d")])
        qdict.setlist("vessel_capacity[]", ["5000"])
        qdict.setlist("lane_code_list[]", [sample_schedule.lane_code])

        # When
        lrs_service.create_lrs(qdict, user)

        # Then
        lrs_qs = LongRangeSchedule.objects.filter(vessel_code="V_BASIC")
        assert lrs_qs.exists()
        assert lrs_qs.first().voyage_number == "0001"

    def test_lrs_svc_head_tail_y_logic(self, lrs_service, pf_complex_data):
        """
        [LRS_SVC_HEAD_Y] Head Y: 가상 포트 생성 (Voyage -1, 반대 방향)
        [LRS_SVC_TAIL_Y] Tail Y: 가상 포트 미생성 (Loop 방지)
        """
        # Given: pf_complex_data fixture (Port A[Y] -> Port B[N] -> Port C[Y])
        rows = list(
            ProformaSchedule.objects.filter(
                scenario=pf_complex_data, lane_code="TEST_LANE"
            ).order_by("calling_port_seq")
        )

        # When: 시퀀스 확장 로직 실행
        expanded = lrs_service._get_expanded_sequence(rows)

        # Then
        # 예상 시퀀스:
        # 1. PORT_A (Virtual): Voy -1, Dir W (Head Y 규칙)
        # 2. PORT_A (Real):    Voy 0,  Dir E
        # 3. PORT_B (Real):    Voy 0,  Dir E
        # 4. PORT_C (Real):    Voy 0,  Dir E (Tail Y지만 Virtual 생성 X)

        assert (
            len(expanded) == 4
        ), "Head Y는 생성하고 Tail Y는 생성하지 않아 총 4개여야 합니다."

        # 1. Head Virtual Check
        assert expanded[0]["obj"].port_code == "PORT_A"
        assert expanded[0]["voyage_offset"] == -1
        assert expanded[0]["direction"] == "W"  # E의 반대

        # 2. Head Real Check
        assert expanded[1]["obj"].port_code == "PORT_A"
        assert expanded[1]["voyage_offset"] == 0
        assert expanded[1]["direction"] == "E"

        # 3. Tail Real Check (마지막 요소)
        assert expanded[3]["obj"].port_code == "PORT_C"
        assert expanded[3]["voyage_offset"] == 0
        assert expanded[3]["direction"] == "E"
        # Tail Virtual이 없으므로 여기서 끝남

    def test_lrs_svc_date_continuity(self, lrs_service, sample_schedule, user):
        """[LRS_SVC_DATE] 항차 간 날짜 연속성 검증"""
        # Given: sample_schedule Duration = 14.0 days
        start_date = timezone.now().date()
        # 14일 * 3항차 = 42일. 여유 있게 60일 설정
        end_date = start_date + timedelta(days=60)

        qdict = QueryDict(mutable=True)
        qdict.update(
            {
                "scenario_id": sample_schedule.scenario.id,
                "lane_code": sample_schedule.lane_code,
                "proforma_name": sample_schedule.proforma_name,
                "apply_start_date": start_date.strftime("%Y-%m-%d"),
                "apply_end_date": end_date.strftime("%Y-%m-%d"),
            }
        )
        qdict.setlist("vessel_code[]", ["V_DT_TEST"])
        qdict.setlist("vessel_start_date[]", [start_date.strftime("%Y-%m-%d")])
        qdict.setlist("vessel_capacity[]", ["5000"])
        qdict.setlist("lane_code_list[]", ["TEST_LANE"])

        # When
        lrs_service.create_lrs(qdict, user)

        # Then
        lrs_qs = LongRangeSchedule.objects.filter(vessel_code="V_DT_TEST").order_by(
            "etb"
        )

        # 첫 번째 항차와 두 번째 항차의 동일 포트(Seq 1) 비교
        # sample_schedule은 포트가 1개(Seq 1)만 존재할 수도 있으므로 fixture 확인 필요하나,
        # fixture 정의상 KRPUS(Seq 1) 하나만 있어도 비교 가능.
        voy1 = lrs_qs.filter(voyage_number="0001", calling_port_seq=1).first()
        voy2 = lrs_qs.filter(voyage_number="0002", calling_port_seq=1).first()

        assert voy1 and voy2, "Voyage 0001과 0002가 모두 생성되어야 합니다."

        # 차이가 Duration(14일)과 같아야 함
        diff = voy2.etb - voy1.etb

        # float 오차 및 시간대 차이 고려하여 1일 이내 오차 허용
        assert (
            abs(diff.days - 14) <= 1
        ), f"날짜 차이는 14일이어야 합니다. 실제: {diff.days}"

    def test_lrs_svc_dup_prevention(self, lrs_service, pf_complex_data, user):
        """[LRS_SVC_DUP] 동일 선박 중복 입력 시 처리"""
        # Given
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=20)

        qdict = QueryDict(mutable=True)
        qdict.update(
            {
                "scenario_id": pf_complex_data.id,
                "lane_code": "TEST_LANE",
                "proforma_name": "PF_COMPLEX",
                "apply_start_date": start_date.strftime("%Y-%m-%d"),
                "apply_end_date": end_date.strftime("%Y-%m-%d"),
            }
        )

        # TypeError 방지를 위해 datetime 객체를 문자열로 변환하여 전달
        date_str = start_date.strftime("%Y-%m-%d")

        # 동일 선박 코드를 2번 전송
        qdict.setlist("vessel_code[]", ["V_DUP", "V_DUP"])
        qdict.setlist("vessel_start_date[]", [date_str, date_str])
        qdict.setlist("vessel_capacity[]", ["5000", "5000"])
        qdict.setlist("lane_code_list[]", ["TEST_LANE", "TEST_LANE"])

        # When
        lrs_service.create_lrs(qdict, user)

        # Then
        # 특정 Voyage/Seq 데이터가 1개만 존재해야 함 (Unique Constraint or Logic check)
        # Voyage 0001의 Calling Port Seq 2 (Real Port) 확인
        count = LongRangeSchedule.objects.filter(
            vessel_code="V_DUP", voyage_number="0001", calling_port_seq=2
        ).count()

        assert count == 1, "중복 입력된 선박은 한 번만 생성되어야 합니다."


@pytest.mark.django_db
class TestLongRangeServiceMissingScenarios:
    """
    [LRS_SVC_002, LRS_SVC_MID_Y] 보완 시나리오 테스트
    """

    def test_lrs_svc_002_validation_duration_zero(
        self, lrs_service, pf_complex_data, user
    ):
        """[LRS_SVC_002] Validation 예외 (Duration 0)"""
        start_date = timezone.now().date()

        # 1. Given: Duration이 0이 되도록 Proforma 데이터 강제 조작
        ProformaSchedule.objects.filter(proforma_name="PF_COMPLEX").update(duration=0)

        qdict = QueryDict(mutable=True)
        qdict.update(
            {
                "scenario_id": pf_complex_data.id,
                "lane_code": "TEST_LANE",
                "proforma_name": "PF_COMPLEX",
                "apply_start_date": start_date.strftime("%Y-%m-%d"),
                "apply_end_date": (start_date + timedelta(days=30)).strftime(
                    "%Y-%m-%d"
                ),
            }
        )
        qdict.setlist("vessel_code[]", ["V_ERR"])
        qdict.setlist("vessel_start_date[]", [start_date.strftime("%Y-%m-%d")])

        # 2. When & Then: create_lrs 호출 시 ValueError가 발생해야 함
        with pytest.raises(ValueError) as exc_info:
            lrs_service.create_lrs(qdict, user)

        assert "Invalid Proforma Duration" in str(exc_info.value) or "0" in str(
            exc_info.value
        )
        # 데이터가 생성되지 않아야 함
        assert not LongRangeSchedule.objects.filter(vessel_code="V_ERR").exists()

    def test_lrs_svc_mid_y_virtual_port(self, lrs_service, pf_complex_data, user):
        """[LRS_SVC_MID_Y] 가상 포트 생성 (Middle Y)"""
        start_date = timezone.now().date()

        # 1. Given: N -> Y -> N 형태의 ProformaSchedule 생성
        ProformaSchedule.objects.create(
            scenario=pf_complex_data,
            lane_code="LANE_MID",
            proforma_name="PF_MID_Y",
            effective_from_date=timezone.now(),
            terminal_code="PORT_A01",
            declared_count=2,
            duration=10.0,
            etb_day_code="SUN",
            etb_day_time="0800",
            etb_day_number=0,
            port_code="PORT_A",
            calling_port_seq=1,
            direction="E",
            turn_port_info_code="N",
            created_by=user,
            updated_by=user,
        )
        ProformaSchedule.objects.create(  # 중간 Y 포트 (환적항 등)
            scenario=pf_complex_data,
            lane_code="LANE_MID",
            proforma_name="PF_MID_Y",
            effective_from_date=timezone.now(),
            terminal_code="PORT_B01",
            declared_count=2,
            duration=10.0,
            etb_day_code="MON",
            etb_day_time="0800",
            etb_day_number=0,
            port_code="PORT_B",
            calling_port_seq=2,
            direction="E",
            turn_port_info_code="Y",
            created_by=user,
            updated_by=user,
        )
        ProformaSchedule.objects.create(
            scenario=pf_complex_data,
            lane_code="LANE_MID",
            proforma_name="PF_MID_Y",
            effective_from_date=timezone.now(),
            declared_count=2,
            duration=10.0,
            calling_port_seq=3,
            direction="W",
            turn_port_info_code="N",
            etb_day_code="SAT",
            etb_day_time="0800",
            etb_day_number=0,
            port_code="PORT_C",
            terminal_code="PORT_C01",
            created_by=user,
            updated_by=user,
        )

        qdict = QueryDict(mutable=True)
        qdict.update(
            {
                "scenario_id": pf_complex_data.id,
                "lane_code": "LANE_MID",
                "proforma_name": "PF_MID_Y",
                "apply_start_date": start_date.strftime("%Y-%m-%d"),
                "apply_end_date": (start_date + timedelta(days=15)).strftime(
                    "%Y-%m-%d"
                ),
            }
        )
        qdict.setlist("vessel_code[]", ["V_MID"])
        qdict.setlist("vessel_start_date[]", [start_date.strftime("%Y-%m-%d")])

        # 2. When
        lrs_service.create_lrs(qdict, user)

        # 3. Then: PORT_B(Seq=2)에 대해 정방향(E)과 역방향(W) 데이터가 모두 생성되었는지 확인
        mid_ports = LongRangeSchedule.objects.filter(
            vessel_code="V_MID", port_code="PORT_B", voyage_number="0001"
        )

        assert mid_ports.count() == 2  # 실제 + 가상 포트
        directions = set(mid_ports.values_list("direction", flat=True))
        assert directions == {"E", "W"}  # 정방향과 역방향 모두 존재해야 함
