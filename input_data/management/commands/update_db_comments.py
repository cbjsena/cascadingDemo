from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection
from common import messages as msg


class Command(BaseCommand):
    help = "Update database table and column comments based on model verbose_name"

    def handle(self, *args, **kwargs):
        vendor = connection.vendor
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                msg.DB_COMMENT_UPDATE_START.format(vendor=vendor)
            )
        )

        # SQLite는 미지원
        if vendor == "sqlite":
            self.stdout.write(
                self.style.ERROR(msg.DB_COMMENT_NOT_SUPPORTED.format(vendor=vendor))
            )
            return

        app_config = apps.get_app_config("input_data")

        with connection.cursor() as cursor:
            for model in app_config.get_models():
                db_table = model._meta.db_table
                table_verbose = model._meta.verbose_name

                # -------------------------------------------------------
                # 1. 테이블 코멘트 (Table Comment)
                # -------------------------------------------------------
                if table_verbose:
                    try:
                        sql = ""
                        if vendor in ["postgresql", "oracle"]:
                            safe_comment = table_verbose.replace("'", "''")
                            sql = f"COMMENT ON TABLE \"{db_table}\" IS '{safe_comment}'"
                        elif vendor == "mysql":
                            safe_comment = table_verbose.replace("'", "\\'")
                            sql = f"ALTER TABLE `{db_table}` COMMENT = '{safe_comment}'"

                        if sql:
                            cursor.execute(sql)
                            self.stdout.write(
                                self.style.SUCCESS(
                                    msg.DB_TABLE_COMMENT_SUCCESS.format(
                                        table=db_table, comment=table_verbose
                                    )
                                )
                            )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                msg.DB_COMMENT_FAIL.format(
                                    target=db_table, error=str(e)
                                )
                            )
                        )

                # -------------------------------------------------------
                # 2. 컬럼 코멘트 (Column Comment)
                # -------------------------------------------------------
                # MySQL은 MODIFY COLUMN 등 복잡한 문법이 필요하여 이 스크립트에서는 생략 (Postgres/Oracle 전용)
                if vendor not in ["postgresql", "oracle"]:
                    continue

                for field in model._meta.fields:
                    column_name = field.column
                    column_verbose = field.verbose_name

                    if (
                        not column_verbose or column_name == "id"
                    ):  # ID는 보통 생략하거나 필요 시 포함
                        continue

                    try:
                        safe_col_comment = str(column_verbose).replace("'", "''")
                        # 문법: COMMENT ON COLUMN table_name.column_name IS 'comment';
                        sql = f'COMMENT ON COLUMN "{db_table}"."{column_name}" IS \'{safe_col_comment}\''

                        cursor.execute(sql)
                        # 너무 로그가 많으면 아래 줄 주석 처리
                        # self.stdout.write(msg.DB_COLUMN_COMMENT_SUCCESS.format(column=column_name, comment=column_verbose))

                    except Exception as e:
                        target_str = f"{db_table}.{column_name}"
                        self.stdout.write(
                            self.style.ERROR(
                                msg.DB_COMMENT_FAIL.format(
                                    target=target_str, error=str(e)
                                )
                            )
                        )

        self.stdout.write(self.style.SUCCESS(msg.DB_COMMENT_COMPLETE))
