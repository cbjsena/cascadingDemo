import os
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.utils import timezone

import pytest

from common import constants
from input_data.models import (
    BaseWeekPeriod,
    CascadingVesselPosition,
    Distance,
    LaneProformaMapping,
    LongRangeSchedule,
    MasterLane,
    MasterPort,
    MasterTrade,
    ProformaSchedule,
    ProformaScheduleDetail,
    ScenarioInfo,
)
from input_data.services.cascading_service import CascadingService
from input_data.services.long_range_service import LongRangeService
from input_data.services.proforma_service import ProformaService


def pytest_configure(config):
    """로컬 환경일 때 마이그레이션을 생략하여 테스트 속도 향상"""
    if os.getenv("APP_ENV") == "local":
        config.option.nomigrations = True


# =========================================================
# 1. Master Data Fixtures (FK 참조 대상)
# =========================================================
@pytest.fixture(autouse=True)
def master_data(db):
    """
    모든 테스트에서 자동으로 생성되는 Master 데이터.
    API 앱과 input_data 앱에서 사용하는 모든 Lane, Port, Trade 코드를 통합 포함.
    """
    # Lanes
    lanes = [
        "TEST_LANE",
        "TEST",
        "FE1",
        "FP1",
        "LANE_A",
        "LANE_B",
        "LANE_X",
        "OTHER",
        "LANE_MID",
        "LANE_DUR0",
        "TEST_SAVE",
        "SVC_TEST",
        "UP_LANE",
    ]
    for code in lanes:
        MasterLane.objects.get_or_create(lane_code=code, defaults={"lane_name": code})

    # Ports
    ports = [
        "KRPUS",
        "JPTYO",
        "USLAX",
        "SGSIN",
        "PUS",
        "TYO",
        "LAX",
        "PORT_A",
        "PORT_B",
        "PORT_C",
        "PORT_1",
        "PORT_2",
        "PORT_3",
        "PORT_X",
        "A",
        "B",
        "C",
        "UP_PORT",
    ]
    for code in ports:
        MasterPort.objects.get_or_create(port_code=code, defaults={"port_name": code})

    # Trades
    trades = ["ASIA", "TPT", "NET"]
    for code in trades:
        MasterTrade.objects.get_or_create(
            trade_code=code, defaults={"trade_name": code}
        )

    # 주차(Week Period) 마스터 생성 로직
    BaseWeekPeriod.objects.filter(base_year__in=["2026", "2027"]).delete()
    current_date = date(2026, 1, 5)  # 2026년 1월 5일 (월요일, 2026년 1주차 시작)

    for year in ["2026", "2027"]:
        for week_num in range(1, 53):
            week_end = current_date + timedelta(days=6)
            month = current_date.month

            BaseWeekPeriod.objects.create(
                base_year=year,
                base_week=f"{week_num:02d}",
                base_month=f"{month:02d}",
                week_start_date=current_date,
                week_end_date=week_end,
            )
            current_date += timedelta(weeks=1)


# =========================================================
# 2. User & Client Fixtures
# =========================================================
@pytest.fixture
def user(db):
    """일반 사용자"""
    return User.objects.create_user(username="test_user", password="password")


@pytest.fixture
def other_user(db):
    """다른 사용자 (권한 분리 테스트용)"""
    return User.objects.create_user(username="other_user", password="password")


@pytest.fixture
def admin_user(db):
    """관리자 사용자"""
    return User.objects.create_superuser(username="admin_user", password="password")


@pytest.fixture
def auth_client(client, user):
    """자동으로 로그인된 Client (API 테스트 및 뷰 테스트 범용)"""
    client.login(username="test_user", password="password")
    return client


# =========================================================
# 3. Scenario & Proforma Fixtures
# =========================================================
@pytest.fixture
def base_scenario(db, user):
    """
    기본 시나리오
    """
    return ScenarioInfo.objects.create(
        code="SC_TEST_BASE",  # 특정 코드를 명시하여 API 테스트와 호환되게 함
        description="Base Test Scenario for testing",
        base_year_week=constants.DEFAULT_BASE_YEAR_WEEK,
        planning_horizon_months=12,
        scenario_type="BASELINE",
        status="ACTIVE",
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def scenario_with_data(db, user):
    """하위 스케줄 데이터가 포함된 시나리오"""
    scenario = ScenarioInfo.objects.create(
        code="SC_TEST_DATA",
        description="Scenario for Cascade Test",
        base_year_week=constants.DEFAULT_BASE_YEAR_WEEK,
        scenario_type="WHAT_IF",
        status="ACTIVE",
        created_by=user,
        updated_by=user,
    )
    master = ProformaSchedule.objects.create(
        scenario=scenario,
        lane_id="TEST_LANE",
        proforma_name="PF_DATA",
        effective_from_date=timezone.now().date(),
        duration=40.0,
        declared_capacity="10000",
        declared_count=1,
        created_by=user,
        updated_by=user,
    )
    ProformaScheduleDetail.objects.create(
        proforma=master,
        direction="E",
        port_id="KRPUS",
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
    """테스트용 단일 Proforma Schedule 데이터 (상세 조회 및 Cascading용)"""
    master = ProformaSchedule.objects.create(
        scenario=base_scenario,
        lane_id="TEST_LANE",
        proforma_name="PF_001",
        effective_from_date=timezone.now().date(),
        duration=14.0,
        declared_capacity="5000",
        declared_count=2,
        own_vessel_count=2,
        created_by=user,
        updated_by=user,
    )
    ProformaScheduleDetail.objects.create(
        proforma=master,
        direction="E",
        port_id="KRPUS",
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
        lane_id="TEST_LANE",
        proforma_name="PF_COMPLEX",
        effective_from_date=timezone.now().date(),
        duration=14.0,
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
        port_id="PORT_A",
        calling_port_indicator="1",
        calling_port_seq=1,
        turn_port_info_code="Y",
        etb_day_number=0,
        etd_day_number=0.5,
    )

    # 2. Middle Port (N)
    ProformaScheduleDetail.objects.create(
        **common_detail_data,
        port_id="PORT_B",
        calling_port_indicator="2",
        calling_port_seq=2,
        turn_port_info_code="N",
        etb_day_number=2,
        etd_day_number=2.5,
    )

    # 3. End Port (Tail Y) -> 마지막 포트이므로 Y여도 Virtual X
    ProformaScheduleDetail.objects.create(
        **common_detail_data,
        port_id="PORT_C",
        calling_port_indicator="3",
        calling_port_seq=3,
        turn_port_info_code="Y",
        etb_day_number=5,
        etd_day_number=5.5,
    )
    return base_scenario


# =========================================================
# 4. LRS & Services & Distance Fixtures
# =========================================================
@pytest.fixture
def lrs_integration_data(db, user):
    """LRS 통합 테스트용 공통 데이터"""
    scenario = ScenarioInfo.objects.create(
        code="SC_LRS_TEST",
        description="Integration Test",
        scenario_type="WHAT_IF",
        status="ACTIVE",
        created_by=user,
    )

    # - Lane A에는 'VESSEL_A' 배정
    LongRangeSchedule.objects.create(
        scenario=scenario,
        lane_id="LANE_A",
        vessel_code="VESSEL_A",
        voyage_number="0001",
        direction="E",
        port_id="PUS",
        calling_port_seq=1,
        etb=timezone.now(),
        created_by=user,
        updated_by=user,
    )

    # - Lane B에는 'VESSEL_B' 배정
    LongRangeSchedule.objects.create(
        scenario=scenario,
        lane_id="LANE_B",
        vessel_code="VESSEL_B",
        voyage_number="0001",
        direction="E",
        port_id="TYO",
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
        from_port_id="KRPUS",
        to_port_id="JPTYO",
        distance=500,
        eca_distance=100,
    )


@pytest.fixture
def proforma_service():
    return ProformaService()


@pytest.fixture
def cascading_service():
    return CascadingService()


@pytest.fixture
def lrs_service():
    return LongRangeService()


# =========================================================
# 5. Cascading Data Fixtures
# =========================================================
@pytest.fixture
def cascading_with_details(db, sample_schedule, user):
    """
    Cascading Vessel Position 테스트 데이터
    IN_CV_DIS_003, IN_CV_DIS_005, IN_CV_DIS_011/002 등에서 사용
    ※ Position 수는 sample_schedule.declared_count(=2)를 초과하지 않도록 한다.
    """
    # Position 데이터 2건 (= sample_schedule.declared_count)
    vessels = ["V001", "V002"]
    positions = []
    for i, vessel_code in enumerate(vessels):
        pos = CascadingVesselPosition.objects.create(
            scenario=sample_schedule.scenario,
            proforma=sample_schedule,
            vessel_code=vessel_code,
            vessel_position=i + 1,
            vessel_position_date=timezone.now().date() + timedelta(days=i * 7),
            created_by=user,
            updated_by=user,
        )
        positions.append(pos)
    return positions


@pytest.fixture
def cascading_form_data(sample_schedule):
    """
    Cascading 생성/수정용 폼 데이터
    IN_CV_DIS_004, IN_CV_DIS_005, IN_CV_DIS_006 등에서 사용
    """
    return {
        "scenario_id": sample_schedule.scenario.id,
        "lane_code": sample_schedule.lane_id,
        "proforma_name": sample_schedule.proforma_name,
        "own_vessel_count": 3,
        "vessel_code[]": ["V001", "V002", "V003"],
        "vessel_capacity[]": ["5000", "5000", "5000"],
        "vessel_start_date[]": ["2026-02-15", "2026-02-22", "2026-03-01"],
        "lane_code_list[]": ["TEST_LANE", "TEST_LANE", "TEST_LANE"],
    }


@pytest.fixture
def cascading_invalid_form_data(sample_schedule):
    """
    Cascading 유효하지 않은 폼 데이터 (Own Vessels와 선박 수 불일치)
    IN_CV_DIS_007, IN_CV_DIS_009 등에서 사용
    """
    return {
        "scenario_id": sample_schedule.scenario.id,
        "lane_code": sample_schedule.lane_id,
        "proforma_name": sample_schedule.proforma_name,
        "own_vessel_count": 3,
        "vessel_code[]": ["V001", "V002"],
        "vessel_capacity[]": ["5000", "5000"],
        "vessel_start_date[]": ["2026-02-15", "2026-02-22"],
        "lane_code_list[]": ["TEST_LANE", "TEST_LANE"],
    }


@pytest.fixture
def multiple_cascading_data(db, base_scenario, user):
    """
    여러 Cascading 데이터 (Vessel Info 대시보드 조회 테스트용)
    IN_CV_DIS_010에서 사용
    - 2개의 Proforma, 각각 CascadingVesselPosition 2건씩 생성
    """
    all_positions = []
    for idx in range(2):
        proforma = ProformaSchedule.objects.create(
            scenario=base_scenario,
            lane_id="TEST_LANE",
            proforma_name=f"PF_MULTI_{idx+1}",
            effective_from_date=timezone.now().date(),
            duration=14.0,
            declared_capacity="5000",
            declared_count=2,
            own_vessel_count=2,
            created_by=user,
            updated_by=user,
        )
        for i in range(2):
            pos = CascadingVesselPosition.objects.create(
                scenario=base_scenario,
                proforma=proforma,
                vessel_code=f"V{idx+1}0{i+1}",
                vessel_position=i + 1,
                vessel_position_date=timezone.now().date() + timedelta(days=i * 7),
                created_by=user,
                updated_by=user,
            )
            all_positions.append(pos)
    return all_positions


# =========================================================
# 6. Lane Proforma Mapping Fixtures
# =========================================================
@pytest.fixture
def lane_proforma_scenario(db, user):
    """
    Lane Proforma Mapping 테스트용 시나리오 + 동일 Lane에 기간이 다른 Proforma 2개
    LPM_VIEW_*, LPM_ACT_*, LPM_LIST_* 테스트에서 사용
    """
    scenario = ScenarioInfo.objects.create(
        code="SC_LPM_TEST",
        description="Lane Proforma Mapping Test",
        base_year_week="202610",
        planning_horizon_months=12,
        scenario_type="WHAT_IF",
        status="ACTIVE",
        created_by=user,
        updated_by=user,
    )

    # 같은 Lane(TEST_LANE)에 기간이 다른 Proforma 2개
    pf1 = ProformaSchedule.objects.create(
        scenario=scenario,
        lane_id="TEST_LANE",
        proforma_name="6101",
        effective_from_date=date(2026, 1, 1),
        duration=14.0,
        declared_capacity="5000",
        declared_count=3,
        created_by=user,
        updated_by=user,
    )
    pf2 = ProformaSchedule.objects.create(
        scenario=scenario,
        lane_id="TEST_LANE",
        proforma_name="6102",
        effective_from_date=date(2026, 7, 2),
        duration=14.0,
        declared_capacity="6000",
        declared_count=4,
        created_by=user,
        updated_by=user,
    )
    pf3 = ProformaSchedule.objects.create(
        scenario=scenario,
        lane_id="FE1",
        proforma_name="7001",
        effective_from_date=date(2026, 3, 1),
        duration=21.0,
        declared_capacity="8000",
        declared_count=5,
        created_by=user,
        updated_by=user,
    )
    return {"scenario": scenario, "pf1": pf1, "pf2": pf2, "pf3": pf3}


@pytest.fixture
def lane_proforma_with_mapping(db, lane_proforma_scenario, user):
    """
    Lane Proforma Mapping이 저장된 상태
    pf1, pf2 모두 선택 (같은 Lane에 기간별 매핑)
    """
    data = lane_proforma_scenario
    m1 = LaneProformaMapping.objects.create(
        scenario=data["scenario"],
        lane_id="TEST_LANE",
        proforma=data["pf1"],
        is_active=True,
        created_by=user,
        updated_by=user,
    )
    m2 = LaneProformaMapping.objects.create(
        scenario=data["scenario"],
        lane_id="TEST_LANE",
        proforma=data["pf2"],
        is_active=True,
        created_by=user,
        updated_by=user,
    )
    m3 = LaneProformaMapping.objects.create(
        scenario=data["scenario"],
        lane_id="FE1",
        proforma=data["pf3"],
        is_active=True,
        created_by=user,
        updated_by=user,
    )
    data["mappings"] = [m1, m2, m3]
    return data
