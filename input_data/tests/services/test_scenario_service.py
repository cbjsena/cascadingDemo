import pytest

from django.contrib.auth import get_user_model
from django.utils import timezone

from input_data.models import (
    BaseProformaSchedule,
    ProformaSchedule,
    ProformaScheduleDetail,
    ScenarioInfo,
)
from input_data.services.scenario_service import create_scenario_from_base

User = get_user_model()


@pytest.mark.django_db
class TestScenarioCreationService:
    """
    create_scenario_from_base 서비스 로직 검증 (Master-Detail 분리 포함)
    """

    @pytest.fixture
    def setup_base_data(self):
        """테스트용 Base 데이터 셋업 (하나의 헤더에 2개의 기항지)"""
        now = timezone.now()
        BaseProformaSchedule.objects.create(
            lane_code="LANE_A",
            proforma_name="PF_01",
            direction="E",
            port_code="PORT_1",
            calling_port_indicator="1",
            calling_port_seq=1,
            effective_from_date=now,
            duration=10,
            declared_capacity=1000,
            declared_count=1,
            turn_port_info_code="N",
            etb_day_number=1,
            etb_day_code="MON",
            etb_day_time="1000",
        )
        BaseProformaSchedule.objects.create(
            lane_code="LANE_A",
            proforma_name="PF_01",
            direction="W",
            port_code="PORT_2",
            calling_port_indicator="2",
            calling_port_seq=2,
            effective_from_date=now,
            duration=10,
            declared_capacity=1000,
            declared_count=1,
            turn_port_info_code="Y",
            etb_day_number=2,
            etb_day_code="TUE",
            etb_day_time="1000",
        )

    def test_sce_svc_001_basic_creation(self, setup_base_data, user):
        """[SCE_SVC_001] 시나리오 기본 생성 및 Master-Detail 분리 검증"""
        # When
        scenario, summary = create_scenario_from_base("Test Scenario 001", user=user)

        # Then
        assert ScenarioInfo.objects.filter(name="Test Scenario 001").exists()

        # Master는 lane+proforma_name 단위로 1개만 생성되어야 함
        masters = ProformaSchedule.objects.filter(scenario=scenario)
        assert masters.count() == 1
        assert masters.first().lane_code == "LANE_A"

        # Detail은 2개가 생성되고, Master를 바라봐야 함
        details = ProformaScheduleDetail.objects.filter(proforma__scenario_id=scenario)
        assert details.count() == 2
        assert details.first().proforma == masters.first()

        # Summary 결과 확인
        assert summary["sce_proforma_schedule"] == 1
        assert summary["sce_proforma_schedule_detail"] == 2

    def test_sce_svc_002_overwrite_scenario(self, setup_base_data, user):
        """[SCE_SVC_002] 기존 시나리오 덮어쓰기 (Reset) 검증"""
        # Given: 첫 번째 생성
        first_scenario, _ = create_scenario_from_base("Test Scenario 002", user=user)
        assert (
            ProformaScheduleDetail.objects.filter(
                proforma__scenario_id=first_scenario.id
            ).count()
            == 2
        )

        # Base 데이터 하나 추가
        BaseProformaSchedule.objects.create(
            lane_code="LANE_B",
            proforma_name="PF_02",
            direction="S",
            port_code="PORT_3",
            calling_port_indicator="1",
            calling_port_seq=1,
            effective_from_date=timezone.now(),
            duration=5,
            declared_capacity=500,
            declared_count=1,
            turn_port_info_code="N",
            etb_day_number=1,
            etb_day_code="WED",
            etb_day_time="1200",
        )

        # When: 동일한 Name으로 두 번째 생성
        second_scenario, _ = create_scenario_from_base("Test Scenario 002", user=user)

        # Then: 기존 데이터는 사라지고 최신 Base 데이터 기준으로 재적재됨 (Master 2개, Detail 3개)
        assert (
            ProformaSchedule.objects.filter(scenario_id=second_scenario.id).count() == 2
        )
        assert (
            ProformaScheduleDetail.objects.filter(
                proforma__scenario_id=second_scenario.id
            ).count()
            == 3
        )

    def test_sce_svc_003_system_user_creation(self, setup_base_data):
        """[SCE_SVC_003] 시스템 유저 자동 할당 검증"""
        # When: user 없이 생성
        scenario, summary = create_scenario_from_base("System Test Scenario", user=None)

        # Then
        system_user = User.objects.get(username="cascading")
        assert scenario.created_by == system_user

        # 생성된 Master 객체에도 시스템 유저가 들어갔는지 확인
        master = ProformaSchedule.objects.filter(scenario=scenario).first()
        assert master.created_by == system_user
