import logging
from typing import Any

from django.conf import settings
from django.utils import timezone

import requests
from celery import shared_task

from simulation.models import SimulationRun, SimulationStatus

logger = logging.getLogger(__name__)


def _fetch_scenario_snapshot(scenario) -> dict[str, Any]:
    base_url = settings.SCENARIO_DATA_API_URL
    if not base_url:
        return {
            "id": scenario.id,
            "code": scenario.code,
            "description": scenario.description,
            "metadata": {
                "base_year_week": scenario.base_year_week,
                "planning_horizon_months": scenario.planning_horizon_months,
                "scenario_type": scenario.scenario_type,
                "status": scenario.status,
                "tags": scenario.tag_list,
            },
        }

    url = f"{base_url.rstrip('/')}/{scenario.id}"
    headers = {"Accept": "application/json"}
    if settings.SCENARIO_DATA_API_KEY:
        headers["Authorization"] = f"Bearer {settings.SCENARIO_DATA_API_KEY}"

    response = requests.get(
        url,
        headers=headers,
        timeout=settings.SCENARIO_DATA_API_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _build_engine_payload(simulation: SimulationRun) -> dict[str, Any]:
    scenario = simulation.scenario
    snapshot = _fetch_scenario_snapshot(scenario)
    return {
        "simulation": {
            "id": simulation.id,
            "code": simulation.code,
            "solver_type": simulation.solver_type,
            "algorithm_type": simulation.algorithm_type,
            "requested_at": (
                simulation.created_at.isoformat() if simulation.created_at else None
            ),
        },
        "scenario": {
            "id": scenario.id,
            "code": scenario.code,
            "description": scenario.description,
        },
        "scenario_data": snapshot,
    }


def _call_engine_api(payload: dict[str, Any]) -> dict[str, Any]:
    api_url = settings.SIMULATION_ENGINE_API_URL
    if not api_url:
        # 기본 모드: 엔진 없이 모의 결과 반환
        return {
            "objective_value": 12345.67,
            "execution_time": 43.2,
            "model_status": "MOCK_COMPLETED",
            "progress": 100,
        }

    headers = {"Content-Type": "application/json"}
    if settings.SIMULATION_ENGINE_API_KEY:
        headers["Authorization"] = f"Bearer {settings.SIMULATION_ENGINE_API_KEY}"

    response = requests.post(
        api_url,
        json=payload,
        headers=headers,
        timeout=settings.SIMULATION_ENGINE_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


@shared_task(
    bind=True,
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def run_simulation_task(self, simulation_id: int) -> None:
    try:
        simulation = SimulationRun.objects.select_related("scenario").get(
            pk=simulation_id
        )
    except SimulationRun.DoesNotExist:
        logger.warning("SimulationRun %s not found when starting task", simulation_id)
        return

    simulation.simulation_status = SimulationStatus.RUNNING
    simulation.progress = 10
    simulation.model_start_time = timezone.now()
    simulation.model_status = "RUNNING"
    simulation.save(
        update_fields=[
            "simulation_status",
            "progress",
            "model_start_time",
            "model_status",
            "updated_at",
        ]
    )

    try:
        payload = _build_engine_payload(simulation)
        result = _call_engine_api(payload)

        simulation.simulation_status = SimulationStatus.SUCCESS
        simulation.progress = result.get("progress", 100)
        simulation.model_end_time = timezone.now()
        simulation.objective_value = result.get("objective_value")
        simulation.execution_time = result.get("execution_time")
        simulation.model_status = result.get("model_status", "COMPLETED")
        simulation.save(
            update_fields=[
                "simulation_status",
                "progress",
                "model_end_time",
                "objective_value",
                "execution_time",
                "model_status",
                "updated_at",
            ]
        )
    except Exception as exc:
        logger.exception("Simulation %s failed during engine execution", simulation_id)
        simulation.simulation_status = SimulationStatus.FAILED
        simulation.model_end_time = timezone.now()
        simulation.model_status = str(exc)[:200]
        simulation.progress = 0
        simulation.save(
            update_fields=[
                "simulation_status",
                "model_end_time",
                "model_status",
                "progress",
                "updated_at",
            ]
        )
        raise
