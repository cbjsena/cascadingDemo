# common/menus.py (파일 생성 추천)


# 메뉴 섹션 상수
class MenuSection:
    CREATION = "creation"
    INPUT_MANAGEMENT = "input_management"


# 메뉴 그룹 상수
class MenuGroup:
    SCHEDULE = "Schedule"
    MASTER = "Master"
    VESSEL = "Vessel"
    COST = "Cost"
    BUNKER = "Bunker"
    CONSTRAINT = "Constraint"


# 메뉴 모델 상수 (현재 활성화된 메뉴 항목)
class MenuItem:
    # Creation - Schedule
    PROFORMA_CREATE = "proforma_create"
    CASCADING_CREATE = "cascading_create"

    # Input Management - Schedule
    PROFORMA_SCHEDULE = "proforma_schedule"
    CASCADING_SCHEDULE = "cascading_schedule"
    LONG_RANGE_SCHEDULE = "long_range_schedule"

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
            "name": "Cascading Creation",
            "url_name": "input_data:cascading_create",
            "key": MenuItem.CASCADING_CREATE,
        },
    ],
    MenuGroup.MASTER: [
        {"name": "Lane Info", "key": "lane_info", "url_name": None},
        {"name": "Port Info", "key": "port_info", "url_name": None},
        # ... 기타 항목들 ...
    ],
}

# Input Management 메뉴 구조
MENU_STRUCTURE = {
    MenuGroup.SCHEDULE: [
        {
            "name": "Proforma Schedule",
            "key": MenuItem.PROFORMA_SCHEDULE,
            "url_name": "input_data:proforma_list",
        },
        {
            "name": "Cascading Schedule",
            "key": MenuItem.CASCADING_SCHEDULE,
            "url_name": "input_data:cascading_list",
        },
        {
            "name": "Long Range Schedule",
            "key": MenuItem.LONG_RANGE_SCHEDULE,
            "url_name": "input_data:long_range_list",
        },
    ],
    MenuGroup.VESSEL: [
        {"name": "Vessel Info", "key": "vessel_info"},
        {"name": "Charter Cost", "key": "charter_cost"},
        {"name": "Vessel Capacity", "key": "vessel_capacity"},
    ],
    MenuGroup.COST: [
        {"name": "Canal Fee", "key": "canal_fee"},
        {"name": "Distance", "key": "distance"},
        {"name": "TS Cost", "key": "ts_cost"},
        # {"name": "Exchange Rate", "key": "exchange_rate"},
        # {"name": "Own Vessel Cost", "key": "own_vessel_cost"},
        # {"name": "Port Charge", "key": "port_charge"},
    ],
    MenuGroup.BUNKER: [
        {"name": "Bunker Consumption Sea", "key": "bunker_consumption_sea"},
        {"name": "Bunker Consumption Port", "key": "bunker_consumption_port"},
        # {"name": "Bunkering Port", "key": "bunkering_port"},
        {"name": "Bunker Price", "key": "bunker_price"},
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
