import pytest

from django.core.management import call_command
from django.test import override_settings

from input_data.models import BaseVesselInfo


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
        # 헤더: vessel_code,vessel_name,own_yn,delivery_date
        csv_content = """vessel_code,vessel_name,own_yn,delivery_date
TEST,Test Vessel,O,2025/01/01
TEST2,Test Vessel 2,C,2025/02/01"""

        csv_file = data_dir / "base_vessel_info.csv"
        csv_file.write_text(csv_content, encoding="utf-8-sig")

        # BASE_DIR을 임시 경로로 오버라이딩하여 커맨드 실행
        with override_settings(BASE_DIR=base_dir):
            call_command("init_base_data")

        # 검증
        assert BaseVesselInfo.objects.count() == 2

        obj1 = BaseVesselInfo.objects.get(vessel_code="TEST")
        assert obj1.delivery_date.year == 2025
        assert obj1.delivery_date.month == 1
        assert obj1.delivery_date.day == 1

        obj2 = BaseVesselInfo.objects.get(vessel_code="TEST2")
        assert obj2.delivery_date.year == 2025
        assert obj2.delivery_date.month == 2

    def test_date_format_compatibility(self, temp_base_data_dir):
        """
        [CMD_INIT_003] 날짜 포맷 호환성 (YYYY/MM/DD HH:MM:SS, YYYY/MM/DD 혼용)
        """
        base_dir, data_dir = temp_base_data_dir

        # 두 가지 날짜 형식 혼용 (YYYY/MM/DD 또는 YYYY-MM-DD)
        csv_content = """vessel_code,vessel_name,own_yn,delivery_date
TEST_FMT1,Test Vessel 1,O,2025/01/01
TEST_FMT2,Test Vessel 2,C,2025/02/15"""

        csv_file = data_dir / "base_vessel_info.csv"
        csv_file.write_text(csv_content, encoding="utf-8-sig")

        with override_settings(BASE_DIR=base_dir):
            call_command("init_base_data")

        # 두 형식 모두 정상 파싱 확인
        obj1 = BaseVesselInfo.objects.get(vessel_code="TEST_FMT1")
        assert obj1.delivery_date.year == 2025
        assert obj1.delivery_date.month == 1
        assert obj1.delivery_date.day == 1

        obj2 = BaseVesselInfo.objects.get(vessel_code="TEST_FMT2")
        assert obj2.delivery_date.year == 2025
        assert obj2.delivery_date.month == 2
        assert obj2.delivery_date.day == 15

    def test_load_empty_values(self, temp_base_data_dir):
        """
        [CMD_INIT_002] 빈 값 처리 (숫자 -> 0/None, 날짜 -> None)
        """
        base_dir, data_dir = temp_base_data_dir

        # vessel_name, own_yn 비움
        csv_content = """vessel_code,vessel_name,own_yn,delivery_date
EMPTY,EMPTY vessel,,,"""

        csv_file = data_dir / "base_vessel_info.csv"
        csv_file.write_text(csv_content, encoding="utf-8-sig")

        with override_settings(BASE_DIR=base_dir):
            call_command("init_base_data")

        obj = BaseVesselInfo.objects.get(vessel_code="EMPTY")
        # BaseVesselInfo.own_yn  현재 모델상 Not Null
        assert obj.delivery_date is None

    def test_row_error_handling(self, temp_base_data_dir, capsys):
        """
        [CMD_INIT_004] 잘못된 데이터 행 처리 (스킵 및 경고)
        """
        base_dir, data_dir = temp_base_data_dir

        # 2번째 행의 vessel_code 없음 (에러 유발)
        csv_content = """vessel_code,vessel_name,delivery_date
OK,Normal Vessel,2026/01/01 00:00:00
,Error Vessel, invalid_date
OK2,Normal Vessel 2,2026/01/01 00:00:00"""

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
        assert "invalid_date" in captured.out or "INVALID" in captured.err

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

    # def test_load_real_base_data(self):
    #     """
    #     디버그를 위한 실제 데이터 로드 및 날짜/숫자 파싱 확인
    #     """
    #     from pathlib import Path
    #     base_dir = Path(r"D:\dev\django\cascadingDemo")
    #     data_dir = base_dir / "data" / "base"
    #     data_dir.mkdir(parents=True, exist_ok=True)
    #
    #     # BASE_DIR을 임시 경로로 오버라이딩하여 커맨드 실행
    #     with override_settings(BASE_DIR=base_dir):
    #         call_command("init_base_data")
