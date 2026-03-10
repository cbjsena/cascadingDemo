from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from common.menus import (
    CREATION_MENU_STRUCTURE,
    MENU_STRUCTURE,
    MenuGroup,
    MenuItem,
    MenuSection,
)
from input_data.models import (
    CanalFee,
    Distance,
    MasterLane,
    MasterPort,
    ScenarioInfo,
    TSCost,
)


@login_required
def canal_fee_list(request):
    """Canal Fee 목록 조회 및 Add/Delete (시나리오 기반)"""

    if request.method == "POST":
        action = request.POST.get("action")
        scenario_id = request.POST.get("scenario_id", "")

        if action == "delete":
            pks = request.POST.getlist("selected_pks")
            if pks:
                deleted_count, _ = CanalFee.objects.filter(pk__in=pks).delete()
                messages.success(request, f"{deleted_count} canal fee(s) deleted.")
            url = reverse("input_data:canal_fee_list")
            if scenario_id:
                return redirect(f"{url}?scenario_id={scenario_id}")
            return redirect(url)

        elif action == "save":
            created = 0
            prefix_indices = set()
            for key in request.POST:
                if key.startswith("new_vessel_code_"):
                    prefix_indices.add(key.replace("new_vessel_code_", ""))

            for idx in sorted(prefix_indices):
                vessel_code = request.POST.get(f"new_vessel_code_{idx}", "").strip()
                direction = request.POST.get(f"new_direction_{idx}", "").strip()
                port_code = request.POST.get(f"new_port_code_{idx}", "").strip()
                canal_fee = request.POST.get(f"new_canal_fee_{idx}", "").strip()

                if scenario_id and all([vessel_code, direction, port_code, canal_fee]):
                    CanalFee.objects.update_or_create(
                        scenario_id=scenario_id,
                        vessel_code=vessel_code,
                        direction=direction,
                        port_id=port_code,
                        defaults={
                            "canal_fee": canal_fee,
                        },
                    )
                    created += 1

            if created:
                messages.success(request, f"{created} canal fee(s) added.")
            url = reverse("input_data:canal_fee_list")
            if scenario_id:
                return redirect(f"{url}?scenario_id={scenario_id}")
            return redirect(url)

    # GET
    search = request.GET.get("search", "").strip()
    scenario_id = request.GET.get("scenario_id", "")
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    queryset = (
        CanalFee.objects.select_related("scenario", "port")
        .all()
        .order_by("scenario", "vessel_code", "direction", "port")
    )
    if scenario_id:
        queryset = queryset.filter(scenario_id=scenario_id)
    if search:
        queryset = queryset.filter(vessel_code__icontains=search) | queryset.filter(
            port__port_code__icontains=search
        )

    # Port 목록 (모달 드롭다운용)
    ports = MasterPort.objects.all().order_by("port_code")

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.COST,
        "current_model": MenuItem.CANAL_FEE,
        "page_title": "Canal Fee",
        "items": queryset,
        "scenarios": scenarios,
        "ports": ports,
        "search": search,
        "search_params": {
            "scenario_id": scenario_id,
            "search": search,
        },
    }
    return render(request, "input_data/canal_fee_list.html", context)


@login_required
def distance_list(request):
    """Distance 목록 조회 및 Add/Delete (시나리오 기반)"""

    if request.method == "POST":
        action = request.POST.get("action")
        scenario_id = request.POST.get("scenario_id", "")

        if action == "delete":
            pks = request.POST.getlist("selected_pks")
            if pks:
                deleted_count, _ = Distance.objects.filter(pk__in=pks).delete()
                messages.success(request, f"{deleted_count} distance(s) deleted.")
            url = reverse("input_data:distance_list")
            if scenario_id:
                return redirect(f"{url}?scenario_id={scenario_id}")
            return redirect(url)

        elif action == "save":
            created = 0
            prefix_indices = set()
            for key in request.POST:
                if key.startswith("new_from_port_"):
                    prefix_indices.add(key.replace("new_from_port_", ""))

            for idx in sorted(prefix_indices):
                from_port = request.POST.get(f"new_from_port_{idx}", "").strip()
                to_port = request.POST.get(f"new_to_port_{idx}", "").strip()
                distance_val = request.POST.get(f"new_distance_{idx}", "").strip()
                eca_distance = request.POST.get(f"new_eca_distance_{idx}", "").strip()

                if scenario_id and all(
                    [from_port, to_port, distance_val, eca_distance]
                ):
                    Distance.objects.update_or_create(
                        scenario_id=scenario_id,
                        from_port_id=from_port,
                        to_port_id=to_port,
                        defaults={
                            "distance": distance_val,
                            "eca_distance": eca_distance,
                        },
                    )
                    created += 1

            if created:
                messages.success(request, f"{created} distance(s) added.")
            url = reverse("input_data:distance_list")
            if scenario_id:
                return redirect(f"{url}?scenario_id={scenario_id}")
            return redirect(url)

    # GET
    search = request.GET.get("search", "").strip()
    scenario_id = request.GET.get("scenario_id", "")
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    queryset = (
        Distance.objects.select_related("scenario", "from_port", "to_port")
        .all()
        .order_by("scenario", "from_port", "to_port")
    )
    if scenario_id:
        queryset = queryset.filter(scenario_id=scenario_id)
    if search:
        queryset = queryset.filter(
            from_port__port_code__icontains=search
        ) | queryset.filter(to_port__port_code__icontains=search)

    # Port 목록 (모달 드롭다운용)
    ports = MasterPort.objects.all().order_by("port_code")

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.COST,
        "current_model": MenuItem.DISTANCE,
        "page_title": "Distance",
        "items": queryset,
        "scenarios": scenarios,
        "ports": ports,
        "search": search,
        "search_params": {
            "scenario_id": scenario_id,
            "search": search,
        },
    }
    return render(request, "input_data/distance_list.html", context)


@login_required
def ts_cost_list(request):
    """TS Cost 목록 조회 및 Add/Delete (시나리오 기반)"""

    if request.method == "POST":
        action = request.POST.get("action")
        scenario_id = request.POST.get("scenario_id", "")

        if action == "delete":
            pks = request.POST.getlist("selected_pks")
            if pks:
                deleted_count, _ = TSCost.objects.filter(pk__in=pks).delete()
                messages.success(request, f"{deleted_count} TS cost(s) deleted.")
            url = reverse("input_data:ts_cost_list")
            if scenario_id:
                return redirect(f"{url}?scenario_id={scenario_id}")
            return redirect(url)

        elif action == "save":
            created = 0
            duplicated = 0
            prefix_indices = set()
            for key in request.POST:
                if key.startswith("new_base_year_month_"):
                    prefix_indices.add(key.replace("new_base_year_month_", ""))

            for idx in sorted(prefix_indices):
                base_year_month = request.POST.get(
                    f"new_base_year_month_{idx}", ""
                ).strip()
                lane_code = request.POST.get(f"new_lane_code_{idx}", "").strip()
                port_code = request.POST.get(f"new_port_code_{idx}", "").strip()
                ts_cost_val = request.POST.get(f"new_ts_cost_{idx}", "").strip()

                if not (
                    scenario_id
                    and all([base_year_month, lane_code, port_code, ts_cost_val])
                ):
                    continue

                # 중복 체크
                if TSCost.objects.filter(
                    scenario_id=scenario_id,
                    base_year_month=base_year_month,
                    lane_id=lane_code,
                    port_id=port_code,
                ).exists():
                    duplicated += 1
                    continue

                TSCost.objects.create(
                    scenario_id=scenario_id,
                    base_year_month=base_year_month,
                    lane_id=lane_code,
                    port_id=port_code,
                    ts_cost=ts_cost_val,
                )
                created += 1

            if created:
                messages.success(request, f"{created} TS cost(s) added.")
            if duplicated:
                messages.warning(
                    request,
                    f"{duplicated} TS cost(s) skipped (already exists in this scenario).",
                )
            url = reverse("input_data:ts_cost_list")
            if scenario_id:
                return redirect(f"{url}?scenario_id={scenario_id}")
            return redirect(url)

    # GET
    search = request.GET.get("search", "").strip()
    base_year_month = request.GET.get("base_year_month", "").strip()
    scenario_id = request.GET.get("scenario_id", "")
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    queryset = (
        TSCost.objects.select_related("scenario", "lane", "port")
        .all()
        .order_by("scenario", "base_year_month", "lane", "port")
    )
    if scenario_id:
        queryset = queryset.filter(scenario_id=scenario_id)
    if base_year_month:
        queryset = queryset.filter(base_year_month=base_year_month)
    if search:
        queryset = queryset.filter(lane__lane_code__icontains=search) | queryset.filter(
            port__port_code__icontains=search
        )

    # Lane/Port 목록 (모달 드롭다운용)
    lanes = MasterLane.objects.all().order_by("lane_code")
    ports = MasterPort.objects.all().order_by("port_code")

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.COST,
        "current_model": MenuItem.TS_COST,
        "page_title": "TS Cost",
        "items": queryset,
        "scenarios": scenarios,
        "lanes": lanes,
        "ports": ports,
        "search": search,
        "base_year_month": base_year_month,
        "search_params": {
            "scenario_id": scenario_id,
            "base_year_month": base_year_month,
            "search": search,
        },
    }
    return render(request, "input_data/ts_cost_list.html", context)
