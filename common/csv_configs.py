# common/csv_configs.py

# --- CSV Config ---
# List of Tuples: (DB Column Name, ORM field name or accessor key, required)
#
# - DB Column Name  : CSV 헤더로 사용 (다운로드/업로드 모두 동일)
# - ORM Field Name  : Model.objects.create()에 전달되는 필드명
#                     "scenario_code"는 특수 키 → 다운로드 시 scenario.code 출력, 업로드 시 무시
# - Required        : 업로드 시 빈 값이면 해당 행을 건너뜀 (True/False)
#
# 첫 번째 항목은 반드시 ("scenario_code", "scenario_code", False) 이어야 한다.
# → 다운로드 시 시나리오 코드 출력, 업로드 시 해당 컬럼 무시 (POST의 scenario_id 사용)

# --- Proforma DB Upload CSV Config ---
# List of Tuples: (CSV Header Name, Data Key)
# Data Key는 Service에서 계산된 Context 딕셔너리의 키와 일치해야 합니다.

PROFORMA_DB_MAP = [
    ("lane_code", "lane_code"),
    ("proforma_name", "proforma_name"),
    ("effective_from_date", "effective_from_date"),
    ("duration", "duration"),
    ("declared_capacity", "capacity"),
    ("declared_count", "count"),
    ("direction", "direction"),
    ("port_code", "port_code"),
    ("calling_port_indicator", "clg_seq"),  # Logic 계산 필드 (Sequence)
    ("calling_port_seq", "port_seq"),
    ("turn_port_info_code", "turn_port_info_code"),
    ("pilot_in_hours", "pilot_in"),
    ("etb_day_number", "etb_no"),
    ("etb_day_code", "etb_day"),
    ("etb_day_time", "etb_time"),
    ("actual_work_hours", "work_hours"),
    ("etd_day_number", "etd_no"),
    ("etd_day_code", "etd_day"),
    ("etd_day_time", "etd_time"),
    ("pilot_out_hours", "pilot_out"),
    ("link_distance", "dist"),
    ("link_eca_distance", "eca_dist"),
    ("link_speed", "spd"),
    ("sea_time_hours", "sea_time"),
    ("terminal_code", "terminal"),
]


# =========================================================
# Vessel Group
# =========================================================

VESSEL_INFO_CSV_MAP = [
    ("scenario_code", "scenario_code", False),
    ("vessel_code", "vessel_code", True),
    ("vessel_name", "vessel_name", True),
    ("own_yn", "own_yn", True),
    ("delivery_port_code", "delivery_port_code", False),
    ("delivery_date", "delivery_date", False),
    ("redelivery_port_code", "redelivery_port_code", False),
    ("redelivery_date", "redelivery_date", False),
    ("next_dock_port_code", "next_dock_port_code", False),
    ("next_dock_in_date", "next_dock_in_date", False),
    ("next_dock_out_date", "next_dock_out_date", False),
]

CHARTER_COST_CSV_MAP = [
    ("scenario_code", "scenario_code", False),
    ("vessel_code", "vessel_code", True),
    ("hire_from_date", "hire_from_date", True),
    ("hire_to_date", "hire_to_date", True),
    ("hire_rate", "hire_rate", True),
]

VESSEL_CAPACITY_CSV_MAP = [
    ("scenario_code", "scenario_code", False),
    ("trade_code", "trade_id", True),
    ("lane_code", "lane_id", True),
    ("vessel_code", "vessel_code", True),
    ("voyage_number", "voyage_number", True),
    ("direction", "direction", True),
    ("vessel_capacity", "vessel_capacity", True),
    ("reefer_capacity", "reefer_capacity", True),
]


# =========================================================
# Cost Group
# =========================================================

CANAL_FEE_CSV_MAP = [
    ("scenario_code", "scenario_code", False),
    ("vessel_code", "vessel_code", True),
    ("direction", "direction", True),
    ("port_code", "port_id", True),
    ("canal_fee", "canal_fee", True),
]

DISTANCE_CSV_MAP = [
    ("scenario_code", "scenario_code", False),
    ("from_port_code", "from_port_id", True),
    ("to_port_code", "to_port_id", True),
    ("distance", "distance", True),
    ("eca_distance", "eca_distance", True),
]

TS_COST_CSV_MAP = [
    ("scenario_code", "scenario_code", False),
    ("base_year_month", "base_year_month", True),
    ("lane_code", "lane_id", True),
    ("port_code", "port_id", True),
    ("ts_cost", "ts_cost", True),
]


# =========================================================
# Bunker Group
# =========================================================

BUNKER_CONSUMPTION_SEA_CSV_MAP = [
    ("scenario_code", "scenario_code", False),
    ("vessel_capacity", "vessel_capacity", True),
    ("sea_speed", "sea_speed", True),
    ("bunker_consumption", "bunker_consumption", True),
]

BUNKER_CONSUMPTION_PORT_CSV_MAP = [
    ("scenario_code", "scenario_code", False),
    ("vessel_capacity", "vessel_capacity", True),
    ("port_stay_bunker_consumption", "port_stay_bunker_consumption", True),
    ("idling_bunker_consumption", "idling_bunker_consumption", True),
    ("pilot_inout_bunker_consumption", "pilot_inout_bunker_consumption", True),
]

BUNKER_PRICE_CSV_MAP = [
    ("scenario_code", "scenario_code", False),
    ("base_year_month", "base_year_month", True),
    ("trade_code", "trade_id", True),
    ("lane_code", "lane_id", True),
    ("bunker_type", "bunker_type", True),
    ("bunker_price", "bunker_price", True),
]


# =========================================================
# Master Group (시나리오 독립 — scenario_code 컬럼 없음)
# =========================================================

MASTER_TRADE_CSV_MAP = [
    ("trade_code", "trade_code", True),
    ("trade_name", "trade_name", True),
    ("from_continent_code", "from_continent_code", False),
    ("to_continent_code", "to_continent_code", False),
]

MASTER_PORT_CSV_MAP = [
    ("port_code", "port_code", True),
    ("port_name", "port_name", True),
    ("continent_code", "continent_code", False),
    ("country_code", "country_code", False),
]

MASTER_LANE_CSV_MAP = [
    ("lane_code", "lane_code", True),
    ("lane_name", "lane_name", True),
    ("vessel_service_type_code", "vessel_service_type_code", False),
    ("effective_from_date", "effective_from_date", False),
    ("effective_to_date", "effective_to_date", False),
    ("feeder_division_code", "feeder_division_code", False),
]

MASTER_WEEK_PERIOD_CSV_MAP = [
    ("base_year", "base_year", True),
    ("base_week", "base_week", True),
    ("base_month", "base_month", False),
    ("week_start_date", "week_start_date", True),
    ("week_end_date", "week_end_date", True),
]
