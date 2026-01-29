import pytest
from input_data.models import InputDataSnapshot, ProformaSchedule


@pytest.mark.django_db
class TestInputDataModels:

    def test_snapshot_creation(self, test_user):
        """InputDataSnapshot 모델 생성 및 Audit 필드 확인"""
        snapshot = InputDataSnapshot.objects.create(
            data_id="TEST_MODEL_01",
            description="Test Description",
            created_by=test_user
        )
        assert snapshot.data_id == "TEST_MODEL_01"
        assert snapshot.created_by == test_user
        assert str(snapshot) == "[TEST_MODEL_01] Test Description"

    def test_child_model_creation(self, base_snapshot):
        """하위 모델(ProformaSchedule) 생성 및 FK 연결 확인"""
        schedule = ProformaSchedule.objects.create(
            data_id=base_snapshot,
            vessel_service_lane_code="TEST_LANE",
            proforma_name="TEST_PF",
            duration=10.0,
            standard_service_speed=20.0,
            declared_capacity_class_code="10000",
            declared_count=5,
            direction="E",
            port_code="USLGB",
            calling_port_indicator_seq="01",
            calling_port_seq=1,
            etb_day_code="MON",
            etb_day_time="0000",
            etb_day_number=1,
            etd_day_code="MON",
            etd_day_time="1200",
            etd_day_number=1,
            link_distance=100,
            link_speed=10.0
        )
        assert schedule.data_id == base_snapshot
        assert schedule.vessel_service_lane_code == "TEST_LANE"