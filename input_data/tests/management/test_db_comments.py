import pytest
from unittest.mock import MagicMock, patch
from django.core.management import call_command
from common import messages as msg


@pytest.mark.django_db
class TestDBComments:
    """
    'update_db_comments' 커맨드 동작 검증
    """

    def test_postgresql_execution(self, capsys):
        """[DB Comment] PostgreSQL 환경에서 테이블/컬럼 코멘트 쿼리 실행 검증"""
        # 1. PostgreSQL 환경 Mocking
        with patch("django.db.connection.vendor", "postgresql"):
            with patch("django.db.connection.cursor") as mock_cursor_ctx:
                mock_cursor = MagicMock()
                mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor

                # 2. 커맨드 실행
                call_command("update_db_comments")

                # 3. 실행된 SQL 수집
                executed_sqls = [
                    call_args[0][0] for call_args in mock_cursor.execute.call_args_list
                ]

                # 4. 검증: 테이블 코멘트 (ScenarioInfo)
                table_sql = 'COMMENT ON TABLE "sce_scenario_info" IS'
                assert any(
                    table_sql in sql for sql in executed_sqls
                ), "Table comment SQL missing"

                # 5. 검증: 컬럼 코멘트 (ScenarioInfo.id)
                col_sql = 'COMMENT ON COLUMN "sce_scenario_info"."scenario_id" IS'
                assert any(
                    col_sql in sql for sql in executed_sqls
                ), "Column comment SQL missing"

    def test_sqlite_skip(self, capsys):
        """[DB Comment] SQLite 환경에서 스킵 메시지 출력 검증"""
        with patch("django.db.connection.vendor", "sqlite"):
            call_command("update_db_comments")

        captured = capsys.readouterr()
        # "Not supported" 메시지가 포함되어야 함
        assert msg.DB_COMMENT_NOT_SUPPORTED.format(vendor="sqlite") in captured.out
