from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from common import messages as msg
from common.menus import (
    CREATION_MENU_STRUCTURE,
    MENU_STRUCTURE,
    MenuGroup,
    MenuItem,
    MenuSection,
)
from input_data.models import (
    BaseVesselCapacity,
    BaseVesselInfo,
    CascadingSchedule,
    ProformaSchedule,
    ScenarioInfo,
)
from input_data.services.cascading_service import CascadingService
from input_data.services.long_range_service import LongRangeService


@login_required
def cascading_vessel_create(request):
    """
    Cascading Schedule 생성 화면
    """
    cascading_svc = CascadingService()
    lrs_svc = LongRangeService()
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    # Vessel 목록 가져오기 (VesselInfo와 VesselCapacity 조인)
    vessel_list = (
        BaseVesselInfo.objects.all()
        .values("vessel_code", "vessel_name")
        .distinct()
        .order_by("vessel_code")
    )

    # 각 vessel에 대한 capacity 정보 추가
    vessel_data = []
    for vessel in vessel_list:
        # 해당 vessel의 capacity 정보를 가져오기 (첫 번째 것만)
        capacity_info = BaseVesselCapacity.objects.filter(
            vessel_code=vessel["vessel_code"]
        ).first()

        vessel_data.append(
            {
                "vessel_code": vessel["vessel_code"],
                "vessel_name": vessel["vessel_name"],
                "max_cap": capacity_info.vessel_capacity if capacity_info else 0,
            }
        )

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.CREATION,
        "current_group": MenuGroup.SCHEDULE,
        "current_model": MenuItem.CASCADING_VESSEL_CREATE,
        "scenarios": scenarios,
        "vessel_list": vessel_data,  # 선박 목록 추가
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

        if q_scenario and q_lane and q_proforma:
            # Edit 모드: 서비스에서 데이터 로드
            data = cascading_svc.get_cascading_data(q_scenario, q_lane, q_proforma)
            if data:
                # scenario_id를 문자열로 변환하여 저장 (템플릿 비교를 위해)
                header = data["header"].copy()
                if header.get("scenario_id"):
                    header["scenario_id"] = str(header["scenario_id"])

                context["preserved_data"] = header
                context["restored_rows"] = data["details"]
                context["is_edit_mode"] = True

                # Edit 모드일 때 Lane Code와 Proforma Name 옵션들을 미리 로드
                # 해당 시나리오의 모든 Lane Code 가져오기
                lane_options = list(
                    ProformaSchedule.objects.filter(scenario_id=q_scenario)
                    .values_list("lane_code", flat=True)
                    .distinct()
                    .order_by("lane_code")
                )

                # 해당 시나리오와 Lane Code의 모든 Proforma Name 가져오기
                proforma_options = list(
                    ProformaSchedule.objects.filter(
                        scenario_id=q_scenario, lane_code=q_lane
                    )
                    .values_list("proforma_name", flat=True)
                    .distinct()
                    .order_by("proforma_name")
                )

                context["lane_options"] = lane_options
                context["proforma_options"] = proforma_options

            else:
                messages.error(request, msg.CASCADING_NOT_FOUND)

        return render(request, "input_data/cascading_vessel_create.html", context)

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
            return redirect("input_data:cascading_vessel_create")

        except Exception as e:
            messages.error(request, msg.CASCADING_PROCESS_ERROR.format(error=str(e)))

            # (에러 복구 로직 - 기존과 동일하게 context 갱신)
            data = request.POST
            context["preserved_data"] = {
                "scenario_id": data.get("scenario_id", ""),
                "lane_code": data.get("lane_code", ""),
                "proforma_name": data.get("proforma_name", ""),
                "own_vessel_count": data.get("own_vessel_count", ""),
                "required_count": data.get("required_count", ""),
            }
            error_restored = []
            vessel_codes = data.getlist("vessel_code[]")
            vessel_dates = data.getlist("vessel_start_date[]")
            vessel_caps = data.getlist("vessel_capacity[]")
            lane_lists = data.getlist("lane_code_list[]")

            for i, (v_code, v_date, v_cap, l_list) in enumerate(
                zip(vessel_codes, vessel_dates, vessel_caps, lane_lists)
            ):
                error_restored.append(
                    {
                        "seq": i + 1,
                        "is_checked": bool(v_code and v_code.strip()),
                        "vessel_code": v_code,
                        "start_date": v_date,
                        "capacity": v_cap,
                        "lane_code": l_list,
                    }
                )
            context["restored_rows"] = error_restored
            context["is_error_state"] = True

    # 템플릿 이름은 요청하신 대로 변경된 파일을 바라봄
    return render(request, "input_data/cascading_vessel_create.html", context)


@login_required
def cascading_vessel_detail(request, pk):
    """
    Cascading Schedule 상세 조회 (Read-Only)
    """
    # 1. Master 객체 가져오기 (없으면 404 에러)
    cascading = get_object_or_404(
        CascadingSchedule.objects.select_related("scenario", "proforma"), pk=pk
    )

    # 2. Detail 목록 가져오기 (역방향 참조명 details 활용)
    details = cascading.details.all().order_by("id")

    # 3. 첫 번째 포트의 ETB 요일 정보 가져오기
    first_port_day = None
    try:
        # Proforma의 첫 번째 포트 스케줄 가져오기
        first_schedule = cascading.proforma.details.filter(
            calling_port_seq=1  # 첫 번째 포트
        ).first()

        if first_schedule and first_schedule.etb_day_code:
            first_port_day = first_schedule.etb_day_code
    except Exception as e:
        # 에러가 발생해도 페이지는 정상 표시
        print(f"Error getting first port day: {e}")

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.SCHEDULE,
        "current_model": MenuItem.CASCADING_VESSEL_INFO,
        "cascading": cascading,
        "details": details,
        "first_port_day": first_port_day,  # 첫 번째 포트 요일 코드 (SUN, MON 등)
    }

    return render(request, "input_data/cascading_vessel_detail.html", context)


@login_required
def cascading_vessel_info(request):
    """
    Cascading Vessel Info: Scenario를 선택하면 Lane 별 Cascading 결과를 한눈에 조회
    선박 배치 슬롯을 가로로 시각화하여 표시
    """
    from datetime import timedelta

    scenario_id = request.GET.get("scenario_id", "")
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    dashboard_data = []
    max_declared = 0  # 테이블 헤더 동적 생성용

    if scenario_id:
        # 해당 시나리오의 모든 Cascading Schedule을 Lane 기준으로 조회
        qs = (
            CascadingSchedule.objects.select_related("scenario", "proforma")
            .prefetch_related("details")
            .filter(scenario_id=scenario_id)
            .order_by(
                "proforma__lane_code",
                "proforma__proforma_name",
            )
        )

        for cascading in qs:
            declared_count = cascading.proforma.declared_count
            if declared_count > max_declared:
                max_declared = declared_count

            # 시작 주차 계산 (proforma_start_etb_date 기준 ISO week)
            start_week = ""
            if cascading.proforma_start_etb_date:
                iso = cascading.proforma_start_etb_date.isocalendar()
                start_week = f"{iso[0]}-W{iso[1]:02d}"

            # 슬롯 배치 계산: 어떤 순번에 vessel이 배정되었는지
            base_date = cascading.proforma_start_etb_date
            saved_details = list(cascading.details.all())

            slots = []
            for i in range(declared_count):
                row_date = base_date + timedelta(days=i * 7) if base_date else None
                matched = next(
                    (d for d in saved_details if d.initial_start_date == row_date),
                    None,
                )
                slots.append(
                    {
                        "index": i + 1,
                        "assigned": matched is not None,
                        "vessel_code": matched.vessel_code if matched else "",
                    }
                )

            dashboard_data.append(
                {
                    "lane_code": cascading.proforma.lane_code,
                    "proforma_name": cascading.proforma.proforma_name,
                    "declared_count": declared_count,
                    "own_vessel_count": cascading.proforma.own_vessel_count,
                    "start_week": start_week,
                    "start_date": cascading.proforma_start_etb_date,
                    "slots": slots,
                    "pk": cascading.pk,
                }
            )

    # 슬롯 헤더 번호 리스트 (1 ~ max_declared)
    slot_headers = list(range(1, max_declared + 1))

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.SCHEDULE,
        "current_model": MenuItem.CASCADING_VESSEL_INFO,
        "scenarios": scenarios,
        "dashboard_data": dashboard_data,
        "selected_scenario_id": scenario_id,
        "slot_headers": slot_headers,
        "max_declared": max_declared,
    }

    return render(request, "input_data/cascading_vessel_info.html", context)
