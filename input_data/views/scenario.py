import json

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldDoesNotExist
from django.db import transaction
from django.db.models import Count, Min
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from common import messages as msg
from common.constants import DEFAULT_BASE_YEAR_MONTH
from common.menus import MENU_STRUCTURE
from input_data.models import ProformaSchedule, ScenarioInfo
from input_data.services.scenario_service import create_scenario_from_base


@login_required
def scenario_list(request):
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    # 기본값 생성 로직 (Helper)
    today_str = timezone.now().strftime("%Y%m%d")
    last_scenario = (
        ScenarioInfo.objects.filter(id__startswith=today_str).order_by("-id").first()
    )
    new_seq = 1
    if last_scenario:
        try:
            new_seq = int(last_scenario.id[8:]) + 1
        except ValueError:
            pass
    default_scenario_id = f"{today_str}{new_seq:02d}"
    default_base_ym = timezone.now().strftime("%Y%m")

    context = {
        "menu_structure": MENU_STRUCTURE,
        "scenarios": scenarios,
        "default_scenario_id": default_scenario_id,
        "default_base_ym": default_base_ym,
    }
    return render(request, "input_data/scenario_list.html", context)


@login_required
@transaction.atomic
def scenario_create(request):
    if request.method == "POST":
        new_scenario_id = request.POST.get("scenario_id")
        source_scenario_id = request.POST.get("source_scenario_id")
        description = request.POST.get("description")
        base_ym = request.POST.get("base_year_month")

        if ScenarioInfo.objects.filter(id=new_scenario_id).exists():
            messages.error(
                request, msg.SCENARIO_ID_DUPLICATE.format(scenario_id=new_scenario_id)
            )
            return redirect("input_data:scenario_list")

        new_scenario = ScenarioInfo.objects.create(
            id=new_scenario_id,
            description=description,
            base_year_month=base_ym,
            created_by=request.user,
            updated_by=request.user,
        )

        if source_scenario_id:
            try:
                _clone_scenario_data(source_scenario_id, new_scenario)
                messages.success(
                    request,
                    msg.SCENARIO_CLONE_SUCCESS.format(
                        scenario_id=new_scenario_id, source_id=source_scenario_id
                    ),
                )
            except Exception as e:
                messages.error(request, msg.SCENARIO_CLONE_ERROR.format(error=str(e)))
                return redirect("input_data:scenario_list")
        else:
            messages.success(
                request, msg.SCENARIO_CREATE_SUCCESS.format(scenario_id=new_scenario_id)
            )

        return redirect("input_data:scenario_list")
    return redirect("input_data:scenario_list")


@login_required
@transaction.atomic
@require_POST
def scenario_delete(request, scenario_id):
    scenario = get_object_or_404(ScenarioInfo, id=scenario_id)
    if not (scenario.created_by == request.user or request.user.is_superuser):
        messages.error(request, msg.PERMISSION_DENIED)
        return redirect("input_data:scenario_list")

    try:
        scenario.delete()
        messages.success(
            request, msg.SCENARIO_DELETE_SUCCESS.format(scenario_id=scenario_id)
        )
    except Exception as e:
        messages.error(request, msg.SCENARIO_DELETE_ERROR.format(error=str(e)))
    return redirect("input_data:scenario_list")


@login_required
@require_POST
def create_base_scenario_view(request):
    """
    [Web UI] Base 시나리오 생성 버튼 클릭 시 호출
    """
    try:
        # JSON Body 혹은 Form Data 처리
        # (Fetch API 사용 시 body, Form submit 시 POST dict)
        if request.content_type == "application/json":
            data = json.loads(request.body)
            target_id = data.get("scenario_id", DEFAULT_BASE_YEAR_MONTH)
            description = data.get("description", "Base Scenario created from Web")
        else:
            target_id = request.POST.get("scenario_id", DEFAULT_BASE_YEAR_MONTH)
            description = request.POST.get(
                "description", "Base Scenario created from Web"
            )

        # [수정 사항 3] 로그인한 사용자(request.user) 전달
        scenario, summary = create_scenario_from_base(
            target_id=target_id, description=description, user=request.user
        )

        return JsonResponse(
            {
                "status": "success",
                "message": msg.SCENARIO_CREATE_SUCCESS.format(scenario_id=target_id),
                "summary": summary,
            }
        )

    except Exception as e:
        return JsonResponse(
            {"status": "error", "message": msg.SAVE_ERROR.format(error=str(e))},
            status=500,
        )


@login_required
def scenario_dashboard(request, scenario_id):
    """
    [View] 시나리오 상세 대시보드
    - Lane별 선박 투입 계획(Proforma) 요약 및 통계 제공
    """
    # Todo lrs 완성 이후 lrs에서 가져와서 보여주도록 수정(count 대비 실제 deploy된 선박, 용량, 첫 날짜)
    # 1. 시나리오 조회 (없으면 404)
    scenario = get_object_or_404(ScenarioInfo, id=scenario_id)

    # 2. 스케줄 데이터 집계 (Group By Lane, Name)
    # ProformaSchedule은 기항지(Port)별로 행이 생성되므로, 헤더 정보 기준으로 묶어야 함
    schedules_qs = (
        ProformaSchedule.objects.filter(scenario=scenario)
        .values(
            "lane_code",
            "proforma_name",
            "declared_capacity",
            "declared_count",
            "duration",
        )
        .annotate(
            # 그룹별 집계 함수 적용
            start_date=Min("effective_from_date"),  # 시작일 (데이터 중 가장 빠른 날짜)
            port_count=Count("port_code"),  # 기항지 수
        )
        .order_by("lane_code", "proforma_name")
    )

    # 3. 전체 통계 계산 (Summary Calculation)
    total_lanes = 0
    total_vessels = 0
    total_capacity = 0

    # 템플릿에서 사용할 리스트 생성 및 통계 합산
    schedules = []
    for item in schedules_qs:
        # 데이터 타입 안전 변환 (DB에 문자열이나 Null로 있을 경우 대비)
        try:
            cnt = int(item["declared_count"] or 0)
            cap = float(item["declared_capacity"] or 0)
        except (ValueError, TypeError):
            cnt = 0
            cap = 0.0

        total_lanes += 1
        total_vessels += cnt
        total_capacity += cnt * cap  # (척수 * 선박크기) 누적

        schedules.append(item)

    # 4. Context 구성
    context = {
        "menu_structure": MENU_STRUCTURE,
        "current_model": "scenario_list",  # 사이드바 메뉴 활성화 (Scenario List 하위 개념)
        "scenario": scenario,
        "schedules": schedules,
        "summary": {
            "total_lanes": total_lanes,
            "total_vessels": total_vessels,
            "total_capacity": total_capacity,
        },
    }

    return render(request, "input_data/scenario_dashboard.html", context)


def _clone_scenario_data(source_id, target_scenario):
    app_config = apps.get_app_config("input_data")
    models_to_clone = [
        m for m in app_config.get_models() if m.__name__ != "ScenarioInfo"
    ]

    for model_class in models_to_clone:
        # 1. ScenarioInfo 자체는 제외
        if model_class.__name__ == "ScenarioInfo":
            continue

        # 2. [중요] 'Std'로 시작하는 표준 테이블 제외 (또는 scenario 필드 존재 여부 확인)
        # 가장 확실한 방법: 'scenario' 필드가 있는지 검사
        try:
            model_class._meta.get_field("scenario")
        except FieldDoesNotExist:
            # scenario 필드가 없는 모델(Std 등)은 복제 대상 아님 -> Skip
            continue

        # 3. 복제 로직 실행
        # (ScenarioBaseModel을 상속받은 모델들만 여기 도달함)
        original_objects = model_class.objects.filter(scenario__id=source_id)
        if original_objects.exists():
            new_objects = []
            for obj in original_objects:
                obj.pk = None
                obj.scenario = target_scenario
                new_objects.append(obj)
            model_class.objects.bulk_create(new_objects)
