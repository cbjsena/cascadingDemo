from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from input_data.models import InputDataSnapshot
from .common import MENU_STRUCTURE

@login_required
def input_home(request):
    """대시보드 View"""
    total_snapshots = InputDataSnapshot.objects.count()
    recent_snapshots = InputDataSnapshot.objects.order_by('-created_at')[:5]

    if recent_snapshots.exists():
        last_update = recent_snapshots.first().created_at
    else:
        last_update = None

    context = {
        "menu_structure": MENU_STRUCTURE,
        "total_snapshots": total_snapshots,
        "recent_snapshots": recent_snapshots,
        "last_update": last_update,
    }
    return render(request, 'input_data/input_home.html', context)