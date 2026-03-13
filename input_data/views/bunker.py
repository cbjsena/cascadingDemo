"""
Bunker 관련 뷰 (Config 기반 공통 CRUD).
Bunker Consumption Sea / Port / Bunker Price 모두 공통 팩토리 사용.
"""

from decimal import Decimal

from django.db.models import CharField, Q
from django.db.models.functions import Cast

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
        ).order_by("vessel_capacity", "sea_speed"),
        "search_filter_fn": lambda qs, s: (
            qs.annotate(
                vc_str=Cast("vessel_capacity", output_field=CharField()),
                ss_str=Cast("sea_speed", output_field=CharField()),
            ).filter(Q(vc_str__icontains=s) | Q(ss_str__icontains=s))
        ),
        "extra_search_fields": [
            {
                "param": "vessel_capacity",
                "filter_kwarg": "vessel_capacity",
            },
            {
                "param": "sea_speed",
                "filter_kwarg": "sea_speed",
            },
        ],
        "extra_context": {
            "sea_speed_choices": _get_sea_speed_choices,
        },
        "fields": [
            {"post_key": "new_vessel_capacity", "model_field": "vessel_capacity"},
            {"post_key": "new_sea_speed", "model_field": "sea_speed"},
            {"post_key": "new_bunker_consumption", "model_field": "bunker_consumption"},
        ],
        "unique_fields": ["vessel_capacity", "sea_speed"],
        "csv_map": BUNKER_CONSUMPTION_SEA_CSV_MAP,
        "max_rows": 1000,
        "dt_columns": [
            "",  # 0. Checkbox (정렬 제외)
            "",  # 1. No (순번, 정렬 제외)
            "vessel_capacity",  # 2. Vessel Capacity
            "sea_speed",  # 3. Sea Speed
            "bunker_consumption",  # 4. Bunker Consumption
        ],
        "serialize_fn": lambda obj: {
            "id": obj.id,
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
        ).order_by("vessel_capacity"),
        "search_filter_fn": lambda qs, s: (
            qs.annotate(
                vc_str=Cast("vessel_capacity", output_field=CharField()),
            ).filter(Q(vc_str__icontains=s))
        ),
        "extra_search_fields": [
            {
                "param": "vessel_capacity",
                "filter_kwarg": "vessel_capacity",
            },
        ],
        "extra_context": {},
        "fields": [
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
        "unique_fields": ["vessel_capacity"],
        "csv_map": BUNKER_CONSUMPTION_PORT_CSV_MAP,
        "dt_columns": [
            "",  # 0. Checkbox (정렬 제외)
            "",  # 1. No (순번, 정렬 제외)
            "vessel_capacity",  # 2. Vessel Capacity
            "port_stay_bunker_consumption",  # 3. Port Stay
            "idling_bunker_consumption",  # 4. Idling
            "pilot_inout_bunker_consumption",  # 5. Pilot In/Out
        ],
        "serialize_fn": lambda obj: {
            "id": obj.id,
            "vessel_capacity": obj.vessel_capacity,
            "port_stay_bunker_consumption": (
                float(obj.port_stay_bunker_consumption)
                if obj.port_stay_bunker_consumption
                else 0
            ),
            "idling_bunker_consumption": (
                float(obj.idling_bunker_consumption)
                if obj.idling_bunker_consumption
                else 0
            ),
            "pilot_inout_bunker_consumption": (
                float(obj.pilot_inout_bunker_consumption)
                if obj.pilot_inout_bunker_consumption
                else 0
            ),
        },
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


def _get_bunker_price_trades(scenario_id):
    """BunkerPrice에서 존재하는 Trade만 선택 목록 반환"""
    if not scenario_id:
        return []
    # 선택된 시나리오의 BunkerPrice 데이터 중 null이 아닌 trade_id만 중복 없이 추출하여 오름차순 정렬
    return list(
        BunkerPrice.objects.filter(scenario_id=scenario_id)
        .exclude(trade_id__isnull=True)
        .values_list("trade_id", flat=True)
        .distinct()
        .order_by("trade_id")
        .order_by("trade_id")
    )


def _get_bunker_price_lanes(scenario_id):
    if not scenario_id:
        return []
    # 선택된 시나리오의 BunkerPrice 데이터 중 null이 아닌 lane_id만 중복 없이 추출하여 오름차순 정렬
    return list(
        BunkerPrice.objects.filter(scenario_id=scenario_id)
        .exclude(lane_id__isnull=True)
        .values_list("lane_id", flat=True)
        .distinct()
        .order_by("lane_id")
    )


def _get_bunker_price_types(scenario_id):
    if not scenario_id:
        return []
    # 선택된 시나리오의 BunkerPrice 데이터 중 null이 아닌 bunker_type만 중복 없이 추출하여 오름차순 정렬
    return list(
        BunkerPrice.objects.filter(scenario_id=scenario_id)
        .exclude(bunker_type__isnull=True)
        .values_list("bunker_type", flat=True)
        .distinct()
        .order_by("bunker_type")
    )


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
            {"param": "base_year_month", "filter_kwarg": "base_year_month"},
            {"param": "trade", "filter_kwarg": "trade__trade_code"},
            {"param": "lane", "filter_kwarg": "lane__lane_code"},
            {"param": "bunker_type", "filter_kwarg": "bunker_type"},
        ],
        "extra_context": {
            "base_year_month_choices": get_scenario_base_year_month_choices,
            "filter_trades": _get_bunker_price_trades,
            "filter_lanes": _get_bunker_price_lanes,
            "filter_bunker_types": _get_bunker_price_types,
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
        "dt_columns": [
            "",  # 0. Checkbox
            "",  # 1. No
            "base_year_month",  # 2. Base Year Month
            "trade__trade_code",  # 3. Trade (FK 참조)
            "lane__lane_code",  # 4. Lane (FK 참조)
            "bunker_type",  # 5. Bunker Type
            "bunker_price",  # 6. Bunker Price
        ],
        "serialize_fn": lambda obj: {
            "id": obj.id,
            "base_year_month": obj.base_year_month,
            "trade": obj.trade.trade_code if obj.trade else (obj.trade_id or ""),
            "lane": obj.lane.lane_code if obj.lane else (obj.lane_id or ""),
            "bunker_type": obj.bunker_type,
            "bunker_price": float(obj.bunker_price) if obj.bunker_price else 0,
        },
    }
)
