"""
Simulation Task (Celery) Tests
===============================
run_simulation_task / _fetch_scenario_snapshot / _build_engine_payload / _call_engine_api 테스트

시나리오 ID 매핑:
  SIM_TSK_SVC_001 ~ SIM_TSK_SVC_006

Fixtures: tests/simulation/conftest.py 참조
"""

from unittest.mock import patch

import pytest

from simulation.models import SimulationRun, SimulationStatus
from simulation.tasks import (
    _build_engine_payload,
    _call_engine_api,
    _fetch_scenario_snapshot,
    run_simulation_task,
)


@pytest.mark.django_db
class TestRunSimulationTask:
    """run_simulation_task Celery Task 테스트"""

    @patch("simulation.tasks._call_engine_api")
    @patch("simulation.tasks._fetch_scenario_snapshot")
    def test_task_success(self, mock_snapshot, mock_engine, active_scenario, user):
        """
        [SIM_TSK_SVC_001] Task 정상 실행 → SUCCESS 상태 전환
        """
        mock_snapshot.return_value = {
            "id": active_scenario.id,
            "code": active_scenario.code,
        }
        mock_engine.return_value = {
            "objective_value": 9999.99,
            "execution_time": 10.5,
            "model_status": "COMPLETED",
            "progress": 100,
        }

        sim = SimulationRun.objects.create(
            scenario=active_scenario,
            simulation_status=SimulationStatus.SNAPSHOTTING,
            created_by=user,
        )

        # EAGER 모드에서 동기 실행
        run_simulation_task(sim.id)

        sim.refresh_from_db()
        assert sim.simulation_status == SimulationStatus.SUCCESS
        assert sim.progress == 100
        assert sim.model_start_time is not None
        assert sim.model_end_time is not None
        assert sim.objective_value == 9999.99
        assert sim.execution_time == 10.5

    def test_task_nonexistent_id(self):
        """
        [SIM_TSK_SVC_002] 존재하지 않는 simulation_id → 에러 없이 종료
        """
        initial_count = SimulationRun.objects.count()

        # 예외 발생 없이 조용히 종료되어야 함
        run_simulation_task(99999)

        assert SimulationRun.objects.count() == initial_count

    @patch("simulation.tasks._call_engine_api")
    @patch("simulation.tasks._fetch_scenario_snapshot")
    def test_task_engine_failure(
        self, mock_snapshot, mock_engine, active_scenario, user
    ):
        """
        [SIM_TSK_SVC_003] 엔진 API 실패 → FAILED 상태 전환 및 에러 기록
        """
        mock_snapshot.return_value = {"id": active_scenario.id}
        mock_engine.side_effect = Exception("Engine connection refused")

        sim = SimulationRun.objects.create(
            scenario=active_scenario,
            simulation_status=SimulationStatus.SNAPSHOTTING,
            created_by=user,
        )

        with pytest.raises(Exception, match="Engine connection refused"):
            run_simulation_task(sim.id)

        sim.refresh_from_db()
        assert sim.simulation_status == SimulationStatus.FAILED
        assert sim.model_end_time is not None
        assert "Engine connection refused" in sim.model_status
        assert sim.progress == 0


@pytest.mark.django_db
class TestFetchScenarioSnapshot:
    """_fetch_scenario_snapshot 내부 함수 테스트"""

    def test_snapshot_without_api_url(self, settings, active_scenario):
        """
        [SIM_TSK_SVC_004] SCENARIO_DATA_API_URL 미설정 → 로컬 DB 스냅샷 반환
        """
        settings.SCENARIO_DATA_API_URL = ""

        result = _fetch_scenario_snapshot(active_scenario)

        assert isinstance(result, dict)
        assert result["id"] == active_scenario.id
        assert result["code"] == active_scenario.code
        assert result["description"] == active_scenario.description
        assert "metadata" in result
        assert "base_year_week" in result["metadata"]
        assert "planning_horizon_months" in result["metadata"]


@pytest.mark.django_db
class TestBuildEnginePayload:
    """_build_engine_payload 내부 함수 테스트"""

    @patch("simulation.tasks._fetch_scenario_snapshot")
    def test_payload_structure(self, mock_snapshot, active_scenario, user):
        """
        [SIM_TSK_SVC_005] 페이로드에 simulation·scenario·scenario_data 키 존재
        """
        mock_snapshot.return_value = {
            "id": active_scenario.id,
            "code": active_scenario.code,
        }

        sim = SimulationRun.objects.create(
            scenario=active_scenario,
            solver_type="gurobi",
            algorithm_type="EFFICIENT",
            created_by=user,
        )

        payload = _build_engine_payload(sim)

        # 최상위 키 검증
        assert "simulation" in payload
        assert "scenario" in payload
        assert "scenario_data" in payload

        # simulation 섹션
        assert payload["simulation"]["code"] == sim.code
        assert payload["simulation"]["solver_type"] == "gurobi"
        assert payload["simulation"]["algorithm_type"] == "EFFICIENT"

        # scenario 섹션
        assert payload["scenario"]["id"] == active_scenario.id
        assert payload["scenario"]["code"] == active_scenario.code


class TestCallEngineApi:
    """_call_engine_api 내부 함수 테스트"""

    def test_mock_result_without_api_url(self, settings):
        """
        [SIM_TSK_SVC_006] SIMULATION_ENGINE_API_URL 미설정 → 모의 결과 반환
        """
        settings.SIMULATION_ENGINE_API_URL = ""

        result = _call_engine_api({"dummy": "payload"})

        assert isinstance(result, dict)
        assert "objective_value" in result
        assert "execution_time" in result
        assert "model_status" in result
        assert "progress" in result
        assert result["model_status"] == "MOCK_COMPLETED"
