from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from input_data.models import Distance

# 메뉴 구조 상수
MENU_STRUCTURE = {
    "Schedule": [
        {"name": "Proforma Schedule", "key": "proforma_schedule"},
        {"name": "Long Range Schedule", "key": "long_range_schedule"},
    ],
    "Vessel": [
        {"name": "Vessel Info", "key": "vessel_info"},
        {"name": "Charter Cost", "key": "charter_cost"},
        {"name": "Vessel Capacity", "key": "vessel_capacity"},
    ],
    "Cost": [
        {"name": "Port Charge", "key": "port_charge"},
        {"name": "Exchange Rate", "key": "exchange_rate"},
        {"name": "Canal Fee", "key": "canal_fee"},
        {"name": "Distance", "key": "distance"},
        {"name": "Own Vessel Cost", "key": "own_vessel_cost"},
        {"name": "TS Cost", "key": "ts_cost"},
    ],
    "Bunker": [
        {"name": "Bunker Consumption Sea", "key": "bunker_consumption_sea"},
        {"name": "Bunker Consumption Port", "key": "bunker_consumption_port"},
        {"name": "Bunkering Port", "key": "bunkering_port"},
        {"name": "Bunker Price", "key": "bunker_price"},
    ],
    "ETS & Fuel EU": [
        {"name": "ETS TS Port", "key": "ets_ts_port"},
        {"name": "ETS Country", "key": "ets_country"},
        {"name": "ETS Bunker Consumption", "key": "ets_bunker_consumption"},
        {"name": "ETS EUA", "key": "ets_eua"},
        {"name": "FUEL EU", "key": "fuel_eu"},
        {"name": "Fuel EU Bunker", "key": "fuel_eu_bunker"},
        {"name": "Greenhouse Gas Target", "key": "greenhouse_gas_target"},
    ],
}

@login_required
def input_list(request, group_name, model_name):
    """공통 입력 목록 View"""
    context = {
        "menu_structure": MENU_STRUCTURE,
        "current_group": group_name,
        "current_model": model_name,
        "page_title": model_name.replace("_", " ").title()
    }
    return render(request, 'input_data/input_list.html', context)

@login_required
@require_GET
def get_port_distance(request):
    """[API] 포트 거리 조회"""
    origin = request.GET.get('origin')
    destination = request.GET.get('destination')
    data_id = request.GET.get('data_id')

    distance = 0
    try:
        obj = Distance.objects.filter(
            data_id=data_id,
            from_port_code=origin,
            to_port_code=destination
        ).first()
        if obj:
            distance = obj.distance
    except Exception:
        pass
    return JsonResponse({'distance': distance})