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
@require_GET
def get_proforma_options(request):
    """
    [AJAX] 동적 셀렉트 박스를 위한 옵션 데이터 반환
    Mode 1: Scenario ID -> Lane Code List
    Mode 2: Scenario ID + Lane Code -> Proforma Name List
    """
    scenario_id = request.GET.get("scenario_id")
    lane_code = request.GET.get("lane_code")

    data = {"options": []}

    if scenario_id:
        if not lane_code:
            # Mode 1: Get Lane Codes
            lanes = ProformaSchedule.objects.filter(scenario_id=scenario_id) \
                .values_list('lane_code', flat=True).distinct().order_by('lane_code')
            data["options"] = list(lanes)
        else:
            # Mode 2: Get Proforma Names
            pfs = ProformaSchedule.objects.filter(scenario_id=scenario_id, lane_code=lane_code) \
                .values_list('proforma_name', flat=True).distinct().order_by('proforma_name')
            data["options"] = list(pfs)

    return JsonResponse(data)


@login_required
@require_GET
def get_proforma_info(request):
    """
    [AJAX] 선택된 Proforma의 상세 정보(선박 수, Duration,첫 번째 포트의 요일(etb_day_code) 등) 반환
    """
    scenario_id = request.GET.get("scenario_id")
    lane_code = request.GET.get("lane_code")
    proforma_name = request.GET.get("proforma_name")

    try:
        pf_first = ProformaSchedule.objects.filter(
            scenario_id=scenario_id, lane_code=lane_code, proforma_name=proforma_name,calling_port_seq=1
        ).first()

        if pf_first:
            data = {
                "status": "success",
                "declared_count": pf_first.declared_count,
                "declared_capacity": pf_first.declared_capacity,
                "duration": pf_first.duration,
                "first_port_day": pf_first.etb_day_code
            }
        else:
            data = {"status": "error", "message": "Proforma not found."}

    except Exception as e:
        data = {"status": "error", "message": str(e)}

    return JsonResponse(data)


@login_required
@require_GET
def get_vessel_list(request):
    """
    [AJAX] 선택된 시나리오의 가용 선박 목록 및 Max Capacity 조회
    Table: sce_vessel_capacity (Model: VesselCapacity)
    """
    scenario_id = request.GET.get("scenario_id")

    data = {"vessels": []}

    if scenario_id:
        # 해당 시나리오에 존재하는 vessel_code 별로 그룹화하여 max capacity 조회
        # .values('vessel_code') -> GROUP BY vessel_code
        qs = (VesselCapacity.objects.filter(scenario_id=scenario_id).values('vessel_code').annotate(max_cap=Max('vessel_capacity')).order_by('vessel_code'))

        data["vessels"] = list(qs)  # [{'vessel_code': 'V001', 'max_cap': 10000}, ...]

    return JsonResponse(data)


@login_required
@require_GET
def get_vessel_lane_check(request):
    """
    [AJAX] 특정 선박이 지정된 기간 내에 이미 스케줄이 있는지 확인
    - 존재하면 해당 Lane Code 반환
    """
    scenario_id = request.GET.get("scenario_id")
    vessel_code = request.GET.get("vessel_code")
    start_date = request.GET.get("start_date") # YYYY-MM-DD
    end_date = request.GET.get("end_date")     # YYYY-MM-DD

    data = {"lane_code": ""}

    if scenario_id and vessel_code and start_date and end_date:
        # 해당 기간 내에 ETB가 포함되는 스케줄이 있는지 조회
        # (혹은 ETA, ETD 기준 등 비즈니스 로직에 맞춰 조정 가능. 여기선 ETB 기준)
        qs = LongRangeSchedule.objects.filter(
            scenario_id=scenario_id,
            vessel_code=vessel_code,
            etb__date__gte=start_date,
            etb__date__lte=end_date
        ).order_by('etb')

        qs = LongRangeSchedule.objects.filter(
            scenario_id=scenario_id,
            vessel_code=vessel_code,
            etb__date__gte=start_date,
            etb__date__lte=end_date
        )
        print(f"--- [DEBUG] Generated SQL: {qs.query}")
        if qs.exists():
            # 가장 빠른 스케줄의 Lane Code 반환
            data["lane_code"] = qs.first().lane_code

    return JsonResponse(data)