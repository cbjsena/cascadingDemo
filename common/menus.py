# common/menus.py (파일 생성 추천)
MENU_STRUCTURE = {
    "Schedule": [
        {"name": "Proforma Schedule", "key": "proforma_schedule"},
        {"name": "Long Range Schedule", "key": "long_range_schedule"},
    ],
    "Vessel": [
        {"name": "Vessel Info", "key": "vessel_info"},
        {"name": "Charter Cost", "key": "charter_cost"},
        {"name": "Vessel Capacity", "key": "vessel_capacity"},
    ],
    "Cost": [
        {"name": "Canal Fee", "key": "canal_fee"},
        {"name": "Distance", "key": "distance"},
        {"name": "Exchange Rate", "key": "exchange_rate"},
        # {"name": "Own Vessel Cost", "key": "own_vessel_cost"},
        # {"name": "Port Charge", "key": "port_charge"},
        {"name": "TS Cost", "key": "ts_cost"},
    ],
    "Bunker": [
        {"name": "Bunker Consumption Sea", "key": "bunker_consumption_sea"},
        {"name": "Bunker Consumption Port", "key": "bunker_consumption_port"},
        # {"name": "Bunkering Port", "key": "bunkering_port"},
        {"name": "Bunker Price", "key": "bunker_price"},
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