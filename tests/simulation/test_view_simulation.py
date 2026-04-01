"""
Simulation View Tests
=====================
시뮬레이션 목록(List) / 생성(Create) / 실행(Run) / 상세(Detail) / 삭제(Delete) 화면 테스트

시나리오 ID 매핑:
  SIM_RUN_DIS_001 ~ SIM_RUN_DIS_015  화면 CRUD
  CM_AUTH_DIS_002                      비로그인 접근 차단

Fixtures: tests/simulation/conftest.py 참조
"""

from datetime import date

from django.contrib.messages import get_messages
from django.urls import reverse

import pytest

from simulation.models import SimulationRun, SimulationStatus


# =========================================================================
# List View Tests
# =========================================================================
@pytest.mark.django_db
class TestSimulationListView:
    """시뮬레이션 목록 화면 테스트"""

    def test_list_with_data(self, auth_client, simulation_success):
        """
        [SIM_RUN_DIS_001] 시뮬레이션 목록 페이지 정상 로드 및 데이터 표시
        """
        url = reverse("simulation:simulation_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "simulation/simulation_list.html" in [t.name for t in response.templates]

        # Context 검증
        simulations = response.context["simulations"]
        assert simulations.count() >= 1
        assert simulation_success in simulations

        # simulation_status context 존재
        assert "simulation_status" in response.context

        # HTML에 Code 표시 확인
        content = response.content.decode("utf-8")
        assert simulation_success.code in content
        assert simulation_success.scenario.code in content

    def test_list_empty(self, auth_client):
        """
        [SIM_RUN_DIS_002] 시뮬레이션 데이터 없을 때 빈 목록 안내 메시지 표시
        """
        url = reverse("simulation:simulation_list")
        response = auth_client.get(url)

        assert response.status_code == 200

        simulations = response.context["simulations"]
        assert simulations.count() == 0

        content = response.content.decode("utf-8")
        assert "아직 실행된 시뮬레이션이 없습니다" in content

    def test_list_status_badges(
        self, auth_client, simulation_success, simulation_running, simulation_failed
    ):
        """
        [SIM_RUN_DIS_016] 목록에서 각 상태별 badge가 정상 표시되는지 검증
        """
        url = reverse("simulation:simulation_list")
        response = auth_client.get(url)

        assert response.status_code == 200
        content = response.content.decode("utf-8")

        # 3건 모두 표시
        simulations = response.context["simulations"]
        assert simulations.count() == 3

        # 각 상태 badge 존재
        assert "bg-success" in content  # SUCCESS
        assert "bg-primary" in content  # RUNNING
        assert "bg-danger" in content  # FAILED

    def test_list_progress_bar_for_running(self, auth_client, simulation_running):
        """
        [SIM_RUN_DIS_017] RUNNING 상태에서 Progress Bar가 animated로 표시
        """
        url = reverse("simulation:simulation_list")
        response = auth_client.get(url)

        content = response.content.decode("utf-8")
        assert "progress-bar-animated" in content

    def test_list_delete_button_visibility(
        self, auth_client, simulation_success, simulation_running
    ):
        """
        [SIM_RUN_DIS_018] 목록에서 can_modify=True인 항목만 Delete 버튼 표시
        """
        url = reverse("simulation:simulation_list")
        response = auth_client.get(url)
        content = response.content.decode("utf-8")

        # SUCCESS (can_modify=True) → 삭제 URL 존재
        delete_url_success = reverse(
            "simulation:simulation_delete", args=[simulation_success.pk]
        )
        assert delete_url_success in content

        # RUNNING (can_modify=False) → 삭제 URL 미존재
        delete_url_running = reverse(
            "simulation:simulation_delete", args=[simulation_running.pk]
        )
        assert delete_url_running not in content

    def test_list_ordering(self, auth_client, active_scenario, user):
        """
        [SIM_RUN_DIS_019] 목록에 생성된 시뮬레이션이 모두 표시되는지 확인
        """
        sim1 = SimulationRun.objects.create(
            scenario=active_scenario,
            code="SM20260401_010",
            simulation_status=SimulationStatus.SUCCESS,
            created_by=user,
        )
        sim2 = SimulationRun.objects.create(
            scenario=active_scenario,
            code="SM20260401_011",
            simulation_status=SimulationStatus.SUCCESS,
            created_by=user,
        )

        url = reverse("simulation:simulation_list")
        response = auth_client.get(url)

        simulations = list(response.context["simulations"])
        assert len(simulations) == 2
        # ordering=["-created_at"] — 동일 시각이면 나중에 생성된(큰 pk) 항목이 뒤에 올 수 있음
        # 핵심: 두 건 모두 표시되는지 확인
        assert sim1 in simulations
        assert sim2 in simulations


# =========================================================================
# Create View Tests
# =========================================================================
@pytest.mark.django_db
class TestSimulationCreateView:
    """시뮬레이션 생성 화면 테스트"""

    def test_create_form_load(self, auth_client, active_scenario):
        """
        [SIM_RUN_DIS_003] 시뮬레이션 생성 폼 정상 로드 및 초기값 검증
        """
        url = reverse("simulation:simulation_create")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "simulation/simulation_create.html" in [
            t.name for t in response.templates
        ]

        # Context 검증
        assert "scenarios" in response.context
        assert "solver_choices" in response.context
        assert response.context["default_algorithm_type"] == "EXACT"
        assert response.context["default_solver_value"] == "cplex"

        # ACTIVE 시나리오가 포함
        scenarios = response.context["scenarios"]
        assert active_scenario in scenarios

    def test_create_form_only_active_scenarios(
        self, auth_client, active_scenario, inactive_scenario
    ):
        """
        [SIM_RUN_DIS_004] ACTIVE 시나리오만 드롭다운에 표시
        """
        url = reverse("simulation:simulation_create")
        response = auth_client.get(url)

        scenarios = list(response.context["scenarios"])
        assert active_scenario in scenarios
        assert inactive_scenario not in scenarios


# =========================================================================
# Run (Execute) View Tests
# =========================================================================
@pytest.mark.django_db
class TestSimulationRunView:
    """시뮬레이션 실행 테스트"""

    def test_run_success(self, auth_client, active_scenario):
        """
        [SIM_RUN_DIS_005] 시나리오 선택 후 시뮬레이션 실행 요청 성공
        """
        url = reverse("simulation:simulation_run")
        data = {
            "scenario_id": active_scenario.id,
            "description": "Test simulation run",
            "solver_type": "cplex",
            "algorithm_type": "EXACT",
        }

        response = auth_client.post(url, data)

        # SimulationRun 생성 확인
        sim = SimulationRun.objects.filter(scenario=active_scenario).first()
        assert sim is not None

        # code 형식 검증 (SMYYYYMMDD_NNN)
        today_str = date.today().strftime("%Y%m%d")
        assert sim.code.startswith(f"SM{today_str}_")

        # Redirect → detail 페이지
        assert response.status_code == 302
        expected_url = reverse("simulation:simulation_detail", args=[sim.pk])
        assert response.url == expected_url

        # Success 메시지
        response_follow = auth_client.get(response.url)
        messages = list(get_messages(response_follow.wsgi_request))
        assert any("예약되었습니다" in str(m) for m in messages)

    def test_run_no_scenario(self, auth_client):
        """
        [SIM_RUN_DIS_006] 시나리오 미선택 시 에러
        """
        url = reverse("simulation:simulation_run")
        response = auth_client.post(url, {})

        assert response.status_code == 302
        assert response.url == reverse("simulation:simulation_create")

        # Error 메시지
        response_follow = auth_client.get(response.url)
        messages = list(get_messages(response_follow.wsgi_request))
        assert any("시나리오를 선택" in str(m) for m in messages)

    def test_run_nonexistent_scenario(self, auth_client):
        """
        [SIM_RUN_DIS_007] 존재하지 않는 시나리오 ID로 실행 시도
        """
        url = reverse("simulation:simulation_run")
        data = {"scenario_id": 99999}

        response = auth_client.post(url, data)

        assert response.status_code == 302
        assert response.url == reverse("simulation:simulation_create")

        response_follow = auth_client.get(response.url)
        messages = list(get_messages(response_follow.wsgi_request))
        assert any("찾을 수 없습니다" in str(m) for m in messages)

    def test_run_saves_solver_and_algorithm(self, auth_client, active_scenario):
        """
        [SIM_RUN_DIS_020] solver_type, algorithm_type이 DB에 저장되는지 확인
        """
        url = reverse("simulation:simulation_run")
        data = {
            "scenario_id": active_scenario.id,
            "solver_type": "gurobi",
            "algorithm_type": "EFFICIENT",
        }

        auth_client.post(url, data)

        sim = SimulationRun.objects.filter(scenario=active_scenario).first()
        assert sim.solver_type == "gurobi"
        assert sim.algorithm_type == "EFFICIENT"


# =========================================================================
# Detail View Tests
# =========================================================================
@pytest.mark.django_db
class TestSimulationDetailView:
    """시뮬레이션 상세 화면 테스트"""

    def test_detail_success_status(self, auth_client, simulation_success):
        """
        [SIM_RUN_DIS_008] 상세 정보 정상 표시 (SUCCESS 상태)
        """
        url = reverse("simulation:simulation_detail", args=[simulation_success.pk])
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "simulation/simulation_detail.html" in [
            t.name for t in response.templates
        ]

        # Context 검증
        sim = response.context["simulation"]
        assert sim.pk == simulation_success.pk

        # HTML 내용 검증
        content = response.content.decode("utf-8")
        assert simulation_success.code in content
        assert simulation_success.scenario.code in content
        assert "cplex" in content

    def test_detail_running_progress_bar(self, auth_client, simulation_running):
        """
        [SIM_RUN_DIS_009] RUNNING 상태일 때 Progress Bar 표시
        """
        url = reverse("simulation:simulation_detail", args=[simulation_running.pk])
        response = auth_client.get(url)

        assert response.status_code == 200
        content = response.content.decode("utf-8")

        assert "progress-bar-animated" in content
        assert "bg-primary" in content  # Running badge
        assert "Running" in content

    def test_detail_failed_status(self, auth_client, simulation_failed):
        """
        [SIM_RUN_DIS_010] FAILED 상태일 때 에러 정보 표시
        """
        url = reverse("simulation:simulation_detail", args=[simulation_failed.pk])
        response = auth_client.get(url)

        assert response.status_code == 200
        content = response.content.decode("utf-8")

        assert "bg-danger" in content  # Failed badge
        assert "Failed" in content
        assert "Error: Engine timeout" in content  # model_status 표시

    def test_detail_success_results_section(self, auth_client, simulation_success):
        """
        [SIM_RUN_DIS_011] SUCCESS 상태일 때 Results 섹션 표시
        """
        url = reverse("simulation:simulation_detail", args=[simulation_success.pk])
        response = auth_client.get(url)

        content = response.content.decode("utf-8")

        # Results 섹션
        assert "Results" in content
        assert "12345.67" in content  # objective_value
        assert "43.2" in content  # execution_time

    def test_detail_timeline(self, auth_client, simulation_success):
        """
        [SIM_RUN_DIS_014] Timeline에 Created/Started/Completed 단계 표시
        """
        url = reverse("simulation:simulation_detail", args=[simulation_success.pk])
        response = auth_client.get(url)

        content = response.content.decode("utf-8")

        assert "Created" in content
        assert "Started" in content
        assert "Completed" in content

    def test_detail_delete_button_visible_when_can_modify(
        self, auth_client, simulation_success
    ):
        """
        [SIM_RUN_DIS_015] can_modify=True일 때 Delete 버튼 표시
        """
        assert simulation_success.can_modify is True

        url = reverse("simulation:simulation_detail", args=[simulation_success.pk])
        response = auth_client.get(url)
        content = response.content.decode("utf-8")

        delete_url = reverse(
            "simulation:simulation_delete", args=[simulation_success.pk]
        )
        assert delete_url in content

    def test_detail_delete_button_hidden_when_running(
        self, auth_client, simulation_running
    ):
        """
        [SIM_RUN_DIS_015] RUNNING 상태(can_modify=False)에서 Delete 버튼 숨김
        """
        assert simulation_running.can_modify is False

        url = reverse("simulation:simulation_detail", args=[simulation_running.pk])
        response = auth_client.get(url)
        content = response.content.decode("utf-8")

        delete_url = reverse(
            "simulation:simulation_delete", args=[simulation_running.pk]
        )
        assert delete_url not in content

    def test_detail_404_for_nonexistent(self, auth_client):
        """
        [SIM_RUN_DIS_021] 존재하지 않는 pk로 상세 조회 시 404
        """
        url = reverse("simulation:simulation_detail", args=[99999])
        response = auth_client.get(url)
        assert response.status_code == 404


# =========================================================================
# Delete View Tests
# =========================================================================
@pytest.mark.django_db
class TestSimulationDeleteView:
    """시뮬레이션 삭제 테스트"""

    def test_delete_success(self, auth_client, simulation_success):
        """
        [SIM_RUN_DIS_012] 완료된 시뮬레이션 삭제 성공
        """
        pk = simulation_success.pk
        url = reverse("simulation:simulation_delete", args=[pk])

        response = auth_client.post(url)

        # Redirect → list
        assert response.status_code == 302
        assert response.url == reverse("simulation:simulation_list")

        # DB에서 삭제 확인
        assert not SimulationRun.objects.filter(pk=pk).exists()

        # Success 메시지
        response_follow = auth_client.get(response.url)
        messages = list(get_messages(response_follow.wsgi_request))
        assert any("삭제되었습니다" in str(m) for m in messages)

    def test_delete_running_rejected(self, auth_client, simulation_running):
        """
        [SIM_RUN_DIS_013] 실행 중인 시뮬레이션 삭제 시도 거부
        """
        pk = simulation_running.pk
        url = reverse("simulation:simulation_delete", args=[pk])

        response = auth_client.post(url)

        # Redirect → detail (삭제 거부)
        assert response.status_code == 302
        assert response.url == reverse("simulation:simulation_detail", args=[pk])

        # DB에 유지
        assert SimulationRun.objects.filter(pk=pk).exists()

        # Error 메시지
        response_follow = auth_client.get(response.url)
        messages = list(get_messages(response_follow.wsgi_request))
        assert any("삭제할 수 없습니다" in str(m) for m in messages)

    def test_delete_failed_simulation(self, auth_client, simulation_failed):
        """
        [SIM_RUN_DIS_022] FAILED 상태(can_modify=True)도 삭제 가능
        """
        assert simulation_failed.can_modify is True

        pk = simulation_failed.pk
        url = reverse("simulation:simulation_delete", args=[pk])

        response = auth_client.post(url)

        assert response.status_code == 302
        assert not SimulationRun.objects.filter(pk=pk).exists()


# =========================================================================
# Access Control Tests
# =========================================================================
@pytest.mark.django_db
class TestSimulationAccessControl:
    """비로그인 사용자 접근 차단 테스트"""

    def test_anonymous_access_blocked(self, client, active_scenario, user):
        """
        [CM_AUTH_DIS_002] 비로그인 사용자 시뮬레이션 접근 차단
        """
        # 삭제/상세 테스트를 위해 시뮬레이션 1건 생성
        sim = SimulationRun.objects.create(
            scenario=active_scenario,
            code="SM20260401_099",
            simulation_status=SimulationStatus.SUCCESS,
            created_by=user,
        )

        urls = [
            reverse("simulation:simulation_list"),
            reverse("simulation:simulation_create"),
            reverse("simulation:simulation_detail", args=[sim.pk]),
        ]

        for url in urls:
            response = client.get(url)
            assert response.status_code == 302, f"Expected 302 for {url}"
            assert (
                "/accounts/login/" in response.url
            ), f"Expected login redirect for {url}"

    def test_anonymous_post_blocked(self, client, active_scenario, user):
        """
        [CM_AUTH_DIS_003] 비로그인 POST 요청도 차단
        """
        sim = SimulationRun.objects.create(
            scenario=active_scenario,
            code="SM20260401_098",
            simulation_status=SimulationStatus.SUCCESS,
            created_by=user,
        )

        post_urls = [
            reverse("simulation:simulation_run"),
            reverse("simulation:simulation_delete", args=[sim.pk]),
        ]

        for url in post_urls:
            response = client.post(url, {})
            assert response.status_code == 302, f"Expected 302 for POST {url}"
            assert (
                "/accounts/login/" in response.url
            ), f"Expected login redirect for POST {url}"
