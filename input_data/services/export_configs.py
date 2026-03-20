"""
시나리오 데이터 Export 설정

■ 동적 탐색 기반이므로 제외 대상만 명시
■ 모델별 필드 매핑(rename) + 중첩 구조(nesting) 지원
"""

# Export에서 제외할 모델명
# - ScenarioInfo: _meta.json으로 별도 처리
# - Proforma 관련 4개 모델: proforma.json으로 통합 처리
EXPORT_EXCLUDE_MODELS = {
    "ScenarioInfo",
    "ProformaSchedule",
    "ProformaScheduleDetail",
    "CascadingVesselPosition",
    "LaneProformaMapping",
}

# 모든 모델에서 공통으로 제외할 필드 (PK, Audit 필드)
EXPORT_EXCLUDE_FIELDS = {
    "id",
    "created_at",
    "created_by",
    "created_by_id",
    "updated_at",
    "updated_by",
    "updated_by_id",
}

# =========================================================
# 모델별 Export 옵션
# =========================================================
#
# field_map: DB attname → Export JSON key 매핑 (rename)
#     지정하지 않은 필드는 attname 그대로 출력.
#     값이 None이면 해당 필드를 제외.
#
# nesting: 여러 필드를 하나의 중첩 객체로 그룹핑
#     { "json_group_key": ["attname1", "attname2", ...] }
#     nesting에 포함된 필드는 최상위에서 제거되고 그룹 안에 배치됨.
#     field_map의 rename이 먼저 적용된 후 nesting에 사용됨.
#
# order_by: 정렬 기준 (기본값: ['pk'])
# exclude_fields: 모델별 추가 제외 필드
#
EXPORT_MODEL_OPTIONS = {
    # ── Bunker ──────────────────────────────────────────
    "BunkerConsumptionPort": {
        "field_map": {
            "vessel_capacity": "nominal_capacity",
            "port_stay_bunker_consumption": "consumption_for_berthing",
            "idling_bunker_consumption": "consumption_for_idling",
            "pilot_inout_bunker_consumption": "consumption_for_pilot",
        },
        "nesting": {
            "consumption": [
                "consumption_for_berthing",
                "consumption_for_idling",
                "consumption_for_pilot",
            ],
        },
    },
    "BunkerConsumptionSea": {
        "field_map": {
            "vessel_capacity": "nominal_capacity",
            "sea_speed": "speed",
            "bunker_consumption": "consumption_for_sailing",
        },
        "nesting": {
            "consumption": [
                "speed",
                "consumption_for_sailing",
            ],
        },
    },
    "BunkerPrice": {
        "field_map": {
            "trade_id": "trade_code",
            "lane_id": "lane_code",
            "bunker_price": "price",
        },
    },
    # ── Cost ────────────────────────────────────────────
    "CanalFee": {
        "field_map": {
            "port_id": "port_code",
            "canal_fee": "fee",
        },
    },
    "TSCost": {
        "field_map": {
            "lane_id": "lane_code",
            "port_id": "port_code",
        },
        "nesting": {
            "ports": [
                "port_code",
                "ts_cost",
            ],
        },
    },
    # ── Vessel ──────────────────────────────────────────
    "VesselInfo": {
        "field_map": {
            "trade_id": "trade_code",
            "lane_id": "lane_code",
        },
    },
    "CharterCost": {
        "field_map": {
            "charter_cost": "daily_cost_usd",
        },
    },
    "VesselCapacity": {
        "field_map": {
            "trade_id": "trade_code",
            "lane_id": "lane_code",
        },
    },
    # ── Schedule (Proforma 통합) ─────────────────────────
    # ProformaSchedule, ProformaScheduleDetail,
    # CascadingVesselPosition, LaneProformaMapping을
    # service_lanes 기준의 2-depth 계층 구조로 통합 Export.
    # 개별 모델 설정은 PROFORMA_EXPORT_OPTIONS에서 관리.
}

# Export 시 모델 정렬 순서 (Master → Detail 순서 보장)
MODEL_EXPORT_ORDER = {
    "ProformaSchedule": 0,
    "CascadingSchedule": 1,
    "CascadingVesselPosition": 1,
}

# =========================================================
# Proforma 통합 Export 설정 (proforma.json)
# =========================================================
# service_lanes[] → versions[] → port_rotation[] 2-depth 계층 구조
#
PROFORMA_EXPORT_FILENAME = "proforma.json"

# ProformaSchedule (version) 필드 설정
PROFORMA_VERSION_FIELDS = {
    "exclude": {
        "id",
        "scenario_id",
        "lane_id",
        "created_at",
        "created_by_id",
        "updated_at",
        "updated_by_id",
    },
    "field_map": {
        "proforma_name": "version_code",
        "effective_from_date": "effective_from",
        "effective_to_date": "effective_to",
        "declared_capacity": "required_capacity_teu",
        "duration": "service_duration",
        "declared_count": "total_vessel_count",
    },
}

# ProformaScheduleDetail (port_rotation) 필드 설정
PROFORMA_PORT_ROTATION_FIELDS = {
    "exclude": {
        "id",
        "proforma_id",
        "direction",
        "calling_port_indicator",
        "turn_port_info_code",
        "actual_work_hours",
        "link_distance",
        "link_eca_distance",
        "link_speed",
        "created_at",
        "created_by_id",
        "updated_at",
        "updated_by_id",
    },
    "field_map": {
        "calling_port_seq": "port_seq",
        "port_id": "port_code",
        "pilot_in_hours": "pilot_in_minutes",
        "pilot_out_hours": "pilot_out_minutes",
        "sea_time_hours": "sea_sailing_time",
    },
}

# CascadingVesselPosition (vessel_positions) 필드 설정
PROFORMA_VESSEL_POSITION_FIELDS = {
    "exclude": {
        "id",
        "scenario_id",
        "proforma_id",
        "created_at",
        "created_by_id",
        "updated_at",
        "updated_by_id",
    },
}

# LaneProformaMapping 필드 설정
PROFORMA_LANE_MAPPING_FIELDS = {
    "exclude": {
        "id",
        "scenario_id",
        "lane_id",
        "proforma_id",
        "created_at",
        "created_by_id",
        "updated_at",
        "updated_by_id",
    },
}

# Export 파일 저장 경로 (MEDIA_ROOT 기준)
EXPORT_BASE_DIR = "exports/scenarios"

# ZIP 파일명 패턴
ZIP_FILENAME_PATTERN = "scenario_{scenario_id}_data.zip"

# Celery task 결과 만료 시간 (초)
EXPORT_RESULT_EXPIRE_SECONDS = 3600  # 1시간

# 생성된 ZIP 파일 자동 삭제 시간 (초)
EXPORT_FILE_EXPIRE_SECONDS = 86400  # 24시간
