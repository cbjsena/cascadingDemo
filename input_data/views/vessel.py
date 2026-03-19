"""
Vessel 관련 뷰 (Config 기반 공통 CRUD).
VesselInfo만 커스텀 save 로직(중복 체크 + 선택적 필드)이 필요하므로
별도 뷰로 유지하고, Charter Cost / Vessel Capacity는 공통 팩토리 사용.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from common.csv_configs import (
    CHARTER_COST_CSV_MAP,
    VESSEL_CAPACITY_CSV_MAP,
    VESSEL_INFO_CSV_MAP,
)
from common.json_configs import (
    CHARTER_COST_JSON,
    VESSEL_CAPACITY_JSON,
    VESSEL_FULL_JSON,
)
from common.menus import (
    CREATION_MENU_STRUCTURE,
    MENU_STRUCTURE,
    MenuGroup,
    MenuItem,
    MenuSection,
)
from input_data.models import (
    CharterCost,
    ScenarioInfo,
    VesselCapacity,
    VesselInfo,
)

from ._crud_base import (
    _handle_csv_download,
    _handle_csv_upload,
    _handle_json_download,
    _handle_json_upload,
    scenario_crud_view,
)

# Vessel Info CSV config (커스텀 뷰이므로 별도 정의)
VESSEL_INFO_CSV_CONFIG = {
    "url_name": "input_data:vessel_info_list",
    "page_title": "Vessel Info",
    "label": "vessel",
    "queryset_fn": lambda: (
        VesselInfo.objects.select_related("scenario")
        .all()
        .order_by("scenario", "vessel_code")
    ),
    "csv_map": VESSEL_INFO_CSV_MAP,
    "json_config": VESSEL_FULL_JSON,
    "unique_fields": ["vessel_code"],
    "model": VesselInfo,
}


# =========================================================
# 1. Vessel Info — 커스텀 save 로직 (선택적 필드가 많아 별도 유지)
# =========================================================
@login_required
def vessel_info_list(request):
    """Vessel Info 목록 조회 및 Add/Delete (시나리오 기반)"""

    if request.method == "POST":
        action = request.POST.get("action")
        scenario_id = request.POST.get("scenario_id", "")

        if action == "delete":
            pks = request.POST.getlist("selected_pks")
            if pks:
                deleted_count, _ = VesselInfo.objects.filter(pk__in=pks).delete()
                messages.success(request, f"{deleted_count} vessel(s) deleted.")
            url = reverse("input_data:vessel_info_list")
            if scenario_id:
                return redirect(f"{url}?scenario_id={scenario_id}")
            return redirect(url)

        elif action == "csv_download":
            return _handle_csv_download(
                request, config=VESSEL_INFO_CSV_CONFIG, scenario_id=scenario_id
            )
        elif action == "csv_upload":
            return _handle_csv_upload(
                request, config=VESSEL_INFO_CSV_CONFIG, scenario_id=scenario_id
            )
        elif action == "json_download":
            return _handle_json_download(
                request, config=VESSEL_INFO_CSV_CONFIG, scenario_id=scenario_id
            )
        elif action == "json_upload":
            return _handle_json_upload(
                request, config=VESSEL_INFO_CSV_CONFIG, scenario_id=scenario_id
            )

        elif action == "save":
            created = 0
            duplicated = 0
            prefix_indices = set()
            for key in request.POST:
                if key.startswith("new_vessel_code_"):
                    prefix_indices.add(key.replace("new_vessel_code_", ""))

            for idx in sorted(prefix_indices):
                vessel_code = request.POST.get(f"new_vessel_code_{idx}", "").strip()
                vessel_name = request.POST.get(f"new_vessel_name_{idx}", "").strip()
                own_yn = request.POST.get(f"new_own_yn_{idx}", "").strip()

                if not (scenario_id and vessel_code and vessel_name and own_yn):
                    continue

                if VesselInfo.objects.filter(
                    scenario_id=scenario_id, vessel_code=vessel_code
                ).exists():
                    duplicated += 1
                    continue

                # 선택적 필드
                delivery_port = request.POST.get(f"new_delivery_port_{idx}", "").strip()
                delivery_date = request.POST.get(f"new_delivery_date_{idx}", "").strip()
                redelivery_port = request.POST.get(
                    f"new_redelivery_port_{idx}", ""
                ).strip()
                redelivery_date = request.POST.get(
                    f"new_redelivery_date_{idx}", ""
                ).strip()
                dock_port = request.POST.get(f"new_dock_port_{idx}", "").strip()
                dock_in = request.POST.get(f"new_dock_in_{idx}", "").strip()
                dock_out = request.POST.get(f"new_dock_out_{idx}", "").strip()

                VesselInfo.objects.create(
                    scenario_id=scenario_id,
                    vessel_code=vessel_code,
                    vessel_name=vessel_name,
                    own_yn=own_yn,
                    delivery_port_code=delivery_port or None,
                    delivery_date=delivery_date or None,
                    redelivery_port_code=redelivery_port or None,
                    redelivery_date=redelivery_date or None,
                    next_dock_port_code=dock_port or None,
                    next_dock_in_date=dock_in or None,
                    next_dock_out_date=dock_out or None,
                )
                created += 1

            if created:
                messages.success(request, f"{created} vessel(s) added.")
            if duplicated:
                messages.warning(
                    request,
                    f"{duplicated} vessel(s) skipped (already exists in this scenario).",
                )
            url = reverse("input_data:vessel_info_list")
            if scenario_id:
                return redirect(f"{url}?scenario_id={scenario_id}")
            return redirect(url)

    # GET
    search = request.GET.get("search", "").strip()
    scenario_id = request.GET.get("scenario_id", "")
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    queryset = (
        VesselInfo.objects.select_related("scenario")
        .all()
        .order_by("scenario", "vessel_code")
    )
    if scenario_id:
        queryset = queryset.filter(scenario_id=scenario_id)
    if search:
        queryset = queryset.filter(vessel_code__icontains=search) | queryset.filter(
            vessel_name__icontains=search
        )

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.VESSEL,
        "current_model": MenuItem.VESSEL_INFO,
        "page_title": "Vessel Info",
        "items": queryset,
        "scenarios": scenarios,
        "search": search,
        "has_csv": True,
        "has_json": True,
        "search_params": {
            "scenario_id": scenario_id,
            "search": search,
        },
    }
    return render(request, "input_data/vessel_info_list.html", context)


# =========================================================
# 2. Charter Cost — 공통 팩토리
# =========================================================
charter_cost_list = scenario_crud_view(
    {
        "model": CharterCost,
        "url_name": "input_data:charter_cost_list",
        "view_name": "charter_cost_list",
        "template": "input_data/charter_cost_list.html",
        "page_title": "Charter Cost",
        "label": "charter cost",
        "menu_group": MenuGroup.VESSEL,
        "menu_item": MenuItem.CHARTER_COST,
        "queryset_fn": lambda: (
            CharterCost.objects.select_related("scenario")
            .all()
            .order_by("scenario", "vessel_code", "hire_from_date")
        ),
        "search_filter_fn": lambda qs, s: qs.filter(vessel_code__icontains=s),
        "fields": [
            {"post_key": "new_vessel_code", "model_field": "vessel_code"},
            {"post_key": "new_hire_from", "model_field": "hire_from_date"},
            {"post_key": "new_hire_to", "model_field": "hire_to_date"},
            {"post_key": "new_hire_rate", "model_field": "hire_rate"},
        ],
        "lookup_fields": ["vessel_code", "hire_from_date"],
        "defaults_fields": ["hire_to_date", "hire_rate"],
        "csv_map": CHARTER_COST_CSV_MAP,
        "json_config": CHARTER_COST_JSON,
    }
)

# =========================================================
# 3. Vessel Capacity — 공통 팩토리
# =========================================================
vessel_capacity_list = scenario_crud_view(
    {
        "model": VesselCapacity,
        "url_name": "input_data:vessel_capacity_list",
        "view_name": "vessel_capacity_list",
        "template": "input_data/vessel_capacity_list.html",
        "page_title": "Vessel Capacity",
        "label": "vessel capacity",
        "menu_group": MenuGroup.VESSEL,
        "menu_item": MenuItem.VESSEL_CAPACITY,
        "queryset_fn": lambda: (
            VesselCapacity.objects.select_related("scenario", "trade", "lane")
            .all()
            .order_by("scenario", "trade", "lane", "vessel_code", "voyage_number")
        ),
        "search_filter_fn": lambda qs, s: (
            qs.filter(vessel_code__icontains=s)
            | qs.filter(lane__lane_code__icontains=s)
        ),
        "fields": [
            {"post_key": "new_vessel_code", "model_field": "vessel_code"},
            {"post_key": "new_trade_code", "model_field": "trade_id"},
            {"post_key": "new_lane_code", "model_field": "lane_id"},
            {"post_key": "new_voyage_number", "model_field": "voyage_number"},
            {"post_key": "new_direction", "model_field": "direction"},
            {"post_key": "new_vessel_capacity", "model_field": "vessel_capacity"},
            {"post_key": "new_reefer_capacity", "model_field": "reefer_capacity"},
        ],
        "lookup_fields": [
            "trade_id",
            "lane_id",
            "vessel_code",
            "voyage_number",
            "direction",
        ],
        "defaults_fields": ["vessel_capacity", "reefer_capacity"],
        "csv_map": VESSEL_CAPACITY_CSV_MAP,
        "json_config": VESSEL_CAPACITY_JSON,
    }
)
