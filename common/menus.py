# common/menus.py (파일 생성 추천)


# 메뉴 섹션 상수
class MenuSection:
    CREATION = "creation"
    INPUT_MANAGEMENT = "input_management"


# 메뉴 그룹 상수
class MenuGroup:
    MASTER = "Master"
    SCHEDULE = "Schedule"
    VESSEL = "Vessel"
    COST = "Cost"
    BUNKER = "Bunker"
    CONSTRAINT = "Constraint"


# 메뉴 모델 상수 (현재 활성화된 메뉴 항목)
class MenuItem:
    # Creation - Schedule
    PROFORMA_CREATE = "proforma_create"
    CASCADING_CREATE = "cascading_create"
    CASCADING_VESSEL_CREATE = "cascading_vessel_create"
    LANE_PROFORMA_MAPPING = "lane_proforma_mapping"

    # Input Management - Schedule
    PROFORMA_SCHEDULE = "proforma_schedule"
    LANE_PROFORMA_LIST = "lane_proforma_list"
    CASCADING_SCHEDULE = "cascading_schedule"
    CASCADING_VESSEL_INFO = "cascading_vessel_info"
    LONG_RANGE_SCHEDULE = "long_range_schedule"

    # Input Management - Master
    TRADE_INFO = "trade_info"
    PORT_INFO = "port_info"
    LANE_INFO = "lane_info"
    WEEK_PERIOD = "week_period"

    # Input Management - Vessel
    VESSEL_INFO = "vessel_info"
    CHARTER_COST = "charter_cost"
    VESSEL_CAPACITY = "vessel_capacity"

    # Input Management - Cost
    CANAL_FEE = "canal_fee"
    DISTANCE = "distance"
    TS_COST = "ts_cost"
    # EXCHANGE_RATE = "exchange_rate"
    # OWN_VESSEL_COST = "own_vessel_cost"
    # PORT_CHARGE = "port_charge"

    # Input Management - Bunker
    BUNKER_CONSUMPTION_SEA = "bunker_consumption_sea"
    BUNKER_CONSUMPTION_PORT = "bunker_consumption_port"
    BUNKER_PRICE = "bunker_price"

    # Input Management - Dashboard & Scenario
    DASHBOARD = "input_home"
    SCENARIO_LIST = "scenario_list"


# Creation 메뉴 구조 (별도 관리)
CREATION_MENU_STRUCTURE = {
    MenuGroup.SCHEDULE: [
        {
            "name": "Proforma Creation",
            "url_name": "input_data:proforma_create",
            "key": MenuItem.PROFORMA_CREATE,
        },
        {
            "name": "Lane Proforma Mapping",
            "url_name": "input_data:lane_proforma_mapping",
            "key": MenuItem.LANE_PROFORMA_MAPPING,
        },
        {
            "name": "Cascading Creation",
            "url_name": "input_data:cascading_create",
            "key": MenuItem.CASCADING_CREATE,
        },
        {
            "name": "Cascading Vessel Creation",
            "url_name": "input_data:cascading_vessel_create",
            "key": MenuItem.CASCADING_VESSEL_CREATE,
        },
    ],
}

# Master 메뉴 구조 (시나리오 독립 기준 데이터 - Scenario List 위에 배치)
MASTER_MENU_STRUCTURE = [
    {
        "name": "Trade Info",
        "key": MenuItem.TRADE_INFO,
        "url_name": "input_data:master_trade_list",
    },
    {
        "name": "Port Info",
        "key": MenuItem.PORT_INFO,
        "url_name": "input_data:master_port_list",
    },
    {
        "name": "Lane Info",
        "key": MenuItem.LANE_INFO,
        "url_name": "input_data:master_lane_list",
    },
    {
        "name": "Week Period",
        "key": MenuItem.WEEK_PERIOD,
        "url_name": "input_data:master_week_period_list",
    },
]

# Input Management 메뉴 구조 (시나리오 의존 데이터)
MENU_STRUCTURE = {
    MenuGroup.SCHEDULE: [
        {
            "name": "Proforma Schedule",
            "key": MenuItem.PROFORMA_SCHEDULE,
            "url_name": "input_data:proforma_list",
        },
        {
            "name": "Lane Proforma Mapping",
            "key": MenuItem.LANE_PROFORMA_LIST,
            "url_name": "input_data:lane_proforma_list",
        },
        {
            "name": "Cascading Schedule",
            "key": MenuItem.CASCADING_SCHEDULE,
            "url_name": "input_data:cascading_schedule_list",
        },
        {
            "name": "Cascading Vessel Info",
            "key": MenuItem.CASCADING_VESSEL_INFO,
            "url_name": "input_data:cascading_vessel_info",
        },
        {
            "name": "Long Range Schedule",
            "key": MenuItem.LONG_RANGE_SCHEDULE,
            "url_name": "input_data:long_range_list",
        },
    ],
    MenuGroup.VESSEL: [
        {
            "name": "Vessel Info",
            "key": MenuItem.VESSEL_INFO,
            "url_name": "input_data:vessel_info_list",
        },
        {
            "name": "Charter Cost",
            "key": MenuItem.CHARTER_COST,
            "url_name": "input_data:charter_cost_list",
        },
        {
            "name": "Vessel Capacity",
            "key": MenuItem.VESSEL_CAPACITY,
            "url_name": "input_data:vessel_capacity_list",
        },
    ],
    MenuGroup.COST: [
        {
            "name": "Canal Fee",
            "key": MenuItem.CANAL_FEE,
            "url_name": "input_data:canal_fee_list",
        },
        {
            "name": "Distance",
            "key": MenuItem.DISTANCE,
            "url_name": "input_data:distance_list",
        },
        {
            "name": "TS Cost",
            "key": MenuItem.TS_COST,
            "url_name": "input_data:ts_cost_list",
        },
        # {"name": "Exchange Rate", "key": "exchange_rate"},
        # {"name": "Own Vessel Cost", "key": "own_vessel_cost"},
        # {"name": "Port Charge", "key": "port_charge"},
    ],
    MenuGroup.BUNKER: [
        {
            "name": "Bunker Consumption Sea",
            "key": MenuItem.BUNKER_CONSUMPTION_SEA,
            "url_name": "input_data:bunker_consumption_sea_list",
        },
        {
            "name": "Bunker Consumption Port",
            "key": MenuItem.BUNKER_CONSUMPTION_PORT,
            "url_name": "input_data:bunker_consumption_port_list",
        },
        # {"name": "Bunkering Port", "key": "bunkering_port"},
        {
            "name": "Bunker Price",
            "key": MenuItem.BUNKER_PRICE,
            "url_name": "input_data:bunker_price_list",
        },
    ],
    MenuGroup.CONSTRAINT: [
        {"name": "Fix Lane Vessel", "key": "constraint_fixed_deployment"},
        {"name": "Fix Vessel Schedule", "key": "constraint_fixed_schedule_change"},
        {"name": "Constraint Port", "key": "constraint_port"},
    ],
    # "ETS & Fuel EU": [
    #     {"name": "ETS TS Port", "key": "ets_ts_port"},
    #     {"name": "ETS Country", "key": "ets_country"},
    #     {"name": "ETS Bunker Consumption", "key": "ets_bunker_consumption"},
    #     {"name": "ETS EUA", "key": "ets_eua"},
    #     {"name": "FUEL EU", "key": "fuel_eu"},
    #     {"name": "Fuel EU Bunker", "key": "fuel_eu_bunker"},
    #     {"name": "Greenhouse Gas Target", "key": "greenhouse_gas_target"},
    # ],
}
