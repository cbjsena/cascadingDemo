from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from common.menus import (
    CREATION_MENU_STRUCTURE,
    MENU_STRUCTURE,
    MenuGroup,
    MenuItem,
    MenuSection,
)
from input_data.models import MasterLane, MasterPort, MasterTrade


@login_required
def master_trade_list(request):
    """Master Trade 목록 조회 및 Add/Delete"""

    # POST 처리
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete":
            pks = request.POST.getlist("selected_pks")
            if pks:
                deleted_count, _ = MasterTrade.objects.filter(
                    trade_code__in=pks
                ).delete()
                messages.success(request, f"{deleted_count} trade(s) deleted.")
            return redirect("input_data:master_trade_list")

        elif action == "save":
            # new_ 필드를 동적으로 찾기
            created = 0
            prefix_indices = set()
            for key in request.POST:
                if key.startswith("new_trade_code_"):
                    idx = key.replace("new_trade_code_", "")
                    prefix_indices.add(idx)

            for idx in sorted(prefix_indices):
                trade_code = request.POST.get(f"new_trade_code_{idx}", "").strip()
                trade_name = request.POST.get(f"new_trade_name_{idx}", "").strip()
                from_continent = request.POST.get(
                    f"new_from_continent_{idx}", ""
                ).strip()
                to_continent = request.POST.get(f"new_to_continent_{idx}", "").strip()

                if trade_code and trade_name:
                    MasterTrade.objects.update_or_create(
                        trade_code=trade_code,
                        defaults={
                            "trade_name": trade_name,
                            "from_continent_code": from_continent or None,
                            "to_continent_code": to_continent or None,
                        },
                    )
                    created += 1

            if created:
                messages.success(request, f"{created} trade(s) added.")
            return redirect("input_data:master_trade_list")

    # GET 처리
    search = request.GET.get("search", "").strip()
    queryset = MasterTrade.objects.all().order_by("trade_code")
    if search:
        queryset = queryset.filter(trade_code__icontains=search) | queryset.filter(
            trade_name__icontains=search
        )
    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.MASTER,
        "current_model": MenuItem.TRADE_INFO,
        "page_title": "Trade Info",
        "items": queryset,
        "search": search,
    }
    return render(request, "input_data/master_trade_list.html", context)


@login_required
def master_port_list(request):
    """Master Port 목록 조회 및 Add/Delete"""

    # POST 처리
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete":
            pks = request.POST.getlist("selected_pks")
            if pks:
                deleted_count, _ = MasterPort.objects.filter(port_code__in=pks).delete()
                messages.success(request, f"{deleted_count} port(s) deleted.")
            return redirect("input_data:master_port_list")

        elif action == "save":
            prefix_indices = set()
            for key in request.POST:
                if key.startswith("new_port_code_"):
                    idx = key.replace("new_port_code_", "")
                    prefix_indices.add(idx)

            created = 0
            for idx in sorted(prefix_indices):
                port_code = request.POST.get(f"new_port_code_{idx}", "").strip()
                port_name = request.POST.get(f"new_port_name_{idx}", "").strip()
                continent_code = request.POST.get(
                    f"new_continent_code_{idx}", ""
                ).strip()
                country_code = request.POST.get(f"new_country_code_{idx}", "").strip()

                if port_code and port_name:
                    MasterPort.objects.update_or_create(
                        port_code=port_code,
                        defaults={
                            "port_name": port_name,
                            "continent_code": continent_code or None,
                            "country_code": country_code or None,
                        },
                    )
                    created += 1

            if created:
                messages.success(request, f"{created} port(s) added.")
            return redirect("input_data:master_port_list")

    # GET 처리
    search = request.GET.get("search", "").strip()
    continent = request.GET.get("continent", "").strip()
    queryset = MasterPort.objects.all().order_by("port_code")
    if search:
        queryset = queryset.filter(port_code__icontains=search) | queryset.filter(
            port_name__icontains=search
        )
    if continent:
        queryset = queryset.filter(continent_code__icontains=continent)
    continent_codes = (
        MasterPort.objects.exclude(continent_code__isnull=True)
        .exclude(continent_code="")
        .values_list("continent_code", flat=True)
        .distinct()
        .order_by("continent_code")
    )
    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.MASTER,
        "current_model": MenuItem.PORT_INFO,
        "page_title": "Port Info",
        "items": queryset,
        "search": search,
        "continent": continent,
        "continent_codes": continent_codes,
    }
    return render(request, "input_data/master_port_list.html", context)


@login_required
def master_lane_list(request):
    """Master Lane 목록 조회 및 Add/Delete"""

    # POST 처리
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete":
            pks = request.POST.getlist("selected_pks")
            if pks:
                deleted_count, _ = MasterLane.objects.filter(lane_code__in=pks).delete()
                messages.success(request, f"{deleted_count} lane(s) deleted.")
            return redirect("input_data:master_lane_list")

        elif action == "save":
            prefix_indices = set()
            for key in request.POST:
                if key.startswith("new_lane_code_"):
                    idx = key.replace("new_lane_code_", "")
                    prefix_indices.add(idx)

            created = 0
            for idx in sorted(prefix_indices):
                lane_code = request.POST.get(f"new_lane_code_{idx}", "").strip()
                lane_name = request.POST.get(f"new_lane_name_{idx}", "").strip()
                service_type = request.POST.get(f"new_service_type_{idx}", "").strip()
                eff_from = request.POST.get(f"new_eff_from_{idx}", "").strip()
                eff_to = request.POST.get(f"new_eff_to_{idx}", "").strip()
                feeder_div = request.POST.get(f"new_feeder_div_{idx}", "").strip()

                if lane_code and lane_name:
                    MasterLane.objects.update_or_create(
                        lane_code=lane_code,
                        defaults={
                            "lane_name": lane_name,
                            "vessel_service_type_code": service_type or None,
                            "effective_from_date": eff_from or None,
                            "effective_to_date": eff_to or None,
                            "feeder_division_code": feeder_div or None,
                        },
                    )
                    created += 1

            if created:
                messages.success(request, f"{created} lane(s) added.")
            return redirect("input_data:master_lane_list")

    # GET 처리
    search = request.GET.get("search", "").strip()
    queryset = MasterLane.objects.all().order_by("lane_code")
    if search:
        queryset = queryset.filter(lane_code__icontains=search) | queryset.filter(
            lane_name__icontains=search
        )
    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.MASTER,
        "current_model": MenuItem.LANE_INFO,
        "page_title": "Lane Info",
        "items": queryset,
        "search": search,
    }
    return render(request, "input_data/master_lane_list.html", context)
