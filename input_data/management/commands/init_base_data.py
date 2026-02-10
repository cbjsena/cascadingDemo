import os
import csv
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from common import messages as msg


class Command(BaseCommand):
    help = 'Load base data from CSV files into Base tables'

    def handle(self, *args, **kwargs):
        # 1. CSV 파일 위치 설정
        base_data_dir = os.path.join(settings.BASE_DIR, 'input_data', 'data', 'base_data')

        if not os.path.exists(base_data_dir):
            self.stdout.write(self.style.ERROR(msg.DIR_NOT_FOUND.format(path=base_data_dir)))
            return

        # 2. input_data 앱의 모든 모델 가져오기
        app_config = apps.get_app_config('input_data')
        models = app_config.get_models()

        # 3. 모델 순회하며 데이터 로드
        for model in models:
            # 테이블명이 'base_'로 시작하는 모델만 대상
            if not model._meta.db_table.startswith('base_'):
                continue

            table_name = model._meta.db_table
            file_name = f"{table_name}.csv"
            file_path = os.path.join(base_data_dir, file_name)

            if not os.path.exists(file_path):
                self.stdout.write(self.style.WARNING(msg.FILE_NOT_FOUND.format(table=table_name, file=file_name)))
                continue

            self.load_data(model, file_path)

    @transaction.atomic
    def load_data(self, model, file_path):
        """CSV 파일을 읽어 모델에 Bulk Insert"""
        table_name = model._meta.db_table
        self.stdout.write(self.style.MIGRATE_HEADING(msg.START_LOADING.format(table=table_name)))

        # 기존 데이터 삭제 (중복 방지)
        model.objects.all().delete()

        data_list = []

        try:
            with open(file_path, mode='r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)

                for i, row in enumerate(reader):
                    try:
                        # 빈 문자열('')을 None으로 변환해야 하는 필드 처리
                        # (IntegerField, DecimalField 등에 ''가 들어가면 에러 발생)
                        cleaned_row = self.clean_row(model, row)
                        data_list.append(model(**cleaned_row))
                    except Exception as e:
                        error_message = msg.ROW_ERROR.format(table=table_name, error=str(e))
                        detailed_message = f"{error_message} | ROW #{i + 1} DATA: {row}"
                        self.stdout.write(self.style.ERROR(detailed_message))

            # Bulk Create
            if data_list:
                model.objects.bulk_create(data_list)
                self.stdout.write(self.style.SUCCESS(msg.DONE_LOADING.format(table=table_name, count=len(data_list))))
            else:
                self.stdout.write(self.style.WARNING(msg.EMPTY_CSV.format(table=table_name)))

        except Exception as e:
            self.stdout.write(self.style.ERROR(msg.LOAD_FAIL.format(table=table_name, error=str(e))))

    def clean_row(self, model, row):
        """CSV 값을 필드 타입에 맞춰 변환 (실패 시 ValueError 발생시켜 행 스킵 유도)"""
        cleaned = {}
        for key, value in row.items():
            try:
                field = model._meta.get_field(key)
            except:
                continue

            val = value.strip() if isinstance(value, str) else value
            internal_type = field.get_internal_type()

            # 1. 빈 값 처리
            if val == '':
                if field.is_relation or internal_type in ['IntegerField', 'DecimalField', 'FloatField',
                                                          'BigIntegerField']:
                    cleaned[key] = None if field.null else 0
                else:
                    cleaned[key] = None if field.null else ''

            # 2. 값이 있는 경우 - 타입별 강제 변환
            else:
                try:
                    # (A) 정수형 (Integer)
                    if internal_type in ['IntegerField', 'BigIntegerField']:
                        # 콤마 제거 후 int 변환 시도 -> "INVALID"일 경우 여기서 ValueError 발생
                        cleaned[key] = int(val.replace(',', ''))

                    # (B) 실수/소수형 (Decimal, Float)
                    elif internal_type == 'DecimalField':
                        cleaned[key] = Decimal(val.replace(',', ''))
                    elif internal_type == 'FloatField':
                        cleaned[key] = float(val.replace(',', ''))

                    # (C) 날짜형 (Date/DateTime)
                    elif internal_type in ['DateTimeField', 'DateField']:
                        try:
                            dt = datetime.strptime(val, '%Y/%m/%d %H:%M:%S')
                        except ValueError:
                            # 시간 포맷 없으면 날짜만 시도
                            dt = datetime.strptime(val, '%Y/%m/%d')
                        cleaned[key] = timezone.make_aware(dt)

                    # (D) 그 외 (문자열 등)
                    else:
                        cleaned[key] = val

                except ValueError as e:
                    # 변환 실패 시 명확한 에러 메시지와 함께 raise -> load_data의 loop에서 잡힘
                    raise ValueError(f"Column '{key}' expects {internal_type}, but got '{val}'")

        return cleaned