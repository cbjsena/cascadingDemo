import json

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.db.models import Count, Min
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from common import messages as msg
from common.menus import MENU_STRUCTURE
from input_data.models import ProformaSchedule, ScenarioInfo
from input_data.services.scenario_service import create_scenario_from_base


@login_required
def scenario_list(request):
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    # 기본값 생성 로직 (시나리오 이름 기반)
    default_base_ym = timezone.now().strftime("%Y%m")

    context = {
        "menu_structure": MENU_STRUCTURE,
        "scenarios": scenarios,
        "default_base_ym": default_base_ym,
    }
    return render(request, "input_data/scenario_list.html", context)


@login_required
@transaction.atomic
def scenario_create(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        source_scenario_id = request.POST.get("source_scenario_id")
        description = request.POST.get("description", "")
        base_ym = request.POST.get("base_year_month")
        scenario_type = request.POST.get("scenario_type", "WHAT_IF")
        base_scenario_id = request.POST.get("base_scenario_id")
        planning_horizon_months = request.POST.get("planning_horizon_months", 12)
        tags = request.POST.get("tags", "")

        if not name:
            messages.error(request, "Scenario name is required.")
            return redirect("input_data:scenario_list")

        if ScenarioInfo.objects.filter(name=name).exists():
            messages.error(
                request,
                f"Scenario name '{name}' already exists. Please use a different name.",
            )
            return redirect("input_data:scenario_list")

        # 베이스 시나리오 참조 설정
        base_scenario = None

        # 1. 명시적으로 base_scenario_id가 지정된 경우 우선 사용
        if base_scenario_id:
            try:
                base_scenario = ScenarioInfo.objects.get(id=base_scenario_id)
            except ScenarioInfo.DoesNotExist:
                pass

        # 2. source_scenario_id가 있는 경우 (복사), 복사 원본을 base_scenario로 자동 설정
        if source_scenario_id and not base_scenario:
            try:
                base_scenario = ScenarioInfo.objects.get(id=source_scenario_id)
            except ScenarioInfo.DoesNotExist:
                pass

        new_scenario = ScenarioInfo.objects.create(
            name=name,
            description=description,
            base_year_month=base_ym,
            scenario_type=scenario_type,
            base_scenario=base_scenario,  # 복사 시 자동으로 원본 시나리오 참조
            planning_horizon_months=int(planning_horizon_months or 12),
            tags=tags,
            created_by=request.user,
            updated_by=request.user,
        )

        if source_scenario_id:
            try:
                _clone_scenario_data(source_scenario_id, new_scenario)
                source_name = (
                    base_scenario.name if base_scenario else source_scenario_id
                )
                messages.success(
                    request,
                    f"Scenario '{name}' created successfully (Cloned from '{source_name}').",
                )
            except Exception as e:
                messages.error(request, msg.SCENARIO_CLONE_ERROR.format(error=str(e)))
                return redirect("input_data:scenario_list")
        else:
            messages.success(request, f"Scenario '{name}' created successfully.")

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
            scenario_name = data.get("scenario_name", "Base Scenario")
            description = data.get("description", "Base Scenario created from Web")
        else:
            scenario_name = request.POST.get("scenario_name", "Base Scenario")
            description = request.POST.get(
                "description", "Base Scenario created from Web"
            )

        # 새로운 서비스 시그니처에 맞게 호출
        scenario, summary = create_scenario_from_base(
            scenario_name=scenario_name, description=description, user=request.user
        )

        return JsonResponse(
            {
                "status": "success",
                "message": f"Scenario '{scenario_name}' (ID: {scenario.id}) created successfully.",
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
    - 새로운 ScenarioInfo 필드들 지원
    """
    # 1. 시나리오 조회 (없으면 404)
    scenario = get_object_or_404(ScenarioInfo, id=scenario_id)

    # 2. 스케줄 데이터 집계 (Group By Lane, Name)
    # ProformaSchedule (Master) + ProformaScheduleDetail (상세) 조인
    schedules_qs = (
        ProformaSchedule.objects.filter(scenario=scenario)
        .annotate(
            # Detail에서 기항지 수 계산
            ports_count=Count("details", distinct=True)
        )
        .values(
            "lane_code",
            "proforma_name",
            "declared_capacity",
            "declared_count",
            "duration",
            "effective_from_date",
        )
        .annotate(
            start_date=Min("effective_from_date"),  # 시작일
            ports_count=Count("details", distinct=True),  # 기항지 수
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

    # 4. 시뮬레이션 상태 및 KPI 정보 추가
    latest_kpi = (
        None  # scenario.kpi_snapshots.first()  # 최신 KPI (TODO: 구현 후 활성화)
    )
    virtual_vessels_count = (
        0  # scenario.virtual_vessels.count()  # 가상 선박 수 (TODO: 구현 후 활성화)
    )
    simulation_runs_count = 0  # scenario.simulation_runs.count()  # 시뮬레이션 실행 횟수 (TODO: 구현 후 활성화)

    # 5. Context 구성
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
        # 새로운 ScenarioInfo 필드들
        "simulation_info": {
            "virtual_vessels_count": virtual_vessels_count,
            "simulation_runs_count": simulation_runs_count,
            "latest_kpi": latest_kpi,
            "tag_list": scenario.tag_list,  # property로 태그 리스트
            "is_baseline": scenario.is_baseline,  # property로 베이스라인 여부
        },
    }

    return render(request, "input_data/scenario_dashboard.html", context)


def _clone_scenario_data(source_id, target_scenario):
    """
    시나리오 하위의 모든 데이터를 동적으로 탐색하여 복제하는 메인 로직
    """
    app_config = apps.get_app_config("input_data")

    # 1. ScenarioInfo를 제외하고 'scenario' 필드가 있는 모든 Master 모델 추출
    master_models = [
        m
        for m in app_config.get_models()
        if m.__name__ != "ScenarioInfo" and hasattr(m, "scenario")
    ]

    for model_class in master_models:
        # 2. 해당 Master 모델과 연결된 Detail 관계(related_name="*details*") 탐색
        detail_rels = [
            rel
            for rel in model_class._meta.related_objects
            if isinstance(rel, models.ManyToOneRel)
            and "details" in (rel.related_name or "")
        ]

        # 3. Master와 Detail들을 일괄 복제 실행
        _clone_relation_data(model_class, detail_rels, source_id, target_scenario)


def _clone_relation_data(master_model, detail_rels, source_id, target_scenario):
    """
    특정 Master 모델과 그에 속한 여러 Detail 모델들을 Bulk로 복제
    related_name에 "details"가 포함된 모든 하위 테이블
    """
    # 1. 원본 Master 데이터 조회
    originals = list(master_model.objects.filter(scenario_id=source_id))
    if not originals:
        return

    # 2. Master 복제 (Bulk Create)
    old_ids = [obj.pk for obj in originals]
    new_masters = []
    for obj in originals:
        obj.pk = None
        obj.scenario = target_scenario
        new_masters.append(obj)

    # PostgreSQL 등에서 신규 PK를 객체에 채워줌
    master_model.objects.bulk_create(new_masters)

    # 원본 ID -> 신규 객체 매핑 맵 생성
    id_map = {old_id: new_obj for old_id, new_obj in zip(old_ids, new_masters)}

    # 3. 모든 연관된 Detail 모델들 순회 및 복제
    for rel in detail_rels:
        detail_model = rel.related_model
        fk_field_name = rel.remote_field.name  # 예: 'proforma'

        # 원본 Master들에 속한 모든 Detail 한 번에 조회
        all_original_details = detail_model.objects.filter(
            **{f"{fk_field_name}__in": old_ids}
        )

        new_details = []
        for d in all_original_details:
            old_parent_id = getattr(d, f"{fk_field_name}_id")
            new_parent_obj = id_map.get(old_parent_id)

            if new_parent_obj:
                d.pk = None
                setattr(d, fk_field_name, new_parent_obj)  # 새 부모 연결

                # Detail에 scenario 필드가 정의된 경우(역정규화) 대비
                if hasattr(d, "scenario"):
                    d.scenario = target_scenario

                new_details.append(d)

        if new_details:
            detail_model.objects.bulk_create(new_details)
