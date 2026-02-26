import pytest

from django.contrib.auth.models import User
from django.utils import timezone

from input_data.models import (
    Distance,
    LongRangeSchedule,
    ProformaSchedule,
    ProformaScheduleDetail,
    ScenarioInfo,
)
from input_data.services.cascading_service import CascadingService
from input_data.services.long_range_service import LongRangeService
from input_data.services.proforma_service import ProformaService


# =========================================================
# User & Client Fixtures
# =========================================================
@pytest.fixture
def user(db):
    """일반 사용자 (test_user)"""
    return User.objects.create_user(username="test_user", password="password")


@pytest.fixture
def other_user(db):
    """다른 사용자 (other_user) - 권한 테스트용"""
    return User.objects.create_user(username="other_user", password="password")


@pytest.fixture
def admin_user(db):
    """관리자 (admin_user) - 슈퍼유저 권한 테스트용"""
    return User.objects.create_superuser(username="admin_user", password="password")


@pytest.fixture
def auth_client(client, user):
    """로그인된 Client"""
    client.login(username="test_user", password="password")
    return client


# =========================================================
# Scenario & Proforma Fixtures
# =========================================================
@pytest.fixture
def base_scenario(db, user):
    """기본 시나리오 (데이터 없음)"""
    return ScenarioInfo.objects.create(
        name="Base Test Scenario",
        description="Base Test Scenario for testing",
        base_year_month="202602",
        scenario_type="BASELINE",
        status="ACTIVE",
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def scenario_with_data(db, user):
    """하위 데이터가 포함된 시나리오"""
    # 1. 부모 생성 (Scenario)
    scenario = ScenarioInfo.objects.create(
        name="Scenario With Test Data",
        description="Scenario for Cascade Test",
        base_year_month="202602",
        scenario_type="WHAT_IF",
        status="ACTIVE",
        created_by=user,
        updated_by=user,
    )

    # 2. 자식 생성 (Proforma Master)
    master = ProformaSchedule.objects.create(
        scenario=scenario,
        lane_code="TEST_LANE",
        proforma_name="PF_DATA",
        effective_from_date=timezone.now(),
        duration=40.0,
        declared_capacity="10000",
        declared_count=1,
        created_by=user,
        updated_by=user,
    )

    # 3. 손자 생성 (Proforma Detail)
    ProformaScheduleDetail.objects.create(
        proforma=master,
        direction="E",
        port_code="KRPUS",
        calling_port_indicator="1",
        calling_port_seq=1,
        turn_port_info_code="N",
        etb_day_code="SUN",
        etb_day_time="0800",
        etb_day_number=0,
        etd_day_code="MON",
        etd_day_time="0800",
        etd_day_number=1,
        terminal_code="PNC",
        created_by=user,
        updated_by=user,
    )
    return scenario


@pytest.fixture
def sample_schedule(db, base_scenario, user):
    """
    테스트용 단일 Proforma Schedule 데이터 (상세 조회용)
    """
    # 1. Master 생성
    master = ProformaSchedule.objects.create(
        scenario=base_scenario,
        lane_code="TEST_LANE",
        proforma_name="PF_001",
        effective_from_date=timezone.now(),
        duration=14.0,
        declared_capacity="5000",
        declared_count=2,
        created_by=user,
        updated_by=user,
    )

    # 2. Detail 생성
    ProformaScheduleDetail.objects.create(
        proforma=master,
        direction="E",
        port_code="KRPUS",
        calling_port_indicator="1",
        calling_port_seq=1,
        turn_port_info_code="N",
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

    return master


@pytest.fixture
def pf_complex_data(db, base_scenario, user):
    """
    복합 로직 테스트를 위한 Proforma 데이터
    - Port A (Seq 1): Head Y (가상 포트 생성 대상)
    - Port B (Seq 2): N
    - Port C (Seq 3): Tail Y (로직상 가상 포트 생성 안 함)
    """

    # 1. Master 생성
    master = ProformaSchedule.objects.create(
        scenario=base_scenario,
        lane_code="TEST_LANE",
        proforma_name="PF_COMPLEX",
        effective_from_date=timezone.now(),
        duration=14.0,  # Round Trip 14일
        declared_capacity="5000",
        declared_count=2,
        created_by=user,
        updated_by=user,
    )

    # Detail 공통 데이터
    common_detail_data = {
        "proforma": master,
        "direction": "E",
        "created_by": user,
        "updated_by": user,
        "pilot_in_hours": 1.0,
        "actual_work_hours": 10.0,
    }

    # 1. Start Port (Head Y)
    ProformaScheduleDetail.objects.create(
        **common_detail_data,
        port_code="PORT_A",
        calling_port_indicator="1",
        calling_port_seq=1,
        turn_port_info_code="Y",  # Head Virtual O
        etb_day_number=0,
        etd_day_number=0.5,
    )

    # 2. Middle Port (N)
    ProformaScheduleDetail.objects.create(
        **common_detail_data,
        port_code="PORT_B",
        calling_port_indicator="2",
        calling_port_seq=2,
        turn_port_info_code="N",
        etb_day_number=2,
        etd_day_number=2.5,
    )

    # 3. End Port (Tail Y) -> 마지막 포트이므로 Y여도 Virtual X
    ProformaScheduleDetail.objects.create(
        **common_detail_data,
        port_code="PORT_C",
        calling_port_indicator="3",
        calling_port_seq=3,
        turn_port_info_code="Y",
        etb_day_number=5,
        etd_day_number=5.5,
    )

    return base_scenario


# =========================================================
# Long Range Schedule (Integration) Fixtures
# =========================================================
@pytest.fixture
def lrs_integration_data(db, user):
    """[추가됨] LRS 통합 테스트용 공통 데이터"""
    scenario = ScenarioInfo.objects.create(
        name="Integration Test Scenario",
        description="Integration Test",
        scenario_type="WHAT_IF",
        status="ACTIVE",
        created_by=user,
    )
    # - Lane A에는 'VESSEL_A' 배정
    LongRangeSchedule.objects.create(
        scenario=scenario,
        lane_code="LANE_A",
        vessel_code="VESSEL_A",
        voyage_number="0001",
        direction="E",
        port_code="PUS",
        calling_port_seq=1,
        etb=timezone.now(),
        created_by=user,
        updated_by=user,
    )
    # - Lane B에는 'VESSEL_B' 배정
    LongRangeSchedule.objects.create(
        scenario=scenario,
        lane_code="LANE_B",
        vessel_code="VESSEL_B",
        voyage_number="0001",
        direction="E",
        port_code="TYO",
        calling_port_seq=1,
        etb=timezone.now(),
        created_by=user,
        updated_by=user,
    )

    return scenario


@pytest.fixture
def distance_data(db, base_scenario):
    """거리 테이블 기초 데이터"""
    return Distance.objects.create(
        scenario=base_scenario,
        from_port_code="KRPUS",
        to_port_code="JPTYO",
        distance=500,
        eca_distance=100,
    )


@pytest.fixture
def proforma_service():
    """ProformaService 인스턴스"""
    return ProformaService()


@pytest.fixture
def cascading_service():
    return CascadingService()


@pytest.fixture
def lrs_service():
    return LongRangeService()
