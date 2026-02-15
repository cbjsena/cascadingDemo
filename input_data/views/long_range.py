# input_data/views/long_range.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from common.menus import MENU_STRUCTURE
from input_data.models import ProformaSchedule, ScenarioInfo
from input_data.services.long_range_service import LongRangeService


@login_required
def long_range_create(request):
    """
    Long Range Schedule (LRS) 생성 화면
    """
    service = LongRangeService()

    # 초기 Context
    context = {
        "menu_structure": MENU_STRUCTURE,
        "current_group": "Schedule",
        "current_model": "long_range_schedule",
        "scenarios": ScenarioInfo.objects.all().order_by("-created_at"),
    }

    if request.method == "POST":
        try:
            # 1. 화면 데이터 파싱
            # form data: scenario_id, lane_code, proforma_name, start_date, end_date, own_count
            # table data: vessel_name[], vessel_start_date[]

            # 2. Service 호출 (LRS 생성 로직)
            service.create_lrs(request.POST, request.user)

            messages.success(request, "Long Range Schedule created successfully.")
            return redirect("input_data:long_range_create")

        except Exception as e:
            messages.error(request, f"Failed to create LRS: {str(e)}")
            # 에러 발생 시 입력했던 값 유지를 위해 context 업데이트 로직 필요 (여기선 생략)

    return render(request, "input_data/long_range_create.html", context)


@login_required
@require_GET
def get_proforma_info(request):
    """
    [AJAX] 선택된 Proforma의 상세 정보(필요 선박 수 등) 반환
    """
    scenario_id = request.GET.get("scenario_id")
    lane_code = request.GET.get("lane_code")
    proforma_name = request.GET.get("proforma_name")

    try:
        # Proforma Header 정보 조회 (첫 번째 행 기준)
        pf = ProformaSchedule.objects.filter(
            scenario_id=scenario_id, lane_code=lane_code, proforma_name=proforma_name
        ).first()

        if pf:
            data = {
                "status": "success",
                "declared_count": pf.declared_count,  # 필요 선박 수
                "declared_capacity": pf.declared_capacity,
                "duration": pf.duration,
            }
        else:
            data = {"status": "error", "message": "Proforma not found."}

    except Exception as e:
        data = {"status": "error", "message": str(e)}

    return JsonResponse(data)
