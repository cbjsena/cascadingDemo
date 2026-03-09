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
    CharterCost,
    ScenarioInfo,
    VesselCapacity,
    VesselInfo,
)


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

        elif action == "save":
            created = 0
            prefix_indices = set()
            for key in request.POST:
                if key.startswith("new_vessel_code_"):
                    prefix_indices.add(key.replace("new_vessel_code_", ""))

            for idx in sorted(prefix_indices):
                vessel_code = request.POST.get(f"new_vessel_code_{idx}", "").strip()
                vessel_name = request.POST.get(f"new_vessel_name_{idx}", "").strip()
                own_yn = request.POST.get(f"new_own_yn_{idx}", "").strip()

                if scenario_id and vessel_code and vessel_name and own_yn:
                    VesselInfo.objects.update_or_create(
                        scenario_id=scenario_id,
                        vessel_code=vessel_code,
                        defaults={
                            "vessel_name": vessel_name,
                            "own_yn": own_yn,
                        },
                    )
                    created += 1

            if created:
                messages.success(request, f"{created} vessel(s) added.")
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
        "search_params": {
            "scenario_id": scenario_id,
            "search": search,
        },
    }
    return render(request, "input_data/vessel_info_list.html", context)


@login_required
def charter_cost_list(request):
    """Charter Cost 목록 조회 및 Add/Delete (시나리오 기반)"""

    if request.method == "POST":
        action = request.POST.get("action")
        scenario_id = request.POST.get("scenario_id", "")

        if action == "delete":
            pks = request.POST.getlist("selected_pks")
            if pks:
                deleted_count, _ = CharterCost.objects.filter(pk__in=pks).delete()
                messages.success(request, f"{deleted_count} charter cost(s) deleted.")
            url = reverse("input_data:charter_cost_list")
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
                hire_from = request.POST.get(f"new_hire_from_{idx}", "").strip()
                hire_to = request.POST.get(f"new_hire_to_{idx}", "").strip()
                hire_rate = request.POST.get(f"new_hire_rate_{idx}", "").strip()

                if scenario_id and vessel_code and hire_from and hire_to and hire_rate:
                    CharterCost.objects.update_or_create(
                        scenario_id=scenario_id,
                        vessel_code=vessel_code,
                        hire_from_date=hire_from,
                        defaults={
                            "hire_to_date": hire_to,
                            "hire_rate": hire_rate,
                        },
                    )
                    created += 1

            if created:
                messages.success(request, f"{created} charter cost(s) added.")
            url = reverse("input_data:charter_cost_list")
            if scenario_id:
                return redirect(f"{url}?scenario_id={scenario_id}")
            return redirect(url)

    # GET
    search = request.GET.get("search", "").strip()
    scenario_id = request.GET.get("scenario_id", "")
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    queryset = (
        CharterCost.objects.select_related("scenario")
        .all()
        .order_by("scenario", "vessel_code", "hire_from_date")
    )
    if scenario_id:
        queryset = queryset.filter(scenario_id=scenario_id)
    if search:
        queryset = queryset.filter(vessel_code__icontains=search)

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.VESSEL,
        "current_model": MenuItem.CHARTER_COST,
        "page_title": "Charter Cost",
        "items": queryset,
        "scenarios": scenarios,
        "search": search,
        "search_params": {
            "scenario_id": scenario_id,
            "search": search,
        },
    }
    return render(request, "input_data/charter_cost_list.html", context)


@login_required
def vessel_capacity_list(request):
    """Vessel Capacity 목록 조회 및 Add/Delete (시나리오 기반)"""

    if request.method == "POST":
        action = request.POST.get("action")
        scenario_id = request.POST.get("scenario_id", "")

        if action == "delete":
            pks = request.POST.getlist("selected_pks")
            if pks:
                deleted_count, _ = VesselCapacity.objects.filter(pk__in=pks).delete()
                messages.success(
                    request, f"{deleted_count} vessel capacity(s) deleted."
                )
            url = reverse("input_data:vessel_capacity_list")
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
                trade_code = request.POST.get(f"new_trade_code_{idx}", "").strip()
                lane_code = request.POST.get(f"new_lane_code_{idx}", "").strip()
                vessel_code = request.POST.get(f"new_vessel_code_{idx}", "").strip()
                voyage_number = request.POST.get(f"new_voyage_number_{idx}", "").strip()
                direction = request.POST.get(f"new_direction_{idx}", "").strip()
                vessel_capacity = request.POST.get(
                    f"new_vessel_capacity_{idx}", ""
                ).strip()
                reefer_capacity = request.POST.get(
                    f"new_reefer_capacity_{idx}", ""
                ).strip()

                if scenario_id and all(
                    [
                        trade_code,
                        lane_code,
                        vessel_code,
                        voyage_number,
                        direction,
                        vessel_capacity,
                        reefer_capacity,
                    ]
                ):
                    VesselCapacity.objects.update_or_create(
                        scenario_id=scenario_id,
                        trade_id=trade_code,
                        lane_id=lane_code,
                        vessel_code=vessel_code,
                        voyage_number=voyage_number,
                        direction=direction,
                        defaults={
                            "vessel_capacity": vessel_capacity,
                            "reefer_capacity": reefer_capacity,
                        },
                    )
                    created += 1

            if created:
                messages.success(request, f"{created} vessel capacity(s) added.")
            url = reverse("input_data:vessel_capacity_list")
            if scenario_id:
                return redirect(f"{url}?scenario_id={scenario_id}")
            return redirect(url)

    # GET
    search = request.GET.get("search", "").strip()
    scenario_id = request.GET.get("scenario_id", "")
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    queryset = (
        VesselCapacity.objects.select_related("scenario", "trade", "lane")
        .all()
        .order_by("scenario", "trade", "lane", "vessel_code", "voyage_number")
    )
    if scenario_id:
        queryset = queryset.filter(scenario_id=scenario_id)
    if search:
        queryset = queryset.filter(vessel_code__icontains=search) | queryset.filter(
            lane__lane_code__icontains=search
        )

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.VESSEL,
        "current_model": MenuItem.VESSEL_CAPACITY,
        "page_title": "Vessel Capacity",
        "items": queryset,
        "scenarios": scenarios,
        "search": search,
        "search_params": {
            "scenario_id": scenario_id,
            "search": search,
        },
    }
    return render(request, "input_data/vessel_capacity_list.html", context)
