from datetime import datetime

import pytest

from django.db.utils import IntegrityError
from django.utils import timezone

from input_data.models import (
    CascadingVesselPosition,
    ProformaSchedule,
    ProformaScheduleDetail,
    ScenarioInfo,
)


@pytest.mark.django_db
class TestScenarioModels:
    """
    ScenarioInfo 모델 및 관계성 테스트
    """

    def test_scenario_creation_defaults(self, base_scenario):
        """
        [MODEL_SCE_001] Scenario 모델 Default
        ScenarioInfo 생성 시 Default 값(status=ACTIVE) 및 ID 자동 할당 검증
        """
        assert base_scenario.code == "SC_TEST_BASE"
        assert base_scenario.status == "ACTIVE"  # Default Value Check
        assert base_scenario.id is not None  # ID가 자동 할당됨
        assert str(base_scenario) == f"SC_TEST_BASE (ID: {base_scenario.id})"

    def test_cascade_delete(self, scenario_with_data):
        """
        [MODEL_SCE_002] Scenario Cascade Delete
        Scenario 삭제 시 하위 ProformaSchedule이 Cascade 삭제되는지 검증
        """
        # Given: 부모와 자식 데이터가 존재함
        target_id = scenario_with_data.id
        assert ScenarioInfo.objects.filter(id=target_id).exists()
        assert ProformaSchedule.objects.filter(scenario=scenario_with_data).exists()

        # When: 부모 삭제
        scenario_with_data.delete()

        # Then: 자식 데이터도 DB에서 사라져야 함
        assert not ScenarioInfo.objects.filter(id=target_id).exists()
        assert not ProformaSchedule.objects.filter(scenario_id=target_id).exists()


@pytest.mark.django_db
class TestProformaModels:
    """
    ProformaSchedule (Master) 및 ProformaScheduleDetail (Detail) 모델 테스트
    """

    def test_proforma_creation_link(self, base_scenario, user):
        """
        [MODEL_PF_001] Proforma Master-Detail FK
        ProformaSchedule(Master)과 ProformaScheduleDetail(Detail) 생성 시 FK 연결 검증
        """
        eff_from_date = timezone.make_aware(datetime(2026, 1, 1))

        master = ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_code="TEST",
            proforma_name="PF_01",
            effective_from_date=eff_from_date,
            duration=10,
            declared_capacity="10k",
            declared_count=1,
            created_by=user,
        )

        detail = ProformaScheduleDetail.objects.create(
            proforma=master,
            direction="E",
            port_code="KRPUS",
            calling_port_indicator="1",
            calling_port_seq=1,
            turn_port_info_code="N",
            etb_day_number=0,
            etd_day_number=0,
            created_by=user,
        )

        assert master.scenario == base_scenario
        assert master.scenario.code == "SC_TEST_BASE"
        assert detail.proforma == master
        assert detail.proforma.scenario == base_scenario

    def test_master_unique_constraint(self, base_scenario, user):
        """
        [MODEL_PF_002] Proforma Master Unique
        동일 시나리오 내 동일 Lane/Proforma Name 중복 생성 시 IntegrityError 발생 검증
        """
        common_master_data = {
            "scenario": base_scenario,
            "lane_code": "TEST_LANE",
            "proforma_name": "PF_DUP_TEST",
            "effective_from_date": timezone.now(),
            "duration": 10,
            "declared_capacity": 5000,
            "declared_count": 2,
            "created_by": user,
        }

        ProformaSchedule.objects.create(**common_master_data)

        with pytest.raises(IntegrityError):
            ProformaSchedule.objects.create(**common_master_data)

    def test_detail_unique_constraint(self, base_scenario, user):
        """
        [MODEL_PF_003] Proforma Detail Unique
        동일 Proforma 내 동일 포트/방향/순서 중복 생성 시 IntegrityError 발생 검증
        """
        master = ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_code="TEST_LANE",
            proforma_name="PF_DETAIL_TEST",
            effective_from_date=timezone.now(),
            duration=14.0,
            declared_capacity="5000",
            declared_count=2,
            created_by=user,
        )

        common_detail_data = {
            "proforma": master,
            "direction": "E",
            "port_code": "KRPUS",
            "calling_port_indicator": "1",
            "calling_port_seq": 1,
            "etb_day_number": 0,
            "created_by": user,
        }

        ProformaScheduleDetail.objects.create(**common_detail_data)

        with pytest.raises(IntegrityError):
            ProformaScheduleDetail.objects.create(**common_detail_data)


@pytest.mark.django_db
class TestCascadingVesselPositionModels:
    """
    CascadingVesselPosition 모델 테스트
    """

    def test_cascading_position_creation(self, sample_schedule, user):
        """
        [MODEL_CVP_001] CascadingVesselPosition 생성
        생성 시 필드 값 및 __str__ 출력 검증
        """
        position = CascadingVesselPosition.objects.create(
            scenario=sample_schedule.scenario,
            proforma=sample_schedule,
            vessel_code="V001",
            vessel_position=1,
            vessel_position_date=timezone.now().date(),
            created_by=user,
            updated_by=user,
        )

        assert position.vessel_code == "V001"
        assert position.vessel_position == 1
        assert position.vessel_position_date is not None
        assert position.scenario == sample_schedule.scenario
        assert position.proforma == sample_schedule
        assert (
            str(position)
            == f"[{sample_schedule.scenario.id}] {sample_schedule.proforma_name} - Pos1: V001"
        )

    def test_cascading_position_query(self, cascading_with_details):
        """
        [MODEL_CVP_002] CascadingVesselPosition 조회
        fixture에서 생성된 Position 데이터 검증
        """
        first_pos = cascading_with_details[0]
        positions = CascadingVesselPosition.objects.filter(
            scenario=first_pos.scenario, proforma=first_pos.proforma
        )

        assert positions.count() == 2

        for pos in positions:
            assert pos.vessel_code in ["V001", "V002"]
            assert pos.vessel_position_date is not None

    def test_cascading_position_unique_constraint(self, sample_schedule, user):
        """
        [MODEL_CVP_003] CascadingVesselPosition Unique
        동일 scenario+proforma+vessel_position 중복 생성 시 IntegrityError 발생 검증
        """
        CascadingVesselPosition.objects.create(
            scenario=sample_schedule.scenario,
            proforma=sample_schedule,
            vessel_code="V001",
            vessel_position=1,
            vessel_position_date=timezone.now().date(),
            created_by=user,
        )

        with pytest.raises(IntegrityError):
            CascadingVesselPosition.objects.create(
                scenario=sample_schedule.scenario,
                proforma=sample_schedule,
                vessel_code="V002",
                vessel_position=1,  # 동일 position
                vessel_position_date=timezone.now().date(),
                created_by=user,
            )

    def test_cascading_position_cascade_delete(self, cascading_with_details):
        """
        [MODEL_CVP_004] Scenario Cascade Delete
        Scenario 삭제 시 CascadingVesselPosition도 함께 삭제되는지 검증
        """
        first_pos = cascading_with_details[0]
        scenario = first_pos.scenario
        scenario_id = scenario.id

        assert (
            CascadingVesselPosition.objects.filter(scenario_id=scenario_id).count() == 2
        )

        scenario.delete()

        assert (
            CascadingVesselPosition.objects.filter(scenario_id=scenario_id).count() == 0
        )
