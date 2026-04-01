"""
Simulation Model Tests
======================
SimulationRun 모델의 생성 / code 자동생성 / Unique 제약 / FK Cascade / 상태 속성 테스트

시나리오 ID 매핑:
  SIM_RUN_MDL_001 ~ SIM_RUN_MDL_007

Fixtures: tests/simulation/conftest.py 참조
"""

from datetime import date

from django.db import IntegrityError

import pytest

from simulation.models import SimulationRun, SimulationStatus


@pytest.mark.django_db
class TestSimulationRunModel:
    """SimulationRun 모델 테스트"""

    def test_create_with_auto_code(self, active_scenario, user):
        """
        [SIM_RUN_MDL_001] code가 SMYYYYMMDD_NNN 형식으로 자동 생성되는지 검증
        """
        sim = SimulationRun.objects.create(
            scenario=active_scenario,
            created_by=user,
        )

        # code 형식 검증
        today_str = date.today().strftime("%Y%m%d")
        assert sim.code.startswith(f"SM{today_str}_")
        assert len(sim.code.split("_")[-1]) == 3  # NNN 3자리

        # 기본값 검증
        assert sim.simulation_status == SimulationStatus.SNAPSHOTTING
        assert sim.progress == 0

        # __str__ 출력 검증
        str_repr = str(sim)
        assert str(sim.id) in str_repr
        assert active_scenario.code in str_repr
        assert SimulationStatus.SNAPSHOTTING in str_repr

    def test_code_auto_increment(self, active_scenario, user):
        """
        [SIM_RUN_MDL_002] 동일 날짜에 복수 시뮬레이션 생성 시 code 순차 증가
        """
        sim1 = SimulationRun.objects.create(
            scenario=active_scenario,
            created_by=user,
        )
        sim2 = SimulationRun.objects.create(
            scenario=active_scenario,
            created_by=user,
        )

        # 동일 접두사
        today_str = date.today().strftime("%Y%m%d")
        prefix = f"SM{today_str}_"
        assert sim1.code.startswith(prefix)
        assert sim2.code.startswith(prefix)

        # 순번 증가
        num1 = int(sim1.code.split("_")[-1])
        num2 = int(sim2.code.split("_")[-1])
        assert num2 == num1 + 1

    def test_code_unique_constraint(self, active_scenario, user):
        """
        [SIM_RUN_MDL_003] 동일 code 중복 생성 시 IntegrityError 발생
        """
        SimulationRun.objects.create(
            scenario=active_scenario,
            code="SM20260401_001",
            created_by=user,
        )

        with pytest.raises(IntegrityError):
            SimulationRun.objects.create(
                scenario=active_scenario,
                code="SM20260401_001",
                created_by=user,
            )

    def test_scenario_fk_cascade_delete(self, active_scenario, user):
        """
        [SIM_RUN_MDL_004] Scenario 삭제 시 연관 SimulationRun도 삭제
        """
        sim = SimulationRun.objects.create(
            scenario=active_scenario,
            created_by=user,
        )
        sim_pk = sim.pk

        active_scenario.delete()

        assert not SimulationRun.objects.filter(pk=sim_pk).exists()

    def test_is_processing_property(self, active_scenario, user):
        """
        [SIM_RUN_MDL_005] is_processing 속성:
        SNAPSHOTTING·SNAPSHOT_DONE·PENDING·RUNNING → True, 나머지 → False
        """
        processing_statuses = [
            SimulationStatus.SNAPSHOTTING,
            SimulationStatus.SNAPSHOT_DONE,
            SimulationStatus.PENDING,
            SimulationStatus.RUNNING,
        ]
        non_processing_statuses = [
            SimulationStatus.SUCCESS,
            SimulationStatus.FAILED,
            SimulationStatus.CANCELED,
        ]

        for status in processing_statuses:
            sim = SimulationRun(
                scenario=active_scenario,
                simulation_status=status,
            )
            assert sim.is_processing is True, f"{status} should be processing"

        for status in non_processing_statuses:
            sim = SimulationRun(
                scenario=active_scenario,
                simulation_status=status,
            )
            assert sim.is_processing is False, f"{status} should NOT be processing"

    def test_can_modify_property(self, active_scenario, user):
        """
        [SIM_RUN_MDL_006] can_modify 속성:
        SUCCESS·FAILED·CANCELED → True, RUNNING·SNAPSHOTTING 등 → False
        """
        modifiable_statuses = [
            SimulationStatus.SUCCESS,
            SimulationStatus.FAILED,
            SimulationStatus.CANCELED,
        ]
        non_modifiable_statuses = [
            SimulationStatus.SNAPSHOTTING,
            SimulationStatus.SNAPSHOT_DONE,
            SimulationStatus.PENDING,
            SimulationStatus.RUNNING,
        ]

        for status in modifiable_statuses:
            sim = SimulationRun(
                scenario=active_scenario,
                simulation_status=status,
            )
            assert sim.can_modify is True, f"{status} should be modifiable"

        for status in non_modifiable_statuses:
            sim = SimulationRun(
                scenario=active_scenario,
                simulation_status=status,
            )
            assert sim.can_modify is False, f"{status} should NOT be modifiable"

    def test_simulation_status_choices(self):
        """
        [SIM_RUN_MDL_007] SimulationStatus 열거형 값 검증 (7개)
        """
        expected = {
            "SNAPSHOTTING",
            "SNAPSHOT_DONE",
            "PENDING",
            "RUNNING",
            "SUCCESS",
            "FAILED",
            "CANCELED",
        }
        actual = {choice[0] for choice in SimulationStatus.choices}
        assert actual == expected
        assert len(SimulationStatus.choices) == 7
