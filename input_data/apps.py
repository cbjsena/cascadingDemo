import csv
import io
import os
import sys

from django.apps import AppConfig
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.db.models.signals import post_migrate
from django.utils import timezone

from common import messages as msg
from input_data.queries import TABLE_DEF_QUERY_POSTGRESQL


class InputDataConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "input_data"

    def ready(self):
        # 1. 테스트 환경인지 감지
        is_testing = "pytest" in sys.modules or (
            len(sys.argv) > 1 and sys.argv[1] == "test"
        )

        # 2. 테스트가 아닐 때만 자동화 로직(Signal) 연결
        if not is_testing:
            # 1. DB 코멘트 업데이트
            post_migrate.connect(add_db_comments, sender=self)
            # 2. 테이블 정의서 문서 생성
            post_migrate.connect(generate_table_definition, sender=self)
            # 4. 초기 슈퍼 유저 입력
            post_migrate.connect(create_default_superuser, sender=self)
            # 4. 초기 데이터 입력
            post_migrate.connect(run_init_base_data, sender=self)


def add_db_comments(sender, **kwargs):
    """
    마이그레이션 후 DB 테이블 및 컬럼 코멘트 추가
    """
    app_config = kwargs.get("app_config")
    if app_config is None or app_config.name != "input_data":
        return

    vendor = connection.vendor
    if vendor == "sqlite":
        return

    print(msg.DB_COMMENT_UPDATE_START.format(vendor=vendor))

    with connection.cursor() as cursor:
        for model in app_config.get_models():
            db_table = model._meta.db_table
            table_verbose = model._meta.verbose_name

            # 1. 테이블 코멘트
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
                except Exception as e:
                    print(msg.DB_COMMENT_FAIL.format(target=db_table, error=str(e)))

            # 2. 컬럼 코멘트 (PostgreSQL / Oracle Only)
            if vendor in ["postgresql", "oracle"]:
                for field in model._meta.fields:
                    column_name = field.column
                    column_verbose = field.verbose_name

                    if not column_verbose:
                        continue

                    try:
                        safe_col_comment = str(column_verbose).replace("'", "''")
                        sql = f'COMMENT ON COLUMN "{db_table}"."{column_name}" IS \'{safe_col_comment}\''
                        cursor.execute(sql)
                    except Exception as e:
                        print(
                            msg.DB_COMMENT_FAIL.format(
                                target=f"{db_table}.{column_name}", error=str(e)
                            )
                        )


def generate_table_definition(sender, **kwargs):
    """
    마이그레이션 후 base 테이블 정의서를 csv 파일로 생성
    기존 파일과 비교하여 변경사항이 있을 때만 갱신
    """
    app_config = kwargs.get("app_config")
    if app_config is None or app_config.name != "input_data":
        return

    # PostgreSQL이 아니면 스킵 (쿼리가 PG 전용)
    if connection.vendor != "postgresql":
        print(msg.DOC_GEN_SKIP)
        return

    # 저장 경로 설정
    output_dir = os.path.join(settings.BASE_DIR, "doc", "db")
    output_file = os.path.join(output_dir, "base_table_definitions.csv")

    os.makedirs(output_dir, exist_ok=True)

    try:
        print(msg.DOC_GEN_START)

        with connection.cursor() as cursor:
            cursor.execute(TABLE_DEF_QUERY_POSTGRESQL)
            rows = cursor.fetchall()

        if not rows:
            return

        # 새 CSV 내용을 메모리에 생성
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        # 1. 문서 헤더 (생성 정보)
        writer.writerow(["[Base Data Table Definition]"])
        writer.writerow(["Generated At", timezone.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])

        # 2. 컬럼 헤더
        headers = [
            "Table Name",
            "Column Name",
            "Data Type",
            "Nullable",
            "Description (Comment)",
        ]
        writer.writerow(headers)

        # 3. 데이터 행 작성
        for row in rows:
            # row: (table_name, column_name, data_type, nullable, comment)
            table_name, col_name, data_type, nullable, comment = row
            data_type = _map_data_type(data_type)
            comment = comment if comment else ""
            writer.writerow([table_name, col_name, data_type, nullable, comment])

        new_content = buffer.getvalue()

        # 4. 기존 파일과 비교
        if os.path.exists(output_file):
            with open(output_file, encoding="utf-8-sig") as f:
                old_content = f.read()

            if _remove_generated_line(old_content) == _remove_generated_line(
                new_content
            ):
                print("No changes detected. File not updated.")
                return

        # 5 변경 있을 때만 저장
        with open(output_file, "w", encoding="utf-8-sig", newline="") as f:
            f.write(new_content)

        print(msg.DOC_GEN_SUCCESS.format(path=output_file))

    except Exception as e:
        print(msg.DOC_GEN_FAIL.format(error=str(e)))


def create_default_superuser(sender, **kwargs):
    """
    migrate 실행 후 자동으로 슈퍼유저를 생성하는 콜백 함수
    """
    # 모델을 함수 내부에서 import해야 App Registry 로딩 순서 문제를 방지할 수 있습니다.
    from django.contrib.auth import get_user_model

    User = get_user_model()

    username = "cascading"
    email = "yukaris@cyberlogitec.com"
    password = "qwer123$"

    # 계정이 없을 때만 생성 (get_or_create 사용 안 함 - 비밀번호 설정 때문)
    if not User.objects.filter(username=username).exists():
        print(msg.AUTO_SETUP_SUPERUSER_START.format(username=username))

        try:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                # create_superuser는 기본적으로 is_staff, is_superuser=True임
                # 명시적으로 필요한 경우 추가 설정:
                # is_active=True
            )
            print(msg.AUTO_SETUP_SUPERUSER_SUCCESS.format(username=username))
        except Exception as e:
            print(msg.AUTO_SETUP_SUPERUSER_FAILED.format(error=e))
    else:
        print(msg.AUTO_SETUP_SUPERUSER_EXIST.format(username=username))


def run_init_base_data(sender, **kwargs):
    """
    migrate 완료 후 'init_master_data' → 'init_base_data' 순서로 자동 실행.
    base_ 테이블이 master_ 테이블을 FK(PROTECT)로 참조하므로
    master_ 데이터가 먼저 존재해야 한다.
    """
    for command_name in ["init_master_data", "init_base_data"]:
        print(msg.AUTO_SETUP_COMMAND_START.format(command=command_name))
        try:
            if command_name == "init_master_data":
                call_command(command_name, "--force")
            else:
                call_command(command_name)
            print(msg.AUTO_SETUP_COMMAND_SUCCESS.format(command=command_name))
        except Exception as e:
            print(msg.AUTO_SETUP_COMMAND_FAILED.format(command=command_name, error=e))


def _map_data_type(data_type):
    if data_type.startswith("character varying"):
        data_type = "string"
    elif data_type == "integer":
        data_type = "int"
    elif data_type == "timestamp with time zone":
        data_type = "datetime"

    return data_type


def _remove_generated_line(content: str) -> str:
    """
    CSV 내용 중 'Generated At' 줄 제거
    """
    lines = content.splitlines()
    filtered = [line for line in lines if not line.startswith("Generated At,")]
    return "\n".join(filtered)
