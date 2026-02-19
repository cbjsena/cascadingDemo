# common/menus.py (파일 생성 추천)
MENU_STRUCTURE = {
    # 1. 생성 관련 메뉴 그룹
    "Creation Data": [
        {
            "name": "Proforma Creation",
            "url_name": "input_data:proforma_create",
            "key": "proforma_create",
        },
        {
            "name": "Long Range Creation",
            "url_name": "input_data:long_range_create",
            "key": "long_range_create",
        },
    ],
    # "Master Data": [
    #
    #     {"name": "Lane Info", "key": "lane_info", "url_name": None},
    #     {"name": "Port Info", "key": "port_info", "url_name": None},
    #     # ... 기타 항목들 ...
    # ],
    "Schedule": [
        {
            "name": "Proforma Schedule",
            "key": "proforma_schedule",
            "url_name": "input_data:proforma_list",
        },
        {
            "name": "Long Range Schedule",
            "key": "long_range_schedule",
            "url_name": "input_data:long_range_list",
        },
    ],
    "Vessel": [
        {"name": "Vessel Info", "key": "vessel_info"},
        {"name": "Charter Cost", "key": "charter_cost"},
        {"name": "Vessel Capacity", "key": "vessel_capacity"},
    ],
    "Cost": [
        {"name": "Canal Fee", "key": "canal_fee"},
        {"name": "Distance", "key": "distance"},
        {"name": "TS Cost", "key": "ts_cost"},
        # {"name": "Exchange Rate", "key": "exchange_rate"},
        # {"name": "Own Vessel Cost", "key": "own_vessel_cost"},
        # {"name": "Port Charge", "key": "port_charge"},
    ],
    "Bunker": [
        {"name": "Bunker Consumption Sea", "key": "bunker_consumption_sea"},
        {"name": "Bunker Consumption Port", "key": "bunker_consumption_port"},
        # {"name": "Bunkering Port", "key": "bunkering_port"},
        {"name": "Bunker Price", "key": "bunker_price"},
    ],
    "Constraint": [
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
