from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from common import messages as msg
from common.menus import MENU_STRUCTURE
from input_data.models import CascadingSchedule, ScenarioInfo
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

    context = {
        "menu_structure": MENU_STRUCTURE,
        "current_group": "Creation Data",
        "current_model": "cascading_create",
        "scenarios": scenarios,
        "preserved_data": {},
        "restored_rows": [],
        "is_edit_mode": False,  # [추가] Edit 모드 플래그
    }

    # =========================================================
    # 1. GET 진입: Edit 모드 데이터 로드 or 빈 껍데기 화면
    # =========================================================
    if request.method == "GET":
        q_scenario = request.GET.get("scenario_id")
        q_lane = request.GET.get("lane_code")
        q_proforma = request.GET.get("proforma_name")
        q_seq = request.GET.get("cascading_seq")  # [핵심] Seq 파라미터 수신

        if q_scenario and q_lane and q_proforma and q_seq:
            # Edit 모드: 서비스에서 데이터 로드
            data = cascading_svc.get_cascading_data(
                q_scenario, q_lane, q_proforma, q_seq
            )
            if data:
                context["preserved_data"] = data["header"]
                context["restored_rows"] = data["details"]
                context["is_edit_mode"] = True
            else:
                messages.error(request, msg.CASCADING_NOT_FOUND)

        return render(request, "input_data/cascading_create.html", context)

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
                    messages.success(request, msg.CASCADING_SAVE_SUCCESS)

                elif action == "create_lrs":
                    # Create LRS 버튼을 눌렀을 때만 엔진 구동
                    lrs_svc.generate_lrs(request.POST, request.user)
                    messages.success(request, msg.CASCADING_LRS_CREATE_SUCCESS)

            # 처리가 끝나면 다시 현재 화면으로 (GET 파라미터는 제거되거나 유지할 수 있음)
            return redirect("input_data:cascading_create")

        except Exception as e:
            messages.error(request, msg.CASCADING_PROCESS_ERROR.format(error=str(e)))

            # (에러 복구 로직 - 기존과 동일하게 context 갱신)
            data = request.POST
            context["preserved_data"] = {
                "scenario_id": data.get("scenario_id", ""),
                "lane_code": data.get("lane_code", ""),
                "proforma_name": data.get("proforma_name", ""),
                "cascading_seq": data.get("cascading_seq", ""),
                "own_vessels": data.get("own_vessel_count", ""),
                "required_count": data.get("required_count", ""),
                "effective_start_date": data.get("effective_start_date", ""),
                "effective_end_date": data.get("effective_end_date", ""),
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


@login_required
def cascading_list(request):
    """
    Cascading Schedule 목록 조회 및 검색 (Vessel 제거, Select 박스 방식)
    """
    scenario_id = request.GET.get("scenario_id", "")
    lane_code = request.GET.get("lane_code", "")
    proforma_name = request.GET.get("proforma_name", "")

    # 1. 기본 QuerySet
    qs = (
        CascadingSchedule.objects.select_related("scenario", "proforma")
        .all()
        .order_by("-created_at")
    )

    # 2. 필터 적용 (Select Box이므로 정확한 일치로 변경)
    if scenario_id:
        qs = qs.filter(scenario_id=scenario_id)
    if lane_code:
        qs = qs.filter(proforma__lane_code=lane_code)
    if proforma_name:
        qs = qs.filter(proforma__proforma_name=proforma_name)

    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    context = {
        "menu_structure": MENU_STRUCTURE,
        "current_group": "Creation Data",
        "current_model": "cascading_list",
        "scenarios": scenarios,
        "cascading_list": qs,
        "search_params": {
            "scenario_id": scenario_id,
            "lane_code": lane_code,
            "proforma_name": proforma_name,
        },
    }

    return render(request, "input_data/cascading_list.html", context)


@login_required
def cascading_detail(request, pk):
    """
    Cascading Schedule 상세 조회 (Read-Only)
    """
    # 1. Master 객체 가져오기 (없으면 404 에러)
    cascading = get_object_or_404(
        CascadingSchedule.objects.select_related("scenario", "proforma"), pk=pk
    )

    # 2. Detail 목록 가져오기 (역방향 참조명 details 활용)
    details = cascading.details.all().order_by("id")

    context = {
        "menu_structure": MENU_STRUCTURE,
        "current_group": "Creation Data",
        "current_model": "cascading_list",  # 메뉴 활성화를 위해 list로 유지
        "cascading": cascading,
        "details": details,
    }

    return render(request, "input_data/cascading_detail.html", context)
