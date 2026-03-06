# api/views.py

from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from common import messages as msg

# ProformaScheduleDetail은 ORM의 related_name('details')으로 접근 가능하지만,
# 명시적으로 필요한 경우 import 할 수 있습니다.
from input_data.models import (
    LongRangeSchedule,
    ProformaSchedule,
    VesselCapacity,
)
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
                .values_list("lane_id", flat=True)
                .distinct()
                .order_by("lane_id")
            )
            data["options"] = list(lanes)
        else:
            pfs = (
                ProformaSchedule.objects.filter(
                    scenario_id=scenario_id, lane_id=lane_code
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
            lane_id=lane_code,
            proforma_name=proforma_name,
        ).first()

        if master:
            # 2. Detail (기항지 정보) 중 첫 번째 포트 조회
            # models.py에서 related_name="details"로 설정된 역참조 활용
            first_detail = master.details.order_by("calling_port_seq").first()
            first_port_day = first_detail.etb_day_code if first_detail else ""

            # Scenario의 from/to week 정보
            scenario = master.scenario

            # base_year_week (YYYYWK) 기반 시작 날짜 계산
            initial_start_date = ""
            if scenario and scenario.base_year_week:
                try:
                    from datetime import datetime, timedelta

                    year = int(scenario.base_year_week[:4])
                    week = int(scenario.base_year_week[4:])
                    # ISO week to date: 해당 주의 월요일
                    first_day = datetime.strptime(
                        f"{year}-W{week:02d}-1", "%Y-W%W-%w"
                    ).date()

                    # first_port_day에 맞춰 날짜 조정
                    if first_port_day:
                        day_map = {
                            "SUN": 6,
                            "MON": 0,
                            "TUE": 1,
                            "WED": 2,
                            "THU": 3,
                            "FRI": 4,
                            "SAT": 5,
                        }
                        target_weekday = day_map.get(first_port_day)
                        if target_weekday is not None:
                            current_weekday = first_day.weekday()
                            days_ahead = (target_weekday - current_weekday) % 7
                            first_day = first_day + timedelta(days=days_ahead)

                    initial_start_date = first_day.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    pass

            data = {
                "status": "success",
                "declared_count": master.declared_count,
                "declared_capacity": master.declared_capacity,
                "duration": master.duration,
                "first_port_day": first_port_day,
                "own_vessel_count": master.own_vessel_count,
                "from_year_week": scenario.base_year_week if scenario else "",
                "to_year_week": scenario.to_year_week if scenario else "",
                "initial_start_date": initial_start_date,
            }

            # 기존 Cascading 데이터 존재 여부 확인
            from input_data.models import CascadingVesselPosition

            existing_positions = CascadingVesselPosition.objects.filter(
                scenario=scenario, proforma=master
            )

            if existing_positions.exists():
                data["existing_cascading"] = {
                    "exists": True,
                    "detail_count": existing_positions.count(),
                    "scenario_id": scenario.id,
                    "proforma_id": master.id,
                }
            else:
                data["existing_cascading"] = {"exists": False}
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
            qs = qs.filter(lane_id=lane_code)

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
            data["lane_code"] = lrs_qs.first().lane_id
            return JsonResponse(data)

        # 2. [추가됨] LRS가 안 만들어졌다면, CascadingVesselPosition에서 찾아봄
        from input_data.models import CascadingVesselPosition

        cas_pos_qs = CascadingVesselPosition.objects.filter(
            vessel_code=vessel_code,
            vessel_position_date__lte=end_date,
        ).select_related("proforma")

        if cas_pos_qs.exists():
            data["lane_code"] = cas_pos_qs.first().proforma.lane_id

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
            qs = qs.filter(lane_id=lane_code)
        vessels = (
            qs.values_list("vessel_code", flat=True).distinct().order_by("vessel_code")
        )
        data["options"] = list(vessels)
    return JsonResponse(data)
