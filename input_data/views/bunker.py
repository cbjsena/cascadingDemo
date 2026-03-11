"""
Bunker 관련 뷰 (Config 기반 공통 CRUD).
Bunker Consumption Sea / Port / Bunker Price 모두 공통 팩토리 사용.
"""

from decimal import Decimal

from common.constants import SEA_SPEED_MAX, SEA_SPEED_MIN, SEA_SPEED_STEP
from common.csv_configs import (
    BUNKER_CONSUMPTION_PORT_CSV_MAP,
    BUNKER_CONSUMPTION_SEA_CSV_MAP,
    BUNKER_PRICE_CSV_MAP,
)
from common.menus import MenuGroup, MenuItem
from common.utils.date_utils import get_scenario_base_year_month_choices
from input_data.models import (
    BunkerConsumptionPort,
    BunkerConsumptionSea,
    BunkerPrice,
    MasterLane,
    MasterTrade,
)

from ._crud_base import scenario_crud_view


def _get_sea_speed_choices():
    """SEA_SPEED_MIN ~ SEA_SPEED_MAX 범위의 0.5 단위 speed 목록을 반환한다."""
    speeds = []
    current = Decimal(str(SEA_SPEED_MIN))
    max_speed = Decimal(str(SEA_SPEED_MAX))
    step = Decimal(str(SEA_SPEED_STEP))
    while current <= max_speed:
        speeds.append(float(current))
        current += step
    return speeds


# =========================================================
# 1. Bunker Consumption Sea
# =========================================================
bunker_consumption_sea_list = scenario_crud_view(
    {
        "model": BunkerConsumptionSea,
        "url_name": "input_data:bunker_consumption_sea_list",
        "view_name": "bunker_consumption_sea_list",
        "template": "input_data/bunker_consumption_sea_list.html",
        "page_title": "Bunker Consumption Sea",
        "label": "bunker consumption sea",
        "menu_group": MenuGroup.BUNKER,
        "menu_item": MenuItem.BUNKER_CONSUMPTION_SEA,
        "queryset_fn": lambda scenario_id="": (
            BunkerConsumptionSea.objects.select_related("scenario").filter(
                scenario_id=scenario_id
            )
            if scenario_id
            else BunkerConsumptionSea.objects.none()
        ).order_by("base_year_month", "vessel_capacity", "sea_speed"),
        "search_filter_fn": lambda qs, s: (
            qs.filter(vessel_capacity__icontains=s) | qs.filter(sea_speed__icontains=s)
        ),
        "extra_search_fields": [
            {
                "param": "base_year_month",
                "filter_kwarg": "base_year_month",
            },
        ],
        "extra_context": {
            "base_year_month_choices": get_scenario_base_year_month_choices,
            "sea_speed_choices": _get_sea_speed_choices,
        },
        "fields": [
            {"post_key": "new_base_year_month", "model_field": "base_year_month"},
            {"post_key": "new_vessel_capacity", "model_field": "vessel_capacity"},
            {"post_key": "new_sea_speed", "model_field": "sea_speed"},
            {"post_key": "new_bunker_consumption", "model_field": "bunker_consumption"},
        ],
        "unique_fields": ["base_year_month", "vessel_capacity", "sea_speed"],
        "csv_map": BUNKER_CONSUMPTION_SEA_CSV_MAP,
        "dt_columns": [
            "",  # 0. Checkbox (정렬 제외)
            "",  # 1. No (순번, 정렬 제외)
            "base_year_month",  # 2. Base Year Month
            "vessel_capacity",  # 3. Vessel Capacity
            "sea_speed",  # 4. Sea Speed
            "bunker_consumption",  # 5. Bunker Consumption
        ],
        "serialize_fn": lambda obj: {
            "id": obj.id,
            "base_year_month": obj.base_year_month,
            "vessel_capacity": obj.vessel_capacity,
            "sea_speed": float(obj.sea_speed) if obj.sea_speed else 0,
            "bunker_consumption": (
                float(obj.bunker_consumption) if obj.bunker_consumption else 0
            ),
        },
    }
)

# =========================================================
# 2. Bunker Consumption Port
# =========================================================
bunker_consumption_port_list = scenario_crud_view(
    {
        "model": BunkerConsumptionPort,
        "url_name": "input_data:bunker_consumption_port_list",
        "view_name": "bunker_consumption_port_list",
        "template": "input_data/bunker_consumption_port_list.html",
        "page_title": "Bunker Consumption Port",
        "label": "bunker consumption port",
        "menu_group": MenuGroup.BUNKER,
        "menu_item": MenuItem.BUNKER_CONSUMPTION_PORT,
        "queryset_fn": lambda scenario_id="": (
            BunkerConsumptionPort.objects.select_related("scenario").filter(
                scenario_id=scenario_id
            )
            if scenario_id
            else BunkerConsumptionPort.objects.none()
        ).order_by("base_year_month", "vessel_capacity"),
        "search_filter_fn": lambda qs, s: (qs.filter(vessel_capacity__icontains=s)),
        "extra_search_fields": [
            {
                "param": "base_year_month",
                "filter_kwarg": "base_year_month",
            },
        ],
        "extra_context": {
            "base_year_month_choices": get_scenario_base_year_month_choices,
        },
        "fields": [
            {"post_key": "new_base_year_month", "model_field": "base_year_month"},
            {"post_key": "new_vessel_capacity", "model_field": "vessel_capacity"},
            {
                "post_key": "new_port_stay_bunker_consumption",
                "model_field": "port_stay_bunker_consumption",
            },
            {
                "post_key": "new_idling_bunker_consumption",
                "model_field": "idling_bunker_consumption",
            },
            {
                "post_key": "new_pilot_inout_bunker_consumption",
                "model_field": "pilot_inout_bunker_consumption",
            },
        ],
        "unique_fields": ["base_year_month", "vessel_capacity"],
        "csv_map": BUNKER_CONSUMPTION_PORT_CSV_MAP,
    }
)


# =========================================================
# 3. Bunker Price
# =========================================================
def _get_trade_choices():
    """MasterTrade에서 선택 목록 반환"""
    return MasterTrade.objects.all().order_by("trade_code")


def _get_lane_choices():
    """MasterLane에서 선택 목록 반환"""
    return MasterLane.objects.all().order_by("lane_code")


bunker_price_list = scenario_crud_view(
    {
        "model": BunkerPrice,
        "url_name": "input_data:bunker_price_list",
        "view_name": "bunker_price_list",
        "template": "input_data/bunker_price_list.html",
        "page_title": "Bunker Price",
        "label": "bunker price",
        "menu_group": MenuGroup.BUNKER,
        "menu_item": MenuItem.BUNKER_PRICE,
        "queryset_fn": lambda scenario_id="": (
            BunkerPrice.objects.select_related("scenario", "trade", "lane").filter(
                scenario_id=scenario_id
            )
            if scenario_id
            else BunkerPrice.objects.none()
        ).order_by("base_year_month", "trade_id", "lane_id", "bunker_type"),
        "search_filter_fn": lambda qs, s: (
            qs.filter(trade__trade_code__icontains=s)
            | qs.filter(lane__lane_code__icontains=s)
            | qs.filter(bunker_type__icontains=s)
        ),
        "extra_search_fields": [
            {
                "param": "base_year_month",
                "filter_kwarg": "base_year_month",
            },
        ],
        "extra_context": {
            "base_year_month_choices": get_scenario_base_year_month_choices,
            "trade_choices": _get_trade_choices,
            "lane_choices": _get_lane_choices,
        },
        "fields": [
            {"post_key": "new_base_year_month", "model_field": "base_year_month"},
            {"post_key": "new_trade", "model_field": "trade_id"},
            {"post_key": "new_lane", "model_field": "lane_id"},
            {"post_key": "new_bunker_type", "model_field": "bunker_type"},
            {"post_key": "new_bunker_price", "model_field": "bunker_price"},
        ],
        "unique_fields": ["base_year_month", "trade_id", "lane_id", "bunker_type"],
        "csv_map": BUNKER_PRICE_CSV_MAP,
    }
)
