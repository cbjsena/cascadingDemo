import pytest

from django.contrib.auth.models import User

from input_data.models import MasterLane, MasterPort, MasterTrade, ScenarioInfo

# =========================================================
# Master Data Fixtures (FK 참조 대상)
# =========================================================


@pytest.fixture(autouse=True)
def master_data(db):
    """FK 참조 무결성을 위한 Master 데이터 자동 생성"""
    for code in ["LANE_A", "LANE_B", "LANE_X"]:
        MasterLane.objects.get_or_create(lane_code=code, defaults={"lane_name": code})
    for code in ["KRPUS", "JPTYO", "PUS"]:
        MasterPort.objects.get_or_create(port_code=code, defaults={"port_name": code})
    for code in ["ASIA"]:
        MasterTrade.objects.get_or_create(
            trade_code=code, defaults={"trade_name": code}
        )


# =========================================================
# User & Client Fixtures
# =========================================================


@pytest.fixture
def user(db):
    """일반 사용자 (test_user)"""
    return User.objects.create_user(username="test_user", password="password")


@pytest.fixture
def auth_client(client, user):
    """로그인된 Client"""
    client.login(username="test_user", password="password")
    return client


@pytest.fixture
def base_scenario(db, user):
    """기본 시나리오 (API 테스트용)"""
    return ScenarioInfo.objects.create(
        code="SC20260201_001",
        description="Scenario for API testing",
        scenario_type="BASELINE",
        status="ACTIVE",
        created_by=user,
        updated_by=user,
    )
