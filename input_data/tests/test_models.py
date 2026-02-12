from datetime import datetime

import pytest

from django.db.utils import IntegrityError
from django.utils import timezone

from input_data.models import ProformaSchedule, ScenarioInfo


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
    ProformaSchedule 모델 및 제약조건 테스트
    """

    def test_proforma_creation_link(self, base_scenario, user):
        """
        [관련 시나리오] PROFORMA_SAVE_FULL
        설명: Proforma 데이터 생성 시 Scenario와 FK 연결 확인
        """
        # When
        eff_from_date = timezone.make_aware(datetime(2026, 1, 1))

        pf = ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_code="TEST",
            proforma_name="PF_01",
            effective_from_date=eff_from_date,
            duration=10,
            declared_capacity="10k",
            declared_count=1,
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
        assert pf.scenario == base_scenario
        assert pf.scenario.id == "TEST_SCENARIO_001"

    def test_unique_constraint(self, base_scenario, user):
        """
        [DB Integrity Check]
        설명: 동일 시나리오 내 동일 포트/순서 중복 생성 방지
        (테스트 시나리오에는 명시되지 않았으나 데이터 무결성을 위해 필수)
        """
        # Given: 첫 번째 데이터 생성
        eff_date = timezone.now()

        common_data = {
            "scenario": base_scenario,
            "lane_code": "TEST",
            "proforma_name": "PF_01",
            "effective_from_date": eff_date,
            "duration": 10,
            "declared_capacity": "10k",
            "declared_count": 1,
            "direction": "E",
            "port_code": "KRPUS",
            "calling_port_indicator": "1",  # Key Factor
            "calling_port_seq": 1,
            "turn_port_info_code": "N",
            "etb_day_number": 0,
            "etd_day_number": 0,
            "created_by": user,
        }

        ProformaSchedule.objects.create(**common_data)

        # When & Then: 동일한 Key 조건으로 생성 시도 시 IntegrityError 발생
        with pytest.raises(IntegrityError):
            ProformaSchedule.objects.create(**common_data)
