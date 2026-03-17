# common/json_configs.py
"""
JSON Export/Import 설정 모듈

CSV는 flat 구조 (1행 = 1레코드)이지만,
JSON은 중첩(nested) 구조를 지원하므로 Master-Detail 관계를 계층적으로 표현할 수 있다.

■ 설정 구조
  각 config는 딕셔너리이며 다음 키를 가진다:

  {
      "root_key": "proforma_schedules",
      "fields": [(json_key, model_field, required), ...],
      "children": [
          {
              "key": "details",
              "related_name": "details",
              "fields": [(json_key, model_field, required), ...],
          },
      ],
  }

  - required: True이면 Import 시 빈 값인 행을 skip한다.
              Export 시에는 무시된다.
  - model_field에 "."이 포함되면 Import 시 무시한다. (scenario.code 등)
"""

# =========================================================
# Schedule Group — 다층 구조
# =========================================================

PROFORMA_SCHEDULE_JSON = {
    "root_key": "proforma_schedules",
    "scenario_field": "scenario.code",
    "prefetch": ["details"],
    "fields": [
        ("scenario_code", "scenario.code", False),
        ("lane_code", "lane_id", True),
        ("proforma_name", "proforma_name", True),
        ("effective_from_date", "effective_from_date", True),
        ("effective_to_date", "effective_to_date", False),
        ("duration", "duration", True),
        ("declared_capacity", "declared_capacity", True),
        ("declared_count", "declared_count", True),
        ("own_vessel_count", "own_vessel_count", False),
    ],
    "children": [
        {
            "key": "details",
            "related_name": "details",
            "order_by": "calling_port_seq",
            "fields": [
                ("calling_port_seq", "calling_port_seq", True),
                ("direction", "direction", True),
                ("port_code", "port_id", True),
                ("calling_port_indicator", "calling_port_indicator", True),
                ("turn_port_info_code", "turn_port_info_code", False),
                ("pilot_in_hours", "pilot_in_hours", False),
                ("etb_day_number", "etb_day_number", True),
                ("etb_day_code", "etb_day_code", True),
                ("etb_day_time", "etb_day_time", True),
                ("actual_work_hours", "actual_work_hours", False),
                ("etd_day_number", "etd_day_number", False),
                ("etd_day_code", "etd_day_code", False),
                ("etd_day_time", "etd_day_time", False),
                ("pilot_out_hours", "pilot_out_hours", False),
                ("link_distance", "link_distance", False),
                ("link_eca_distance", "link_eca_distance", False),
                ("link_speed", "link_speed", False),
                ("sea_time_hours", "sea_time_hours", False),
                ("terminal_code", "terminal_code", False),
            ],
        },
    ],
}

CASCADING_VESSEL_POSITION_JSON = {
    "root_key": "cascading_vessel_positions",
    "scenario_field": "scenario.code",
    "prefetch": ["cascading_positions"],
    "fields": [
        ("scenario_code", "scenario.code", False),
        ("lane_code", "proforma.lane_id", True),
        ("proforma_name", "proforma.proforma_name", True),
    ],
    "source_model_key": "proforma",
    "children": [
        {
            "key": "positions",
            "related_name": "cascading_positions",
            "order_by": "vessel_position",
            "fields": [
                ("vessel_position", "vessel_position", True),
                ("vessel_code", "vessel_code", True),
                ("vessel_position_date", "vessel_position_date", True),
            ],
        },
    ],
}

# =========================================================
# Vessel Group — 다층 구조
# =========================================================

VESSEL_FULL_JSON = {
    "root_key": "vessels",
    "scenario_field": "scenario.code",
    "fields": [
        ("scenario_code", "scenario.code", False),
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
    ],
}


# =========================================================
# Cost Group — flat 구조
# =========================================================

CANAL_FEE_JSON = {
    "root_key": "canal_fees",
    "scenario_field": "scenario.code",
    "fields": [
        ("scenario_code", "scenario.code", False),
        ("vessel_code", "vessel_code", True),
        ("direction", "direction", True),
        ("port_code", "port_id", True),
        ("canal_fee", "canal_fee", True),
    ],
}

DISTANCE_JSON = {
    "root_key": "distances",
    "scenario_field": "scenario.code",
    "fields": [
        ("scenario_code", "scenario.code", False),
        ("from_port_code", "from_port_id", True),
        ("to_port_code", "to_port_id", True),
        ("distance", "distance", True),
        ("eca_distance", "eca_distance", True),
    ],
}

TS_COST_JSON = {
    "root_key": "ts_costs",
    "scenario_field": "scenario.code",
    "fields": [
        ("scenario_code", "scenario.code", False),
        ("base_year_month", "base_year_month", True),
        ("lane_code", "lane_id", True),
        ("port_code", "port_id", True),
        ("ts_cost", "ts_cost", True),
    ],
}


# =========================================================
# Bunker Group — flat 구조
# =========================================================

BUNKER_CONSUMPTION_SEA_JSON = {
    "root_key": "bunker_consumption_sea",
    "scenario_field": "scenario.code",
    "fields": [
        ("scenario_code", "scenario.code", False),
        ("vessel_capacity", "vessel_capacity", True),
        ("sea_speed", "sea_speed", True),
        ("bunker_consumption", "bunker_consumption", True),
    ],
}

BUNKER_CONSUMPTION_PORT_JSON = {
    "root_key": "bunker_consumption_port",
    "scenario_field": "scenario.code",
    "fields": [
        ("scenario_code", "scenario.code", False),
        ("vessel_capacity", "vessel_capacity", True),
        ("port_stay_bunker_consumption", "port_stay_bunker_consumption", True),
        ("idling_bunker_consumption", "idling_bunker_consumption", True),
        ("pilot_inout_bunker_consumption", "pilot_inout_bunker_consumption", True),
    ],
}

BUNKER_PRICE_JSON = {
    "root_key": "bunker_prices",
    "scenario_field": "scenario.code",
    "fields": [
        ("scenario_code", "scenario.code", False),
        ("base_year_month", "base_year_month", True),
        ("trade_code", "trade_id", True),
        ("lane_code", "lane_id", True),
        ("bunker_type", "bunker_type", True),
        ("bunker_price", "bunker_price", True),
    ],
}


# =========================================================
# Master Group — flat, 시나리오 없음
# =========================================================

MASTER_TRADE_JSON = {
    "root_key": "trades",
    "fields": [
        ("trade_code", "trade_code", True),
        ("trade_name", "trade_name", True),
        ("from_continent_code", "from_continent_code", False),
        ("to_continent_code", "to_continent_code", False),
    ],
}

MASTER_PORT_JSON = {
    "root_key": "ports",
    "fields": [
        ("port_code", "port_code", True),
        ("port_name", "port_name", True),
        ("continent_code", "continent_code", False),
        ("country_code", "country_code", False),
    ],
}

MASTER_LANE_JSON = {
    "root_key": "lanes",
    "fields": [
        ("lane_code", "lane_code", True),
        ("lane_name", "lane_name", True),
        ("vessel_service_type_code", "vessel_service_type_code", False),
        ("effective_from_date", "effective_from_date", False),
        ("effective_to_date", "effective_to_date", False),
        ("feeder_division_code", "feeder_division_code", False),
    ],
}

MASTER_WEEK_PERIOD_JSON = {
    "root_key": "week_periods",
    "fields": [
        ("base_year", "base_year", True),
        ("base_week", "base_week", True),
        ("base_month", "base_month", False),
        ("week_start_date", "week_start_date", True),
        ("week_end_date", "week_end_date", True),
    ],
}
