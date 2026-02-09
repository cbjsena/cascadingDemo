from django.core.exceptions import FieldDoesNotExist
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.apps import apps
from django.views.decorators.http import require_POST

from input_data.models import ScenarioInfo
from common import messages as msg
from common.menus import MENU_STRUCTURE


@login_required
def scenario_list(request):
    scenarios = ScenarioInfo.objects.all().order_by('-created_at')

    # 기본값 생성 로직 (Helper)
    today_str = timezone.now().strftime('%Y%m%d')
    last_scenario = ScenarioInfo.objects.filter(id__startswith=today_str).order_by('-id').first()
    new_seq = 1
    if last_scenario:
        try:
            new_seq = int(last_scenario.id[8:]) + 1
        except ValueError:
            pass
    default_scenario_id = f"{today_str}{new_seq:02d}"
    default_base_ym = timezone.now().strftime('%Y%m')

    context = {
        "menu_structure": MENU_STRUCTURE,
        "scenarios": scenarios,
        "default_scenario_id": default_scenario_id,
        "default_base_ym": default_base_ym,
    }
    return render(request, 'input_data/scenario_list.html', context)


@login_required
@transaction.atomic
def scenario_create(request):
    if request.method == "POST":
        new_scenario_id = request.POST.get("scenario_id")
        source_scenario_id = request.POST.get("source_scenario_id")
        description = request.POST.get("description")
        base_ym = request.POST.get("base_year_month")

        if ScenarioInfo.objects.filter(id=new_scenario_id).exists():
            messages.error(request, msg.SCENARIO_ID_DUPLICATE.format(scenario_id=new_scenario_id))
            return redirect("input_data:scenario_list")

        new_scenario = ScenarioInfo.objects.create(
            id=new_scenario_id,
            description=description,
            base_year_month=base_ym,
            created_by=request.user,
            updated_by=request.user
        )

        if source_scenario_id:
            try:
                _clone_scenario_data(source_scenario_id, new_scenario )
                messages.success(request,
                                 msg.SCENARIO_CLONE_SUCCESS.format(scenario_id=new_scenario_id, source_id=source_scenario_id))
            except Exception as e:
                messages.error(request, msg.SCENARIO_CLONE_ERROR.format(error=str(e)))
                return redirect("input_data:scenario_list")
        else:
            messages.success(request, msg.SCENARIO_CREATE_SUCCESS.format(scenario_id=new_scenario_id))

        return redirect("input_data:scenario_list")
    return redirect("input_data:scenario_list")


@login_required
@transaction.atomic
@require_POST
def scenario_delete(request, scenario_id):
    scenario  = get_object_or_404(ScenarioInfo, id=scenario_id)
    if not (scenario.created_by == request.user or request.user.is_superuser):
        messages.error(request, msg.PERMISSION_DENIED)
        return redirect("input_data:scenario_list")

    try:
        scenario.delete()
        messages.success(request, msg.SCENARIO_DELETE_SUCCESS.format(scenario_id=scenario_id))
    except Exception as e:
        messages.error(request, msg.SCENARIO_DELETE_ERROR.format(error=str(e)))
    return redirect("input_data:scenario_list")


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from input_data.services.scenario_service import create_scenario_from_base
from common import messages as msg
import json


@login_required
@require_POST
def create_base_scenario_view(request):
    """
    [Web UI] Base 시나리오 생성 버튼 클릭 시 호출
    """
    try:
        # JSON Body 혹은 Form Data 처리
        # (Fetch API 사용 시 body, Form submit 시 POST dict)
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            target_id = data.get('scenario_id', '202601_BASE')
            description = data.get('description', 'Base Scenario created from Web')
        else:
            target_id = request.POST.get('scenario_id', '202601_BASE')
            description = request.POST.get('description', 'Base Scenario created from Web')

        # [수정 사항 3] 로그인한 사용자(request.user) 전달
        scenario, summary = create_scenario_from_base(
            target_id=target_id,
            description=description,
            user=request.user
        )

        return JsonResponse({
            "status": "success",
            "message": msg.SCENARIO_CREATE_SUCCESS.format(scenario_id=target_id),
            "summary": summary
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": msg.SAVE_ERROR.format(error=str(e))
        }, status=500)


def _clone_scenario_data(source_id, target_scenario):
    app_config = apps.get_app_config('input_data')
    models_to_clone = [m for m in app_config.get_models() if m.__name__ != 'ScenarioInfo']

    for model_class in models_to_clone:
        # 1. ScenarioInfo 자체는 제외
        if model_class.__name__ == 'ScenarioInfo':
            continue

        # 2. [중요] 'Std'로 시작하는 표준 테이블 제외 (또는 scenario 필드 존재 여부 확인)
        # 가장 확실한 방법: 'scenario' 필드가 있는지 검사
        try:
            model_class._meta.get_field('scenario')
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