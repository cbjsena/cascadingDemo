import pytest

from django.contrib.auth import get_user_model
from django.utils import timezone

from input_data.models import (
    BaseCascadingSchedule,
    BaseProformaSchedule,
    BaseVesselCapacity,
    BaseVesselInfo,
    CascadingSchedule,
    CascadingScheduleDetail,
    ProformaSchedule,
    ProformaScheduleDetail,
    ScenarioInfo,
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
            lane_code="LANE_A",
            proforma_name="PF_01",
            direction="E",
            port_code="PORT_1",
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
            lane_code="LANE_A",
            proforma_name="PF_01",
            direction="W",
            port_code="PORT_2",
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
            trade_code="ASIA",
            lane_code="FE1",
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
            lane_code="FE1",
            proforma_name="3101",
            direction="E",
            port_code="KRPUS",
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
            lane_code="FE1",
            proforma_name="3101",
            direction="E",
            port_code="USLAX",
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
        """BaseCascadingSchedule 데이터 셋업 (Master-Detail 분리가 필요한 테이블)"""
        BaseCascadingSchedule.objects.create(
            lane_code="FE1",
            proforma_name="3101",
            cascading_seq=1,
            own_vessel_count=3,
            effective_start_date="2026-02-01",
            effective_end_date="2027-02-01",
            vessel_code="V001",
            initial_start_date="2026-02-15",
        )
        BaseCascadingSchedule.objects.create(
            lane_code="FE1",
            proforma_name="3101",
            cascading_seq=1,
            own_vessel_count=3,
            effective_start_date="2026-02-01",
            effective_end_date="2027-02-01",
            vessel_code="V002",
            initial_start_date="2026-02-22",
        )
        BaseCascadingSchedule.objects.create(
            lane_code="FE1",
            proforma_name="3101",
            cascading_seq=1,
            own_vessel_count=3,
            effective_start_date="2026-02-01",
            effective_end_date="2027-02-01",
            vessel_code="V003",
            initial_start_date="2026-03-01",
        )

    def test_sce_svc_001_general_tables_creation(self, setup_base_general_data, user):
        """
        [SCE_SVC_001] 시나리오 기본 생성 (일반 테이블)
        Master-Detail 분리가 없는 일반 테이블들이 Base에서 Scenario로 정상 복사되는지 검증
        """
        # When
        scenario, summary = create_scenario_from_base("Test Scenario 001", user=user)

        # Then: ScenarioInfo 생성 확인
        assert ScenarioInfo.objects.filter(name="Test Scenario 001").exists()
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
            declared_capacity="500",
            declared_count=1,
            turn_port_info_code="N",
            etb_day_number=1,
            etb_day_code="WED",
            etb_day_time="1200",
            terminal_code="PORT_301",
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

    def test_sce_svc_004_proforma_master_detail_separation(
        self, setup_base_proforma_data, user
    ):
        """
        [SCE_SVC_004] Proforma Master-Detail 분리 검증
        BaseProformaSchedule Flat 데이터가 ProformaSchedule(Master)와 ProformaScheduleDetail로 정상 분리되는지 검증
        """
        # When
        scenario, summary = create_scenario_from_base("Test Scenario 004", user=user)

        # Then: Master 1건 생성 확인
        masters = ProformaSchedule.objects.filter(scenario=scenario)
        assert masters.count() == 1

        master = masters.first()
        assert master.lane_code == "FE1"
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
        port_codes = list(details.values_list("port_code", flat=True))
        assert "KRPUS" in port_codes
        assert "USLAX" in port_codes

        # Summary 결과 확인
        assert summary["sce_proforma_schedule"] == 1
        assert summary["sce_proforma_schedule_detail"] == 2

    def test_sce_svc_005_cascading_master_detail_separation(
        self, setup_base_cascading_data, user
    ):
        """
        [SCE_SVC_005] Cascading Master-Detail 분리 검증
        BaseCascadingSchedule Flat 데이터가 CascadingSchedule(Master)와 CascadingScheduleDetail로 정상 분리되는지 검증
        """
        # When
        scenario, summary = create_scenario_from_base("Test Scenario 005", user=user)

        # Then: Master 1건 생성 확인
        masters = CascadingSchedule.objects.filter(scenario=scenario)
        assert masters.count() == 1

        master = masters.first()
        assert master.cascading_seq == 1
        assert master.own_vessel_count == 3
        assert master.scenario == scenario
        assert master.created_by == user

        # proforma_start_etb_date 자동 계산 확인
        assert master.proforma_start_etb_date is not None

        # Detail 3건 생성 확인
        details = CascadingScheduleDetail.objects.filter(cascading=master)
        assert details.count() == 3

        # Master-Detail FK 관계 확인
        for detail in details:
            assert detail.cascading == master
            assert detail.created_by == user

        # 선박 데이터 확인
        vessel_codes = list(details.values_list("vessel_code", flat=True))
        assert "V001" in vessel_codes
        assert "V002" in vessel_codes
        assert "V003" in vessel_codes

        # Summary 결과 확인
        assert summary["sce_schedule_cascading"] == 1
        assert summary["sce_schedule_cascading_detail"] == 3
