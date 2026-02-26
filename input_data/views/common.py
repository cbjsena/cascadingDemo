from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from common.menus import (
    CREATION_MENU_STRUCTURE,
    MENU_STRUCTURE,
    MenuSection,
)
from input_data.models import ScenarioInfo

# 메뉴 구조 상수


@login_required
def input_list(request, group_name, model_name):
    """공통 입력 목록 View"""
    # 기본 시나리오 ID (첫 번째 시나리오 또는 None)
    default_scenario = ScenarioInfo.objects.first()
    default_scenario_id = default_scenario.id if default_scenario else None

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": group_name,
        "current_model": model_name,
        "page_title": model_name.replace("_", " ").title(),
        "default_scenario_id": default_scenario_id,
    }
    return render(request, "input_data/input_list.html", context)
