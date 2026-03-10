"""
init_master_data 커맨드 테스트
Test Scenarios: CMD_INIT_MASTER_001~004
"""

import pytest

from django.core.management import call_command
from django.test import override_settings

from input_data.models import (
    BaseVesselInfo,
    MasterLane,
    MasterPort,
    MasterTrade,
    ScenarioInfo,
    VesselInfo,
)


@pytest.fixture
def temp_master_data_dir(tmp_path):
    """
    테스트용 임시 CSV 디렉토리 구조 생성.
    master_trade, master_port, master_lane CSV 파일을 포함.
    """
    target_dir = tmp_path / "input_data" / "data" / "base_data"
    target_dir.mkdir(parents=True)

    # master_trade.csv
    trade_csv = target_dir / "master_trade.csv"
    trade_csv.write_text(
        "trade_code,trade_name,from_continent_code,to_continent_code\n"
        "TST,Test Trade,AS,EU\n",
        encoding="utf-8-sig",
    )

    # master_port.csv
    port_csv = target_dir / "master_port.csv"
    port_csv.write_text(
        "port_code,port_name,continent_code,country_code\n" "TSTPT,Test Port,AS,KR\n",
        encoding="utf-8-sig",
    )

    # master_lane.csv
    lane_csv = target_dir / "master_lane.csv"
    lane_csv.write_text(
        "lane_code,lane_name,vessel_service_type_code,effective_from_date,"
        "effective_to_date,feeder_division_code\n"
        "TSTLN,Test Lane,,,,\n",
        encoding="utf-8-sig",
    )

    return tmp_path, target_dir


@pytest.mark.django_db
class TestInitMasterData:

    def test_master_data_prompt_abort(self, temp_master_data_dir, capsys, monkeypatch):
        """
        [CMD_INIT_MASTER_001] 확인 프롬프트에 'no' 입력 시 중단
        """
        base_dir, _ = temp_master_data_dir

        # 기존 master 데이터 수 기록
        trade_count_before = MasterTrade.objects.count()

        # 'no' 입력 시뮬레이션
        monkeypatch.setattr("builtins.input", lambda _: "no")

        with override_settings(BASE_DIR=base_dir):
            call_command("init_master_data")

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "Aborted" in captured.out

        # 데이터 변경 없음
        assert MasterTrade.objects.count() == trade_count_before

    def test_master_data_force(self, temp_master_data_dir, capsys):
        """
        [CMD_INIT_MASTER_002] --force 옵션으로 확인 스킵 후 정상 실행
        """
        base_dir, _ = temp_master_data_dir

        with override_settings(BASE_DIR=base_dir):
            call_command("init_master_data", "--force")

        captured = capsys.readouterr()
        assert "[init_master_data]" in captured.out
        assert "Done" in captured.out

        # CSV에서 로드한 데이터 확인
        assert MasterTrade.objects.filter(trade_code="TST").exists()
        assert MasterPort.objects.filter(port_code="TSTPT").exists()
        assert MasterLane.objects.filter(lane_code="TSTLN").exists()

    def test_master_data_delete_order(self, temp_master_data_dir, capsys, user):
        """
        [CMD_INIT_MASTER_003] PROTECT FK 의존성 순서 준수
        sce_ -> base_ -> master_ 순서로 삭제 시 ProtectedError 미발생
        """
        base_dir, data_dir = temp_master_data_dir

        # 사전 데이터: ScenarioInfo + VesselInfo(sce_) + BaseVesselInfo(base_)
        scenario = ScenarioInfo.objects.create(
            code="SC_DEL_TEST",
            description="Delete order test",
            scenario_type="WHAT_IF",
            status="ACTIVE",
            created_by=user,
            updated_by=user,
        )
        VesselInfo.objects.create(
            scenario=scenario,
            vessel_code="VDEL",
            vessel_name="Delete Test",
            own_yn="O",
            created_by=user,
            updated_by=user,
        )
        BaseVesselInfo.objects.create(
            vessel_code="BVDEL", vessel_name="Base Delete", own_yn="O"
        )

        # ProtectedError가 발생하지 않아야 함
        with override_settings(BASE_DIR=base_dir):
            call_command("init_master_data", "--force")

        # 모두 삭제됨
        assert ScenarioInfo.objects.count() == 0
        assert VesselInfo.objects.count() == 0
        assert BaseVesselInfo.objects.count() == 0

    def test_master_then_base_reload(self, temp_master_data_dir, capsys):
        """
        [CMD_INIT_MASTER_004] master_ 리로드 후 init_base_data로 base_ 리로드 연계
        """
        base_dir, data_dir = temp_master_data_dir

        # base_vessel_info.csv 추가 (init_base_data용)
        base_csv = data_dir / "base_vessel_info.csv"
        base_csv.write_text(
            "vessel_code,vessel_name,own_yn\n" "V_RELOAD,Reload Test,O\n",
            encoding="utf-8-sig",
        )

        # Step 1: init_master_data
        with override_settings(BASE_DIR=base_dir):
            call_command("init_master_data", "--force")

        assert MasterTrade.objects.filter(trade_code="TST").exists()

        # Step 2: init_base_data
        with override_settings(BASE_DIR=base_dir):
            call_command("init_base_data")

        assert BaseVesselInfo.objects.filter(vessel_code="V_RELOAD").exists()


@pytest.mark.django_db
class TestInitBaseDataSeparation:

    def test_base_data_does_not_delete_master_or_sce(self, temp_master_data_dir, user):
        """
        [CMD_INIT_BASE_001] init_base_data는 master_/sce_ 영향 없음
        """
        base_dir, data_dir = temp_master_data_dir

        # 사전 데이터
        ScenarioInfo.objects.create(
            code="SC_SAFE",
            description="Should survive",
            scenario_type="WHAT_IF",
            status="ACTIVE",
            created_by=user,
            updated_by=user,
        )
        master_count_before = MasterTrade.objects.count()

        # base_vessel_info.csv 추가
        base_csv = data_dir / "base_vessel_info.csv"
        base_csv.write_text(
            "vessel_code,vessel_name,own_yn\n" "V_SAFE,Safe Test,O\n",
            encoding="utf-8-sig",
        )

        with override_settings(BASE_DIR=base_dir):
            call_command("init_base_data")

        # master_, sce_ 데이터 그대로
        assert MasterTrade.objects.count() == master_count_before
        assert ScenarioInfo.objects.filter(code="SC_SAFE").exists()
        # base_ 데이터 리로드됨
        assert BaseVesselInfo.objects.filter(vessel_code="V_SAFE").exists()

    def test_base_data_loader_shared_logic(self, temp_master_data_dir):
        """
        [CMD_INIT_BASE_002] 공통 로직(load_data/clean_row) 정상 동작
        """
        base_dir, data_dir = temp_master_data_dir

        base_csv = data_dir / "base_vessel_info.csv"
        base_csv.write_text(
            "vessel_code,vessel_name,own_yn,delivery_date\n"
            "V_LD1,Loader Test 1,O,2026/01/01\n"
            "V_LD2,Loader Test 2,C,2026/06/15\n",
            encoding="utf-8-sig",
        )

        with override_settings(BASE_DIR=base_dir):
            call_command("init_base_data")

        assert BaseVesselInfo.objects.count() == 2
        obj1 = BaseVesselInfo.objects.get(vessel_code="V_LD1")
        assert obj1.delivery_date.year == 2026
        assert obj1.delivery_date.month == 1
        assert obj1.delivery_date.day == 1
