"""
공통 데이터 Import / Export 모듈

■ CSV : csv_configs.py의 flat 매핑 사용 (기존과 동일)
■ JSON: json_configs.py의 중첩 매핑 사용 (Master-Detail 계층 지원)

사용 예시:
    from common.export_manager import export_csv, export_json, parse_json_upload

    # CSV (flat)
    return export_csv(queryset, CANAL_FEE_CSV_MAP, filename="canal_fee.csv")

    # JSON (flat — children 없음)
    return export_json(queryset, CANAL_FEE_JSON, filename="canal_fee.json")

    # JSON (nested — children 있음)
    return export_json(queryset, PROFORMA_SCHEDULE_JSON, filename="proforma.json")

    # JSON Upload (flat)
    rows, error = parse_json_upload(json_file, CANAL_FEE_JSON)
"""

import csv
import io
import json
from datetime import date, datetime
from decimal import Decimal

from django.http import HttpResponse


# =========================================================
# 공통 유틸
# =========================================================
def _resolve_field(obj, field_path):
    """점(.) 구분 경로로 필드 값을 가져온다. 예: 'scenario.code'"""
    value = obj
    for attr in field_path.split("."):
        if value is None:
            return None
        value = getattr(value, attr, None)
    return value


def _to_serializable(value):
    """JSON 직렬화 가능한 타입으로 변환."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return int(value) if value == int(value) else float(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, (int, float, bool)):
        return value
    return str(value)


# =========================================================
# CSV Export (csv_configs.py 매핑 사용)
# =========================================================
def export_csv(queryset, csv_map, *, filename="export.csv"):
    """
    csv_configs.py의 flat 매핑으로 CSV HttpResponse를 반환한다.

    Args:
        queryset: Django QuerySet
        csv_map: [(db_column, model_field, required), ...]
        filename: 다운로드 파일명
    """
    output = io.StringIO()
    output.write("\ufeff")  # BOM (Excel 한글 깨짐 방지)
    writer = csv.writer(output)

    # 헤더
    writer.writerow([col[0] for col in csv_map])

    # 데이터
    for obj in queryset:
        row = []
        for _, model_field, _ in csv_map:
            if model_field == "scenario_code":
                scenario = getattr(obj, "scenario", None)
                val = scenario.code if scenario else ""
            else:
                val = getattr(obj, model_field, None)
            row.append("" if val is None else str(val))
        writer.writerow(row)

    response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# =========================================================
# JSON Export (json_configs.py 매핑 사용 — 중첩 구조 지원)
# =========================================================
def export_json(queryset, json_config, *, filename="export.json"):
    """
    json_configs.py의 매핑으로 JSON HttpResponse를 반환한다.
    children 설정이 있으면 1:N 관계를 중첩 배열로 포함한다.

    Args:
        queryset: Django QuerySet
        json_config: json_configs.py에서 정의된 설정 딕셔너리
            {
                "root_key": "proforma_schedules",
                "fields": [("json_key", "model_field_path"), ...],
                "prefetch": ["details"],               # 선택
                "children": [                           # 선택
                    {
                        "key": "details",
                        "related_name": "details",
                        "order_by": "calling_port_seq", # 선택
                        "fields": [("json_key", "model_field"), ...],
                    },
                ],
            }
        filename: 다운로드 파일명
    """
    # prefetch 적용 (N+1 쿼리 방지)
    prefetch = json_config.get("prefetch", [])
    if prefetch:
        queryset = queryset.prefetch_related(*prefetch)

    fields = json_config.get("fields", [])
    children = json_config.get("children", [])

    # 직렬화
    data = []
    for obj in queryset:
        record = {}

        # 루트 필드 (3-tuple: json_key, model_field, required — required는 export에서 무시)
        for field_tuple in fields:
            json_key, model_field = field_tuple[0], field_tuple[1]
            record[json_key] = _to_serializable(_resolve_field(obj, model_field))

        # 자식 데이터 (1:N 관계)
        for child_conf in children:
            child_key = child_conf["key"]
            related_name = child_conf["related_name"]
            child_fields = child_conf["fields"]
            order_by = child_conf.get("order_by")

            related_manager = getattr(obj, related_name, None)
            if related_manager is None:
                record[child_key] = []
                continue

            child_qs = related_manager.all()
            if order_by:
                child_qs = child_qs.order_by(order_by)

            child_records = []
            for child_obj in child_qs:
                child_record = {}
                for child_tuple in child_fields:
                    cj_key, cj_field = child_tuple[0], child_tuple[1]
                    child_record[cj_key] = _to_serializable(
                        _resolve_field(child_obj, cj_field)
                    )
                child_records.append(child_record)
            record[child_key] = child_records

        data.append(record)

    # 최종 JSON
    root_key = json_config.get("root_key", "data")
    payload = {"count": len(data), root_key: data}

    content = json.dumps(payload, ensure_ascii=False, indent=2)
    response = HttpResponse(content, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# =========================================================
# JSON Import (json_configs.py 매핑 사용 — flat 레코드 파싱)
# =========================================================
def parse_json_upload(json_file, json_config):
    """
    업로드된 JSON 파일을 파싱하여 모델 필드 딕셔너리 리스트로 반환한다.

    JSON 파일 구조 (export_json이 생성한 형식):
        {
            "count": 3,
            "canal_fees": [
                {"scenario_code": "SC_001", "vessel_code": "V001", ...},
                ...
            ]
        }

    Args:
        json_file: request.FILES의 파일 객체
        json_config: json_configs.py에 정의된 설정 딕셔너리

    Returns:
        (rows, error): rows는 [{model_field: value}, ...] 리스트,
                        error는 에러 메시지 문자열 (없으면 None)
    """
    try:
        content = json_file.read().decode("utf-8-sig")
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return [], f"Invalid JSON file: {e}"

    root_key = json_config.get("root_key", "data")
    records = payload.get(root_key, [])

    if not records:
        return [], None  # 빈 데이터 — 에러는 아님

    fields = json_config.get("fields", [])

    # json_key → (model_field, required) 매핑 구성
    # "scenario.code" 같은 점 경로는 업로드 시 무시 (scenario_id는 POST에서 받음)
    field_map = {}  # {json_key: (model_field, required)}
    for field_tuple in fields:
        json_key, model_field = field_tuple[0], field_tuple[1]
        required = field_tuple[2] if len(field_tuple) > 2 else True
        if "." in model_field:
            continue
        field_map[json_key] = (model_field, required)

    rows = []
    for record in records:
        obj_data = {}
        skip = False
        for json_key, (model_field, required) in field_map.items():
            val = record.get(json_key)
            if val is not None and str(val).strip():
                obj_data[model_field] = str(val).strip()
            else:
                obj_data[model_field] = None
                if required:
                    skip = True
                    break
        if not skip:
            rows.append(obj_data)

    return rows, None
