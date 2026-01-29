import pytest
from django.contrib.auth.models import User
from input_data.models import InputDataSnapshot, ProformaSchedule

@pytest.fixture
def test_user(db):
    """테스트용 사용자 생성"""
    return User.objects.create_user(username='testuser', password='password')

@pytest.fixture
def auth_client(client, test_user):
    """로그인된 Client 반환"""
    client.force_login(test_user)
    return client

@pytest.fixture
def other_user(db):
    """다른 일반 사용자 (작성자가 아닌 사람)"""
    return User.objects.create_user(username='other_user', password='password')

@pytest.fixture
def admin_user(db):
    """슈퍼유저 (모든 권한)"""
    return User.objects.create_superuser(username='admin_user', password='password', email='admin@test.com')

@pytest.fixture
def admin_client(client, admin_user):
    """슈퍼유저로 로그인된 Client"""
    client.force_login(admin_user)
    return client

@pytest.fixture
def snapshot_of_other(db, other_user):
    """다른 사용자가 만든 스냅샷"""
    return InputDataSnapshot.objects.create(
        data_id="OTHER_USER_SNAPSHOT",
        description="Snapshot created by other user",
        base_year_month="202505",
        created_by=other_user, # 작성자가 other_user임
        updated_by=other_user
    )

@pytest.fixture
def base_snapshot(db, test_user):
    """기본 스냅샷 생성"""
    return InputDataSnapshot.objects.create(
        data_id="TEST_BASE_01",
        description="Base Snapshot for Testing",
        base_year_month="202501",
        created_by=test_user,
        updated_by=test_user
    )

@pytest.fixture
def snapshot_with_data(db, base_snapshot, test_user):
    """하위 데이터(ProformaSchedule)가 포함된 스냅샷"""
    ProformaSchedule.objects.create(
        data_id=base_snapshot,
        vessel_service_lane_code="NE2",
        proforma_name="NE2_PF_V1",
        duration=70.0,
        standard_service_speed=18.5,
        declared_capacity_class_code="14000",
        declared_count=10,
        direction="W",
        port_code="KRPUS",
        calling_port_indicator_seq="01",
        calling_port_seq=1,
        etb_day_code="MON",
        etb_day_time="0800",
        etb_day_number=1,
        etd_day_code="TUE",
        etd_day_time="1800",
        etd_day_number=2,
        link_distance=500,
        link_speed=15.0,
        created_by=test_user,
        updated_by=test_user
    )
    return base_snapshot