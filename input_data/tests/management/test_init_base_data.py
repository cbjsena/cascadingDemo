import pytest
import os
from django.core.management import call_command
from django.test import override_settings
from input_data.models import BaseVesselInfo
from common import messages as msg


@pytest.fixture
def temp_base_data_dir(tmp_path):
    """
    테스트용 임시 CSV 디렉토리 구조 생성
    구조: {tmp_path}/input_data/data/base_data/
    """
    target_dir = tmp_path / "input_data" / "data" / "base_data"
    target_dir.mkdir(parents=True)
    return tmp_path, target_dir


@pytest.mark.django_db
class TestInitBaseData:

    def test_load_base_data_success(self, temp_base_data_dir):
        """
        [CMD_INIT_001] 정상 데이터 로드 및 날짜/숫자 파싱 확인
        """
        base_dir, data_dir = temp_base_data_dir

        # 테스트용 CSV 작성 (BaseVesselInfo)
        # 헤더: vessel_code,vessel_name,nominal_capacity,own_yn,delivery_date
        csv_content = """vessel_code,vessel_name,nominal_capacity,own_yn,delivery_date
TEST,Test Vessel,10000,O,2025/01/01 12:00:00
TEST2,Test Vessel 2,20000,C,2025/02/01"""

        csv_file = data_dir / "base_vessel_info.csv"
        csv_file.write_text(csv_content, encoding="utf-8-sig")

        # BASE_DIR을 임시 경로로 오버라이딩하여 커맨드 실행
        with override_settings(BASE_DIR=base_dir):
            call_command("init_base_data")

        # 검증
        assert BaseVesselInfo.objects.count() == 2

        obj1 = BaseVesselInfo.objects.get(vessel_code="TEST")
        assert obj1.nominal_capacity == 10000
        # Timezone Aware 변환 확인
        assert obj1.delivery_date.year == 2025
        assert obj1.delivery_date.month == 1
        assert obj1.delivery_date.hour == 12

        obj2 = BaseVesselInfo.objects.get(vessel_code="TEST2")
        # 시간 없는 날짜 포맷 확인
        assert obj2.delivery_date.year == 2025
        assert obj2.delivery_date.month == 2

    def test_load_empty_values(self, temp_base_data_dir):
        """
        [CMD_INIT_002] 빈 값 처리 (숫자 -> 0/None, 날짜 -> None)
        """
        base_dir, data_dir = temp_base_data_dir

        # nominal_capacity(Int)와 delivery_date(Date)를 비움
        csv_content = """vessel_code,vessel_name,nominal_capacity,own_yn,delivery_date
EMPTY,Empty Value Vessel,,O,"""

        csv_file = data_dir / "base_vessel_info.csv"
        csv_file.write_text(csv_content, encoding="utf-8-sig")

        with override_settings(BASE_DIR=base_dir):
            call_command("init_base_data")

        obj = BaseVesselInfo.objects.get(vessel_code="EMPTY")
        # IntegerField 빈 값 -> 0 (모델 필드가 null=False라면) 또는 None (null=True라면)
        # BaseVesselInfo.nominal_capacity는 현재 모델상 Not Null이므로 0으로 변환됨
        assert obj.nominal_capacity == 0 or obj.nominal_capacity is None
        assert obj.delivery_date is None

    def test_row_error_handling(self, temp_base_data_dir, capsys):
        """
        [CMD_INIT_004] 잘못된 데이터 행 처리 (스킵 및 경고)
        """
        base_dir, data_dir = temp_base_data_dir

        # 2번째 행의 nominal_capacity에 문자가 들어감 (에러 유발)
        csv_content = """vessel_code,vessel_name,nominal_capacity,own_yn
OK,Normal Vessel,5000,O
ERR,Error Vessel,INVALID,O
OK2,Normal Vessel 2,6000,O"""

        csv_file = data_dir / "base_vessel_info.csv"
        csv_file.write_text(csv_content, encoding="utf-8-sig")

        with override_settings(BASE_DIR=base_dir):
            call_command("init_base_data")

        # 검증: 정상 행 2개만 저장되어야 함
        assert BaseVesselInfo.objects.count() == 2
        assert BaseVesselInfo.objects.filter(vessel_code="OK").exists()
        assert BaseVesselInfo.objects.filter(vessel_code="OK2").exists()

        # 로그 출력 확인
        captured = capsys.readouterr()
        # "invalid literal for int()" 에러 메시지가 포함되어야 함
        assert "Row skipped" in captured.out or "Row skipped" in captured.err
        assert "INVALID" in captured.out or "INVALID" in captured.err

    def test_file_not_found(self, temp_base_data_dir, capsys):
        """
        [CMD_INIT_005] 파일이 없을 때 처리
        """
        base_dir, data_dir = temp_base_data_dir
        # CSV 파일 생성 안 함

        with override_settings(BASE_DIR=base_dir):
            call_command("init_base_data")

        captured = capsys.readouterr()
        # 모든 Base 모델에 대해 File not found 메시지가 찍혀야 함 (하나라도 확인)
        # 메시지 포맷: [SKIP] base_vessel_info: File not found ...
        assert "[SKIP]" in captured.out
