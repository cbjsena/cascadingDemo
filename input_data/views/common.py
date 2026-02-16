from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from common.constants import DEFAULT_SCENARIO_ID
from common.menus import MENU_STRUCTURE
from input_data.models import Distance

# 메뉴 구조 상수


@login_required
def input_list(request, group_name, model_name):
    """공통 입력 목록 View"""
    context = {
        "menu_structure": MENU_STRUCTURE,
        "current_group": group_name,
        "current_model": model_name,
        "page_title": model_name.replace("_", " ").title(),
        "default_scenario_id": DEFAULT_SCENARIO_ID,
    }
    return render(request, "input_data/input_list.html", context)


@login_required
@require_GET
def get_port_distance(request):
    """[API] 포트 거리 조회"""
    origin = request.GET.get("origin")
    destination = request.GET.get("destination")
    scenario_id = request.GET.get("scenario_id")

    distance = 0
    try:
        obj = Distance.objects.filter(
            scenario_id=scenario_id, from_port_code=origin, to_port_code=destination
        ).first()
        if obj:
            distance = obj.distance
    except Exception:
        pass
    return JsonResponse({"distance": distance})
