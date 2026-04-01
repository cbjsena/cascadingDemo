"""
Simulation 앱 테스트 공통 Fixtures
==================================
시뮬레이션 뷰 / 모델 / 태스크 테스트에서 공유하는 fixture 모음.
"""

from django.utils import timezone

import pytest

from input_data.models import ScenarioInfo
from simulation.models import SimulationRun, SimulationStatus


# =========================================================================
# Scenario Fixtures
# =========================================================================
@pytest.fixture
def active_scenario(db, user):
    """ACTIVE 상태 시나리오"""
    return ScenarioInfo.objects.create(
        code="SC_SIM_ACTIVE",
        description="Active scenario for simulation",
        status="ACTIVE",
        created_by=user,
    )


@pytest.fixture
def inactive_scenario(db, user):
    """INACTIVE 상태 시나리오"""
    return ScenarioInfo.objects.create(
        code="SC_SIM_INACTIVE",
        description="Inactive scenario",
        status="INACTIVE",
        created_by=user,
    )


# =========================================================================
# SimulationRun Fixtures (상태별)
# =========================================================================
@pytest.fixture
def simulation_success(db, active_scenario, user):
    """SUCCESS 상태의 시뮬레이션"""
    return SimulationRun.objects.create(
        scenario=active_scenario,
        code="SM20260401_001",
        simulation_status=SimulationStatus.SUCCESS,
        progress=100,
        solver_type="cplex",
        algorithm_type="EXACT",
        objective_value=12345.67,
        execution_time=43.2,
        model_start_time=timezone.now(),
        model_end_time=timezone.now(),
        model_status="COMPLETED",
        description="Test simulation",
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def simulation_running(db, active_scenario, user):
    """RUNNING 상태의 시뮬레이션"""
    return SimulationRun.objects.create(
        scenario=active_scenario,
        code="SM20260401_002",
        simulation_status=SimulationStatus.RUNNING,
        progress=50,
        solver_type="cplex",
        algorithm_type="EXACT",
        model_start_time=timezone.now(),
        model_status="RUNNING",
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def simulation_failed(db, active_scenario, user):
    """FAILED 상태의 시뮬레이션"""
    return SimulationRun.objects.create(
        scenario=active_scenario,
        code="SM20260401_003",
        simulation_status=SimulationStatus.FAILED,
        progress=0,
        solver_type="cplex",
        algorithm_type="EXACT",
        model_start_time=timezone.now(),
        model_end_time=timezone.now(),
        model_status="Error: Engine timeout",
        created_by=user,
        updated_by=user,
    )
