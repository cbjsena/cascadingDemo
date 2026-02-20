# Create your views here.
# api/views.py

from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from input_data.models import LongRangeSchedule, ProformaSchedule, VesselCapacity
from input_data.services.common_service import get_distance_between_ports


@login_required
@require_GET
def port_distance(request):
    """[API] 포트 거리 조회"""
    origin = request.GET.get("origin")
    destination = request.GET.get("destination")
    scenario_id = request.GET.get("scenario_id")
    data = {"status": "success", "distance": 0, "eac_distance": 0}
    try:
        distance, eca_distance = get_distance_between_ports(
            scenario_id, origin, destination
        )
        data = {"status": "success", "distance": distance, "eac_distance": eca_distance}
    except Exception as e:
        data = {"status": "error", "message": str(e)}
    return JsonResponse(data)


@login_required
@require_GET
def proforma_options(request):
    """Scenario -> Lane -> Proforma Cascade Select 옵션 반환"""
    scenario_id = request.GET.get("scenario_id")
    lane_code = request.GET.get("lane_code")
    data = {"options": []}

    if scenario_id:
        if not lane_code:
            lanes = (
                ProformaSchedule.objects.filter(scenario_id=scenario_id)
                .values_list("lane_code", flat=True)
                .distinct()
                .order_by("lane_code")
            )
            data["options"] = list(lanes)
        else:
            pfs = (
                ProformaSchedule.objects.filter(
                    scenario_id=scenario_id, lane_code=lane_code
                )
                .values_list("proforma_name", flat=True)
                .distinct()
                .order_by("proforma_name")
            )
            data["options"] = list(pfs)
    return JsonResponse(data)


@login_required
@require_GET
def proforma_detail(request):
    """선택된 Proforma의 상세 정보 반환"""
    scenario_id = request.GET.get("scenario_id")
    lane_code = request.GET.get("lane_code")
    proforma_name = request.GET.get("proforma_name")
    try:
        pf_first = (
            ProformaSchedule.objects.filter(
                scenario_id=scenario_id,
                lane_code=lane_code,
                proforma_name=proforma_name,
            )
            .order_by("calling_port_seq")
            .first()
        )

        if pf_first:
            data = {
                "status": "success",
                "declared_count": pf_first.declared_count,
                "declared_capacity": pf_first.declared_capacity,
                "duration": pf_first.duration,
                "first_port_day": pf_first.etb_day_code,
            }
        else:
            data = {"status": "error", "message": "Proforma not found."}
    except Exception as e:
        data = {"status": "error", "message": str(e)}
    return JsonResponse(data)


@login_required
@require_GET
def vessel_list(request):
    """가용 선박 목록 조회 (VesselCapacity)"""
    scenario_id = request.GET.get("scenario_id")
    data = {"vessels": []}
    if scenario_id:
        qs = (
            VesselCapacity.objects.filter(scenario_id=scenario_id)
            .values("vessel_code")
            .annotate(max_cap=Max("vessel_capacity"))
            .order_by("vessel_code")
        )
        data["vessels"] = list(qs)
    return JsonResponse(data)


@login_required
@require_GET
def vessel_lane_check(request):
    """특정 선박의 기간 내 Lane 점유 확인"""
    scenario_id = request.GET.get("scenario_id")
    vessel_code = request.GET.get("vessel_code")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    data = {"lane_code": ""}

    if scenario_id and vessel_code and start_date and end_date:
        qs = LongRangeSchedule.objects.filter(
            scenario_id=scenario_id,
            vessel_code=vessel_code,
            etb__date__gte=start_date,
            etb__date__lte=end_date,
        )
        if qs.exists():
            data["lane_code"] = qs.first().lane_code
    return JsonResponse(data)


@login_required
@require_GET
def vessel_options(request):
    """LRS 테이블 기준 존재하는 선박 목록 (검색 필터용)"""
    scenario_id = request.GET.get("scenario_id")
    lane_code = request.GET.get("lane_code")
    data = {"options": []}
    if scenario_id:
        qs = LongRangeSchedule.objects.filter(scenario_id=scenario_id)
        if lane_code:
            qs = qs.filter(lane_code=lane_code)
        vessels = (
            qs.values_list("vessel_code", flat=True).distinct().order_by("vessel_code")
        )
        data["options"] = list(vessels)
    return JsonResponse(data)
