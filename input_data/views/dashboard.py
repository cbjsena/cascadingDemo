from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from common.menus import (
    CREATION_MENU_STRUCTURE,
    MENU_STRUCTURE,
    MenuSection,
)
from input_data.models import ScenarioInfo


@login_required
def input_home(request):
    """대시보드 View"""
    total_scenarios = ScenarioInfo.objects.count()
    recent_scenarios = ScenarioInfo.objects.order_by("-created_at")[:5]

    # 기본 시나리오 ID (첫 번째 시나리오 또는 None)
    default_scenario = ScenarioInfo.objects.first()
    default_scenario_id = default_scenario.id if default_scenario else None

    if recent_scenarios.exists():
        last_update = recent_scenarios.first().created_at
    else:
        last_update = None

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "total_scenarios": total_scenarios,
        "recent_scenarios": recent_scenarios,
        "last_update": last_update,
        "default_scenario_id": default_scenario_id,
    }
    return render(request, "input_data/input_home.html", context)
