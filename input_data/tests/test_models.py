from datetime import datetime

import pytest

from django.db.utils import IntegrityError
from django.utils import timezone

from input_data.models import (
    CascadingSchedule,
    CascadingScheduleDetail,
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
        [관련 시나리오] INPUT_SCENARIO_CREATE_001
        설명: 시나리오 생성 시 Default 값(Status) 확인
        """
        assert base_scenario.id == "TEST_SCENARIO_001"
        assert base_scenario.status == "T"  # Default Value Check
        assert str(base_scenario) == "[TEST_SCENARIO_001] Base Test Scenario"

    def test_cascade_delete(self, scenario_with_data):
        """
        [관련 시나리오] INPUT_SCENARIO_DELETE_001
        설명: 부모(Scenario) 삭제 시 자식(ProformaSchedule)이 Cascade 삭제되는지 검증
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
        [관련 시나리오] PROFORMA_SAVE_FULL
        설명: Proforma Master 및 Detail 데이터 생성 시 FK 연결 완결성 확인
        """
        # When
        eff_from_date = timezone.make_aware(datetime(2026, 1, 1))

        # 1. Master 생성
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

        # 2. Detail 생성
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

        # Then
        # Master -> Scenario 연결 확인
        assert master.scenario == base_scenario
        assert master.scenario.id == "TEST_SCENARIO_001"

        # Detail -> Master 및 Scenario 연결 확인
        assert detail.proforma == master
        assert detail.proforma.scenario == base_scenario

    def test_master_unique_constraint(self, base_scenario, user):
        """
        [DB Integrity Check - Master]
        설명: 동일 시나리오 내 동일 Lane/Proforma Name 중복 생성 방지
        """
        # Given: 첫 번째 Master 데이터 생성
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

        # When & Then: 동일한 Key (scenario, lane_code, proforma_name) 조건으로 생성 시도
        with pytest.raises(IntegrityError):
            ProformaSchedule.objects.create(**common_master_data)

    def test_detail_unique_constraint(self, base_scenario, user):
        """
        [DB Integrity Check - Detail]
        설명: 동일 Proforma 내 동일 포트/방향/순서 중복 생성 방지
        """
        # Given: 부모 Master 생성
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

        # 첫 번째 Detail 데이터 생성
        ProformaScheduleDetail.objects.create(**common_detail_data)

        # When & Then: 동일한 Key (scenario, proforma, direction, port_code, calling_port_indicator) 조건으로 생성 시도
        with pytest.raises(IntegrityError):
            ProformaScheduleDetail.objects.create(**common_detail_data)


@pytest.mark.django_db
class TestCascadingModels:
    """[신규] CascadingSchedule 관련 모델 무결성 테스트"""

    def test_cascading_unique_constraint(self, sample_schedule, user):
        """동일한 Proforma에 동일한 cascading_seq 중복 생성 방지"""
        CascadingSchedule.objects.create(
            scenario=sample_schedule.scenario,
            proforma=sample_schedule,
            cascading_seq=1,
            own_vessels=1,
            start_date=timezone.now().date(),
            created_by=user,
        )
        with pytest.raises(IntegrityError):
            CascadingSchedule.objects.create(
                scenario=sample_schedule.scenario,
                proforma=sample_schedule,
                cascading_seq=1,
                own_vessels=2,
                start_date=timezone.now().date(),
                created_by=user,
            )

    def test_cascading_detail_unique_constraint(self, sample_schedule, user):
        """동일 Cascading 내 동일 선박(vessel_code) 중복 등록 방지"""
        cascading = CascadingSchedule.objects.create(
            scenario=sample_schedule.scenario,
            proforma=sample_schedule,
            cascading_seq=1,
            own_vessels=2,
            start_date=timezone.now().date(),
            created_by=user,
        )
        CascadingScheduleDetail.objects.create(
            cascading=cascading,
            vessel_code="VESSEL_1",
            initial_start_date=timezone.now().date(),
            created_by=user,
        )
        with pytest.raises(IntegrityError):
            CascadingScheduleDetail.objects.create(
                cascading=cascading,
                vessel_code="VESSEL_1",
                initial_start_date=timezone.now().date(),
                created_by=user,
            )
