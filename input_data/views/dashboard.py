from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from input_data.models import ScenarioInfo
from common.menus import MENU_STRUCTURE

@login_required
def input_home(request):
    """대시보드 View"""
    total_scenarios = ScenarioInfo.objects.count()
    recent_scenarios = ScenarioInfo.objects.order_by('-created_at')[:5]

    if recent_scenarios .exists():
        last_update = recent_scenarios .first().created_at
    else:
        last_update = None

    context = {
        "menu_structure": MENU_STRUCTURE,
        "total_scenarios ": total_scenarios ,
        "recent_scenarios ": recent_scenarios ,
        "last_update": last_update,
    }
    return render(request, 'input_data/input_home.html', context)