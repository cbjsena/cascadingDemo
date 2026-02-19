from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from common.menus import MENU_STRUCTURE
from input_data.models import ProformaSchedule, ScenarioInfo, VesselCapacity, LongRangeSchedule
from input_data.services.long_range_service import LongRangeService


@login_required
def long_range_create(request):
    """
    Long Range Schedule (LRS) 생성 화면
    """
    service = LongRangeService()
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    context = {
        "menu_structure": MENU_STRUCTURE,
        "current_group": "Creation Data",
        "current_model": "long_range_create",
        "scenarios": scenarios,
    }

    if request.method == "POST":
        try:
            service.create_lrs(request.POST, request.user)
            messages.success(request, "Long Range Schedule created successfully.")
            return redirect("input_data:long_range_create")

        except Exception as e:
            messages.error(request, f"Failed to create LRS: {str(e)}")

            # --- 에러 발생 시 입력 데이터 복구 로직 ---
            data = request.POST
            scenario_id = data.get("scenario_id")
            lane_code = data.get("lane_code")

            # 1. 동적 옵션 데이터 복구 (Select Box용)
            lane_options = []
            proforma_options = []
            vessel_list = []

            if scenario_id:
                # Lane Options
                lane_options = ProformaSchedule.objects.filter(scenario_id=scenario_id) \
                    .values_list('lane_code', flat=True).distinct().order_by('lane_code')

                # Vessel Options (Capacity 포함)
                vessel_qs = VesselCapacity.objects.filter(scenario_id=scenario_id) \
                    .values('vessel_code') \
                    .annotate(max_cap=Max('vessel_capacity')) \
                    .order_by('vessel_code')
                vessel_list = list(vessel_qs)

                if lane_code:
                    # Proforma Options
                    proforma_options = ProformaSchedule.objects.filter(scenario_id=scenario_id, lane_code=lane_code) \
                        .values_list('proforma_name', flat=True).distinct().order_by('proforma_name')

            # 2. 테이블 행(Rows) 데이터 복구
            # request.POST.getlist는 순서를 보장함
            v_codes = data.getlist("vessel_code[]")  # TBN 포함
            v_caps = data.getlist("vessel_capacity[]")
            v_dates = data.getlist("vessel_start_date[]")
            l_codes = data.getlist("lane_code_list[]")

            restored_rows = []
            for i, code in enumerate(v_codes):
                # 'TBN'이 아니고 값이 있으면 체크된 상태로 간주
                is_own = (code and code != "TBN")

                row = {
                    "seq": i + 1,
                    "vessel_code": code if is_own else "",  # TBN이면 화면엔 빈값 표시
                    "capacity": v_caps[i],
                    "start_date": v_dates[i],
                    "lane_code": l_codes[i],
                    "is_checked": is_own
                }
                restored_rows.append(row)

            # Context 업데이트
            context.update({
                "preserved_data": data,  # 입력값 전체
                "lane_options": lane_options,  # 복구된 Lane 목록
                "proforma_options": proforma_options,  # 복구된 Proforma 목록
                "vessel_list": vessel_list,  # 복구된 선박 목록
                "restored_rows": restored_rows,  # 복구된 테이블 행
                "is_error_state": True,  # 에러 상태 플래그
            })

    return render(request, "input_data/long_range_create.html", context)


@login_required
def long_range_list(request):
    """
    Long Range Schedule 목록 조회 및 검색
    """
    # 1. 검색 파라미터
    scenario_id = request.GET.get("scenario_id")
    lane_code = request.GET.get("lane_code")
    proforma_name = request.GET.get("proforma_name")
    vessel_code = request.GET.get("vessel_code")

    # 2. 기본 쿼리셋
    lrs_qs = LongRangeSchedule.objects.none()

    # 시나리오는 필수 (또는 기본 구조상 최상위 필터)
    if scenario_id:
        lrs_qs = LongRangeSchedule.objects.filter(scenario_id=scenario_id)

        if lane_code:
            lrs_qs = lrs_qs.filter(lane_code=lane_code)

        if proforma_name:
            lrs_qs = lrs_qs.filter(proforma_name=proforma_name)

        # Vessel Code 검색 (부분 일치 허용)
        if vessel_code:
            lrs_qs = lrs_qs.filter(vessel_code__icontains=vessel_code)

        # 정렬: Voyage -> Seq
        lrs_qs = lrs_qs.order_by("vessel_code", "voyage_number", "direction", "calling_port_seq")

    context = {
        "menu_structure": MENU_STRUCTURE,
        "current_group": "Schedule",
        "current_model": "long_range_list",
        "scenarios": ScenarioInfo.objects.all().order_by("-created_at"),
        "lrs_list": lrs_qs,
        # 검색 상태 유지용
        "search_params": {
            "scenario_id": scenario_id,
            "lane_code": lane_code,
            "proforma_name": proforma_name,
            "vessel_code": vessel_code,
        }
    }

    return render(request, "input_data/long_range_list.html", context)
