# api/views.py

from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from common import messages as msg
from input_data.models import (
    BaseVesselInfo,
    BaseWeekPeriod,
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

    try:
        distance, eca_distance = get_distance_between_ports(
            scenario_id, origin, destination
        )
        data = {"status": "success", "distance": distance, "eca_distance": eca_distance}
    except Exception as e:
        data = {"status": "error", "message": str(e)}

    return JsonResponse(data)


@login_required
@require_GET
def proforma_options(request):
    """Scenario -> Lane -> Proforma Cascade Select 옵션 반환"""
    scenario_id = request.GET.get("scenario_id")
    lane_code = request.GET.get("lane_code")

    try:
        options = []
        if scenario_id:
            if not lane_code:
                lanes = (
                    ProformaSchedule.objects.filter(scenario_id=scenario_id)
                    .values_list("lane_id", flat=True)
                    .distinct()
                    .order_by("lane_id")
                )
                options = list(lanes)
            else:
                pfs = (
                    ProformaSchedule.objects.filter(
                        scenario_id=scenario_id, lane_id=lane_code
                    )
                    .values_list("proforma_name", flat=True)
                    .distinct()
                    .order_by("proforma_name")
                )
                options = list(pfs)

        data = {"status": "success", "options": options}
    except Exception as e:
        data = {"status": "error", "message": str(e), "options": []}

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
            first_detail = master.details.order_by("calling_port_seq").first()
            first_port_day = first_detail.etb_day_code if first_detail else ""

            # Scenario의 from/to week 정보
            scenario = master.scenario

            initial_start_date = ""

            # [방어 로직 추가] base_year_week가 있고, 6자리 숫자형인지 엄격하게 검증
            if (
                scenario
                and scenario.base_year_week
                and len(scenario.base_year_week) == 6
                and scenario.base_year_week.isdigit()
            ):

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
                    pass  # 파싱 실패 시 초기 빈 문자열("") 유지

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

    try:
        vessels = []
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
            vessels = list(qs)

        data = {"status": "success", "vessels": vessels}
    except Exception as e:
        data = {"status": "error", "message": str(e), "vessels": []}

    return JsonResponse(data)


@login_required
@require_GET
def vessel_lane_check(request):
    """특정 선박의 기간 내 Lane 점유 확인"""
    scenario_id = request.GET.get("scenario_id")
    vessel_code = request.GET.get("vessel_code")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    try:
        lane_code = ""
        if scenario_id and vessel_code and start_date and end_date:
            # 1. 먼저 생성된 LRS 엔진 데이터에서 찾아봄
            lrs_qs = LongRangeSchedule.objects.filter(
                scenario_id=scenario_id,
                vessel_code=vessel_code,
                etb__date__gte=start_date,
                etb__date__lte=end_date,
            )
            if lrs_qs.exists():
                lane_code = lrs_qs.first().lane_id
            else:
                # 2. [추가됨] LRS가 안 만들어졌다면, CascadingVesselPosition에서 찾아봄
                from input_data.models import CascadingVesselPosition

                cas_pos_qs = CascadingVesselPosition.objects.filter(
                    vessel_code=vessel_code,
                    vessel_position_date__lte=end_date,
                ).select_related("proforma")

                if cas_pos_qs.exists():
                    lane_code = cas_pos_qs.first().proforma.lane_id

        data = {"status": "success", "lane_code": lane_code}
    except Exception as e:
        data = {"status": "error", "message": str(e), "lane_code": ""}

    return JsonResponse(data)


@login_required
@require_GET
def base_vessel_list(request):
    """[API] Base Vessel Info 마스터 선박 목록 반환"""
    try:
        vessels = list(
            BaseVesselInfo.objects.all()
            .order_by("vessel_code")
            .values("vessel_code", "vessel_name", "own_yn")
        )
        data = {"status": "success", "vessels": vessels}
    except Exception as e:
        data = {"status": "error", "message": str(e), "vessels": []}

    return JsonResponse(data)


@login_required
@require_GET
def vessel_options(request):
    """LRS 테이블 기준 존재하는 선박 목록 (검색 필터용)"""
    scenario_id = request.GET.get("scenario_id")
    lane_code = request.GET.get("lane_code")

    try:
        options = []
        if scenario_id:
            qs = LongRangeSchedule.objects.filter(scenario_id=scenario_id)
            if lane_code:
                qs = qs.filter(lane_id=lane_code)
            options = list(
                qs.values_list("vessel_code", flat=True)
                .distinct()
                .order_by("vessel_code")
            )
        data = {"status": "success", "options": options}
    except Exception as e:
        data = {"status": "error", "message": str(e), "options": []}

    return JsonResponse(data)


@login_required
@require_GET
def week_period_info(request):
    """
    [API] 특정 주차(YYYYWK)의 정확한 날짜와 월 정보를 반환
    사용 예: /api/v1/week-info/?year_week=202601
    """
    year_week = request.GET.get("year_week")

    if not year_week or len(year_week) != 6:
        return JsonResponse(
            {"status": "error", "message": "Invalid format (use YYYYWK)"}
        )

    try:
        year = int(year_week[:4])
        week = int(year_week[4:])

        period = BaseWeekPeriod.objects.filter(base_year=year, base_week=week).first()
        if period:
            return JsonResponse(
                {
                    "status": "success",
                    "base_year": period.base_year,
                    "base_month": period.base_month,
                    "base_week": period.base_week,
                    "start_date": period.week_start_date.strftime("%Y-%m-%d"),
                    "end_date": period.week_end_date.strftime("%Y-%m-%d"),
                }
            )
        else:
            return JsonResponse({"status": "error", "message": "Period not found"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
