"""
Cost 관련 뷰 (Config 기반 공통 CRUD).
Canal Fee, Distance, TS Cost 모두 공통 팩토리 사용.
"""

from common.csv_configs import CANAL_FEE_CSV_MAP, DISTANCE_CSV_MAP, TS_COST_CSV_MAP
from common.menus import MenuGroup, MenuItem
from common.utils.date_utils import get_scenario_base_year_month_choices
from input_data.models import (
    CanalFee,
    Distance,
    MasterLane,
    MasterPort,
    TSCost,
)

from ._crud_base import scenario_crud_view

# =========================================================
# 1. Canal Fee
# =========================================================
canal_fee_list = scenario_crud_view(
    {
        "model": CanalFee,
        "url_name": "input_data:canal_fee_list",
        "view_name": "canal_fee_list",
        "template": "input_data/canal_fee_list.html",
        "page_title": "Canal Fee",
        "label": "canal fee",
        "menu_group": MenuGroup.COST,
        "menu_item": MenuItem.CANAL_FEE,
        "queryset_fn": lambda: (
            CanalFee.objects.select_related("scenario", "port")
            .all()
            .order_by("scenario", "vessel_code", "direction", "port")
        ),
        "search_filter_fn": lambda qs, s: (
            qs.filter(vessel_code__icontains=s)
            | qs.filter(port__port_code__icontains=s)
        ),
        "extra_context": {
            "ports": lambda: MasterPort.objects.all().order_by("port_code"),
        },
        "fields": [
            {"post_key": "new_vessel_code", "model_field": "vessel_code"},
            {"post_key": "new_direction", "model_field": "direction"},
            {"post_key": "new_port_code", "model_field": "port_id"},
            {"post_key": "new_canal_fee", "model_field": "canal_fee"},
        ],
        "lookup_fields": ["vessel_code", "direction", "port_id"],
        "defaults_fields": ["canal_fee"],
        "csv_map": CANAL_FEE_CSV_MAP,
    }
)

# =========================================================
# 2. Distance
# =========================================================
distance_list = scenario_crud_view(
    {
        "model": Distance,
        "url_name": "input_data:distance_list",
        "view_name": "distance_list",
        "template": "input_data/distance_list.html",
        "page_title": "Distance",
        "label": "distance",
        "menu_group": MenuGroup.COST,
        "menu_item": MenuItem.DISTANCE,
        "queryset_fn": lambda: (
            Distance.objects.select_related("scenario", "from_port", "to_port")
            .all()
            .order_by("scenario", "from_port", "to_port")
        ),
        "search_filter_fn": lambda qs, s: (
            qs.filter(from_port__port_code__icontains=s)
            | qs.filter(to_port__port_code__icontains=s)
        ),
        "extra_context": {
            "ports": lambda: MasterPort.objects.all().order_by("port_code"),
        },
        "fields": [
            {"post_key": "new_from_port", "model_field": "from_port_id"},
            {"post_key": "new_to_port", "model_field": "to_port_id"},
            {"post_key": "new_distance", "model_field": "distance"},
            {"post_key": "new_eca_distance", "model_field": "eca_distance"},
        ],
        "lookup_fields": ["from_port_id", "to_port_id"],
        "defaults_fields": ["distance", "eca_distance"],
        "csv_map": DISTANCE_CSV_MAP,
    }
)

# =========================================================
# 3. TS Cost
# =========================================================
ts_cost_list = scenario_crud_view(
    {
        "model": TSCost,
        "url_name": "input_data:ts_cost_list",
        "view_name": "ts_cost_list",
        "template": "input_data/ts_cost_list.html",
        "page_title": "TS Cost",
        "label": "TS cost",
        "menu_group": MenuGroup.COST,
        "menu_item": MenuItem.TS_COST,
        "queryset_fn": lambda: (
            TSCost.objects.select_related("scenario", "lane", "port")
            .all()
            .order_by("scenario", "base_year_month", "lane", "port")
        ),
        "search_filter_fn": lambda qs, s: (
            qs.filter(lane__lane_code__icontains=s)
            | qs.filter(port__port_code__icontains=s)
        ),
        "extra_search_fields": [
            {
                "param": "base_year_month",
                "filter_kwarg": "base_year_month",
            },
        ],
        "extra_context": {
            "base_year_month_choices": get_scenario_base_year_month_choices,
            "lanes": lambda: MasterLane.objects.all().order_by("lane_code"),
            "ports": lambda: MasterPort.objects.all().order_by("port_code"),
        },
        "fields": [
            {"post_key": "new_base_year_month", "model_field": "base_year_month"},
            {"post_key": "new_lane_code", "model_field": "lane_id"},
            {"post_key": "new_port_code", "model_field": "port_id"},
            {"post_key": "new_ts_cost", "model_field": "ts_cost"},
        ],
        "unique_fields": ["base_year_month", "lane_id", "port_id"],
        "csv_map": TS_COST_CSV_MAP,
    }
)
