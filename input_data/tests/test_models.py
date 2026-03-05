from datetime import datetime, timedelta

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
        [MODEL_SCE_001] Scenario 모델 Default
        ScenarioInfo 생성 시 Default 값(status=ACTIVE) 및 ID 자동 할당 검증
        """
        assert base_scenario.name == "Base Test Scenario"
        assert base_scenario.status == "ACTIVE"  # Default Value Check
        assert base_scenario.id is not None  # ID가 자동 할당됨
        assert str(base_scenario) == f"Base Test Scenario (ID: {base_scenario.id})"

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
        assert master.scenario.name == "Base Test Scenario"

        # Detail -> Master 및 Scenario 연결 확인
        assert detail.proforma == master
        assert detail.proforma.scenario == base_scenario

    def test_master_unique_constraint(self, base_scenario, user):
        """
        [MODEL_PF_002] Proforma Master Unique
        동일 시나리오 내 동일 Lane/Proforma Name 중복 생성 시 IntegrityError 발생 검증
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
        [MODEL_PF_003] Proforma Detail Unique
        동일 Proforma 내 동일 포트/방향/순서 중복 생성 시 IntegrityError 발생 검증
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
    """
    CascadingSchedule 및 CascadingScheduleDetail 모델 테스트
    """

    def test_cascading_model_creation(self, sample_schedule, user):
        """
        [MODEL_CAS_001] Cascading 모델 생성
        CascadingSchedule 생성 시 필드 값 및 __str__ 출력 검증
        """
        # Given & When: CascadingSchedule 생성
        cascading = CascadingSchedule.objects.create(
            scenario=sample_schedule.scenario,
            proforma=sample_schedule,
            cascading_seq=1,
            proforma_start_etb_date=timezone.now().date(),
            effective_start_date=timezone.now().date(),
            effective_end_date=timezone.now().date() + timedelta(days=365),
            created_by=user,
            updated_by=user,
        )

        # ProformaSchedule에 own_vessel_count 설정
        sample_schedule.own_vessel_count = 3
        sample_schedule.save(update_fields=["own_vessel_count"])

        # Then: 필드 검증
        assert cascading.cascading_seq == 1
        assert sample_schedule.own_vessel_count == 3
        assert cascading.proforma_start_etb_date is not None
        assert cascading.scenario == sample_schedule.scenario
        assert cascading.proforma == sample_schedule
        assert (
            str(cascading)
            == f"[{sample_schedule.scenario.id}] {sample_schedule.proforma_name} - Seq 1"
        )

    def test_cascading_detail_creation(self, cascading_with_details):
        """
        [MODEL_CAS_002] Cascading Detail 생성 및 FK
        CascadingScheduleDetail 생성 시 Master와의 FK 관계 검증
        """
        # Given: cascading_with_details fixture에서 생성된 데이터
        details = CascadingScheduleDetail.objects.filter(
            cascading=cascading_with_details
        )

        # Then: Detail 데이터 검증
        assert details.count() == 2

        for detail in details:
            assert detail.cascading == cascading_with_details
            assert detail.vessel_code in ["V001", "V002"]
            assert detail.initial_start_date is not None

    def test_cascading_unique_constraint(self, sample_schedule, user):
        """
        [MODEL_CAS_003] Cascading Unique
        동일 proforma+seq 조합 중복 생성 시 IntegrityError 발생 검증
        """
        # Given: 첫 번째 Cascading 생성
        CascadingSchedule.objects.create(
            scenario=sample_schedule.scenario,
            proforma=sample_schedule,
            cascading_seq=1,
            proforma_start_etb_date=timezone.now().date(),
            effective_start_date=timezone.now().date(),
            created_by=user,
        )

        # When & Then: 동일한 proforma + seq 조합으로 중복 생성 시도
        with pytest.raises(IntegrityError):
            CascadingSchedule.objects.create(
                scenario=sample_schedule.scenario,
                proforma=sample_schedule,
                cascading_seq=1,  # 동일한 seq
                proforma_start_etb_date=timezone.now().date(),
                effective_start_date=timezone.now().date(),
                created_by=user,
            )

    def test_cascading_detail_unique_constraint(self, cascading_with_details, user):
        """
        [MODEL_CAS_004] Cascading Detail Unique
        동일 cascading+vessel_code 중복 생성 시 IntegrityError 발생 검증
        """
        # When & Then: 동일한 cascading + vessel_code 조합으로 중복 생성 시도
        with pytest.raises(IntegrityError):
            CascadingScheduleDetail.objects.create(
                cascading=cascading_with_details,
                vessel_code="V001",  # 이미 존재하는 vessel_code
                initial_start_date=timezone.now().date(),
                created_by=user,
            )

    def test_cascading_cascade_delete(self, cascading_with_details):
        """
        [MODEL_CAS_005] Cascading Cascade Delete
        CascadingSchedule 삭제 시 Detail 데이터도 함께 삭제되는지 검증
        """
        # Given: Detail 데이터 존재 확인
        detail_count = CascadingScheduleDetail.objects.filter(
            cascading=cascading_with_details
        ).count()
        assert detail_count == 2

        # When: Master 삭제
        cascading_with_details.delete()

        # Then: Detail 데이터도 함께 삭제됨
        remaining_details = CascadingScheduleDetail.objects.filter(
            cascading_id=cascading_with_details.id
        ).count()
        assert remaining_details == 0
