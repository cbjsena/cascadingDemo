import csv
from unittest.mock import MagicMock, patch

import pytest

from django.apps import apps

from input_data.apps import generate_table_definition


@pytest.mark.django_db
class TestDocGeneration:
    """
    'generate_table_definition' 시그널 동작 검증
    """

    @pytest.fixture
    def mock_pg_data(self):
        """테스트용 가짜 PostgreSQL 스키마 데이터 반환"""
        return [
            # table_name, column_name, data_type, nullable, comment
            ("base_test_table", "col_1", "varchar", "NO", "Test Desc"),
            ("base_test_table", "col_2", "int", "YES", None),
        ]

    def test_generate_csv_success(self, tmp_path, mock_pg_data):
        """[Table Doc] PostgreSQL 환경에서 CSV 파일 정상 생성 검증"""

        # 1. settings.BASE_DIR을 pytest가 제공하는 임시 폴더(tmp_path)로 변경
        with patch("django.conf.settings.BASE_DIR", str(tmp_path)):
            with patch("django.db.connection.vendor", "postgresql"):
                with patch("django.db.connection.cursor") as mock_cursor_ctx:
                    # 2. DB 커서 Mocking (가짜 데이터 반환)
                    mock_cursor = MagicMock()
                    mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor
                    mock_cursor.fetchall.return_value = mock_pg_data

                    # 3. 함수 직접 실행 (Signal Trigger 시뮬레이션)
                    app_config = apps.get_app_config("input_data")
                    generate_table_definition(sender=None, app_config=app_config)

                    # 4. 파일 생성 확인
                    expected_file = (
                        tmp_path / "doc" / "db" / "base_table_definitions.csv"
                    )
                    assert expected_file.exists(), "CSV file was not created"

                    # 5. 파일 내용 검증 (utf-8-sig 인코딩 확인)
                    with open(expected_file, "r", encoding="utf-8-sig") as f:
                        reader = csv.reader(f)
                        rows = list(reader)

                        # 헤더 확인
                        assert rows[0][0] == "[Base Data Table Definition]"
                        # 데이터 확인 (None 코멘트가 빈 문자열로 변환되었는지 등)
                        assert rows[4] == [
                            "base_test_table",
                            "col_1",
                            "varchar",
                            "NO",
                            "Test Desc",
                        ]
                        assert rows[5] == ["base_test_table", "col_2", "int", "YES", ""]

    def test_skip_non_postgresql(self, tmp_path):
        """[Table Doc] MySQL 등 타 DB에서는 파일 생성 스킵"""
        with patch("django.conf.settings.BASE_DIR", str(tmp_path)):
            with patch("django.db.connection.vendor", "mysql"):
                app_config = apps.get_app_config("input_data")
                generate_table_definition(sender=None, app_config=app_config)

                expected_file = tmp_path / "doc" / "db" / "base_table_definitions.csv"
                assert (
                    not expected_file.exists()
                ), "File should NOT be created for MySQL"

    def test_empty_data_handling(self, tmp_path):
        """[TEST_DOC_05] DB 쿼리 결과가 없을 때 파일 생성하지 않음"""
        with patch("django.conf.settings.BASE_DIR", str(tmp_path)):
            with patch("django.db.connection.vendor", "postgresql"):
                with patch("django.db.connection.cursor") as mock_cursor_ctx:
                    # 빈 데이터 반환 Mocking
                    mock_cursor = MagicMock()
                    mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor
                    mock_cursor.fetchall.return_value = []  # 빈 리스트

                    app_config = apps.get_app_config("input_data")
                    generate_table_definition(sender=None, app_config=app_config)

                    expected_file = (
                        tmp_path / "doc" / "db" / "base_table_definitions.csv"
                    )
                    assert (
                        not expected_file.exists()
                    ), "File should NOT be created for empty data"
