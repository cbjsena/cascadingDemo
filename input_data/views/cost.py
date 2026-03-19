"""
Cost 관련 뷰 (Config 기반 공통 CRUD).
Canal Fee, TS Cost: 시나리오 기반 팩토리 사용.
Distance: 시나리오 독립 (BaseDistance) — master_crud_view 사용.
"""

from common.csv_configs import CANAL_FEE_CSV_MAP, DISTANCE_CSV_MAP, TS_COST_CSV_MAP
from common.json_configs import CANAL_FEE_JSON, DISTANCE_JSON, TS_COST_JSON
from common.menus import MenuGroup, MenuItem
from common.utils.date_utils import get_scenario_base_year_month_choices
from input_data.models import (
    BaseDistance,
    CanalFee,
    MasterLane,
    MasterPort,
    TSCost,
)

from ._crud_base import scenario_crud_view
from .master import master_crud_view


# =========================================================
# [동적 필터용] 현재 시나리오의 데이터만 추출
# =========================================================
def _get_canal_fee_vessels(scenario_id):
    if not scenario_id:
        return []
    return list(
        CanalFee.objects.filter(scenario_id=scenario_id)
        .values_list("vessel_code", flat=True)
        .distinct()
        .order_by("vessel_code")
    )


def _get_canal_fee_ports(scenario_id):
    if not scenario_id:
        return []
    return list(
        CanalFee.objects.filter(scenario_id=scenario_id)
        .values_list("port", flat=True)
        .distinct()
        .order_by("port")
    )


def _get_ts_cost_lanes(scenario_id):
    if not scenario_id:
        return []
    return list(
        TSCost.objects.filter(scenario_id=scenario_id)
        .exclude(lane__isnull=True)
        .values_list("lane__lane_code", flat=True)
        .distinct()
        .order_by("lane__lane_code")
    )


def _get_ts_cost_ports(scenario_id):
    if not scenario_id:
        return []
    return list(
        TSCost.objects.filter(scenario_id=scenario_id)
        .exclude(port__isnull=True)
        .values_list("port__port_code", flat=True)
        .distinct()
        .order_by("port__port_code")
    )


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
        "queryset_fn": lambda scenario_id="": (
            CanalFee.objects.select_related("scenario", "port").filter(
                scenario_id=scenario_id
            )
            if scenario_id
            else CanalFee.objects.none()
        ).order_by("vessel_code", "direction", "port__port_code"),
        "search_filter_fn": lambda qs, s: (
            qs.filter(vessel_code__icontains=s)
            | qs.filter(port__port_code__icontains=s)
        ),
        "extra_search_fields": [
            {"param": "vessel_code", "filter_kwarg": "vessel_code"},
            {"param": "port", "filter_kwarg": "port__port_code"},
        ],
        "extra_context": {
            "filter_vessels": _get_canal_fee_vessels,
            "filter_ports": _get_canal_fee_ports,
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
        "json_config": CANAL_FEE_JSON,
        "dt_columns": [
            "",
            "",
            "vessel_code",
            "direction",
            "port__port_code",
            "canal_fee",
        ],
        "serialize_fn": lambda obj: {
            "id": obj.id,
            "vessel_code": obj.vessel_code,
            "direction": (
                obj.get_direction_display()
                if hasattr(obj, "get_direction_display")
                else obj.direction
            ),
            "port": obj.port.port_code if obj.port else "",
            "canal_fee": float(obj.canal_fee) if obj.canal_fee else 0,
        },
    }
)


# =========================================================
# 2. Distance — 시나리오 독립 (BaseDistance)
# =========================================================
def _save_distance(request):
    """Distance 모달 저장 (update_or_create)"""
    prefix_indices = set()
    for key in request.POST:
        if key.startswith("new_from_port_"):
            prefix_indices.add(key.replace("new_from_port_", ""))

    created = 0
    for idx in sorted(prefix_indices):
        from_port = request.POST.get(f"new_from_port_{idx}", "").strip()
        to_port = request.POST.get(f"new_to_port_{idx}", "").strip()
        distance = request.POST.get(f"new_distance_{idx}", "").strip()
        eca_distance = request.POST.get(f"new_eca_distance_{idx}", "").strip()

        if not (from_port and to_port and distance and eca_distance):
            continue

        BaseDistance.objects.update_or_create(
            from_port_id=from_port,
            to_port_id=to_port,
            defaults={
                "distance": distance,
                "eca_distance": eca_distance,
            },
        )
        created += 1
    return created


distance_list = master_crud_view(
    {
        "model": BaseDistance,
        "url_name": "input_data:distance_list",
        "view_name": "distance_list",
        "template": "input_data/distance_list.html",
        "page_title": "Distance",
        "label": "distance",
        "menu_group": MenuGroup.COST,
        "menu_item": MenuItem.DISTANCE,
        "pk_field": "id",
        "queryset_fn": lambda: (
            BaseDistance.objects.select_related("from_port", "to_port")
            .all()
            .order_by("from_port__port_code", "to_port__port_code")
        ),
        "search_fields": ["from_port__port_code", "to_port__port_code"],
        "save_fn": _save_distance,
        "extra_filters": [
            {"param": "from_port", "filter_kwarg": "from_port__port_code"},
            {"param": "to_port", "filter_kwarg": "to_port__port_code"},
        ],
        "extra_context_fn": lambda request: {
            "filter_from_ports": list(
                BaseDistance.objects.values_list("from_port__port_code", flat=True)
                .distinct()
                .order_by("from_port__port_code")
            ),
            "filter_to_ports": list(
                BaseDistance.objects.values_list("to_port__port_code", flat=True)
                .distinct()
                .order_by("to_port__port_code")
            ),
            "ports": MasterPort.objects.all().order_by("port_code"),
        },
        "csv_map": DISTANCE_CSV_MAP,
        "json_config": DISTANCE_JSON,
        "dt_columns": [
            "",
            "",
            "from_port__port_code",
            "to_port__port_code",
            "distance",
            "eca_distance",
        ],
        "serialize_fn": lambda obj: {
            "id": obj.id,
            "from_port": obj.from_port.port_code if obj.from_port else "",
            "to_port": obj.to_port.port_code if obj.to_port else "",
            "distance": float(obj.distance) if obj.distance else 0,
            "eca_distance": float(obj.eca_distance) if obj.eca_distance else 0,
        },
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
        "queryset_fn": lambda scenario_id="": (
            TSCost.objects.select_related("scenario", "lane", "port").filter(
                scenario_id=scenario_id
            )
            if scenario_id
            else TSCost.objects.none()
        ).order_by("base_year_month", "lane__lane_code", "port__port_code"),
        "search_filter_fn": lambda qs, s: (
            qs.filter(lane__lane_code__icontains=s)
            | qs.filter(port__port_code__icontains=s)
        ),
        "extra_search_fields": [
            {"param": "base_year_month", "filter_kwarg": "base_year_month"},
            {"param": "lane", "filter_kwarg": "lane__lane_code"},
            {"param": "port", "filter_kwarg": "port__port_code"},
        ],
        "extra_context": {
            "base_year_month_choices": get_scenario_base_year_month_choices,
            "filter_lanes": _get_ts_cost_lanes,
            "filter_ports": _get_ts_cost_ports,
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
        "json_config": TS_COST_JSON,
        "dt_columns": [
            "",
            "",
            "base_year_month",
            "lane__lane_code",
            "port__port_code",
            "ts_cost",
        ],
        "serialize_fn": lambda obj: {
            "id": obj.id,
            "base_year_month": obj.base_year_month,
            "lane": obj.lane.lane_code if obj.lane else "",
            "port": obj.port.port_code if obj.port else "",
            "ts_cost": float(obj.ts_cost) if obj.ts_cost else 0,
        },
    }
)
