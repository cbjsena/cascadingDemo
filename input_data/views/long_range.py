from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from common.menus import (
    CREATION_MENU_STRUCTURE,
    MENU_STRUCTURE,
    MenuGroup,
    MenuItem,
    MenuSection,
)
from input_data.models import (
    LongRangeSchedule,
    ScenarioInfo,
)


@login_required
def long_range_list(request):
    """
    Long Range Schedule 목록 조회 및 검색
    """
    # 1. 검색 파라미터
    scenario_id = request.GET.get("scenario_id")
    lane_code = request.GET.get("lane_code")
    proforma_name = request.GET.get("proforma_name")
    vessel_code = request.GET.get("vessel_code")

    # 2. 기본 쿼리셋
    lrs_qs = LongRangeSchedule.objects.none()

    # 시나리오는 필수 (또는 기본 구조상 최상위 필터)
    if scenario_id:
        lrs_qs = LongRangeSchedule.objects.filter(scenario_id=scenario_id)

        if lane_code:
            lrs_qs = lrs_qs.filter(lane_code=lane_code)

        if proforma_name:
            lrs_qs = lrs_qs.filter(proforma_name=proforma_name)

        # Vessel Code 검색 (부분 일치 허용)
        if vessel_code:
            lrs_qs = lrs_qs.filter(vessel_code__icontains=vessel_code)

        # 정렬: Voyage -> Seq
        lrs_qs = lrs_qs.order_by(
            "vessel_code", "voyage_number", "direction", "calling_port_seq"
        )

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.SCHEDULE,
        "current_model": MenuItem.LONG_RANGE_SCHEDULE,
        "scenarios": ScenarioInfo.objects.all().order_by("-created_at"),
        "lrs_list": lrs_qs,
        # 검색 상태 유지용
        "search_params": {
            "scenario_id": scenario_id,
            "lane_code": lane_code,
            "proforma_name": proforma_name,
            "vessel_code": vessel_code,
        },
    }

    return render(request, "input_data/long_range_list.html", context)
