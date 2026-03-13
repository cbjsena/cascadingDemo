from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from common.menus import (
    CREATION_MENU_STRUCTURE,
    MENU_STRUCTURE,
    MenuGroup,
    MenuItem,
    MenuSection,
)
from input_data.models import BaseWeekPeriod, MasterLane, MasterPort, MasterTrade


@login_required
def master_trade_list(request):
    """Master Trade 목록 조회 및 Add/Delete (DataTables 기반)"""

    # POST 처리 (Add/Delete)
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

    # AJAX 처리 (DataTables draw 파라미터 포함)
    if request.GET.get("draw"):
        search = request.GET.get("search[value]", "").strip()

        queryset = MasterTrade.objects.all().order_by("trade_code")
        if search:
            queryset = queryset.filter(trade_code__icontains=search) | queryset.filter(
                trade_name__icontains=search
            )

        # DataTables 서버사이드 처리
        total_count = MasterTrade.objects.count()
        filtered_count = queryset.count()

        # 페이징
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 50))
        items = queryset[start : start + length]

        data = [
            {
                "id": item.trade_code,
                "trade_code": item.trade_code,
                "trade_name": item.trade_name,
                "from_continent_code": item.from_continent_code or "-",
                "to_continent_code": item.to_continent_code or "-",
            }
            for item in items
        ]

        return JsonResponse(
            {
                "draw": int(request.GET.get("draw", 0)),
                "recordsTotal": total_count,
                "recordsFiltered": filtered_count,
                "data": data,
            }
        )

    # GET 처리 (초기 페이지 로드)
    search = request.GET.get("search", "").strip()
    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.MASTER,
        "current_model": MenuItem.TRADE_INFO,
        "page_title": "Trade Info",
        "search": search,
        "reset_url": reverse("input_data:master_trade_list"),
    }
    return render(request, "input_data/master_trade_list.html", context)


@login_required
def master_port_list(request):
    """Master Port 목록 조회 및 Add/Delete (DataTables 기반)"""

    # POST 처리 (Add/Delete)
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

    # AJAX 처리 (DataTables draw 파라미터 포함)
    if request.GET.get("draw"):
        search = request.GET.get("search[value]", "").strip()
        continent = request.GET.get("continent", "").strip()

        queryset = MasterPort.objects.all().order_by("port_code")
        if search:
            queryset = queryset.filter(port_code__icontains=search) | queryset.filter(
                port_name__icontains=search
            )
        if continent:
            queryset = queryset.filter(continent_code__icontains=continent)

        # DataTables 서버사이드 처리
        total_count = MasterPort.objects.count()
        filtered_count = queryset.count()

        # 페이징
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 50))
        items = queryset[start : start + length]

        data = [
            {
                "id": item.port_code,
                "port_code": item.port_code,
                "port_name": item.port_name,
                "continent_code": item.continent_code or "-",
                "country_code": item.country_code or "-",
            }
            for item in items
        ]

        return JsonResponse(
            {
                "draw": int(request.GET.get("draw", 0)),
                "recordsTotal": total_count,
                "recordsFiltered": filtered_count,
                "data": data,
            }
        )

    # GET 처리 (초기 페이지 로드)
    search = request.GET.get("search", "").strip()
    continent = request.GET.get("continent", "").strip()
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
        "search": search,
        "continent": continent,
        "continent_codes": continent_codes,
        "reset_url": reverse("input_data:master_port_list"),
    }
    return render(request, "input_data/master_port_list.html", context)


@login_required
def master_lane_list(request):
    """Master Lane 목록 조회 및 Add/Delete (DataTables 기반)"""

    # POST 처리 (Add/Delete)
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

    # AJAX 처리 (DataTables draw 파라미터 포함)
    if request.GET.get("draw"):
        search = request.GET.get("search[value]", "").strip()

        queryset = MasterLane.objects.all().order_by("lane_code")
        if search:
            queryset = queryset.filter(lane_code__icontains=search) | queryset.filter(
                lane_name__icontains=search
            )

        # DataTables 서버사이드 처리
        total_count = MasterLane.objects.count()
        filtered_count = queryset.count()

        # 페이징
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 50))
        items = queryset[start : start + length]

        data = [
            {
                "id": item.lane_code,
                "lane_code": item.lane_code,
                "lane_name": item.lane_name,
                "vessel_service_type_code": item.vessel_service_type_code or "-",
                "effective_from_date": (
                    item.effective_from_date.strftime("%Y-%m-%d")
                    if item.effective_from_date
                    else "-"
                ),
                "effective_to_date": (
                    item.effective_to_date.strftime("%Y-%m-%d")
                    if item.effective_to_date
                    else "-"
                ),
                "feeder_division_code": item.feeder_division_code or "-",
            }
            for item in items
        ]

        return JsonResponse(
            {
                "draw": int(request.GET.get("draw", 0)),
                "recordsTotal": total_count,
                "recordsFiltered": filtered_count,
                "data": data,
            }
        )

    # GET 처리 (초기 페이지 로드)
    search = request.GET.get("search", "").strip()
    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.MASTER,
        "current_model": MenuItem.LANE_INFO,
        "page_title": "Lane Info",
        "search": search,
        "reset_url": reverse("input_data:master_lane_list"),
    }
    return render(request, "input_data/master_lane_list.html", context)


@login_required
def master_week_period_list(request):
    """Master Week Period 목록 조회 및 Add/Delete (DataTables 기반)"""

    # POST 처리 (Add/Delete)
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete":
            pks = request.POST.getlist("selected_pks")
            if pks:
                deleted_count, _ = BaseWeekPeriod.objects.filter(pk__in=pks).delete()
                messages.success(request, f"{deleted_count} week period(s) deleted.")
            return redirect("input_data:master_week_period_list")

        elif action == "save":
            # new_ 필드를 동적으로 찾기
            prefix_indices = set()
            for key in request.POST:
                if key.startswith("new_base_year_"):
                    idx = key.replace("new_base_year_", "")
                    prefix_indices.add(idx)

            created = 0
            for idx in sorted(prefix_indices):
                base_year = request.POST.get(f"new_base_year_{idx}", "").strip()
                base_week = request.POST.get(f"new_base_week_{idx}", "").strip()
                base_month = request.POST.get(f"new_base_month_{idx}", "").strip()
                week_start_date = request.POST.get(
                    f"new_week_start_date_{idx}", ""
                ).strip()
                week_end_date = request.POST.get(f"new_week_end_date_{idx}", "").strip()

                if base_year and base_week and week_start_date and week_end_date:
                    BaseWeekPeriod.objects.update_or_create(
                        base_year=base_year,
                        base_week=base_week,
                        defaults={
                            "base_month": base_month or None,
                            "week_start_date": week_start_date,
                            "week_end_date": week_end_date,
                        },
                    )
                    created += 1

            if created:
                messages.success(request, f"{created} week period(s) added.")
            return redirect("input_data:master_week_period_list")

    # AJAX 처리 (DataTables draw 파라미터 포함)
    if request.GET.get("draw"):
        search = request.GET.get("search[value]", "").strip()

        queryset = BaseWeekPeriod.objects.all().order_by("base_year", "base_week")
        if search:
            queryset = queryset.filter(base_year__icontains=search) | queryset.filter(
                base_week__icontains=search
            )

        # DataTables 서버사이드 처리
        total_count = BaseWeekPeriod.objects.count()
        filtered_count = queryset.count()

        # 페이징
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 50))
        items = queryset[start : start + length]

        data = [
            {
                "id": item.id,
                "base_year": item.base_year,
                "base_week": item.base_week,
                "base_month": item.base_month or "-",
                "week_start_date": item.week_start_date.strftime("%Y-%m-%d"),
                "week_end_date": item.week_end_date.strftime("%Y-%m-%d"),
            }
            for item in items
        ]

        return JsonResponse(
            {
                "draw": int(request.GET.get("draw", 0)),
                "recordsTotal": total_count,
                "recordsFiltered": filtered_count,
                "data": data,
            }
        )

    # GET 처리 (초기 페이지 로드)
    search = request.GET.get("search", "").strip()
    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.MASTER,
        "current_model": MenuItem.WEEK_PERIOD,
        "page_title": "Week Period",
        "search": search,
        "reset_url": reverse("input_data:master_week_period_list"),
    }
    return render(request, "input_data/master_week_period_list.html", context)
