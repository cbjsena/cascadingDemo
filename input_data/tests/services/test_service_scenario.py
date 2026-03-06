import pytest

from django.contrib.auth import get_user_model
from django.utils import timezone

from input_data.models import (
    BaseCascadingSchedule,
    BaseCascadingVesselPosition,
    BaseProformaSchedule,
    BaseVesselCapacity,
    BaseVesselInfo,
    CascadingSchedule,
    CascadingVesselPosition,
    ProformaSchedule,
    ProformaScheduleDetail,
    VesselCapacity,
    VesselInfo,
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
            lane_id="LANE_A",
            proforma_name="PF_01",
            direction="E",
            port_id="PORT_1",
            calling_port_indicator="1",
            calling_port_seq=1,
            effective_from_date=now,
            duration=10,
            declared_capacity="1000",
            declared_count=1,
            turn_port_info_code="N",
            etb_day_number=1,
            etb_day_code="MON",
            etb_day_time="1000",
            terminal_code="PORT_101",
        )
        BaseProformaSchedule.objects.create(
            lane_id="LANE_A",
            proforma_name="PF_01",
            direction="W",
            port_id="PORT_2",
            calling_port_indicator="2",
            calling_port_seq=2,
            effective_from_date=now,
            duration=10,
            declared_capacity="1000",
            declared_count=1,
            turn_port_info_code="Y",
            etb_day_number=2,
            etb_day_code="TUE",
            etb_day_time="1000",
            terminal_code="PORT_201",
        )

    @pytest.fixture
    def setup_base_general_data(self):
        """일반 Base 테이블 데이터 셋업 (Master-Detail 분리가 없는 테이블들)"""
        BaseVesselInfo.objects.create(
            vessel_code="V001", vessel_name="Test Vessel 1", own_yn="O"
        )
        BaseVesselInfo.objects.create(
            vessel_code="V002", vessel_name="Test Vessel 2", own_yn="C"
        )

        BaseVesselCapacity.objects.create(
            trade_id="ASIA",
            lane_id="FE1",
            vessel_code="V001",
            voyage_number="0001",
            direction="E",
            vessel_capacity=1000,
            reefer_capacity=100,
        )

    @pytest.fixture
    def setup_base_proforma_data(self):
        """BaseProformaSchedule 데이터 셋업 (Master-Detail 분리가 필요한 테이블)"""
        now = timezone.now()
        BaseProformaSchedule.objects.create(
            lane_id="FE1",
            proforma_name="3101",
            direction="E",
            port_id="KRPUS",
            calling_port_indicator="01",
            calling_port_seq=1,
            effective_from_date=now,
            duration=14.0,
            declared_capacity="1000",
            declared_count=5,
            turn_port_info_code="N",
            etb_day_number=0,
            etb_day_code="SUN",
            etb_day_time="0800",
            terminal_code="KRPUS01",
        )
        BaseProformaSchedule.objects.create(
            lane_id="FE1",
            proforma_name="3101",
            direction="E",
            port_id="USLAX",
            calling_port_indicator="01",
            calling_port_seq=2,
            effective_from_date=now,
            duration=14.0,
            declared_capacity="1000",
            declared_count=5,
            turn_port_info_code="N",
            etb_day_number=7,
            etb_day_code="SUN",
            etb_day_time="0600",
            terminal_code="USLAX01",
        )

    @pytest.fixture
    def setup_base_cascading_data(self, setup_base_proforma_data):
        """BaseCascadingVesselPosition 데이터 셋업"""
        BaseCascadingVesselPosition.objects.create(
            lane_id="FE1",
            proforma_name="3101",
            vessel_code="V001",
            vessel_position=1,
            vessel_position_date="2026-02-15",
        )
        BaseCascadingVesselPosition.objects.create(
            lane_id="FE1",
            proforma_name="3101",
            vessel_code="V002",
            vessel_position=2,
            vessel_position_date="2026-02-22",
        )
        BaseCascadingVesselPosition.objects.create(
            lane_id="FE1",
            proforma_name="3101",
            vessel_code="V003",
            vessel_position=3,
            vessel_position_date="2026-03-01",
        )

    def test_sce_svc_001_general_tables_creation(self, setup_base_general_data, user):
        """
        [SCE_SVC_001] 시나리오 기본 생성 (일반 테이블)
        Master-Detail 분리가 없는 일반 테이블들이 Base에서 Scenario로 정상 복사되는지 검증
        """
        # When

        scenario, summary = create_scenario_from_base(
            description="Test Scenario 001", user=user
        )

        # Then: ScenarioInfo 생성 확인 (code는 자동 생성)
        assert scenario.code is not None
        assert scenario.code.startswith("SC")
        assert scenario.created_by == user

        # VesselInfo 1:1 복사 확인
        vessel_infos = VesselInfo.objects.filter(scenario=scenario)
        assert vessel_infos.count() == 2

        vessel_codes = list(vessel_infos.values_list("vessel_code", flat=True))
        assert "V001" in vessel_codes
        assert "V002" in vessel_codes

        # scenario FK 연결 확인
        for vessel_info in vessel_infos:
            assert vessel_info.scenario == scenario
            assert vessel_info.created_by == user

        # VesselCapacity 1:1 복사 확인
        vessel_capacities = VesselCapacity.objects.filter(scenario=scenario)
        assert vessel_capacities.count() == 1
        assert vessel_capacities.first().vessel_code == "V001"
        assert vessel_capacities.first().scenario == scenario

    def test_sce_svc_002_multiple_scenario_creation(self, setup_base_data, user):
        """[SCE_SVC_002] 여러 시나리오 생성 검증"""
        # Given: 첫 번째 생성
        first_scenario, _ = create_scenario_from_base(
            description="First Scenario", user=user
        )
        assert (
            ProformaScheduleDetail.objects.filter(
                proforma__scenario_id=first_scenario.id
            ).count()
            == 2
        )

        # Base 데이터 하나 추가
        BaseProformaSchedule.objects.create(
            lane_id="LANE_B",
            proforma_name="PF_02",
            direction="S",
            port_id="PORT_3",
            calling_port_indicator="1",
            calling_port_seq=1,
            effective_from_date=timezone.now(),
            duration=5,
            declared_capacity="500",
            declared_count=1,
            turn_port_info_code="N",
            etb_day_number=1,
            etb_day_code="WED",
            etb_day_time="1200",
            terminal_code="PORT_301",
        )

        # When: 두 번째 생성 (새로운 코드 생성)
        second_scenario, _ = create_scenario_from_base(
            description="Second Scenario", user=user
        )

        # Then: 두 시나리오 모두 존재하고 코드가 다름
        assert first_scenario.code != second_scenario.code
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
        scenario, summary = create_scenario_from_base(
            description="System Test Scenario", user=None
        )

        # Then
        system_user = User.objects.get(username="cascading")
        assert scenario.created_by == system_user

        # 생성된 Master 객체에도 시스템 유저가 들어갔는지 확인
        master = ProformaSchedule.objects.filter(scenario=scenario).first()
        assert master.created_by == system_user

    def test_sce_svc_004_proforma_master_detail_separation(
        self, setup_base_proforma_data, user
    ):
        """
        [SCE_SVC_004] Proforma Master-Detail 분리 검증
        BaseProformaSchedule Flat 데이터가 ProformaSchedule(Master)와 ProformaScheduleDetail로 정상 분리되는지 검증
        """
        # When
        scenario, summary = create_scenario_from_base(
            description="Test Scenario 004", user=user
        )

        # Then: Master 1건 생성 확인
        masters = ProformaSchedule.objects.filter(scenario=scenario)
        assert masters.count() == 1

        master = masters.first()
        assert master.lane_id == "FE1"
        assert master.proforma_name == "3101"
        assert master.declared_count == 5
        assert master.scenario == scenario
        assert master.created_by == user

        # Detail 2건 생성 확인
        details = ProformaScheduleDetail.objects.filter(proforma=master)
        assert details.count() == 2

        # Master-Detail FK 관계 확인
        for detail in details:
            assert detail.proforma == master
            assert detail.created_by == user

        # 기항지 데이터 확인
        port_codes = list(details.values_list("port_id", flat=True))
        assert "KRPUS" in port_codes
        assert "USLAX" in port_codes

        # Summary 결과 확인
        assert summary["sce_proforma_schedule"] == 1
        assert summary["sce_proforma_schedule_detail"] == 2

    def test_sce_svc_005_cascading_vessel_position_creation(
        self, setup_base_cascading_data, user
    ):
        """
        [SCE_SVC_005] Cascading Vessel Position 생성 검증
        BaseCascadingVesselPosition Flat 데이터가 CascadingVesselPosition으로 정상 복사되는지 검증
        """
        # When
        scenario, summary = create_scenario_from_base(
            description="Test Scenario 005", user=user
        )

        # Then: Position 3건 생성 확인
        positions = CascadingVesselPosition.objects.filter(scenario=scenario)
        assert positions.count() == 3

        # 각 position 검증
        for pos in positions:
            assert pos.scenario == scenario
            assert pos.created_by == user
            assert pos.vessel_position_date is not None

        # 선박 데이터 확인
        vessel_codes = list(positions.values_list("vessel_code", flat=True))
        assert "V001" in vessel_codes
        assert "V002" in vessel_codes
        assert "V003" in vessel_codes

        # vessel_position 순서 확인
        position_nums = list(
            positions.order_by("vessel_position").values_list(
                "vessel_position", flat=True
            )
        )
        assert position_nums == [1, 2, 3]

        # Summary 결과 확인
        assert summary["sce_schedule_cascading_vessel_position"] == 3

    def test_sce_svc_006_cascading_schedule_creation(
        self, setup_base_cascading_data, user
    ):
        """
        [SCE_SVC_006] Cascading Schedule Base 복사 검증
        BaseCascadingSchedule Flat 데이터가 CascadingSchedule로 정상 복사되는지 검증
        """

        # Given: BaseCascadingSchedule 데이터 추가 (BaseCascadingVesselPosition과 같은 proforma)
        BaseCascadingSchedule.objects.create(
            lane_id="FE1",
            proforma_name="3101",
            vessel_position=1,
            vessel_position_date="2026-02-15",
        )
        BaseCascadingSchedule.objects.create(
            lane_id="FE1",
            proforma_name="3101",
            vessel_position=3,
            vessel_position_date="2026-03-01",
        )

        # When
        scenario, summary = create_scenario_from_base(
            description="Test Scenario 006", user=user
        )

        # Then: CascadingSchedule 2건 생성
        schedules = CascadingSchedule.objects.filter(scenario=scenario)
        assert schedules.count() == 2

        # vessel_position, vessel_position_date가 Base 값 그대로 복사됨
        schedule_positions = list(
            schedules.order_by("vessel_position").values_list(
                "vessel_position", flat=True
            )
        )
        assert schedule_positions == [1, 3]

        for cs in schedules:
            assert cs.scenario == scenario
            assert cs.proforma is not None
            assert cs.created_by == user
            assert cs.vessel_position_date is not None

        # Summary 결과 확인
        assert summary["sce_schedule_cascading"] == 2
