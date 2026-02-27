# api/views.py

from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from common import messages as msg

# ProformaScheduleDetail은 ORM의 related_name('details')으로 접근 가능하지만,
# 명시적으로 필요한 경우 import 할 수 있습니다.
from input_data.models import (
    CascadingScheduleDetail,
    LongRangeSchedule,
    ProformaSchedule,
    VesselCapacity,
)
from input_data.services.cascading_service import CascadingService
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
    """선택된 Proforma의 상세 정보 반환 (Master + 첫 번째 Detail)"""
    scenario_id = request.GET.get("scenario_id")
    lane_code = request.GET.get("lane_code")
    proforma_name = request.GET.get("proforma_name")

    try:
        # 1. Master (헤더 정보) 조회
        master = ProformaSchedule.objects.filter(
            scenario_id=scenario_id,
            lane_code=lane_code,
            proforma_name=proforma_name,
        ).first()

        if master:
            # 2. Detail (기항지 정보) 중 첫 번째 포트 조회
            # models.py에서 related_name="details"로 설정된 역참조 활용
            first_detail = master.details.order_by("calling_port_seq").first()
            first_port_day = first_detail.etb_day_code if first_detail else ""

            cascading_svc = CascadingService()
            cascading_next_seq = cascading_svc.get_next_cascading_seq(
                scenario_id, lane_code, proforma_name
            )

            data = {
                "status": "success",
                "declared_count": master.declared_count,
                "declared_capacity": master.declared_capacity,
                "duration": master.duration,
                "first_port_day": first_port_day,
                "cascading_next_seq": cascading_next_seq,
            }
        else:
            data = {"status": "error", "message": msg.PROFORMA_NOT_FOUND}
    except Exception as e:
        data = {"status": "error", "message": str(e)}
    return JsonResponse(data)


@login_required
@require_GET
def vessel_list(request):
    """가용 선박 목록 조회 (VesselCapacity)"""
    scenario_id = request.GET.get("scenario_id")
    lane_code = request.GET.get("lane_code")  # Lane별 필터링 지원
    data = {"vessels": []}

    if scenario_id:
        qs = VesselCapacity.objects.filter(scenario_id=scenario_id)

        # Lane 필터링이 있는 경우 적용
        if lane_code:
            qs = qs.filter(lane_code=lane_code)

        qs = (
            qs.values("vessel_code")
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
        # 1. 먼저 생성된 LRS 엔진 데이터에서 찾아봄
        lrs_qs = LongRangeSchedule.objects.filter(
            scenario_id=scenario_id,
            vessel_code=vessel_code,
            etb__date__gte=start_date,
            etb__date__lte=end_date,
        )
        if lrs_qs.exists():
            data["lane_code"] = lrs_qs.first().lane_code
            return JsonResponse(data)

        # 2. [추가됨] LRS가 안 만들어졌다면, Cascading 저장 데이터에서 찾아봄
        cas_qs = CascadingScheduleDetail.objects.filter(
            vessel_code=vessel_code,
            initial_start_date__lte=end_date,  # 선박의 투입일(첫 ETB)이 검색 종료일보다 이전이고
            cascading__effective_end_date__gte=start_date,  # 스케줄 그룹의 종료일이 검색 시작일보다 이후일 때
        ).select_related("cascading__proforma")

        if cas_qs.exists():
            data["lane_code"] = cas_qs.first().cascading.proforma.lane_code

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
