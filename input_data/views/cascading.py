from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from common.menus import MENU_STRUCTURE
from input_data.models import ScenarioInfo
from input_data.services.cascading_service import CascadingService
from input_data.services.long_range_service import LongRangeService


@login_required
def cascading_create(request):
    """
    Cascading Schedule 생성 화면
    """
    cascading_svc = CascadingService()
    lrs_svc = LongRangeService()
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    # =========================================================
    # 1. GET 데이터 로드 (저장된 Cascading 불러오기)
    # =========================================================
    scenario_id_get = request.GET.get("scenario_id")
    lane_code_get = request.GET.get("lane_code")
    proforma_name_get = request.GET.get("proforma_name")

    preserved_data = {}
    restored_rows = []

    if scenario_id_get and lane_code_get and proforma_name_get:
        preserved_data = {
            "scenario_id": scenario_id_get,
            "lane_code": lane_code_get,
            "proforma_name": proforma_name_get,
        }
        cascading_data = cascading_svc.get_cascading_data(
            scenario_id_get, lane_code_get, proforma_name_get
        )
        if cascading_data:
            preserved_data.update(cascading_data["header"])
            restored_rows = cascading_data["details"]

    context = {
        "menu_structure": MENU_STRUCTURE,
        "current_group": "Creation Data",
        "current_model": "cascading_create",
        "scenarios": scenarios,
        "preserved_data": preserved_data,
        "restored_rows": restored_rows,
    }

    # =========================================================
    # 2. POST 처리 (Cascading 저장 -> LRS 엔진 호출)
    # =========================================================
    if request.method == "POST":
        action = request.POST.get("action")

        try:
            with transaction.atomic():
                # 공통: Cascading 데이터는 어느 버튼을 누르든 우선 저장됨
                cascading_svc.save_cascading(request.POST, request.user)

                if action == "save":
                    messages.success(request, "Cascading Schedule saved successfully.")

                elif action == "create_lrs":
                    # Create LRS 버튼을 눌렀을 때만 엔진 구동
                    lrs_svc.generate_lrs(request.POST, request.user)
                    messages.success(
                        request, "Cascading & Long Range Schedule created successfully."
                    )

            # 처리가 끝나면 다시 현재 화면으로 (GET 파라미터는 제거되거나 유지할 수 있음)
            return redirect("input_data:cascading_create")

        except Exception as e:
            messages.error(request, f"Failed to process: {str(e)}")

            # (에러 복구 로직 - 기존과 동일하게 context 갱신)
            data = request.POST
            context["preserved_data"] = {
                "scenario_id": data.get("scenario_id", ""),
                "lane_code": data.get("lane_code", ""),
                "proforma_name": data.get("proforma_name", ""),
                "apply_start_date": data.get("apply_start_date", ""),
                "apply_end_date": data.get("apply_end_date", ""),
            }
            error_restored = []
            for v_code, v_date, v_cap, l_list in zip(
                data.getlist("vessel_code[]"),
                data.getlist("vessel_start_date[]"),
                data.getlist("vessel_capacity[]"),
                data.getlist("lane_code_list[]"),
            ):
                error_restored.append(
                    {
                        "vessel_code": v_code,
                        "vessel_start_date": v_date,
                        "capacity": v_cap,
                        "lane_code_list": l_list,
                    }
                )
            context["restored_rows"] = error_restored
            context["is_error_state"] = True

    # 템플릿 이름은 요청하신 대로 변경된 파일을 바라봄
    return render(request, "input_data/cascading_create.html", context)
