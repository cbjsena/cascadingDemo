import pytest

from django.contrib.auth.models import User

from input_data.models import ScenarioInfo

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
    """기본 시나리오 (데이터 없음)"""
    return ScenarioInfo.objects.create(
        id="SC01",
        description="API Test Scenario",
        status="T",
        created_by=user,
        updated_by=user,
    )
