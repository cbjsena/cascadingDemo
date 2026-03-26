from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from common.menus import (
    CREATION_MENU_STRUCTURE,
    MENU_STRUCTURE,
    MenuItem,
    MenuSection,
)
from input_data.models import ScenarioInfo
from simulation.models import SimulationRun, SimulationStatus


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
def simulation_create(request):
    """시뮬레이션 생성 폼"""
    scenarios = ScenarioInfo.objects.filter(status="ACTIVE").order_by("-created_at")

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.SIMULATION,
        "current_model": MenuItem.SIMULATION_CREATE,
        "scenarios": scenarios,
    }
    return render(request, "simulation/simulation_create.html", context)


@login_required
@require_POST
def simulation_run(request):
    """시뮬레이션 실행 시작"""
    scenario_id = request.POST.get("scenario_id")
    description = request.POST.get("description", "")
    tags = request.POST.get("tags", "")
    solver_type = request.POST.get("solver_type", "OR-Tools")

    if not scenario_id:
        messages.error(request, "시나리오를 선택해주세요.")
        return redirect("simulation:simulation_create")

    try:
        scenario = ScenarioInfo.objects.get(id=scenario_id)

        # 시뮬레이션 실행 객체 생성
        simulation = SimulationRun.objects.create(
            scenario=scenario,
            description=description,
            tags=tags,
            solver_type=solver_type,
            created_by=request.user,
            updated_by=request.user,
        )

        # TODO: 실제 시뮬레이션 실행 로직 구현
        # 현재는 즉시 성공으로 설정 (데모용)
        simulation.simulation_status = SimulationStatus.SUCCESS
        simulation.progress = 100
        simulation.objective_value = 12345.67  # 샘플 값
        simulation.execution_time = 45.2  # 샘플 값
        simulation.save()

        messages.success(
            request, f"시뮬레이션 {simulation.code}이(가) 성공적으로 실행되었습니다."
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
