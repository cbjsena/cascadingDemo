from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from celery.result import AsyncResult

from common.constants import SIMULATION_SOLVER_CHOICES
from common.menus import (
    CREATION_MENU_STRUCTURE,
    MENU_STRUCTURE,
    MenuItem,
    MenuSection,
)
from input_data.models import ScenarioInfo
from simulation.models import SimulationRun, SimulationStatus
from simulation.tasks import run_simulation_task

MONITORING_STATUSES = [
    SimulationStatus.SNAPSHOTTING,
    SimulationStatus.SNAPSHOT_DONE,
    SimulationStatus.PENDING,
    SimulationStatus.RUNNING,
]


@login_required
def simulation_list(request):
    """시뮬레이션 실행 목록"""
    simulations = SimulationRun.objects.select_related("scenario").order_by(
        "-created_at"
    )

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.SIMULATION,
        "current_model": MenuItem.SIMULATION_LIST,
        "simulations": simulations,
        "simulation_status": SimulationStatus,
    }
    return render(request, "simulation/simulation_list.html", context)


@login_required
@require_GET
def simulation_monitoring(request):
    """진행 중 시뮬레이션 모니터링 화면"""
    running_simulations = (
        SimulationRun.objects.select_related("scenario")
        .filter(simulation_status__in=MONITORING_STATUSES)
        .order_by("-created_at")
    )

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.SIMULATION,
        "current_model": MenuItem.SIMULATION_MONITORING,
        "simulations": running_simulations,
        "simulation_status": SimulationStatus,
    }
    return render(request, "simulation/simulation_monitoring.html", context)


@login_required
@require_GET
def simulation_monitoring_data(request):
    """진행 중 시뮬레이션 목록 JSON (프론트 polling용)"""
    rows = (
        SimulationRun.objects.select_related("scenario")
        .filter(simulation_status__in=MONITORING_STATUSES)
        .order_by("-created_at")
    )

    status_label_map = dict(SimulationStatus.choices)

    payload = [
        {
            "id": sim.pk,
            "code": sim.code,
            "scenario_code": sim.scenario.code,
            "simulation_status": sim.simulation_status,
            "status_label": status_label_map.get(
                sim.simulation_status, sim.simulation_status
            ),
            "progress": sim.progress,
            "model_status": sim.model_status or "",
            "updated_at": sim.updated_at.isoformat() if sim.updated_at else None,
            "detail_url": reverse("simulation:simulation_detail", args=[sim.pk]),
            "cancel_url": reverse("simulation:simulation_cancel", args=[sim.pk]),
        }
        for sim in rows
    ]

    return JsonResponse({"items": payload, "count": len(payload)})


@login_required
@require_POST
def simulation_cancel(request, pk):
    """진행 중 시뮬레이션 중단 요청"""
    simulation = get_object_or_404(SimulationRun, pk=pk)

    if simulation.simulation_status not in MONITORING_STATUSES:
        return JsonResponse(
            {
                "status": "rejected",
                "message": "이미 종료된 시뮬레이션은 중단할 수 없습니다.",
            },
            status=400,
        )

    simulation.simulation_status = SimulationStatus.CANCELED
    simulation.model_end_time = timezone.now()
    simulation.model_status = "Canceled by user"
    simulation.save(
        update_fields=[
            "simulation_status",
            "model_end_time",
            "model_status",
            "updated_at",
        ]
    )

    if simulation.task_id:
        try:
            AsyncResult(simulation.task_id).revoke(terminate=True)
        except Exception:
            # revoke 실패 시에도 상태는 CANCELED로 유지
            pass

    return JsonResponse({"status": "ok", "simulation_id": simulation.pk})


@login_required
@require_GET
def simulation_create(request):
    """시뮬레이션 생성 폼"""
    scenarios = ScenarioInfo.objects.filter(status="ACTIVE").order_by("-created_at")

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.SIMULATION,
        "current_model": MenuItem.SIMULATION_CREATE,
        "scenarios": scenarios,
        "solver_choices": SIMULATION_SOLVER_CHOICES,
        "default_solver_group": SIMULATION_SOLVER_CHOICES.get("EXACT", []),
        "default_solver_value": SimulationRun._meta.get_field("solver_type").default,
        "default_algorithm_type": SimulationRun._meta.get_field(
            "algorithm_type"
        ).default,
    }
    return render(request, "simulation/simulation_create.html", context)


@login_required
@require_POST
def simulation_run(request):
    """시뮬레이션 실행 시작"""
    scenario_id = request.POST.get("scenario_id")
    description = request.POST.get("description", "")
    solver_type = request.POST.get(
        "solver_type", SimulationRun._meta.get_field("solver_type").default
    )
    algorithm_type = request.POST.get(
        "algorithm_type", SimulationRun._meta.get_field("algorithm_type").default
    )

    if not scenario_id:
        messages.error(request, "시나리오를 선택해주세요.")
        return redirect("simulation:simulation_create")

    try:
        scenario = ScenarioInfo.objects.get(id=scenario_id)

        # 시뮬레이션 실행 객체 생성
        simulation = SimulationRun.objects.create(
            scenario=scenario,
            description=description,
            solver_type=solver_type,
            algorithm_type=algorithm_type,
            created_by=request.user,
            updated_by=request.user,
        )
        async_result = run_simulation_task.delay(simulation.id)
        simulation.task_id = async_result.id
        simulation.save(update_fields=["task_id", "updated_at"])

        messages.success(
            request,
            f"시뮬레이션 {simulation.code} 실행이 예약되었습니다. 실행 현황은 목록에서 확인하세요.",
        )
        return redirect("simulation:simulation_detail", pk=simulation.pk)

    except ScenarioInfo.DoesNotExist:
        messages.error(request, "선택한 시나리오를 찾을 수 없습니다.")
        return redirect("simulation:simulation_create")
    except Exception as e:
        messages.error(request, f"시뮬레이션 실행 중 오류가 발생했습니다: {str(e)}")
        return redirect("simulation:simulation_create")


@login_required
def simulation_detail(request, pk):
    """시뮬레이션 상세 정보 및 결과"""
    simulation = get_object_or_404(
        SimulationRun.objects.select_related("scenario"), pk=pk
    )

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.SIMULATION,
        "current_model": MenuItem.SIMULATION_LIST,
        "simulation": simulation,
        "simulation_status": SimulationStatus,
    }
    return render(request, "simulation/simulation_detail.html", context)


@login_required
@require_POST
def simulation_delete(request, pk):
    """시뮬레이션 삭제"""
    simulation = get_object_or_404(SimulationRun, pk=pk)

    if not simulation.can_modify:
        messages.error(request, "실행 중인 시뮬레이션은 삭제할 수 없습니다.")
        return redirect("simulation:simulation_detail", pk=pk)

    simulation_code = simulation.code
    simulation.delete()

    messages.success(request, f"시뮬레이션 {simulation_code}이(가) 삭제되었습니다.")
    return redirect("simulation:simulation_list")
